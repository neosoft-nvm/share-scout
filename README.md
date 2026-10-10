# ShareScout 0.5.0 — find, pick, connect

Discover and connect shared resources across PCs, network storage, and cloud services without knowing hostnames or share names. ShareScout is for desktop PCs and laptops, with Android support planned for the future.

## Project scope

| Capability | Current scope |
| --- | --- |
| Run ShareScout | Linux and Windows PCs, including desktops and laptops |
| Find and connect network folders | Devices offering compatible SMB file sharing, including PCs, NAS devices, and file servers |
| Connect cloud storage | OneDrive and Google Drive through rclone |
| Offer local sharing setup | Linux PCs through Samba, including chosen folders; Windows requests administrator approval for its shared-folder wizard |
| Android | Future target; no Android app or installer is available yet |

The goal is a simple **scan → choose a device → choose a folder → connect** experience. Device type should not determine whether a compatible shared folder can be discovered. See [the roadmap](ROADMAP.md) for the planned Android scope.

## First launch

For Debian/Ubuntu desktops, the `.deb` package is the easiest option: open it in your software installer, install, then open **ShareScout** from the applications menu. The installer resolves the dependencies. This package has been structurally verified but has not been installed on a Debian/Ubuntu test machine.

For Windows or other Linux distributions, extract the ZIP first.

**Windows:** double-click **Launch-Windows.cmd**. Setup installs missing tools through winget and adds **ShareScout** to the Start menu. The computer may request administrator approval during installation. Run the app as your normal desktop user.

**Linux:** open **Start-Resource-Mapper** as a program. If your file manager opens scripts as text, run `bash Launch-Linux.sh` once in a terminal. Setup installs the required packages, copies the app into `~/.local/share/ResourceMapper`, and adds **ShareScout** to your applications menu. Supported setup package managers: Debian/Ubuntu apt, Fedora dnf, and Arch pacman. Installation may ask for your administrator password. An active desktop session is required.

Zorin/Ubuntu setup installs `libglib2.0-bin` for the `gio` command and `gvfs-backends` for SMB support. If an older download fails with “gvfs-bin has no installation candidate,” use the latest source or ZIP and rerun `bash Launch-Linux.sh`. Version 0.3.1 also fixes this dependency in the Debian package.

Window title bars show the installed application version, including the sharing and discovery dialogs.

After setup, open **ShareScout** from your application menu. No terminal is needed for network browsing or mapping. ShareScout allows one main session per user: launching it again requests that the existing window come forward. The OS releases the session lock after exit or a crash, so a stale lock file does not prevent restarting. Window activation uses an authenticated localhost connection; if activation fails, the second launch still does not start another session. Standalone file-manager sharing dialogs remain separate from the main session.

## Check for updates

ShareScout checks for a newer version in the background when it opens. If one is available, it asks whether you want to see the upgrade options. Check **Don’t check for updates automatically** in that prompt to turn off launch checks; you can still use **Check for updates** at any time. Offline checks stay quiet. The upgrade window links directly to the latest source ZIP and shows the short steps for cloned, ZIP, and Debian package installs. ShareScout never installs downloaded code without your choice.

For a clone, close ShareScout, run `git pull --ff-only` inside the repository, then run `bash Launch-Linux.sh` on Linux or `Launch-Windows.cmd` on Windows to update the installed copy. ZIP users can extract the latest source ZIP and rerun the launcher. Debian-package users need an updated package, or can build it from the updated repository.

## Sharing check during setup

Setup checks the **local Linux computer** for a Samba server, configured file shares (including file-manager usershares), and an IPv4 listener on port 445. If sharing is already configured and listening, normal first-run startup keeps it. You can inspect or repair it with **Help sharing from this PC**.

If sharing is missing, setup offers **Set up sharing**. Accepting opens a setup terminal for the operating system’s administrator prompt and the sharing-password prompt. It installs Samba when missing and starts the correct service for Fedora or Zorin/Ubuntu. Declining leaves local sharing settings untouched.

