# ShareScout Agent Summary & Project Directives

## Project Overview & Ownership
- **Lead Agent**: David (appointed 2026-10-10; probation through 10/17/26 10:44 AM). Predecessor (ChatGPT) terminated.
- **Repository**: Authoritative root is `/home/lsparks1/VsCode/share-scout` (`git@github.com:neosoft-nvm/share-scout.git`).
- **Core Purpose**: Lightweight, beginner-friendly desktop file share & cloud mount utility for Linux and Windows.

## Non-Negotiable Directives
1. **Source Tree Integrity**: Work exclusively in repository root. `archive/` contains preserved historical artifacts and an unrelated legacy DriveConnect project; never treat `archive/` as active source.
2. **Platform Scope**: Linux (smbclient/GIO/Samba) and Windows (Native NetShare/WinFsp/Credential Manager). Android is strictly **research-only** until explicitly authorized by the user.
3. **Display Targets**: Minimum test target is 1280x720 (720p); scaling-aware up to 4K (100%, 150%, 200%).
4. **Testing Protocol**: Run `python3 -m unittest discover -s tests` before and after all changes. All tests must pass.
5. **Release Milestone**: Bumping to `v0.6.0` to introduce professional visual redesign and flow upgrades.
6. **Commitment & Delivery Integrity**: Never promise designs, features, or UI capabilities that cannot be delivered exactly as presented. Verify feasibility, rendering engines, and dependencies upfront before committing to deliverables.
7. **Communication Standard**: Keep all responses short, concise, and directly to the point.

## Historical Versions & Rollback
- Previous release `v0.5.3` is permanently pinned via git tag `v0.5.3` on GitHub (`57f0b91`).
- To inspect or run `v0.5.3`:
  ```bash
  git clone --branch v0.5.3 https://github.com/neosoft-nvm/share-scout.git
  # or in existing clone:
  git checkout v0.5.3
  ```
- Local archives: `archive/previous-deliverables/ShareScout-0.5.3.zip` and `resource-mapper_0.5.3_all.deb`.

## Architecture & Key Components
- `resource_mapper.py`: Main Tk application, connection manager, startup lifecycle, single instance bridge.
- `discovery.py`: Local IPv4 network scanner, device discovery, and interactive SMB share browser.
- `network.py`: Low-level SMB mounting (GIO on Linux, NetUse on Windows) and IP subnet discovery.
- `cloud_ui.py`: Rclone-based non-interactive browser OAuth for Google Drive & OneDrive.
- `sharing_setup.py` / `sharing_ui.py`: Optional local Linux Samba provisioning, firewall, and SELinux config.
- `folder_share.py` / `folder_share_ui.py`: User-directed local folder sharing dialogs.
- `ui.py`: Centralized design system (Slate/Indigo theme tokens, scaling math, responsive layouts).
- `updates.py` / `updates_ui.py`: In-app GitHub update checker and seamless staging helper.
- `app_info.py`: Canonical app name and SemVer declaration.

## Installation & Execution Reference
- Linux install/run: `bash Launch-Linux.sh` (or `python3 resource_mapper.py`)
- Windows install/run: `Launch-Windows.cmd` (or `Setup-Windows.ps1`)
- Build Debian package: `python3 scripts/build_deb.py`
