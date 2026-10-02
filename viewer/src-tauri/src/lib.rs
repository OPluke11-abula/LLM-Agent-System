use notify::{recommended_watcher, Event, RecursiveMode, Watcher};
use serde_json::Value;
use std::{
    fs,
    path::{Path, PathBuf},
    sync::mpsc,
    thread,
};
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager,
};

fn workspace_dir() -> PathBuf {
    let p = std::env::var("AGENT_WORKSPACE_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            std::env::current_dir()
                .unwrap_or_else(|_| PathBuf::from("."))
                .join("..")
                .join("workspace")
        });
    let _ = fs::create_dir_all(&p);
    p
}

fn agent_memory_path() -> PathBuf {
    workspace_dir().join("agent_memory.json")
}

fn topology_state_path() -> PathBuf {
    workspace_dir().join("topology_state.json")
}

fn read_agent_memory(path: &Path) -> Result<Value, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

fn read_topology_state(path: &Path) -> Result<Value, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

#[tauri::command]
fn save_agent_memory(memory: Value) -> Result<(), String> {
    let path = agent_memory_path();
    let json = serde_json::to_string_pretty(&memory).map_err(|error| error.to_string())?;
    fs::write(&path, json).map_err(|error| error.to_string())
}

fn emit_agent_memory_update(app_handle: &AppHandle, path: &Path) {
    match read_agent_memory(path) {
        Ok(agent_memory) => {
            let _ = app_handle.emit("agent_memory_updated", agent_memory);
        }
        Err(error) => {
            eprintln!("Failed to read agent_memory.json: {error}");
        }
    }
}

fn emit_topology_state_update(app_handle: &AppHandle, path: &Path) {
    match read_topology_state(path) {
        Ok(topology_state) => {
            let _ = app_handle.emit("topology_updated", topology_state);
        }
        Err(error) => {
            eprintln!("Failed to read topology_state.json: {error}");
        }
    }
}

fn is_agent_memory_event(event: &Event) -> bool {
    event.paths.iter().any(|path| {
        path.file_name()
            .and_then(|file_name| file_name.to_str())
            .map(|file_name| file_name == "agent_memory.json")
            .unwrap_or(false)
    })
}

fn is_topology_state_event(event: &Event) -> bool {
    event.paths.iter().any(|path| {
        path.file_name()
            .and_then(|file_name| file_name.to_str())
            .map(|file_name| file_name == "topology_state.json")
            .unwrap_or(false)
    })
}

fn watch_agent_memory(app_handle: AppHandle) {
    let workspace = workspace_dir();
    let memory_path = workspace.join("agent_memory.json");

    thread::spawn(move || {
        let (tx, rx) = mpsc::channel();

        let mut watcher = match recommended_watcher(move |result| {
            let _ = tx.send(result);
        }) {
            Ok(watcher) => watcher,
            Err(error) => {
                eprintln!("Failed to initialize file watcher: {error}");
                return;
            }
        };

        if let Err(error) = watcher.watch(&workspace, RecursiveMode::NonRecursive) {
            eprintln!("Failed to watch workspace directory: {error}");
            return;
        }

        emit_agent_memory_update(&app_handle, &memory_path);

        for event in rx {
            match event {
                Ok(file_event) if is_agent_memory_event(&file_event) => {
                    emit_agent_memory_update(&app_handle, &memory_path);
                }
                Ok(_) => {}
                Err(error) => {
                    eprintln!("File watcher event error: {error}");
                }
            }
        }
    });
}
fn watch_topology_state(app_handle: AppHandle) {
    let workspace = workspace_dir();
    let topology_path = workspace.join("topology_state.json");

    thread::spawn(move || {
        let (tx, rx) = mpsc::channel();

        let mut watcher = match recommended_watcher(move |result| {
            let _ = tx.send(result);
        }) {
            Ok(watcher) => watcher,
            Err(error) => {
                eprintln!("Failed to initialize topology file watcher: {error}");
                return;
            }
        };

        if let Err(error) = watcher.watch(&workspace, RecursiveMode::NonRecursive) {
            eprintln!("Failed to watch workspace directory for topology state: {error}");
            return;
        }

        emit_topology_state_update(&app_handle, &topology_path);

        for event in rx {
            match event {
                Ok(file_event) if is_topology_state_event(&file_event) => {
                    emit_topology_state_update(&app_handle, &topology_path);
                }
                Ok(_) => {}
                Err(error) => {
                    eprintln!("Topology file watcher event error: {error}");
                }
            }
        }
    });
}

