# Handoff
Updated: 2026-10-11T23:22:41-04:00
Agent: Tommy (Codex)
Commit: 3d60953

## Done
- Read README.md first; committed all pre-existing changes on new branch tommy-rebuild (06a1eff).
- Added ShareScout 0.6.1 to the native titlebar (3d60953).
- Passed 20 frontend tests, frontend build, and Rust check. Python suite before/after: 132 tests, same 1 failure and 4 errors from sandbox socket restrictions.

## Next
- Push tommy-rebuild and open its pull request from a network-enabled session, then install the rebuilt native app on the owner's test PC.

## Blockers
- GitHub DNS/API access is unavailable, blocking push and pull request creation.
- Sandbox socket restrictions prevent the full Python suite from passing; native titlebar rendering requires desktop verification.

---

# Handoff
Updated: 2026-10-11T22:15:48-04:00
Agent: Tommy (Codex)
Commit: 75ff36d

## Done
- Read README.md first; added the native Local Network Info button and dialog for active IPv4 addresses, full subnets/netmasks, and default gateways on Linux and Windows.
- Updated README.md to confirm the feature; preserved pre-existing work.
- Verification: 20 frontend tests, frontend build, Rust check, and 3 new Python tests passed. Full Python suite before/after has the same 1 failure and 4 errors caused by sandbox socket restrictions.

## Next
- Resolve the uncommitted native prerequisite work, then commit this feature on a new branch and open its pull request in a writable, network-enabled session.

## Blockers
- Read-only .git blocked creation of feat/local-network-info; no commit was created. Commit above is unchanged HEAD.
- GitHub API access is blocked, preventing a pull request.
- Sandbox socket restrictions prevent the full Python suite from passing; live Linux/Windows behavior remains unverified.

---

# Handoff
Updated: 2026-10-11T22:05:00-04:00
Agent: Claude Sonnet 5.5
Commit: 87f57ed

## Done
- Added one-line comment '<!-- approval test -->' at top of README.md on branch docs/readme-approval-test-comment.
- Ran Python tests: 129 tests ran; I did not confirm the pass/fail breakdown (prior run had socket-denied failures).

## Next
- Review and merge the pull request.

## Blockers
- None

---

# Handoff
Updated: 2026-10-11T21:44:25-04:00
Agent: Tommy (Codex)
Commit: 87f57ed

## Done
- Read README.md and added <!-- ChatGPTR test --> at its top; preserved existing content.
- Ran Python tests before and after: 129 tests, 1 failure and 4 errors from denied socket access.

## Next
- Commit these changes on a new branch and open a pull request when access is available.

## Blockers
- .git is read-only, preventing branch creation and commits; the SHA above is the unchanged HEAD.
- GitHub DNS/network access is blocked; sandbox socket restrictions prevent all tests passing.

---

# Handoff
Updated: 2026-10-11T19:43:14-04:00
Agent: Claude Sonnet 5.5
Commit: ffb867c

## Done
- Added one-line comment '<!-- second test -->' at top of README.md on branch docs/readme-second-test-comment

## Next
- Review and merge the pull request

## Blockers
- None

---

# ShareScout agent handoff
Updated: 2026-10-08. Current version: 0.5.0.

## Canonical project and repository
- Work here: /home/lsparks1/VsCode/share-scout
- GitHub: https://github.com/neosoft-nvm/share-scout
- Remote: git@github.com:neosoft-nvm/share-scout.git
- Branch: main. Last published commit: 69081b9.
- This folder was consolidated from Documents/Codex/2026-10-07/bu/outputs/share-scout.
- Git history, source, packages, prior builds and development evidence were preserved.
- archive/DriveConnect-original is an unrelated pre-existing Expo/TypeScript project.
- Preserve that project; do not treat it as an Android ShareScout implementation.
- archive/previous-deliverables contains old sources, ZIPs and Debian packages.
- archive/development-work contains historical render scripts, screenshots and logs.
- Historical render scripts contain old paths and need adaptation before reuse.
- archive/ is locally excluded from Git; do not commit its dependencies or artifacts.
- Old workspace directories retain only protected Codex metadata placeholders.

