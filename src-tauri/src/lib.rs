#[cfg(all(not(debug_assertions), not(feature = "custom-protocol")))]
compile_error!("Production builds must enable custom-protocol to embed the ShareScout interface.");

use serde_json::{json, Value};
use std::{
    collections::HashMap,
    io::{BufRead, BufReader, Write},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{mpsc, Arc, Mutex},
    time::Duration,
};
use tauri::Manager;

type Reply = Result<Value, Value>;
type Pending = Arc<Mutex<HashMap<u64, mpsc::Sender<Reply>>>>;

struct Bridge {
    input: Mutex<ChildStdin>,
    child: Mutex<Child>,
    pending: Pending,
    next: std::sync::atomic::AtomicU64,
}

fn failure(message: impl ToString) -> Value {
    json!({"message": message.to_string(), "auth": false})
}

impl Bridge {
    fn start(
        script: &std::path::Path,
        app: tauri::AppHandle,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        #[cfg(target_os = "windows")]
        let mut command = {
            use std::os::windows::process::CommandExt;
            let available = Command::new("py")
                .args(["-3", "--version"])
                .creation_flags(0x08000000)
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false);
            if available {
                let mut command = Command::new("py");
                command.arg("-3");
                command
            } else {
                Command::new("python")
            }
        };
        #[cfg(not(target_os = "windows"))]
        let mut command = Command::new("/usr/bin/python3");
        command
            .arg("-u")
            .arg(script)
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut child = command.spawn()?;
        let input = child.stdin.take().ok_or("Backend stdin unavailable")?;
        let output = child.stdout.take().ok_or("Backend stdout unavailable")?;
        let pending: Pending = Arc::new(Mutex::new(HashMap::new()));
        let responses = pending.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(output).lines() {
                let Ok(line) = line else { break };
                let Ok(response) = serde_json::from_str::<Value>(&line) else {
                    continue;
                };
                if response["event"] == "already_running" {
                    app.exit(0);
                    break;
                }
                if response["event"] == "activate" {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                    continue;
                }
                if let Some(id) = response["id"].as_u64() {
                    if let Some(sender) = responses.lock().unwrap().remove(&id) {
                        let reply = if let Some(error) = response.get("error") {
                            Err(error.clone())
                        } else {
                            Ok(response["result"].clone())
                        };
                        let _ = sender.send(reply);
                    }
                }
            }
            for (_, sender) in responses.lock().unwrap().drain() {
                let _ = sender.send(Err(failure(
                    "The desktop service stopped. Restart ShareScout.",
                )));
            }
        });
        Ok(Self {
            input: Mutex::new(input),
            child: Mutex::new(child),
            pending,
            next: std::sync::atomic::AtomicU64::new(1),
        })
    }

    fn call(&self, method: &str, args: Value) -> Reply {
        let id = self.next.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let (sender, receiver) = mpsc::channel();
        self.pending.lock().unwrap().insert(id, sender);
        let message = json!({"id": id, "method": method, "args": args});
        let write = {
            let mut input = self.input.lock().unwrap();
            writeln!(input, "{}", message).and_then(|_| input.flush())
        };
        if write.is_err() {
            self.pending.lock().unwrap().remove(&id);
            return Err(failure(
                "The desktop service is unavailable. Restart ShareScout.",
            ));
        }
        let reply = receiver
            .recv_timeout(Duration::from_secs(660))
            .unwrap_or_else(|_| {
                Err(failure(
                    "The operation timed out. Restart ShareScout before retrying.",
                ))
            });
        self.pending.lock().unwrap().remove(&id);
        reply
    }
}

impl Drop for Bridge {
    fn drop(&mut self) {
        if let Ok(child) = self.child.get_mut() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

// Run blocking OS operations away from the window thread. Only allow known operations.
#[tauri::command]
async fn desktop_call(app: tauri::AppHandle, method: String, args: Value) -> Reply {
    let allowed = [
        "load",
        "save",
        "mount",
        "unmount",
        "open",
        "scan",
        "stop_scan",
        "shares",
        "cloud_accounts",
        "cloud_start",
        "cloud_step",
        "cloud_cancel",
        "cloud_finish",
        "defaults",
        "pick_folder",
        "share",
        "diagnostics",
        "network_info",
        "repair",
        "check_updates",
        "startup_update",
        "update_preference",
        "prepare_update",
        "install_update",
        "shutdown",
    ];
    if !allowed.contains(&method.as_str()) {
        return Err(failure("Unsupported desktop operation."));
    }
    let installing = method == "install_update";
    let handle = app.clone();
    let result =
        tauri::async_runtime::spawn_blocking(move || app.state::<Bridge>().call(&method, args))
            .await
            .map_err(failure)?;
    if installing && result.is_ok() {
        handle.exit(0);
    }
    result
}

fn screen_size(width: u32, height: u32, scale: f64) -> (f64, f64) {
    (
        (width as f64 / scale - 32.0).clamp(200.0, 940.0),
        (height as f64 / scale - 32.0).clamp(180.0, 680.0),
    )
}

fn fit_window(window: &tauri::Window) -> tauri::Result<()> {
    if let Some(monitor) = window.current_monitor()? {
        let area = monitor.work_area();
        let (width, height) =
            screen_size(area.size.width, area.size.height, monitor.scale_factor());
        window.set_min_size(Some(tauri::LogicalSize::new(
            width.min(720.0),
            height.min(500.0),
        )))?;
        window.set_size(tauri::LogicalSize::new(width, height))?;
        window.center()?;
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::ScaleFactorChanged { .. }) {
                let _ = fit_window(window);
            }
        })
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                fit_window(&window.as_ref().window())?;
            }
            let beside = std::env::current_exe()?
                .parent()
                .ok_or("Executable directory unavailable")?
                .join("backend/desktop_service.py");
            let bundled = if beside.is_file() {
                beside
            } else {
                app.path()
                    .resource_dir()?
                    .join("backend/desktop_service.py")
            };
            #[cfg(debug_assertions)]
            let script =
                std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../desktop_service.py");
            #[cfg(not(debug_assertions))]
            let script = bundled;
            #[cfg(debug_assertions)]
            let _ = bundled;
            app.manage(Bridge::start(&script, app.handle().clone())?);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![desktop_call])
        .run(tauri::generate_context!())
        .expect("error while running ShareScout");
}

#[cfg(test)]
mod tests {
    use super::screen_size;
    #[cfg(feature = "custom-protocol")]
    #[test]
    fn production_interface_is_embedded() {
        let context: tauri::Context<tauri::Wry> = tauri::generate_context!();
        let index = context
            .assets()
            .get(&"index.html".into())
            .expect("Production index.html must be embedded");
        assert!(String::from_utf8_lossy(&index).contains("/assets/"));
        assert!(context.assets().iter().any(|(path, _)| path
            .trim_start_matches('/')
            .starts_with("assets/")
            && path.ends_with(".js")));
    }
    #[test]
    fn scaled_720p_window_fits_available_display() {
        for scale in [1.0, 1.5, 2.0] {
            let (width, height) = screen_size(1280, 720, scale);
            assert!(width * scale < 1280.0);
            assert!(height * scale < 720.0);
        }
    }
    #[test]
    fn four_k_uses_standard_bounded_window_size() {
        for scale in [1.0, 1.5, 2.0] {
            assert_eq!(screen_size(3840, 2160, scale), (940.0, 680.0));
        }
    }
}