When no file shares are configured, it creates a dedicated, password-protected share named `ShareScout-<your username>` under `/srv/share-scout/<your username>`. A **Shared with ShareScout** shortcut in your home folder points to it. Put files you want to share there. Existing shares and their permissions are kept; the original Samba configuration is backed up before adding a new section, and the new configuration is validated with `testparm` before it replaces the original.

Fedora’s SELinux label is applied only to the dedicated folder. For active firewalld or UFW, setup allows IPv4 TCP port 445 from the current connection’s subnet. It keeps the firewall enabled and does not use a global firewall reload. Custom firewall setups or network isolation can still block access; readiness is verified locally, then you rescan from the other device.

**Run sharing setup on each Linux PC that should provide shared folders.** Samba installation is checked on the computer where setup runs; it does not remotely install software on discovered computers. If a share already exists but its service is stopped, setup keeps the share and offers to enable sharing and repair supported firewall access.

## Share an existing folder or create a new share

On Linux, click **Share a folder**, then **Choose folder…** or **Create a new folder…**. Choose a share name and access level, then click **Share this folder**. Read-only access is the default; read/write access lets signed-in devices change and delete files. The selected folder and its subfolders are shared, and symbolic links are not followed.

Setup installs Samba if needed, keeps existing shares, validates and backs up the configuration, and configures supported local-network firewall access. Sign in from another device using your Linux username and sharing password. An existing Samba password is retained; a missing account gets a password prompt in the setup terminal. The completion dialog shows the IP address, share name and sign-in account. Scan from another device to verify access.

Choose an owned folder inside your home, `/srv/share-scout`, or a mounted drive under `/media`, `/mnt` or `/run/media`. Sharing your entire home, hidden settings folders, system folders, symbolic-link paths, or names containing `%` or line breaks is not supported. Original Unix ownership and permissions are preserved. On SELinux systems, home-folder sharing explicitly asks before enabling the system-wide `samba_enable_home_dirs` policy if needed; other chosen folders are labeled for Samba. SELinux stays enabled. If later setup steps fail, the error is shown; already completed configuration changes may remain and can be repaired with **Help sharing from this PC**.

On Windows, **Share a folder from this PC** requests Windows administrator approval and opens the operating system’s shared-folder wizard. Approve the Windows prompt to choose a local folder and access permissions. Only the wizard is elevated; ordinary connections run in your desktop session. If approval is declined, ShareScout explains how to retry. Connecting to another computer’s folder uses **Find network folders** and normally needs no administrator rights. The Linux file-manager integrations below are not installed on Windows.

## Right-click sharing in Linux file managers

Setup and each app startup automatically detect supported native file managers by their executable commands and install per-user **Share with ShareScout** actions for those found. Multiple installed managers are supported, and a manager added later is picked up on the next launch. They open the same folder-sharing dialog, so sharing requires the user to choose access and click **Share this folder**.

| File manager | Where to find it |
| --- | --- |
| Thunar | Right-click a folder → **Share with ShareScout** |
| Dolphin | Right-click a folder → **Share with ShareScout**; some versions place it under Actions |
| Nemo | Right-click one local folder → **Share with ShareScout** |
| Nautilus / GNOME Files | Right-click a folder → **Scripts → Share with ShareScout** |
| Caja | Right-click a folder → **Scripts → Share with ShareScout** |
| Other file managers | Open **ShareScout — Share a folder** from the application menu, or add a custom action pointing to the installed share-folder helper |

Reopen your file manager after setup. Thunar actions are merged with existing custom actions, with a backup before changes; malformed existing configuration is left intact. **File-manager shortcuts** in ShareScout rechecks detection and reports which managers were found, installed actions, and any failures. If no supported manager is found, the application-menu sharing shortcut is still installed. Sandboxed Flatpak/Snap file-manager integrations are not detected by this native-command check. Installation uses XDG data/config locations and requires no additional file-manager plugins. The default helper is `~/.local/share/sharescout/share-folder`; it accepts one absolute local folder path as an argument.

