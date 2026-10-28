# ShareScout handover

Authoritative source: `/home/lsparks1/VsCode/share-scout`. Current feature version: **0.7.1**.

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
- Validation: 154 Python, 30 frontend and 3 native tests pass; generated units pass systemd validation.
- Installed 0.7.1 locally, on .20 and .30. Saved connections were preserved; .30 has no saved cloud connection or running rclone process after launch.
- Permanent-mount approval uses the desktop user manager so SSH-launched apps can reach the graphical polkit agent.
- Manual disconnect turns off startup reconnect; the dashboard provides an explicit toggle. See HANDOFF.md.
- Keep responses short and concise.