#[tauri::command]
fn load_agent_memory() -> Result<Value, String> {
    read_agent_memory(&agent_memory_path())
}

#[tauri::command]
fn load_topology_state() -> Result<Value, String> {
    read_topology_state(&topology_state_path())
}

#[tauri::command]
fn load_agent_memory_from(path: String) -> Result<Value, String> {
    let p = PathBuf::from(&path).join("agent_memory.json");
    read_agent_memory(&p)
}

#[tauri::command]
fn save_agent_memory_to(path: String, memory: Value) -> Result<(), String> {
    let dir = PathBuf::from(&path);
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let json = serde_json::to_string_pretty(&memory).map_err(|e| e.to_string())?;
    fs::write(dir.join("agent_memory.json"), json).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_workspace_file(path: String, filename: String, content: String) -> Result<(), String> {
    let dir = PathBuf::from(&path);
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    fs::write(dir.join(filename), content).map_err(|e| e.to_string())
}

#[tauri::command]
fn open_dashboard_window(app_handle: AppHandle, session_id: String, role: String) -> Result<(), String> {
    use tauri::Manager;
    let label = format!("{}-window", role.to_lowercase());
    let url_str = format!("http://localhost:8000/v1/dashboard/{}/{}", session_id, role.to_lowercase());
    let url = tauri::Url::parse(&url_str).map_err(|e| e.to_string())?;

    if let Some(window) = app_handle.get_webview_window(&label) {
        window.navigate(url).map_err(|e| e.to_string())?;
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    } else {
        tauri::WebviewWindowBuilder::new(&app_handle, &label, tauri::WebviewUrl::External(url))
            .title(&format!("{} Dashboard", role))
            .inner_size(1000.0, 700.0)
            .build()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn toggle_companion_window(app_handle: AppHandle) -> Result<(), String> {
    use tauri::Manager;
    if let Some(window) = app_handle.get_webview_window("companion-window") {
        let is_visible = window.is_visible().map_err(|e| e.to_string())?;
        if is_visible {
            window.hide().map_err(|e| e.to_string())?;
        } else {
            window.show().map_err(|e| e.to_string())?;
            window.set_focus().map_err(|e| e.to_string())?;
        }
    } else {
        let url = tauri::WebviewUrl::App("index.html#/companion".into());
        tauri::WebviewWindowBuilder::new(&app_handle, "companion-window", url)
            .title("LAS Ambient Companion")
            .inner_size(400.0, 240.0)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .resizable(false)
            .skip_taskbar(true)
            .build()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn update_tray_status(app_handle: AppHandle, status: String, tooltip: Option<String>) -> Result<(), String> {
    if let Some(tray) = app_handle.tray_by_id("main-tray") {
        let label = tooltip.unwrap_or_else(|| format!("LAS Agent: {}", status));
        let _ = tray.set_tooltip(Some(label));
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            watch_agent_memory(app.handle().clone());
            watch_topology_state(app.handle().clone());

            let show_cockpit = MenuItem::with_id(app, "show_cockpit", "Open Mission Cockpit", true, None::<&str>)?;
            let toggle_companion = MenuItem::with_id(app, "toggle_companion", "Toggle Ambient Companion", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit LAS", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_cockpit, &toggle_companion, &quit])?;

            if let Some(icon) = app.default_window_icon() {
                let _ = TrayIconBuilder::with_id("main-tray")
                    .tooltip("LAS - AI Mission Control")
                    .icon(icon.clone())
                    .menu(&menu)
                    .on_menu_event(|app, event| {
                        match event.id().as_ref() {
                            "show_cockpit" => {
                                if let Some(window) = app.get_webview_window("main") {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                            "toggle_companion" => {
                                let _ = toggle_companion_window(app.clone());
                            }
                            "quit" => {
                                app.exit(0);
                            }
                            _ => {}
                        }
                    })
                    .on_tray_icon_event(|tray, event| {
                        if let TrayIconEvent::Click {
                            button: MouseButton::Left,
                            button_state: MouseButtonState::Up,
                            ..
                        } = event {
                            let app = tray.app_handle();
                            let _ = toggle_companion_window(app.clone());
                        }
                    })
                    .build(app)?;
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            load_agent_memory,
            load_topology_state,
            load_agent_memory_from,
            save_agent_memory,
            save_agent_memory_to,
            save_workspace_file,
            open_dashboard_window,
            toggle_companion_window,
            update_tray_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
