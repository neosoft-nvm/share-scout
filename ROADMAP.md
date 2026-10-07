# ShareScout roadmap

ShareScout connects people to shared resources across PCs, storage devices, and cloud services. Desktop PCs and laptops are both part of the current Linux and Windows scope.

## Current foundation

- Discover compatible SMB devices on connected IPv4 networks and list their shared folders.
- Connect folders from Linux and Windows PCs, with remembered connections.
- Connect OneDrive and Google Drive through rclone.
- Offer optional Samba sharing setup on Linux PCs.
- Keep discovery, sign-in, and connection controls usable on small and scaled displays.

## Future Android support

An Android client or companion is a future project target. It is not included in the current release. The intended experience is to discover compatible shared resources, select a folder, sign in when needed, and access files through a simple mobile interface.

Before implementation, define and validate:

- Mobile network discovery and manual IP fallback.
- How users browse, open, upload, and download files on Android.
- Secure handling of account credentials and cloud sign-in.
- How saved connections behave across network changes and app restarts.
- A touch-friendly interface and testing on real Android devices.

Providing shared folders from an Android device is a separate capability to assess. Android access should use a platform-appropriate experience; desktop drive letters and Linux mounts are not a promised mobile feature.

## Release expectations

Keep implemented capabilities separate from planned targets. Validate real network connections and platform behavior before claiming support for a new platform or device category.
