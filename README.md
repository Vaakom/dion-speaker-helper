# Dion Speaker Helper

Chrome extension and local Native Messaging host for Dion speaker journals. The extension records no audio and performs no voice identification. Version 0.7.3 includes per-tab lifecycle signals for Dion Secretary's automatic recording stop.

## Install

Windows, Chrome and Python 3.12+ are required. Clone this repository into a permanent source folder. Load its `extension` folder through **Load unpacked** at `chrome://extensions`, then copy the ID shown by Chrome.

```text
python -X utf8 -B install.py --extension-id YOUR_EXTENSION_ID --runtime ABSOLUTE_EXTERNAL_RUNTIME
```

The runtime must be outside the source checkout. If omitted, it defaults to `%LOCALAPPDATA%/DionSpeakerHelper/runtime`. It contains the installed native host, configuration and journals; it is never committed to Git. The source extension remains in the checkout, so do not move it without reloading it in Chrome and updating registration.

Use `--python`, `--sessions`, `--active-file` and `--secretary-config` to select an existing recorder environment and settings. The optional secretary config is updated with `journal_root` and the selected extension identity. The legacy `--data-dir` option still chooses a separate journal parent directory. `--dry-run` prints the plan without writing files or changing registration.

For a maintained local installation, copy `config.example.json` to ignored `config.local.json` and set this machine's paths and extension ID. Then `python -X utf8 -B install.py` uses those settings. Unused optional fields can be omitted. The installer registers `local.dion_speaker_helper` for the current Windows user and replaces any existing registration under that name. It does not install Chrome extensions, record audio, download models or change browser permissions.

## Journals and recording lifecycle

Journal entries contain observed speaker indicators, timestamps and meeting identity hashes. Meeting URLs and invitation parameters are not retained in plaintext. Gaps caused by throttling, frozen tabs, sleep, disconnected native messaging or changed Dion selectors cannot be recovered later.

The popup shows selected-tab status and the last saved journal. Stale acknowledgements are not presented as a live connection. Observed names and indicators are not guaranteed ground truth.

Version 0.6 adds durable per-tab lifecycle events for tab/window closure, navigation away and observed meeting exit. Meeting-end detection uses an eight-second participant-UI debounce and depends on Dion selectors; silence or a transient missing DOM alone is not proof of meeting end. The extension does not stop audio itself: the recorder consumes the lifecycle signal, preserves both audio tracks and records its stop reason. This is separate from transcription.

Configure [Dion Secretary](https://github.com/Vaakom/agent-skills/tree/main/dion-secretary) with `journal_root` matching this host's journals directory. Simultaneous meetings remain separate; ambiguous selection requires an explicit choice.

## Checks

```text
python -X utf8 -B verify.py
```

Node.js must be on PATH, supplied with `--node`, or configured locally. Checks use synthetic fixtures and do not connect to accounts or capture sound. `--runtime PATH` also tests an existing native launcher with a harmless unbind message. CI checks the standalone product without a local runtime or secretary checkout.

The optional `test_recording_autostop.py` checks recorder integration with mocked audio; it needs the secretary source and NumPy. Set `DION_SECRETARY_SKILL` to that skill directory when it is not in the sibling vault layout. Real Dion exit detection still needs live validation after reloading an updated extension.

See [INSTALL.md](INSTALL.md), [PRIVACY.md](PRIVACY.md), [CHANGELOG.md](CHANGELOG.md) and the MIT [license](LICENSE).

## Toolbar status

Green indicates a fresh speaking observation acknowledged as saved by the native host. Silence, stale acknowledgements, disabled journaling and disconnection return it to grey. This is journal status, not audio recording or verified voice identity. Reload the unpacked extension after updating its code.

Secretary 2.1+ stops healthy audio on bound meeting-window closure or whole-browser closure; other lifecycle signals remain advisory. Missing journals do not block audio capture. Recording and processing remain explicit requests.
