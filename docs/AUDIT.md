# Bitwarden Desktop upstream audit — source inspected 2026-11-09

Selected upstream: `bitwarden/clients` (not the archived `bitwarden/desktop`). Baseline stable release seen: `desktop-v2026.10.4` (commit short `94f7537`, published 2026-11-05). New CI builds resolve the then-latest stable desktop release and record its exact commit and vendor asset checksum; `latest` is not hardcoded.

Source references, all under exact stable tag `desktop-v2026.10.4`:

1. `apps/desktop/package.json` — Electron/Angular/TypeScript + Windows `pack:win`; actual native module under `desktop_native`. Windows Electron builder version is in `electron-builder.json`.
2. `apps/desktop/electron-builder.json`: `win.target` includes `portable`, portable asset naming `Bitwarden-Portable-${version}.exe`, `win.extraFiles` includes browser desktop proxy; Windows protocol `bitwarden` is defined. The vendor's installer builds are distinct from portable release.
3. `apps/desktop/src/main.ts`, lines 111-159: `BITWARDEN_APPDATA_DIR` wins over the upstream `PORTABLE_EXECUTABLE_DIR/bitwarden-appdata` fallback; `app.setPath('userData',...)`, `app.setPath('logs',path.join(...,'logs'))`, local state/log services use the profile path.
4. `apps/desktop/src/main/native-messaging.main.ts`, lines 171-203, 422-436, 621-634: userData/browsers/ chrome + firefox manifests; per-user registry keys for `com.8bit.bitwarden` in Firefox, Chrome, Chromium, Edge, Vivaldi and Brave. The proxy path is relative to unpacked main executable; stable App/Bitwarden is therefore important.
5. `apps/desktop/src/main/messaging.main.ts`, lines 22-28 and 110-124: startup settings regenerated at startup using Electron `setLoginItemSettings` on Windows.
6. `apps/desktop/src/main/updater.main.ts`, lines 44-49 and 244-253: portable detection disables updates; `BITWARDEN_NO_UPDATER` / `ELECTRON_NO_UPDATER` is supported.
7. `LICENSE.txt`: default GPLv3, designated Bitwarden-licensed additions under `/bitwarden_license`, trademarks require separate compliance.

| Finding | Evidence | Location / component | PortableApps remedy | Safety / tradeoff | Test | State |
|---|---|---|---|---|---|---|
| Main persistent vault/settings/logs | `src/main.ts` 111-159 | Electron `userData` + logs; default installed `%APPDATA%/Bitwarden` | Set `BITWARDEN_APPDATA_DIR=Data/Profile` before startup | No installed profile migration | Restart/profile persistence | SOURCE-INSPECTED |
| Portable image self-extraction | `electron-builder.json` 94-97, 196-198 | Upstream portable EXE + temp extraction | Verify vendor SHA256, unpack real x64 app into stable `App/Bitwarden` | Packaging change fails rather than silent fallback | x64 PE/resources check; real Windows GUI test | SOURCE-INSPECTED / runtime NOT YET VERIFIED |
| Electron process temp files | Electron framework, potential | `%TEMP%` process-local | Point child TEMP/TMP at `Data/Temp` only | Windows OS system caches may remain; no global changes | Before/after trace | INFERRED |
| Browser native messaging | `native-messaging.main.ts` 171-203,422-436 | Six exact HKCU keys + Data/Profile/browsers | Snapshot before launch; restore preexisting after exit; remove only newly owned entries | Installed Bitwarden browser integration may collide during portable session | 6 browsers and installed coexistence | SOURCE-INSPECTED / runtime NOT YET VERIFIED |
| Login autostart | `messaging.main.ts` 22-28,110-124 | Electron `setLoginItemSettings`; HKCU Run Bitwarden key *likely* | Snapshot one HKCU Run value; recover only attributable changes | Precise name needs runtime observation; never blindly erase unrelated values | installed Run entry / portable option | SOURCE-INSPECTED / Run name INFERRED |
| Browser proxy binaries | `electron-builder.json` 102-114; `native-messaging.main.ts` 591-611 | `App/Bitwarden/desktop_proxy.exe` | Require in staging and ZIP; stable executable path | Does not guarantee every browser extension will activate | actual browser native messaging and autofill | SOURCE-INSPECTED |
| Updater | `updater.main.ts` 44-49,244-253 | Electron updater | Vendor portable detection plus scoped disable env | Update occurs via builder instead | no updater background writes | SOURCE-INSPECTED |
| Notifications / shell | Electron and desktop app integration | toast/AUMID/CLSID, Jump Lists, Start Menu | Preserve application functions; no speculative cleanup | Residual Windows-managed traces; identity collisions possible | real notification/click/Explorer test | NOT YET VERIFIED |
| Credentials / biometric | Electron + OS integration | Windows credential storage/DPAPI, Windows Hello | Do not bypass security or force migrations | Cross-PC restoration may require fresh login/2FA | move PC / login and unlock | NOT YET VERIFIED |
| Installer | Verified shared package builder tag | App/Other/launcher transaction; Data excluded | Invoke independent custom-NSIS action after ZIP validation | Installer not official; GUI requires manual test | GUI install/upgrade/rollback | SOURCE-INSPECTED |

**Mode separation:** No native source-compiled `Bitwarden.exe` claimed. This is a PORTABLEAPPS-only vendor-binary packaging workflow with community-compiled root launcher. NATIVE trace harvesting would be prohibited; not applicable here.

**Host-state policy:** The exact native messaging HKCU paths are evidence-supported. There is no proof of every cache, shortcut or notification path on every Windows version; never delete them by broad folder name. The launcher does not attempt blanket preservation of unrelated `%APPDATA%`, `%LOCALAPPDATA%`, `HKLM`, `PROGRAMDATA`, or `TEMP`. Unverified write paths remain an acceptance-test task.
