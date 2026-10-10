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

#[tauri::command]
fn get_saved_resources() -> Vec<ResourceItem> {
    // Returns initial / saved resources
    vec![
        ResourceItem {
            name: "Family Photos".into(),
            kind: "Network share".into(),
            source: "smb://192.168.1.120/Family Photos".into(),
            target: Some("".into()),
            auto: true,
            status: "Connected".into(),
        },
        ResourceItem {
            name: "Google Drive".into(),
            kind: "Google Drive".into(),
            source: "Google Drive".into(),
            target: Some("~/ShareScout/Google Drive".into()),
            auto: true,
            status: "Connected".into(),
        },
        ResourceItem {
            name: "Backup NAS".into(),
            kind: "Network share".into(),
            source: "smb://192.168.1.200/Backup".into(),
            target: Some("".into()),
            auto: false,
            status: "Disconnected".into(),
        },
    ]
}

#[tauri::command]
fn save_resources(_items: Vec<ResourceItem>) -> bool {
    true
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
    vec![
        DiscoveredDevice {
            address: "192.168.1.120".into(),
            name: Some("Synology NAS".into()),
            category: Some("NAS".into()),
        },
        DiscoveredDevice {
            address: "192.168.1.155".into(),
            name: Some("LivingRoom-PC".into()),
            category: Some("Desktop".into()),
        },
        DiscoveredDevice {
            address: "192.168.1.180".into(),
            name: Some("Backup-Server".into()),
            category: Some("Server".into()),
        },
    ]
}

#[tauri::command]
fn list_device_shares(address: String) -> Vec<DiscoveredShare> {
    if address == "192.168.1.120" {
        vec![
            DiscoveredShare {
                name: "Family Photos".into(),
                comment: Some("Family memories and archives".into()),
                permission: Some("Read/Write".into()),
            },
            DiscoveredShare {
                name: "Public".into(),
                comment: Some("Shared public files".into()),
                permission: Some("Guest Access".into()),
            },
            DiscoveredShare {
                name: "Media".into(),
                comment: Some("Home streaming media".into()),
                permission: Some("Read Only".into()),
            },
        ]
    } else {
        vec![
            DiscoveredShare {
                name: "Documents".into(),
                comment: Some("User documents".into()),
                permission: Some("Read/Write".into()),
            },
            DiscoveredShare {
                name: "Shared".into(),
                comment: Some("General shared folder".into()),
                permission: Some("Read/Write".into()),
            },
        ]
    }
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
