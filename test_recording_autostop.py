import datetime
import os
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
if not (skill / 'scripts').is_dir():
    raise unittest.SkipTest('Set DION_SECRETARY_SKILL for optional recorder integration checks')
sys.path.insert(0, str(skill / 'scripts'))
from meeting_autostop import MeetingMonitor, select_binding, chrome_windows_open
from native_host import Journal
import secretary


class TestDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        # Windows may briefly report a directory nonempty after its entries were deleted.
        # Retry only cleanup of this fixture's own directory, never a user session.
        for attempt in range(10):
            try:
                return super().cleanup()
            except OSError as exc:
                if getattr(exc, 'winerror', None) != 145 or attempt == 9:
                    raise
                time.sleep(.1)


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
            with self.subTest(reason=reason), TestDirectory() as folder:
                j, binding = self.fixture(folder)
                j = Journal(j.config)  # No in-memory streams survive reconnect.
                j.handle(self.sample(type='auto_end', reason=reason))
                monitor = MeetingMonitor(binding, browser_probe=lambda: True)
                self.assertEqual(monitor.poll(0), reason)

    def test_browser_close_works_without_extension_end_event(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            state = [True]
            monitor = MeetingMonitor(binding, browser_probe=lambda: state[0])
            self.assertIsNone(monitor.poll(0))
            state[0] = False
            self.assertIsNone(monitor.poll(1))
            self.assertIsNone(monitor.poll(2))
            self.assertEqual(monitor.poll(3), 'browser_closed')

    def test_browser_close_without_journal_and_unknown_probe_do_not_fabricate_close(self):
        state = [True]
        monitor = MeetingMonitor(None, browser_probe=lambda: state[0])
        self.assertIsNone(monitor.poll(0))
        state[0] = None
        self.assertIsNone(monitor.poll(1))
        self.assertIsNone(monitor.poll(5))
        state[0] = False
        self.assertIsNone(monitor.poll(6))
        self.assertEqual(monitor.poll(8), 'browser_closed')

    def test_other_tab_stale_journal_and_unknown_browser_do_not_stop(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(tab=2, meeting_id='b'*64))
            j.handle(self.sample(tab=2, type='auto_end', reason='tab_closed'))
            monitor = MeetingMonitor(binding, browser_probe=lambda: None)
            self.assertIsNone(monitor.poll(100))
            Path(binding['lifecycle_path']).write_text('{incomplete', 'utf-8')
            self.assertIsNone(monitor.poll(1000))

    def test_window_close_is_not_masked_by_earlier_advisory(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            path = Path(binding['lifecycle_path'])
            state = json.loads(path.read_text('utf-8'))
            state['ends'] = [dict(meeting_id=binding['meeting_id'], ended_at=time.time(), reason=reason)
                             for reason in ('meeting_ended', 'browser_window_closed')]
            path.write_text(json.dumps(state), 'utf-8')
            self.assertEqual(MeetingMonitor(binding, browser_probe=lambda: True).poll(0),
                             'browser_window_closed')

    def test_legacy_end_and_stale_document_cannot_stop_new_document(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(type='auto_end'))
            monitor = MeetingMonitor(binding, browser_probe=lambda: True)
            self.assertIsNone(monitor.poll(0))
            j.handle(self.sample(page_id='document-67890'))
            j.handle(self.sample(type='auto_end', reason='tab_closed'))
            self.assertIsNone(monitor.poll(1))

    def test_end_not_lost_on_fast_rejoin_and_new_recording_ignores_old_end(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            j.handle(self.sample(type='auto_end', reason='meeting_ended'))
            result = j.handle(self.sample(page_id='document-67890'))
            self.assertEqual(MeetingMonitor(binding, browser_probe=lambda: True).poll(0), 'meeting_ended')
            new = select_binding({'meetings': [{'path': result['path']}]})
            self.assertIsNone(MeetingMonitor(new, browser_probe=lambda: True).poll(0))

    def test_ambiguous_or_legacy_binding_rejected_before_recording(self):
        with TestDirectory() as folder:
            j, binding = self.fixture(folder)
            result = j.handle(self.sample(lifecycle_version=0))
            candidates = {'meetings': [{'path': result['path']}]}
            with self.assertRaises(RuntimeError):
                select_binding(candidates)
            candidates['meetings'] *= 2
            with self.assertRaises(RuntimeError):
                select_binding(candidates)

    def test_start_without_journal_still_starts_worker_with_explicit_issue(self):
        with TestDirectory() as folder:
            root = Path(folder)
            def launch(command, **kwargs):
                session = Path(command[command.index('--session')+1])
                (session/'status.json').write_text(json.dumps({'state': 'recording'}), 'utf-8')
                return types.SimpleNamespace(pid=99999, poll=lambda: None)
            devices = [dict(index=1, loopback=True, default_output=True, default_mic=False),
                       dict(index=2, loopback=False, default_output=False, default_mic=True)]
            with patch.object(secretary, 'ACTIVE', root/'active.json'), patch.object(secretary, 'SESSIONS', root), \
                 patch.object(secretary, 'live_journals', return_value={'meetings': []}), \
                 patch.object(secretary, 'devices', return_value=devices), \
                 patch.object(secretary.subprocess, 'Popen', side_effect=launch), patch.object(secretary, 'output'):
                secretary.start(types.SimpleNamespace(title='Synthetic', mic=None, speaker=None, no_mic=False, meeting_journal=None))
            session = next(p for p in root.iterdir() if p.is_dir())
            metadata = json.loads((session/'meta.json').read_text('utf-8'))
            self.assertIsNone(metadata['meeting_watch_binding'])
            self.assertTrue(metadata['journal_issue'])

    def test_only_window_and_browser_close_stop_capture_and_notify_after_wav_finalization(self):
        # All audio is synthetic; no real device is opened.
        reasons = ('browser_closed', 'browser_window_closed', 'tab_closed', 'meeting_ended',
                   'meeting_page_closed', 'meeting_changed', 'notification_failure', 'completion_failure', 'monitor_failure', 'monitor_init_failure', None)
        for reason in reasons:
            with self.subTest(reason=reason), TestDirectory() as folder:
                session = Path(folder)
                binding = {'tab': 1} if reason is not None else None
                (session/'meta.json').write_text(json.dumps({'title': 'Synthetic', 'meeting_watch_binding': binding}), 'utf-8')
                frames, notifications, sleeps = [], [], []
                automatic = reason in ('browser_closed', 'browser_window_closed', 'completion_failure')
                class Stream:
                    def __init__(self, callback): self.callback = callback
                    def is_active(self):
                        self.callback(b'\0'*2048, 1024, None, 0)
                        frames.append(1024)
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
                def notify(path, message, **kwargs):
                    self.assertFalse((session/'stop.flag').exists())
                    state = json.loads((session/'status.json').read_text('utf-8'))
                    self.assertEqual(state['state'], 'stopped' if automatic else 'recording')
                    if automatic:
                        self.assertTrue(kwargs['prominent'])
                        self.assertIn('Synthetic', message)
                        self.assertIn('сохранена', message)
                        self.assertTrue(state['stop_reason']['automatic'])
                        for name in ('remote.wav', 'microphone.wav'):
                            with wave.open(str(session/name), 'rb') as saved:
                                self.assertEqual(saved.getnframes(), 1024)
                    notifications.append(message)
                    if reason in ('notification_failure', 'completion_failure'): raise OSError('Synthetic desktop failure')
                def manual_stop_after_four_iterations(*args):
                    self.assertFalse((session/'stop.flag').exists())
                    sleeps.append(True)
                    if len(sleeps) == 4: (session/'stop.flag').touch()
                with patch.dict(sys.modules, {'pyaudiowpatch': fake}), \
                     patch('meeting_autostop.MeetingMonitor') as monitor, \
                     patch('recording_reminders.RecordingReminders'), \
                     patch('recording_reminders.launch_notification', side_effect=notify), \
                     patch.object(secretary.time, 'sleep', side_effect=manual_stop_after_four_iterations):
                    if reason == 'monitor_init_failure':
                        monitor.side_effect = RuntimeError('Synthetic monitor init failure')
                    elif reason == 'monitor_failure':
                        monitor.return_value.poll.side_effect = RuntimeError('Synthetic monitor failure')
                    else:
                        detected = ('meeting_ended' if reason == 'notification_failure' else
                                    'browser_closed' if reason == 'completion_failure' else reason)
                        monitor.return_value.poll.side_effect = [None, detected, detected, detected]
                    secretary.record(types.SimpleNamespace(session=folder, speaker=10, mic=9, no_mic=False))
                self.assertEqual(len(sleeps), 1 if automatic else 4)
                self.assertEqual(len(frames), 2 if automatic else 8)
                self.assertEqual(len(notifications), 0 if reason in (None, 'monitor_failure', 'monitor_init_failure') else 1)
                state = json.loads((session/'status.json').read_text('utf-8'))
                self.assertEqual(state['stop_reason']['code'], ('browser_closed' if reason == 'completion_failure' else reason) if automatic else 'manual_stop')
                self.assertEqual(state['stop_reason']['automatic'], automatic)
                if reason == 'completion_failure':
                    self.assertEqual(json.loads((session/'meeting-completion.json').read_text('utf-8'))['state'], 'error')
                for name in ('remote.wav', 'microphone.wav'):
                    with wave.open(str(session/name), 'rb') as stream:
                        self.assertEqual(stream.getnframes(), 1024 if automatic else 4096)


if __name__ == '__main__':
    unittest.main()
