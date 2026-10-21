# Installation details

Load the checked-out `extension` directory into Chrome and use that installation's actual ID when registering the host. Do not assume another computer's ID. Local Chrome storage may be reset if the extension is removed; reloading the existing installation is preferable for an update.

Keep runtime outside the source tree. Native configuration restricts the accepted origin to the chosen extension. Moving runtime requires updating the Native Messaging registration and the recorder's journal lookup. Use the installer with the selected paths; it does not move or delete existing journals. Preserve and copy existing data deliberately before changing its location.

`DION_HELPER_RUNTIME` overrides the installer's default runtime. `DION_JOURNALS_ROOT` or `DION_HELPER_RUNTIME` can provide a discovery default for journal helpers; an explicit configured `journal_root` takes precedence in Dion Secretary.

The installed native host imports `lifecycle.py`; both files are deployed by the installer. No extra Node package is required for installation. Python and Chrome are existing prerequisites; Node.js is used only by the development test suite.

After registration, reload the Chrome extension and inspect its popup during a requested Dion session. Do not start recording merely as an installation check. No successful synthetic test proves real browser observation, device capture or semantic accuracy.
