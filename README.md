# Bitwarden Desktop PortableApps Builder b1r2

**Mode: PORTABLEAPPS only.** This repository is an independent community build kit, not a fork of Bitwarden and not an official Bitwarden or PortableApps.com release.

Run **Actions > Bitwarden Desktop - Build PortableApps ZIP and Installer > Run workflow** with `version=latest` (default) or a numbered stable version such as `2026.10.4`.

The hosted Windows runner will:

1. Resolve official **bitwarden/clients desktop** stable releases; sort version components numerically; reject preview builds.
2. Retrieve exact upstream source commit, dependency lockfile SHA-256 and vendor `Bitwarden-Portable-VERSION.exe` release-asset SHA-256 from GitHub.
3. Download and check the official portable executable by SHA-256; fail closed on missing digest.
4. Unpack the official x64 Electron app using 7-Zip. **It does not build the vendor's app from source** and does not substitute a changed-version image.
5. Compile the **real BitwardenPortable.exe Windows PE** from transparent MIT-licensed C# NativeAOT source.
6. Place the official unpacked Bitwarden.exe, resources and desktop_proxy.exe inside `App/Bitwarden`, with authentic vendor icon extracted from the official app.
7. Set `BITWARDEN_APPDATA_DIR=Data/Profile` before the child application starts; set scoped `TEMP` and `TMP` to Data/Temp. Record narrowly scoped HKCU native messaging / autostart changes.
8. Independently validate ZIP layout, PE signatures, vendor resources, metadata, identity, and preserved empty Data folders; create ready-to-extract ZIP **before** installer generation.
9. Invoke pinned `Portable-Package-Builder@v1.0.0` (immutable SHA, independent `custom-nsis` installer), then validate the real output independently.
10. Invoke pinned `portable-release-publisher@v1.1.1` for a dry run, then release only verified ZIP/installer. If installer generation fails, the ZIP may still publish; the job is correctly marked **failed/partial**.

No PAT, paid runner, upstream fork, local compiler, manual installation or GUI-dependent CI step is required. Internet access during GitHub Actions is required. Never place passwords, vault backups or tokens in workflow logs.

## Output packages

- `BitwardenPortable_VERSION_x64_b1r2_BUILDER8.zip` (independent ready-to-extract PortableApps directory).
- `BitwardenPortable_VERSION.0_custom-nsis-b1r2.paf.exe` (PortableApps-style NSIS installer; **not the official PortableApps.com Installer**).
- `SHA256SUMS.txt` released by the pinned publisher.

Both artifacts are emitted from your **own builder repository's Releases**, never from the upstream Bitwarden repository. The release tag includes the Bitwarden version and builder Git commit prefix to avoid identity collision.

The packaged layout is:

```text
BitwardenPortable/
  BitwardenPortable.exe           <- compiled NativeAOT PE launcher
  App/
    AppInfo/appinfo.ini
    AppInfo/appicon.ico
    AppInfo/appicon_16.png
    AppInfo/appicon_32.png
    Bitwarden/
      Bitwarden.exe               <- official unpacked Bitwarden x64 desktop app
      desktop_proxy.exe           <- official browser messaging helper
      resources/                  <- official Electron resources
      ...
  Data/
    Profile/                      <- vault appdata, settings, cache and logs
    Temp/                         <- scoped temporary files
    TraceGuard/                   <- bounded HKCU shell journal/recovery
  Other/
    Source/                       <- recorded upstream identity, license and launcher source
  README.txt
```

The custom NSIS installer from the pinned shared builder leaves `Data` intact during upgrades and backs up the managed `App`/`Other`/launcher files; if an interrupted installer leaves `.__UPB_Backup`, **do not delete it**. It requires a normal Windows installer GUI to install; CI only builds and statically checks the installer.

## Beginner-friendly setup with GitHub Desktop

