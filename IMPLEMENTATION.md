# ShareScout 0.7.0 desktop

Lead: Tommy. Authoritative source: `/home/lsparks1/VsCode/share-scout`.

## Application path

React/TypeScript supplies the desktop UI, Tauri supplies the native window, and a private JSON-lines Python worker reuses the existing platform services. No browser-only preview pretends to mount drives. The Python/Tk application remains a reference and fallback.

- `desktop_service.py`: persisted connections, SMB discovery/authentication, cloud OAuth/mounts, sharing helpers, dependency checks, and single-instance activation.
- `src-tauri/src/lib.rs`: concurrent request/response bridge, packaged resource lookup, and native activation.
- `src/services/api.ts`: typed operations and visible errors; no production demo fallbacks.
- `native_updates.py`: checks stable GitHub releases, verifies the published SHA-256 digest, stages a bounded runtime ZIP, and installs with rollback.
- `scripts/package_desktop.py` and `scripts/install_desktop.py`: build/install the native runtime and update the desktop shortcut.

Cloud mounts use rclone's full VFS cache. An ephemeral authenticated loopback status endpoint checks open files and queued/running/errored uploads before disconnecting. Its random credential is passed through the child environment and kept in memory. Passwords are remembered only on explicit opt-in through the existing OS credential store.

Local shares stay password-protected, with read-only selected initially. The unused guest-access control was removed following the user's decision. Network device categories and share permissions are displayed only when actually supplied; IP suffixes and folder names do not establish those properties.

## Permanent system mounts

`permanent_mounts.py` is the isolated Linux helper. The frontend requests defaults and a preview through the allowlisted native bridge; only an explicit confirmation invokes `pkexec --disable-internal-agent /usr/bin/python3 -I ... --admin` through `systemd-run --user --pipe` when available. This reaches the desktop graphical approval agent even after a remote update. JSON credentials remain on stdin, outside command arguments. The helper identifies the caller through `PKEXEC_UID`, serializes changes, validates SMB roots and direct `/mnt/sharescout` children, rejects symlink/conflicting targets, and creates only its managed systemd units and root-owned credential/metadata files. It leaves `/etc/fstab` unchanged.

`PermanentMountModal.tsx` separates configuration, confirmation, success and removal. Credentials cross the privileged boundary through stdin. Unit/readback and selected-account directory access must succeed before success; rollback keeps busy mounts recoverable. Managed mounts are merged into saved connections on refresh and cannot accidentally fall back to GVfs or the ordinary Disconnect/Remove actions.

The native entry point also applies WebKit's DMA-BUF workaround when an NVIDIA kernel module is present, before GUI threads start, respecting explicit environment overrides.

## Build and install

```bash
npm ci
npm run build
cargo build --release --features custom-protocol --manifest-path src-tauri/Cargo.toml
python3 scripts/package_desktop.py
python3 scripts/install_desktop.py --no-launch
```

Open ShareScout from the desktop menu after installation. The native install lives in `~/.local/share/ShareScoutDesktop` (Linux) or `%LOCALAPPDATA%/ShareScoutDesktop` (Windows). Saved connections and password stores retain their existing locations. The old Python installation is preserved.

Linux requires system Python/PyGObject, GIO/GVfs SMB support, smbclient, rclone, FUSE, iproute2, zenity, and optional libsecret password storage. Run `Launch-Linux.sh` for dependency setup and installation after building the native binary. Windows requires Python, rclone, WinFsp, and WebView2; `Setup-Windows.ps1` installs the required tools and prefers a built native binary.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
npm test
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

Historical 0.6.1 verification: 129 Python tests, 18 frontend tests and 3 Rust tests passed (including the embedded production interface). TypeScript, production frontend and Linux native release builds succeeded. The 0.6.1 runtime was installed and its files/menu launcher checked; it was not launched because this session cannot access the native display. The previous menu launcher is backed up as `resource-mapper.desktop.before-native`.

Regression coverage includes failed mounts, settings preservation, credential forwarding, cloud OAuth cancellation, selected mount paths, upload protection, active scanning, and update archive validation/rollback. Passing tests do not establish real cloud access or target-device behavior.

Browser rendering checks use the actual frontend at desktop sizes and reduced logical viewports representing display scaling. This execution session cannot connect to the native desktop display. Real Windows behavior, browser OAuth, cross-device sharing, and a published-release upgrade still need user/device validation.

CI produces installers and native ZIP artifacts without publishing a release. Automatic GUI upgrade is enabled only when a stable GitHub release includes the matching `sharescout-desktop-{platform}-{architecture}.zip` asset with a GitHub SHA-256 digest. Publishing remains a separate action. Android remains a future target; its existing shell is not a functional desktop-mount client.

The `custom-protocol` feature is enabled by default for production builds. A compile guard prevents installing a release that depends on the localhost development server. An embedded-assets regression test checks the packaged interface.

Build and install in one command (installation runs only after a successful build):

```bash
python3 scripts/build_install_desktop.py
```

0.7.0 verification: current test results and delivery status are recorded in HANDOVER.md and HANDOFF.md. New mount checks use controlled mocks; real administrator approval, SMB mounting, reboot reconnection, and Plex playback require device verification.
