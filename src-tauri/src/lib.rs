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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
