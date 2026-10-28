# Changelog

## 0.7.1 — 2026-10-28

- Route permanent-mount approval through the desktop user manager so remotely launched apps can reach the graphical polkit agent; distinguish cancellation from a missing agent.
- Manual Disconnect now disables startup reconnection for that saved folder.
- Add a visible reconnect toggle for the selected folder; cloud setup now defaults to no automatic reconnection.
- Cover disconnect/restart, remove/restart, and update preservation of removed cloud connections with regression checks.

## 0.7.0 — 2026-10-28

- Add Permanent Mount to network discovery and saved SMB connections on Linux.
- Preview a stable folder path, choose access for your account or Plex, and default to read-only access.
- Require explicit credential-storage consent and desktop administrator approval; verify the mount and selected-account access, with rollback and a dedicated removal flow.
- Keep managed mounts available outside ShareScout and after reboot through systemd automounts.
- Explain sharing versus mounting and apply the NVIDIA WebKit startup workaround automatically.
- Windows mapping and cloud connections keep their existing behavior; permanent service mounts require Linux/systemd.

## 0.6.2 — 2026-10-27

- Show Done after confirmed local folder sharing; closing keeps the folder shared.
- Prevent duplicate sharing submissions after success and reset the dialog on reopening.
- Keep failed sharing setup retryable; launching the Windows wizard is not treated as success.
- Clarify that device passwords survive app restarts only when saving to the system keychain is selected.