1. On GitHub.com, create a **new empty repository**, for example `Bitwarden-PortableApps-Builder`. It must not be a fork of `bitwarden/clients`. Choose **private** if you do not wish to publish the finished packages publicly. The GitHub Release publisher obeys the repository visibility.
2. Clone your new repository using **GitHub Desktop**. No command-line Git initialization is needed.
3. Extract this builder kit ZIP and copy **all its contents** into the root of the cloned repository. Make sure the hidden `.github/workflows/build-portableapps.yml` file is included. Do **not** copy a parent folder around the contents.
4. In GitHub Desktop, enter a summary such as `Add Bitwarden Desktop PortableApps Builder b1r2`, click **Commit to main**, then **Push origin**.
5. On the GitHub website, open **Actions** and choose **Bitwarden Desktop - Build PortableApps ZIP and Installer**. Click **Run workflow**. Keep `version=latest` or enter the exact stable version, then run.
6. Open the workflow run. Check **Resolve stable desktop release**, **Compile... NativeAOT**, **Validate independent ZIP**, **Build... installer**, and **Release** steps. A green CI job does **not** prove interactive Windows portability, notifications or installed-app coexistence.
7. On the repository's **Releases** page, download the `.zip` or `.paf.exe`. The publisher also creates `SHA256SUMS.txt`. The `.zip` is valid even if an installer failure is reported; in that case the run is marked partial failure.
8. **ZIP:** extract `BitwardenPortable/` to your preferred location and run `BitwardenPortable.exe`. **Installer:** run the `.paf.exe` manually on Windows and select the destination. In PortableApps Platform, refresh the menu if the app is not immediately shown.
9. Your vault profile lives in `BitwardenPortable/Data/Profile`. Always close Bitwarden completely from the system tray and back up `Data` before replacing a version. Do not copy installed Bitwarden's `%APPDATA%/Bitwarden` automatically.
10. **Upgrade:** make a backup of `Data`, then use the new installer for the same `AppID` or replace only `App`, `Other`, root `.exe` and metadata from ZIP. Never delete `Data`. **Rollback:** close the app and restore the complete previous matching binary/resources with a safe `Data` backup from before a schema migration.

## Important operating-system limitations

Bitwarden is a **password manager**, so do not assume its encrypted disk cache works on every different Windows user or computer. Login tokens, biometrics and Windows-bound cryptographic functions can be machine-bound; always have your master password and 2FA recovery method available. Avoid shared/untrusted computers; clear clipboard history and log out if necessary. USB-drive encryption and careful physical custody are recommended.

The upstream app runs its own native messaging, login-startup, notifications and protocol code. The community launcher uses explicit `BITWARDEN_APPDATA_DIR`, scopes TEMP to its child, and carefully snapshots only **six source-evidenced per-user native messaging keys** and **one Bitwarden per-user login Run value**. It does **not** scan or delete unrelated AppData/ProgramData/registry trees, and it does not touch HKLM.

- If the portable app adds an exclusively owned new registry value pointing inside its package, ShellGuard writes a recovery receipt and removes only that value after full main-process exit. It restores a pre-existing string value only when missing or overwritten by a verifiably package-owned value. Ambiguous entries are kept and logged.
- Existing installed Bitwarden native messaging registrations can be disrupted **while the portable app is running**, because upstream uses the same `com.8bit.bitwarden` browser host identity. The launcher restores the original registration after exit if it can prove ownership, but *simultaneous installed-app browser integration is not guaranteed*. If newly registered native messaging entries are removed after exit, the integration might need to be re-enabled on a later launch.
- Windows toast notifications, Start Menu shortcuts, protocol handlers, shell/Explorer caches and notification activation may not be fully contained. Unknown or unverifiable shortcuts/registry entries are deliberately preserved, not aggressively cleaned.
- A renamed/moved package may contain stale entries from an interrupted session. Its journal is left for safe manual review rather than blindly restoring registrations into a new location.
- An upstream portable release might alter its NSIS archive structure or its app binary naming. The builder **fails closed** in that case, requiring a reviewed revision; it will not silently build an incomplete package.
- Verified ZIP packaging and headless CI do not validate GUI launch, browser autofill integration, drag/drop, biometric unlock, native notifications or full Windows session cleanup. See `docs/WINDOWS-ACCEPTANCE.md`.

