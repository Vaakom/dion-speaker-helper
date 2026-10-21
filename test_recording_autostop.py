import os
import datetime
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import wave
import numpy  # Load before patch.dict(sys.modules), which restores the module cache.

skill = Path(os.environ.get('DION_SECRETARY_SKILL', str(Path(__file__).resolve().parents[2] / 'skills/dion-secretary')))
sys.path.insert(0, str(skill / 'scripts'))
from meeting_autostop import MeetingMonitor, select_binding, chrome_windows_open
from native_host import Journal
import secretary


class AutoStopTests(unittest.TestCase):
    def test_native_browser_probe_available(self):
        # Read-only: never closes windows or captures audio.
        observed = chrome_windows_open()
        self.assertIsInstance(observed, bool)
        print(f'Chrome desktop window probe: {observed}')

    def sample(self, **changes):
        return dict(type='auto_sample', client='client-12345', page_id='document-12345', tab=1,
                    meeting_id='a'*64, title='Synthetic', at=time.time()*1000,
                    state='observing', speakers=[], profile='{}', calibrated=True,
                    lifecycle_version=1) | changes

    def fixture(self, folder):
        journal = Journal({'journals': str(Path(folder)/'journals')})
        result = journal.handle(self.sample())
        binding = select_binding({'meetings': [{'path': result['path']}]})
        return journal, binding

    def test_explicit_tab_window_and_meeting_end_after_native_host_restart(self):
        for reason in ('tab_closed', 'browser_window_closed', 'meeting_ended'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                j, binding = self.fixture(folder)
                j = Journal(j.config)  # No in-memory streams survive reconnect.
                j.handle(self.sample(type='auto_end', reason=reason))
                monitor = MeetingMonitor(binding, browser_probe=lambda: True)
                self.assertEqual(monitor.poll(0), reason)

    def test_browser_close_works_without_extension_end_event(self):
        with tempfile.TemporaryDirectory() as folder:
            j, binding = self.fixture(folder)
            state = [True]
            monitor = MeetingMonitor(binding, browser_probe=lambda: state[0])
            self.assertIsNone(monitor.poll(0))
            state[0] = False
            self.assertIsNone(monitor.poll(1))
            self.assertIsNone(monitor.poll(2))
            self.assertEqual(monitor.poll(3), 'browser_closed')

    def test_other_tab_stale_journal_and_unknown_browser_do_not_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(tab=2, meeting_id='b'*64))
            j.handle(self.sample(tab=2, type='auto_end', reason='tab_closed'))
            monitor = MeetingMonitor(binding, browser_probe=lambda: None)
            self.assertIsNone(monitor.poll(100))
            Path(binding['lifecycle_path']).write_text('{incomplete', 'utf-8')
            self.assertIsNone(monitor.poll(1000))

    def test_legacy_end_and_stale_document_cannot_stop_new_document(self):
        with tempfile.TemporaryDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(type='auto_end'))
            monitor = MeetingMonitor(binding, browser_probe=lambda: True)
            self.assertIsNone(monitor.poll(0))
            j.handle(self.sample(page_id='document-67890'))
            j.handle(self.sample(type='auto_end', reason='tab_closed'))
            self.assertIsNone(monitor.poll(1))

    def test_end_not_lost_on_fast_rejoin_and_new_recording_ignores_old_end(self):
        with tempfile.TemporaryDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(type='auto_end', reason='meeting_ended'))
            result = j.handle(self.sample(page_id='document-67890'))
            self.assertEqual(MeetingMonitor(binding, browser_probe=lambda: True).poll(0), 'meeting_ended')
            new = select_binding({'meetings': [{'path': result['path']}]})
            self.assertIsNone(MeetingMonitor(new, browser_probe=lambda: True).poll(0))

    def test_ambiguous_or_legacy_binding_rejected_before_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            j, binding = self.fixture(folder)
            result = j.handle(self.sample(lifecycle_version=0))
            candidates = {'meetings': [{'path': result['path']}]}
            with self.assertRaises(RuntimeError):
                select_binding(candidates)
            candidates['meetings'] *= 2
            with self.assertRaises(RuntimeError):
                select_binding(candidates)

    def test_record_finalizes_both_wavs_and_reason_before_notification(self):
        # No audio devices are opened: callbacks receive a generated PCM fixture.
        for reason in ('browser_closed', 'tab_closed', 'meeting_ended'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                session = Path(folder)
                (session/'meta.json').write_text(json.dumps({'title': 'Synthetic', 'auto_stop_binding': {'tab': 1}}), 'utf-8')
                class Stream:
                    def __init__(self, callback): self.callback = callback
                    def is_active(self):
                        self.callback(b'\0'*2048, 1024, None, 0)
                        return True
                    def stop_stream(self): pass
                    def close(self): pass
                class Audio:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def get_device_info_by_index(self, index):
                        return {'maxInputChannels': 1, 'defaultSampleRate': 8000}
                    def open(self, **kwargs): return Stream(kwargs['stream_callback'])
                fake = types.SimpleNamespace(PyAudio=Audio, paInt16=8, paContinue=0, paAbort=2)
                notifications = []
                def notify(path, message):
                    state = json.loads((session/'status.json').read_text('utf-8'))
                    self.assertEqual(state['state'], 'stopped')
                    self.assertEqual(state['stop_reason']['code'], reason)
                    for name in ('remote.wav', 'microphone.wav'):
                        with wave.open(str(session/name), 'rb') as w:
                            self.assertGreater(w.getnframes(), 0)
                    notifications.append(message)
                with patch.dict(sys.modules, {'pyaudiowpatch': fake}), \
                     patch('meeting_autostop.MeetingMonitor') as monitor, \
                     patch('recording_reminders.RecordingReminders'), \
                     patch('recording_reminders.launch_stop_notification', side_effect=notify), \
                     patch.object(secretary.time, 'sleep'):
                    monitor.return_value.poll.side_effect = [None, reason]
                    monitor.return_value.browser_seen = True
                    secretary.record(types.SimpleNamespace(session=folder, speaker=10, mic=9, no_mic=False))
                self.assertEqual(len(notifications), 1)
                self.assertTrue((session/'stop.flag').exists())


if __name__ == '__main__':
    unittest.main()
