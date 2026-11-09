# Windows hands-on acceptance plan (not run in CI)

This is a test guide, **not a claim that tests have passed**. Use a dedicated Windows 11 test user/VM and dummy Bitwarden account, never an active production vault. Back up the Windows test VM before registry/installed-app coexistence tests. Do not post registry exports or vault profiles containing secrets in public GitHub issues.

## Stage 1: vendor app and launcher

1. Download the published ZIP from your **builder's own** GitHub Releases. Compare the SHA-256 against the publisher's `SHA256SUMS.txt` using PowerShell `Get-FileHash`.
2. Extract `BitwardenPortable` under `C:\Portable Tests\Bitwarden Portable 安全\`.
3. Double-click `BitwardenPortable.exe`. Verify the real Bitwarden login interface appears. Exit fully from Bitwarden's **tray icon**.
4. Confirm `Data\Profile\data.json` (or contemporary profile files), `Data\Profile\logs` and new settings persist across launches; no value was copied from `%APPDATA%\Bitwarden`. Test both unlocked and signed-out flows.
5. Move the entire folder to another drive letter; start again. Change current working directory with a terminal invocation and verify profile remains relative to launcher location.
6. Test launch twice from same folder while running. The second launcher must refuse rather than damage active profile. Test passing legitimate Bitwarden desktop arguments, if any.
7. Inspect `Data\TraceGuard\launcher.log` and `Data\TraceGuard\History`; verify no passwords/session tokens appear in log text.

## Stage 2: profile containment & user data safety

1. Create an empty directory and nested empty directory tree under `Data\Profile`, relaunch, upgrade and verify they still exist.
2. With a VM file/registry diff tool, record **before, during and after** snapshots of app-owned `%APPDATA%`, `%LOCALAPPDATA%`, `%LOCALAPPDATA%\Low` (Windows LocalLow), `%PROGRAMDATA%`, `%TEMP%`, Desktop, Start Menu and the registry. Distinguish the launched app from Windows cache/indexing activity.
3. Verify the launcher creates only `Data\Profile`, `Data\Temp`, `Data\TraceGuard` and source-evidenced required shell changes. Note Windows-managed caches can remain without constituting app-owned persistent data.
4. Place distinct sentinel files in an existing `%APPDATA%\Bitwarden` installed-app profile. Launch and quit portable. Compare checksums. Existing files MUST NOT be changed by launcher handling.
5. Close/force-close **only the test Bitwarden app**, restart the launcher and inspect whether `shellguard-pending.json` was recovered. Do not force terminate production vaults.
6. Test staging under `C:\Portable Tests\` with spaces and Unicode, then inspect all paths for hard-coded original drive letter.

## Stage 3: source-evidenced Windows shell integration

1. Snapshot the **six HKCU native messaging keys** listed in `docs/AUDIT.md`: Firefox, Chrome, Chromium, Edge, Vivaldi and Brave, each ending `NativeMessagingHosts\com.8bit.bitwarden`. Also snapshot the `Bitwarden` **value only** in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Export keys as backup before testing.
2. Install regular Bitwarden Desktop in the VM and enable its browser integration. Record the installed browser host registry values. Launch portable and use browser integration. Observe whether the two Bitwarden instances collide; **do not assume simultaneous integration works**. After fully quitting portable, compare installed registration values and restore the VM if disturbed.
3. On a test user without installed Bitwarden, enable browser integration in portable and test each supported browser extension and desktop unlock. Quit and inspect `Data\TraceGuard\Recovered\Registry`. Test next-launch behavior and re-enabling integration.
4. Enable and disable Windows login-startup **only after backing up** the user's existing Run entry; see whether the portable app creates transient/stale references. It must not silently destroy an installed Bitwarden startup entry.
5. Exercise real native notifications and click-to-open. Snapshot Start Menu, Startup, Desktop shortcuts, HKCU protocol registrations, Jump Lists and toast activator registrations. The kit does NOT claim cleanup of unverified OS-managed entries.
6. Test graceful Quit from tray, Windows sign-out, Explorer restart and crash; compare after-exit file/registry state. Verify all app subprocesses have terminated before USB ejection.

## Stage 4: installer and recovery

1. Run the independent `custom-nsis` `.paf.exe` on a test Windows VM. Confirm the default destination and that only `App`, `Other`, the launcher and metadata are installed. No elevation required. Do not use unverified silent-install switches.
2. Sign in to a **test account**, change a non-sensitive setting, and fully exit. Record `Data` checksums and empty directories.
3. Install the *same AppID* upgrade, verifying the installed `Data` is preserved and `App/Other` binaries change appropriately. Inspect `.__UPB_Backup` and `.__UPB_Stage` after success; if a failure leaves them, preserve and inspect them.
4. Deliberately inject a controlled failure only in a disposable VM (for example, hold a managed app binary open), confirm the installer aborts and existing `Data` is intact. Test rollback with a matching pre-upgrade Data backup.
5. Try installing to a folder containing an unrelated app. The installer must refuse. Try symlink/junction for top-level `App`/`Other` and verify the shared builder blocks unsafe cleanup; deeper nested junction handling remains a limitation.
6. Test PortableApps Platform Menu refresh, menu launch and quit. Record exact Windows build numbers, Bitwarden version, package release tag and outcome.

## Stage 5: profile mobility and credential security

1. Back up your test vault or know its server login. Move the USB package to a different Windows test account/device. Test sign-in and session handling; use 2FA normally.
2. Verify optional biometric unlock behaves according to Windows policies. Never weaken DPAPI, TPM, Hello or OS secure store configuration to force portability.
3. Disable Bitwarden browser integration before moving to another machine if your test showed stale host registry entries. Restore installed-app host registration if the test exposed a conflict.
4. Test missing/offline network and startup. Confirm no surprise updater rewrites the package.

## Acceptance record template

- Windows version and architecture:
- Bitwarden upstream release/commit:
- Builder release and installer revision:
- ZIP SHA-256 / installer SHA-256:
- ZIP extraction + app login: PASS / FAIL / NOT TESTED
- Data/Profile persisted: PASS / FAIL / NOT TESTED
- Installed Bitwarden coexistence: PASS / FAIL / NOT TESTED
- Browser integration: PASS / FAIL / NOT TESTED
- Notifications and activation: PASS / FAIL / NOT TESTED
- Tray/subprocess completion: PASS / FAIL / NOT TESTED
- Registry recovery and crash recovery: PASS / FAIL / NOT TESTED
- Empty directories: PASS / FAIL / NOT TESTED
- Installer, upgrade, rollback: PASS / FAIL / NOT TESTED
- Portability after drive relocation: PASS / FAIL / NOT TESTED
- Non-portable Windows traces and severity:
- Evidence retained securely:
