# ShareScout handover

Authoritative source: `/home/lsparks1/VsCode/share-scout`. Current feature version: **0.7.2**.

- Read `AGENTS.md`, `IMPLEMENTATION.md`, `README.md` and `HANDOFF.md` before changes.
- React/Tauri UI uses `src/`, `src-tauri/`, and private `desktop_service.py` worker.
- New Permanent Mount option is Linux/systemd only; Windows/cloud behavior is preserved.
- `permanent_mounts.py` uses desktop polkit approval, stdin credentials, protected root files, and managed mount/automount units. Existing fstab entries and mounts are not adopted or replaced.
- Creation is previewed and explicitly confirmed, including credential storage. Removal has its own confirmation and refuses force-unmounting busy folders.
- Selected-account directory readback gates success; failures roll back or report preserved recovery configuration.
- Saved system mounts never fall back silently to ordinary desktop mounts.
- Preserve saved connections, OS credential stores, the Python fallback and historical mockups.
- The user authorized versioning, commits and repository pushes, and deployment to .20 (lsparks1/Zorin) and .30 (leesparks/Fedora).
- Unit tests and a simulated UI check do not prove real administrator prompts, network mounts, reboot reconnection, or Plex playback. Those require target-device verification.
- Validation: 167 Python, 34 frontend and 6 native tests pass; generated units pass systemd validation.
- Installed matching 0.7.2 binaries locally, on .20 and .30; saved connections preserved. The .30 startup disk wait cleared; direct X11 readback confirms the current frame fits the usable screen. See HANDOFF.md.
- Permanent-mount approval uses the desktop user manager so SSH-launched apps can reach the graphical polkit agent.
- Manual disconnect turns off startup reconnect; the dashboard provides an explicit toggle. See HANDOFF.md.
- Keep responses short and concise.

- Share a Local Folder opens local SMB share inventory; Set Up a Share opens creation and returns to a refreshed inventory. Network/cloud connections are labeled separately.
