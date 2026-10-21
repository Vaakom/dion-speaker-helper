# Changelog

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
