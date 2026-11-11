# Changelog

## 0.7.6 - 2026-11-08

- During screen sharing, use the header's active microphone chips when no participant tile signals speech. Ignore the broadcaster label.
- Recognize a visible screen share as evidence of an active meeting even when all participant tiles are hidden.

## 0.7.5 - 2026-11-08

- Keep an observed room's journal alive when sharing or full-screen viewing hides participant tiles. Record the gap with no speaker names.
- Require an existing matching tab, page and room journal for uncertain observations; a room URL before joining still cannot start a journal.
- Stop treating prolonged tile disappearance as proof that a meeting ended. Add screen-sharing regressions.

## 0.7.4 - 2026-11-08

- Read room names from each meeting tab's `/event/<room>` URL, including simultaneous meetings. Decode URL escapes and never use the generic browser tab title as a room name.
- Require both a room URL and a visible participant tile before starting a meeting journal. Pages without a room name in the URL do not start one.
- Add regression checks for separate room names, unjoined room pages and hidden tiles.
- Do not display a previous room's cached journal when the same tab navigates to another room.

## 0.7.3 - 2026-10-27

- Validation: standalone suite completed 36 Python tests (one skipped) and 22 JavaScript tests; 11 optional synthetic recorder integration tests passed. No live audio or extension reload was performed.

- Verify installed host identity against the independently configured actual extension ID; reject changes to installed configuration during tests.
- Include toolbar regression checks and retain configurable optional recorder integration checks.
- Reconcile portable documentation; preserve machine setup/repair history in ignored local notes.

## 0.7.2 - 2026-10-23

- Report profile verification without reverting the saved-speech activity indicator.

## 0.7.1 - 2026-10-22

- Enlarge toolbar artwork with 16/20/24/32/48-pixel variants.

## 0.7.0 - 2026-10-22

- Show green for freshly acknowledged saved speech; reset on silence, stale acknowledgements, disabled journaling and connection errors.
- Keep audio capture independent of the toolbar indicator; no additional permissions.

## 0.6.1 - 2026-10-22

- Publish the current working source directly, with machine settings and operational data excluded from Git.
- Provide a portable native-host installer with explicit paths/extension ID, ignored local settings, dry-run, external runtime and optional recorder configuration update. Retain the earlier --extension-id, --data-dir and --sessions options.
- Deploy lifecycle support with the native host and check the standalone product without requiring a particular vault or installed recorder.

## 0.6.0 - 2026-10-21

- Durable per-tab lifecycle events for tab/window closure, navigation away and observed meeting exit, including reconnects.
- Eight-second participant-UI debounce for observed exit; stale data and transient missing DOM do not establish meeting end. Live Dion validation remains necessary.
- Integration with the recorder preserves audio and stop reasons; the extension still captures no audio and requests no additional permissions.

## 0.5.1 - 2026-10-17

- Initial public package with a portable installer and synthetic checks.
