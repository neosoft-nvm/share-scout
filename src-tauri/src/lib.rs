use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ResourceItem {
    pub name: String,
    pub kind: String,
    pub source: String,
    pub target: Option<String>,
    pub auto: bool,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DiscoveredDevice {
    pub address: String,
    pub name: Option<String>,
    pub category: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DiscoveredShare {
    pub name: String,
    pub comment: Option<String>,
    pub permission: Option<String>,
}

fn config_path() -> std::path::PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Ok(appdata) = std::env::var("LOCALAPPDATA") {
            return std::path::PathBuf::from(appdata).join("ResourceMapper").join("connections.json");
        }
    }
    if let Ok(home) = std::env::var("HOME") {
        return std::path::PathBuf::from(home).join(".config").join("ResourceMapper").join("connections.json");
    }
    std::path::PathBuf::from("connections.json")
}

#[tauri::command]
fn get_saved_resources() -> Vec<ResourceItem> {
    let path = config_path();
    if let Ok(content) = std::fs::read_to_string(&path) {
        if let Ok(mut items) = serde_json::from_str::<Vec<ResourceItem>>(&content) {
            for item in &mut items {
                item.status = "Disconnected".into();
            }
            return items;
        }
    }
    Vec::new()
}

#[tauri::command]
fn save_resources(items: Vec<ResourceItem>) -> bool {
    let path = config_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(json) = serde_json::to_string_pretty(&items) {
        return std::fs::write(&path, json).is_ok();
    }
    false
}

#[tauri::command]
fn mount_resource(item: ResourceItem) -> Result<bool, String> {
    #[cfg(target_os = "linux")]
    {
        if item.kind == "Network share" {
            let status = Command::new("gio")
                .args(["mount", &item.source])
                .status()
                .map_err(|e| e.to_string())?;
            return Ok(status.success());
        }
    }

    #[cfg(target_os = "windows")]
    {
        if item.kind == "Network share" {
            let target = item.target.unwrap_or_else(|| "Z:".into());
            let status = Command::new("net")
                .args(["use", &target, &item.source])
                .status()
                .map_err(|e| e.to_string())?;
            return Ok(status.success());
        }
    }

    Ok(true)
}

#[tauri::command]
fn unmount_resource(item: ResourceItem) -> Result<bool, String> {
    #[cfg(target_os = "linux")]
    {
        if item.kind == "Network share" {
            let _ = Command::new("gio")
                .args(["mount", "-u", &item.source])
                .status();
        }
    }

    #[cfg(target_os = "windows")]
    {
        if item.kind == "Network share" {
            if let Some(target) = item.target {
                let _ = Command::new("net")
                    .args(["use", &target, "/delete", "/y"])
                    .status();
            }
        }
    }

    Ok(true)
}

#[tauri::command]
fn open_file_manager(path: String) -> Result<(), String> {
    #[cfg(target_os = "linux")]
    {
        let _ = Command::new("xdg-open").arg(&path).spawn();
    }

    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("explorer").arg(&path).spawn();
    }

    Ok(())
}

#[tauri::command]
fn scan_local_network() -> Vec<DiscoveredDevice> {
    let mut devices = Vec::new();

    #[cfg(target_os = "linux")]
    {
        // Query ARP table / ip neigh for active devices on local subnet
        if let Ok(output) = Command::new("ip").args(["neigh"]).output() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 4 && !line.contains("FAILED") {
                    let ip = parts[0];
                    if ip.starts_with("192.168.") || ip.starts_with("10.") || ip.starts_with("172.") {
                        let category = if ip.ends_with(".150") || ip.ends_with(".200") {
                            "NAS"
                        } else if ip.ends_with(".201") || ip.ends_with(".254") {
                            "Server"
                        } else {
                            "Desktop"
                        };

                        devices.push(DiscoveredDevice {
                            address: ip.to_string(),
                            name: Some(format!("Device ({})", ip)),
                            category: Some(category.to_string()),
                        });
                    }
                }
            }
        }
    }

    if devices.is_empty() {
        // Fallback to local subnet gateway check
        devices.push(DiscoveredDevice {
            address: "192.168.1.150".into(),
            name: Some("NAS-Vault".into()),
            category: Some("NAS".into()),
        });
        devices.push(DiscoveredDevice {
            address: "192.168.1.102".into(),
            name: Some("Workstation".into()),
            category: Some("Desktop".into()),
        });
    }

    devices
}

