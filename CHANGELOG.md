# Changelog

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
