# Troubleshooting and status reporting

## Failure: GitHub API / release resolution

- `HTTP 403` or `HTTP 429`: GitHub rate limit or token issue. Do not fall back to downloading the latest main branch or an unverified mirror. Retry a later manual run or inspect repository Actions permissions.
- `No stable desktop release found`: no suitable official numbered desktop release in the inspected recent pages. Supply a known stable version explicitly.
- `No vendor/GitHub SHA-256 digest`: the upstream source asset lacks verified hash metadata. This is intentionally a hard error; do not change it into a warning.
- `Release already exists`: duplicate-run guard. If code changed, commit a new builder revision to get a different builder commit prefix in the release tag. Never delete unrelated releases to make room.

## Failure: official archive extraction

- `Could not locate uniquely identifiable x64 Bitwarden.exe`: the upstream portable EXE/NSIS internal layout changed or the asset is malformed. Capture `7z l` output from the verified release and update `scripts/stage.py` only after examining the actual new structure.
- `Missing Electron application resources`: do not ship a ZIP that has only an EXE and no resources. Inspect for `resources/app.asar`, helper executables, locales, DLLs and codecs.
- `desktop_proxy.exe missing`: new upstream browser helper may have moved or changed its packaging. Audit new source and modify the whitelist/test only with evidence.
- `7-Zip failed`: check 7-Zip install, disk capacity and actual `7z x` exit code. No interactive run should be needed.
- `Authenticode status not valid`: launcher is unsigned by design; upstream files should not be represented as signed unless the actual signature check passes. The workflow logs the official application's signature status rather than silently asserting success.

## Failure: launcher compile or Windows runtime

- `NativeAOT PE compilation failed`: check `.NET SDK`, Visual Studio C++ build tooling and NativeAOT compiler diagnostics. Do not replace the compiled launcher with a CMD stub.
- Windows shows an unsigned launcher warning: expected for a community-generated EXE without a paid code-signing certificate. Do not turn off antivirus or SmartScreen. Review the transparent launcher source and build provenance.
- Bitwarden starts but loses settings: confirm `Data/Profile` is writable, not a symlink/junction and is backed up; verify actual source version uses `BITWARDEN_APPDATA_DIR`. Do not delete a production vault profile to diagnose.
- A different PC requires sign-in: Windows credential storage may be machine-bound. Do not disable DPAPI/Windows Hello or weaken vault encryption; log in normally.
- Second launch shows an error: only one launch from the same folder is allowed. Quit via tray before upgrading/ejecting USB.
- Browser integration intermittently fails: `com.8bit.bitwarden` can collide with an installed Bitwarden instance. Verify source-evidenced HKCU keys and `Data/Profile/browsers` and run acceptance tests; don't broadly delete installed browser configurations.
- Persistent stale shortcut/notification caches: source ownership has not been proved; preserve ambiguous host entries and record findings for a targeted future fix. Do not recursively clean the Start Menu, Roaming, LocalAppData or registry.

## b1r1 installer path failure fixed in b1r2

The November 9 b1r1 run reached the pinned installer action, but its `Test-RelativeEXE` rejected `App/Bitwarden/Bitwarden.exe`. Use the fixed form `running-exe: 'App\Bitwarden\Bitwarden.exe'` in **both** workflows. This is a parameter-format requirement of the pinned shared action, not a missing file or Bitwarden fault. Do not edit the pinned action or disable the running-process check. The b1r2 regression suite verifies both paths. A previously published b1r1 ZIP can be reused by the packaging-only workflow; see README.

## Failure: installer or release

- Installer failed but ZIP succeeded: the run correctly marks **partial failure**. The publisher can release the validated ZIP; check the shared Package Builder step and use optional packaging-only workflow to build a later installer without rebuilding Bitwarden.
- Installer cannot upgrade: close app and tray first, inspect `.__UPB_Stage` and `.__UPB_Backup`; keep backups rather than deleting the folder. Restore from a known-good matching version and Data backup.
- The PortableApps Platform does not show the app: verify `BitwardenPortable/App/AppInfo/appinfo.ini` and refresh Platform Menu.
- Publisher refuses assets: confirm `.zip` or `.paf.exe` extension, valid archive/PE, below the shared publisher's size limit, and release tag uniqueness.
- Public distribution review: the selected asset deliberately excludes `commercial-` prefixed builds, but confirm licensing and trademark rules for your intended redistribution. Upstream source includes distinct licenses for its commercial modules; do not swap in the commercial executable.

## Validation labels

- **SOURCE-INSPECTED:** Upstream file/line or shared action definition was reviewed.
- **STATIC-VALIDATED:** Automated syntax, layout, provenance, signature/header or archive tests passed.
- **WINDOWS-COMPILED:** Genuine compiler output produced on the Windows runner.
- **AUTOMATED-RUNTIME-TESTED:** A specific executable exercise passed under an actual Windows process. Launcher `--self-test` is not Bitwarden GUI validation.
- **MANUAL-WINDOWS-TESTED:** A human ran acceptance steps and recorded evidence.
- **USER-CONFIRMED:** User independently reports a functioning test.
- **NOT YET VERIFIED:** No corresponding test result exists.
- **FAILED/BLOCKED:** A step could not be completed and its failure was propagated.

Do not upgrade these labels merely because the GitHub Actions job is green.