Integration formats follow the [Thunar custom-action documentation](https://docs.xfce.org/xfce/thunar/custom-actions), [Dolphin service-menu documentation](https://develop.kde.org/docs/apps/dolphin/service-menus/), [GNOME Scripts documentation](https://help.gnome.org/gnome-help/nautilus-behavior.html), and [Nemo action reference](https://github.com/linuxmint/nemo/blob/master/files/usr/share/nemo/action-info.md).

## Screen sizes and scaling

All five windows have screen-aware sizes and a scrollable body. The main action buttons stay outside that scrolling area at the bottom. Toolbars wrap into multiple rows, discovery lists stack on narrow screens, tables have horizontal and vertical scrolling, and headings shrink on small displays. Keyboard focus scrolls form fields into view.

The minimum display test target is **1280×720**. Current controlled rendering checks cover seven windows, including folder sharing, at **1280×720 and 3840×2160**, each at **100%, 150%, and 200%** scaling. The 720p checks use simulated screen bounds on a 4K test display. Earlier releases also checked 640×480. Windows DPI awareness is enabled before Tk starts. Actual Windows display behavior still requires Windows-machine testing.

## Everyday use

1. On a new installation, finish or skip the sharing check. The app then opens **Find shared folders** and scans your connected IPv4 networks automatically.
2. Click a device’s **IP address** in the left list.
3. Click a **shared folder** in the right list.
4. Click **Connect this folder**. The app remembers it and opens your file manager.

If a device requires a username and password, a sign-in form appears in the app. Use an account on that device. The domain is usually blank. Check **Remember this password in the system password store** to reuse it on later launches; passwords are kept in Windows Credential Manager or the Linux desktop keyring, never in ShareScout settings. If a device answers but shows no folders, try **Sign in to see more folders**.

Windows chooses an unused drive letter automatically. Linux mounts through GVfs; the folder opens in your file manager and is available through the desktop’s mounted network locations. Most GNOME, Cinnamon, MATE and XFCE desktops support this flow. KDE’s file manager may use its own SMB sign-in when opening a URI.

Next time you open ShareScout, remembered connections reconnect. Passwords are kept only in memory by this app, so a protected device may ask you to sign in again. Windows may reuse its existing operating-system SMB session. Reconnect is on app launch, not a login service.

## Your folders on the home screen

The home screen lists saved folders, connection status, and locations. **Open folder** opens a connected folder; for a disconnected saved folder, it connects first and opens when ready. **Refresh connected folders** also brings existing Windows mapped network drives and Linux desktop SMB mounts into the list, including those connected outside ShareScout. The status reflects completed connection operations and the most recent desktop refresh; it is not continuous server availability monitoring.

**Add network address** is for users who already know a full address such as `\\server\photos` or `smb://server/photos`. The dialog explains the format, chooses the drive letter automatically, and connects after saving. If you only know an IP address, use **Find network folders**.

**Help sharing from this PC** explains how to make this computer’s folders available to others. On Linux, **Check sharing again** only checks the current status. **Set up sharing** installs missing tools and enables sharing. **Restart sharing & allow local access** restarts the sharing service and updates supported firewall rules for the current local network; it requests administrator approval in the setup terminal. These are local sharing actions, not cloud connection repairs.

The refreshed interface uses indigo headings and teal progress bars over a pale background. Primary connection actions and the selected-folder controls stay easy to find, and forms retain scrolling on small displays.

## If a device is missing

Enter its **IPv4 address** and click **Show its folders**. You still do not need a hostname or share name.

Discovery checks TCP port 445 on directly connected IPv4 networks. It finds devices already offering compatible SMB file sharing, such as PCs, NAS devices, and file servers. A device with file sharing disabled will not appear; the owner needs to share a folder first. Firewalls, Wi-Fi guest isolation, VPNs and other subnets can prevent discovery. IPv6-only hosts and other protocols such as NFS are not included.

Typical home networks finish quickly. On large networks, discovery limits each interface to its nearby /24 when the actual network contains more than 4,096 addresses; the screen labels this limit. Use an IP address for a device beyond that range. Stop and rescan are available.

## OneDrive and Google Drive

Click **Connect cloud storage**, choose Google Drive or OneDrive, then **Sign in with browser**. Google or Microsoft sign-in opens in your browser; account and drive choices appear inside ShareScout. No setup terminal or manually typed rclone remote name is needed. When sign-in completes, ShareScout saves the connection, chooses an available drive letter (Windows) or dedicated mount folder (Linux), connects and opens your files.

Already configured accounts appear in the same dialog: select one and click **Connect saved account**. Existing accounts are kept. New sign-ins use unique account names so they cannot overwrite another account. Cancel stops sign-in and removes the unfinished account created by that dialog. Browser sign-in times out after five minutes and can be retried. Cloud account setup uses rclone’s [application configuration protocol](https://rclone.org/commands/rclone_config_create/); use a current rclone version supporting `--non-interactive`.

Cloud drives remain mounted while the app is open. Disconnect cloud drives before closing and allow pending uploads to finish. This utility mounts cloud storage; it is not an offline backup client. Windows cloud mounts require WinFsp, Linux cloud mounts require FUSE. The setup scripts install these dependencies.

## Local settings

Connection names and locations are stored in `%LOCALAPPDATA%\ResourceMapper` on Windows or `~/.config/ResourceMapper` on Linux. Network passwords are saved only when you choose the system password store option. Linux uses the desktop keyring (`secret-tool`); Windows uses Credential Manager. Passwords are never stored in ShareScout settings or put in command arguments. Linux browsing passes a password only to the child process environment; Linux mounting passes credentials through stdin. Cloud OAuth tokens are managed by rclone’s configuration.

Use **Check required tools** if tools are missing. Windows installer logs appear in the initial setup terminal. Cloud logs are in the settings directory. Cloud cache size is a soft 2 GB limit; open files can exceed it.

## Verification and implementation

Run `python3 -m unittest discover -s tests`. Tests cover network detection, bounded scans, cancellation, share filtering, protected-server errors, encoded folder names, credential transport, and the choose-folder/save/connect/open flow. Tests use controlled discovery responses. Setup tests verify configuration preservation and backups, rejection of invalid configuration, existing-share repair, service/package choices, and scoped firewall commands. Current UI checks rendered 42 window layouts at the supported display test targets and verified bottom-button visibility and text width. Folder-sharing tests cover owned-path validation, configuration backups and preservation, duplicate names, staging failures, credential reuse, and CLI dispatch. Single-instance tests verify duplicate-launch blocking before Tk starts, authenticated window activation, stale metadata, and process-crash recovery. Windows locking still needs Windows-machine verification. File-manager tests check automatic detection, selective installation, fallback behavior, detection of newly added managers, action generation, existing Thunar actions, malformed configuration, repeated installation, XDG paths and literal argument transport. Actual context-menu visibility and remote folder access still require testing with the target file managers and devices. Live Samba provisioning, remote mapping, and Windows native API behavior still require target-machine testing. No real network scan or system Samba installation was run during development.

Linux share browsing uses [Samba smbclient](https://www.samba.org/samba/docs/current/man-html/smbclient.1.html) and mounting uses [GIO](https://docs.gtk.org/gio/method.File.mount_enclosing_volume.html). Windows uses the native [network share APIs](https://learn.microsoft.com/en-us/windows/win32/netshare/network-share-functions). Cloud mounts use [rclone](https://rclone.org/commands/rclone_mount/).

Sharing setup references: [Samba testparm](https://devel.samba.org/samba/docs/4.20/man-html/testparm.1.html), [firewalld rules](https://firewalld.org/documentation/man-pages/firewall-cmd.html), [Fedora SELinux Samba labeling](https://fedoraproject.org/wiki/SELinux/samba).

## Develop and build

Clone this repository and run `python3 -m unittest discover -s tests` from its root. No pip dependencies are required for the test suite; Python must include Tk. Linux runtime mounting also requires PyGObject/GIO and the system tools installed by the launch script.

To build the Debian package, run `python3 scripts/build_deb.py`. The script requires `ar` (binutils) and `desktop-file-validate` (desktop-file-utils). It writes an independently inspected package to `dist/resource-mapper_0.5.0_all.deb`. Fedora users should use `bash Launch-Linux.sh`; an RPM build is not included.

The existing ResourceMapper settings directory and package identifier are retained for compatibility with earlier builds. The application is now named ShareScout.