## Product intent and implemented work
- Beginner-friendly resource access for Linux/Windows desktop PCs and laptops.
- Discover local IPv4 SMB devices by IP; users need no hostnames or share names.
- List folders, request sign-in, connect, remember connections and open a file manager.
- Windows uses native network APIs and automatically assigns a drive letter.
- Linux uses smbclient for browsing and GIO/GVfs for mounting.
- OneDrive/Google Drive use rclone; cloud mounts require the app to remain open.
- Optional local Samba setup detects missing software, installs it and repairs sharing.
- Creates a protected dedicated folder when appropriate, keeping existing shares.
- Fedora/Zorin/Ubuntu/Arch setup handles service names and supported local firewalls.
- Zorin fix: libglib2.0-bin supplies gio; do not restore obsolete gvfs-bin dependency.
- Share a folder supports owned existing folders or creation of a new folder.
- Read-only is default; optional read/write; guest access and symlink following are off.
- Existing Unix permissions and Samba passwords are preserved.
- Configuration is validated and backed up before replacement.
- SELinux stays enabled; home-folder policy changes require an explicit prompt.
- Auto-detect installed Thunar, Dolphin, Nautilus, Nemo and Caja via native commands.
- Install matching per-user sharing actions; Nautilus/Caja use their Scripts submenu.
- Windows Share a folder opens the operating system's shared-folder wizard.
- Single main session per user; repeat launches request activation of the existing window.
- OS locks allow crash recovery; activation uses authenticated localhost messaging.
- All window titles include VERSION from app_info.py; Debian builds use that version.
- Check for updates compares VERSION with GitHub main in a background thread.
- Downloaded version code is parsed, never executed; upgrades remain user-initiated.

## Code map and validation
- resource_mapper.py: main Tk app, connection operations and startup.
- network.py / discovery.py: detection, authentication and SMB client operations.
- sharing_setup.py / sharing_ui.py: optional Samba provisioning and setup dialog.
- folder_share.py / folder_share_ui.py: chosen-folder sharing and validation.
- file_manager.py: native manager detection and context-menu integration.
- single_instance.py: process lock and existing-window activation.
- updates.py / updates_ui.py: GitHub version check and upgrade instructions.
- ui.py: responsive layouts, scaling, scrolling and fixed action footers.
- Run: python3 -m unittest discover -s tests (76 tests passed after relocation; localhost sockets required).
- Build Debian package: python3 scripts/build_deb.py (writes ignored dist/).
- Build needs ar and desktop-file-validate; runtime needs desktop/system dependencies.
- Linux install/update: git pull --ff-only; bash Launch-Linux.sh.
- Windows install/update: git pull --ff-only; Launch-Windows.cmd.
- Linux launcher updates the stable copy in ~/.local/share/ResourceMapper.
- Compatibility settings/package identifiers retain ResourceMapper/resource-mapper.
- Minimum display test target is 1280x720; also test 4K at 100/150/200% scaling.
- UI-verification.json records 42 rendered layouts; 720p bounds were simulated on 4K.
- Tests used controlled hosts/configuration; actual Samba provisioning was not tested.
- Real context-menu visibility, remote access and Windows behavior need device testing.

## Next work and constraints
- First verify the moved checkout and review README.md and ROADMAP.md.
- Test real Zorin/Fedora folder sharing, context actions and cross-device connections.
- Test Windows mapping, DPI behavior, shared-folder wizard and single-instance locking.
- Exercise offline/rate-limited update checks and real cloud sign-in/mount lifecycle.
- Android was researched only: the user explicitly said DO NOT build it.
- Future Android direction: native Kotlin/Compose client for existing SMB shares first.
- Android needs new UI/network code; document-provider/cloud/server work comes later.
- Research estimates: 2-4 weeks prototype, 6-10 weeks usable client, 3-5 months polished.
- Those estimates are unvalidated; require fresh Android/library research before planning.
- User prefers autonomous work, simple flows and preserving existing configuration.
- If Git SSH fails on system config, prior workaround: ssh -F /dev/null -o BatchMode=yes.
- HANDOFF.md and AGENTS.md are local handoff additions; no new push was requested here.

## Priority usability fixes — 2026-10-08
- Windows sharing wizard now uses ShellExecuteW/runas; only the wizard requests UAC elevation.
- Main screen separates finding network folders, connecting cloud storage, and sharing local folders.
- Existing Windows mapped SMB drives and Linux desktop SMB mounts are read and merged on startup/refresh.
- Open folder reconnects a saved disconnected folder before opening it.
- Cloud setup uses rclone non-interactive JSON questions in Tk, provider browser OAuth, cancellable background processes, unique remote names, and unfinished-account cleanup. No cloud setup terminal.
- Existing cloud accounts can be picked from the GUI; successful sign-in automatically saves/connects/opens.
- Manual network form explains addresses and assigns a free Windows letter automatically.
- Sharing check/repair labels explain checking versus service/firewall changes.
- Indigo headings, teal progress bars, connected-folder count and green connected rows.
- Added cloud protocol/cancellation/account reuse and mocked Windows elevation/mount import checks.
- Real Windows UAC, remote SMB access, Google/Microsoft OAuth and cloud mount/device behavior still require target-machine testing. Automated tests do not establish real-world service success.