## Security and attribution

Vendor desktop app: **Bitwarden Inc.** Official source repository https://github.com/bitwarden/clients. Per upstream `LICENSE.txt`, most core code is GPLv3, and the `/bitwarden_license` folder uses an additional Bitwarden-specific license. This kit includes the upstream license texts in the finished release; review them and the trademark guidelines before public redistribution. The **community launcher** is MIT licensed; its source ships in the ZIP.

Pinned independently verified shared actions:

- `vhick/Portable-Package-Builder@v1.0.0` = `0112c35580e83b37eb8757ebcb949274e1631a04`.
- `vhick/portable-release-publisher@v1.1.1` = `cb64f86ac2d8c67506db5832de07f9ff58cbeaeb`.

No source-built NATIVE product is generated. No official PortableApps.com installer/certification is claimed. No binaries have been compiled or interactive Bitwarden tests run by the authoring environment; GitHub Actions and a real Windows system must perform those checks.

## b1r2 repair for the November 9, 2026 b1r1 installer failure

**Observed result:** b1r1 compiled its Windows x64 root launcher, verified Bitwarden Desktop 2026.10.4, produced an independently checked ZIP, and published that ZIP. The pinned shared installer action rejected `running-exe: App/Bitwarden/Bitwarden.exe` because its `Test-RelativeEXE` contract allows only Windows **backslash** separators. The intentional last-step failure correctly reported partial success.

**Changes:** Both full-build and packaging-only workflows now pass the exact source-evidenced form `running-exe: 'App\Bitwarden\Bitwarden.exe'`. A regression test protects both workflows. Package/builder revision was bumped to b1r2 without changing the vendor binary or profile recovery design.

**Most economical repair:** The original validated b1r1 ZIP has already been published under tag `portable-bitwarden-v2026.10.4-b1r1-59bd9319` in the builder repository. After updating the repository to this b1r2 kit, run **Bitwarden - Packaging Only from Previously Validated ZIP**, using the original tag, original ZIP name (`BitwardenPortable_2026.10.4_x64_b1r1_59bd9319.zip`), the exact SHA-256 of that ZIP from the original run (`d54c7a6214540fc6f1832c62e356444fa113ddd840a55c6ddc6800813448e4a5`; confirm against the original release's `SHA256SUMS.txt`), and a new release tag such as `portable-bitwarden-installer-2026.10.4-b1r2-repair`. This recompiles neither Bitwarden nor the portable launcher; it validates the existing ZIP and invokes the pinned installer builder. The created installer is identified as a *packaging-only revision* of the original source build, not a new upstream build.

**Alternative:** Run the complete `Bitwarden Desktop - Build PortableApps ZIP and Installer` workflow with `version=2026.10.4`. It rebuilds the launcher and stages the vendor image anew. The source identity remains anchored to the same upstream release, while the builder commit and package revision distinguish the new release. Because the original ZIP already exists, packaging-only is generally faster and saves GitHub minutes.

**Verification boundary:** The shared action's raw `v1.0.0/scripts/common.ps1` and `build.ps1` were inspected; actual installer generation following this repair is **NOT YET VERIFIED**. Run the GitHub Actions workflow and test an installer on Windows before treating it as working.

## Optional: Packaging-only workflow

If a prior build already published a verified ZIP but the installer failed, choose **Actions > Bitwarden - Packaging Only from Previously Validated ZIP**. Enter the original release tag, exact ZIP filename, its SHA-256 from the original `SHA256SUMS.txt`, and a **new** unique `portable-bitwarden-installer-...` release tag. The job downloads only the existing ZIP from your current builder repository, verifies the complete SHA-256 and PortableApps layout, compiles only the independent NSIS installer and publishes it through the same pinned publisher. The original Bitwarden build/source identity is retained; the upstream download, launcher compilation and original ZIP publication are not repeated. Do not use it with untrusted ZIP files or omit the checksum.
