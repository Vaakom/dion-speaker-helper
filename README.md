# DION Speaker Helper
Chrome Manifest V3 extension that saves observed DION speaker names to local JSONL journals. It records no audio and performs no voice identification.

## Install (Windows, Chrome, Python 3.12+)
1. Download a release and extract it into a permanent folder.
2. Open `chrome://extensions`, enable Developer mode and choose **Load unpacked** → `extension`.
3. Copy the extension ID shown by Chrome.
4. Run `python install.py --extension-id YOUR_EXTENSION_ID`.
5. Reload the extension, open a DION meeting and inspect its popup.
The installer registers a Native Messaging host for the current Windows user. Do not move the folder afterwards without rerunning installation.
The registration uses the host name `local.dion_speaker_helper`; on a computer with an existing installation this replaces that host registration. Do not run it alongside a working installation without reviewing paths first.

Default journals: `%LOCALAPPDATA%/DionSpeakerHelper/journals/YYYY-MM-DD/document-id/`.
Use `--data-dir PATH` to choose another location. Configure the secretary's `DION_JOURNALS_DIR` to the same journals directory if changed.

## Status
The popup shows the selected tab's journal, last saved event, speaker indicators, and **Copy path**.
No acknowledgement for more than five seconds means stale data. A closed meeting retains its journal path.
The observer samples about every 500 ms; background-tab throttling, frozen tabs, sleep and DION changes can create gaps.

## Integration
Use [DION Secretary](https://github.com/Vaakom/agent-skills/tree/main/skills/dion-secretary) to import the segment overlapping a recording. Simultaneous meetings remain separate; ambiguous selection requires explicit choice.
Names reflect DION's UI indicators, not verified ground truth. Hidden overlap and UI delays can remain undetected.

## Tests
`python -m unittest test_helper test_browser_names test_auto_journals`
`node --test test_content.cjs test_auto_background.cjs test_status.cjs`
CI uses synthetic fixtures, without real meeting data.
Version 0.5.1: portable public installer; local 0.5.0 behavior retained.
See [PRIVACY.md](PRIVACY.md), [CHANGELOG.md](CHANGELOG.md), and the MIT license.

Русский: расширение сохраняет журнал имён локально. Настройка требует загрузить папку extension в Chrome и зарегистрировать локальный помощник командой выше.