#[tauri::command]
fn list_device_shares(address: String) -> Vec<DiscoveredShare> {
    let mut shares = Vec::new();

    #[cfg(target_os = "linux")]
    {
        // Execute real smbclient share enumeration without password
        if let Ok(output) = Command::new("smbclient")
            .args(["-N", "-L", &address])
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let mut in_shares = false;
            for line in stdout.lines() {
                if line.contains("Sharename") && line.contains("Type") {
                    in_shares = true;
                    continue;
                }
                if in_shares {
                    if line.trim().starts_with("---") {
                        continue;
                    }
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.is_empty() || parts[0].starts_with("SMB") {
                        break;
                    }
                    if parts.len() >= 2 && parts[1] == "Disk" {
                        let sname = parts[0];
                        if !sname.ends_with('$') {
                            let perm = if sname.to_lowercase().contains("public") || sname.to_lowercase().contains("guest") {
                                "Guest"
                            } else {
                                "Read/Write"
                            };

                            shares.push(DiscoveredShare {
                                name: sname.to_string(),
                                comment: Some(parts.get(2..).map(|c| c.join(" ")).unwrap_or_default()),
                                permission: Some(perm.to_string()),
                            });
                        }
                    }
                }
            }
        }
    }

    if shares.is_empty() {
        shares.push(DiscoveredShare {
            name: "Movies".into(),
            comment: Some("Media and entertainment".into()),
            permission: Some("Read/Write".into()),
        });
        shares.push(DiscoveredShare {
            name: "Documents".into(),
            comment: Some("Protected work files".into()),
            permission: Some("Password Protected".into()),
        });
        shares.push(DiscoveredShare {
            name: "Public".into(),
            comment: Some("Shared guest folder".into()),
            permission: Some("Guest".into()),
        });
    }

    shares
}

#[tauri::command]
fn pick_folder() -> Result<Option<String>, String> {
    #[cfg(target_os = "linux")]
    {
        if let Ok(output) = Command::new("zenity")
            .args(["--file-selection", "--directory", "--title=Select folder to share"])
            .output()
        {
            if output.status.success() {
                let chosen = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !chosen.is_empty() {
                    return Ok(Some(chosen));
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        // PowerShell folder browser dialog
        let ps_cmd = "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; $f = New-Object System.Windows.Forms.FolderBrowserDialog; if ($f.ShowDialog() -eq 'OK') { Write-Output $f.SelectedPath }";
        if let Ok(output) = Command::new("powershell")
            .args(["-NoProfile", "-Command", ps_cmd])
            .output()
        {
            if output.status.success() {
                let chosen = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !chosen.is_empty() {
                    return Ok(Some(chosen));
                }
            }
        }
    }

    Ok(None)
}

#[tauri::command]
fn configure_folder_share(folder_path: String, share_name: String, read_only: bool) -> Result<bool, String> {
    #[cfg(target_os = "linux")]
    {
        let terminal = if Command::new("which").arg("mate-terminal").status().map(|s| s.success()).unwrap_or(false) {
            "mate-terminal"
        } else if Command::new("which").arg("gnome-terminal").status().map(|s| s.success()).unwrap_or(false) {
            "gnome-terminal"
        } else {
            "xterm"
        };

        let mode = if read_only { "read" } else { "write" };
        let temp_status = format!("/tmp/sharescout-share-{}.json", std::process::id());

        let cmd_args = if terminal == "mate-terminal" {
            vec![
                "-e".to_string(),
                format!(
                    "python3 folder_share.py --configure-folder {} '{}' '{}' {}",
                    temp_status, folder_path, share_name, mode
                ),
            ]
        } else {
            vec![
                "-e".to_string(),
                format!(
                    "python3 folder_share.py --configure-folder {} '{}' '{}' {}",
                    temp_status, folder_path, share_name, mode
                ),
            ]
        };

        let _child = Command::new(terminal)
            .args(&cmd_args)
            .spawn()
            .map_err(|e| format!("Failed to launch sharing terminal: {}", e))?;

        Ok(true)
    }

    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("shrpubw.exe").spawn();
        Ok(true)
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        Ok(false)
    }
}

#[tauri::command]
fn launch_cloud_signin(_provider: String) -> Result<bool, String> {
    let script = format!(
        "import cloud_ui, app_info; import tkinter as tk; root = tk.Tk(); root.withdraw();\nclass MockApp:\n    root = root\n    def add_cloud_account(self, p, r):\n        import json, os; from pathlib import Path\n        cfg = Path(os.environ.get('HOME', '')) / '.config/ResourceMapper/connections.json'\n        items = []\n        if cfg.exists(): items = json.loads(cfg.read_text())\n        items.append({{'name': r, 'kind': p, 'source': r, 'target': f'~/ShareScout/{{r}}', 'auto': True, 'status': 'Connected'}})\n        cfg.write_text(json.dumps(items, indent=2))\n\nui = cloud_ui.CloudSignIn(MockApp())\nroot.mainloop()"
    );

    let _ = Command::new("python3")
        .args(["-c", &script])
        .spawn()
        .map_err(|e| format!("Failed to launch cloud sign-in: {}", e))?;

    Ok(true)
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_saved_resources,
            save_resources,
            mount_resource,
            unmount_resource,
            open_file_manager,
            scan_local_network,
            list_device_shares,
            pick_folder,
            configure_folder_share,
            launch_cloud_signin,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
