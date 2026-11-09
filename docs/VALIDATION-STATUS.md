# Builder b1r1 validation status — 2026-11-09

This status applies to the **builder kit files** prepared in this environment, not to a finished Bitwarden PortableApps release.

| Stage | Evidence | Result |
|---|---|---|
| Upstream Bitwarden Desktop release and source audit | GitHub release/tag and release-tagged source configuration inspected | SOURCE-INSPECTED |
| Shared package builder interface and pinned v1.0.0 action | `action.yml`, release tag and immutable action commit inspected | SOURCE-INSPECTED |
| Shared release publisher interface and pinned v1.1.1 action | `action.yml`, release tag and immutable action commit inspected | SOURCE-INSPECTED |
| Python resolver/ZIP unit regression tests | `python -m unittest discover -s tests -p 'test_*.py' -v` | STATIC-VALIDATED: 7 tests |
| Python syntax | `python -m compileall -q scripts tests` | STATIC-VALIDATED |
| GitHub Actions YAML syntax | Parsed both workflow YAML files | STATIC-VALIDATED |
| Live GitHub release resolve/download with actual credentials | Must run in GitHub Actions | NOT YET VERIFIED |
| NativeAOT Windows x64 launcher compilation | Requires hosted Windows .NET + C++ toolchain | NOT YET VERIFIED |
| Extraction of actual vendor portable EXE and staged Bitwarden resources | Requires official asset download and Windows runner | NOT YET VERIFIED |
| Launcher with Bitwarden GUI, single-instance and tray lifetime | Requires interactive Windows session | NOT YET VERIFIED |
| Data persistence, empty directory recovery and cross-account relocation | Windows acceptance checklist included | NOT YET VERIFIED |
| ShellGuard recovery/installed-client browser coexistence | Windows acceptance checklist included | NOT YET VERIFIED |
| Native notifications, protocol activation and biometrics | Windows acceptance checklist included | NOT YET VERIFIED |
| Installer generation and static embedded-file verification | Must run the pinned shared builder in CI | NOT YET VERIFIED |
| Actual installer GUI install/reinstall/upgrade | Requires interactive Windows session | NOT YET VERIFIED |
| Shared publisher dry-run and live GitHub release | Requires new independent builder repo | NOT YET VERIFIED |

Do not claim that vault/profile portability, full ShellGuard cleanup, Bitwarden notifications, biometrics or installed-client coexistence passed until tested on Windows. A successful GitHub Actions run validates build and package stages, not desktop behaviour.

## Specific safety limitations

- The upstream installed application and portable build use the same native messaging host identity, so simultaneous browser integration is **not verified** and cannot be promised.
- Electron and Windows may create OS-managed shell/cache state that should not be removed by speculative broad cleanup.
- Windows Hello and OS-protected credentials may not be portable to another Windows account or device.
- An interrupted run with ambiguous HKCU changes is preserved for review under `Data/TraceGuard` instead of deleted.
- The official vendor's portable executable archive layout and helper files may change in newer releases; the builder is designed to fail closed, not silently omit functionality.
- This is a community package and is not signed/certified by PortableApps.com or Bitwarden Inc.
