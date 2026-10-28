#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Set before WebKit starts any threads; respect explicit user overrides.
    #[cfg(target_os = "linux")]
    if std::env::var_os("WEBKIT_DISABLE_DMABUF_RENDERER").is_none()
        && std::path::Path::new("/sys/module/nvidia").exists()
    {
        std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    }
    share_scout_lib::run();
}
