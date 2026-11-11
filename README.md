# Dion Speaker Helper

Chrome extension and local Native Messaging host for Dion speaker journals. The extension records no audio and performs no voice identification. Each active meeting's room name comes from its own `/event/<room>` URL, including when several meeting tabs are open.

## Install

Windows, Chrome and Python 3.12+ are required. Clone this repository into a permanent source folder. Load its `extension` folder through **Load unpacked** at `chrome://extensions`, then copy the ID shown by Chrome.

```text
python -X utf8 -B install.py --extension-id YOUR_EXTENSION_ID --runtime ABSOLUTE_EXTERNAL_RUNTIME
```

The runtime must be outside the source checkout. If omitted, it defaults to `%LOCALAPPDATA%/DionSpeakerHelper/runtime`. It contains the installed native host, configuration and journals; it is never committed to Git. The source extension remains in the checkout, so do not move it without reloading it in Chrome and updating registration.

Use `--python`, `--sessions`, `--active-file` and `--secretary-config` to select an existing recorder environment and settings. The optional secretary config is updated with `journal_root` and the selected extension identity. The legacy `--data-dir` option still chooses a separate journal parent directory. `--dry-run` prints the plan without writing files or changing registration.

For a maintained local installation, copy `config.example.json` to ignored `config.local.json` and set this machine's paths and extension ID. Then `python -X utf8 -B install.py` uses those settings. Unused optional fields can be omitted. The installer registers `local.dion_speaker_helper` for the current Windows user and replaces any existing registration under that name. It does not install Chrome extensions, record audio, download models or change browser permissions.

## Journals and recording lifecycle

Journal entries contain observed speaker indicators, timestamps, room names from the URL and meeting identity hashes. Full meeting URLs and invitation parameters are not retained in plaintext. A room URL alone does not start a journal: a participant tile or the shared screen must also be visible. When the shared screen is visible and no tile signals speech, the extension reads active microphone chips in the upper-right header. The broadcaster label on the shared screen is never a speaker signal. If all meeting indicators disappear, the existing journal stays open with empty speaker observations. Gaps caused by throttling, frozen tabs, sleep or disconnected native messaging cannot be recovered later.

The popup shows selected-tab status and the last saved journal. Stale acknowledgements are not presented as a live connection. Observed names and indicators are not guaranteed ground truth.

Version 0.6 added durable per-tab lifecycle events for tab/window closure and navigation away. Missing participant tiles no longer signal meeting exit because screen sharing and full-screen viewing can hide them. If Dion returns to a waiting screen at the same URL, the extension may continue the journal with empty speaker observations until navigation or tab closure. The extension does not stop audio itself: the recorder consumes lifecycle signals, preserves both audio tracks and records its stop reason. This is separate from transcription.

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

Machine-local Dion settings: `%LOCALAPPDATA%/DionSecretary/config.json` and `%LOCALAPPDATA%/DionSpeakerHelper/config.json`. The helper runtime and new journals are under `%LOCALAPPDATA%/DionSpeakerHelper/runtime`. Legacy local config is a fallback only.
