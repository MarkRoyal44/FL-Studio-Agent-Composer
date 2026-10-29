//! Agent Composer as a CLAP plugin. Pick it from FL Studio's Add menu (or the Channel rack) and
//! the chat window opens inside the plugin window, the way Claudian lives inside Obsidian.
//!
//! It's a generator that makes no sound. It is only a window: it starts the Agent Composer app
//! (app/server.py) if it isn't running, then shows its page in an embedded WebView2. FL itself is
//! still driven by the controller script, so everything works the same as the standalone window.
use nih_plug::prelude::*;
use raw_window_handle::{HandleError, HasWindowHandle, RawWindowHandle, Win32WindowHandle, WindowHandle};
use std::any::Any;
use std::num::NonZeroIsize;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Duration;

const WIDTH: u32 = 460;
const HEIGHT: u32 = 760;

fn port() -> u16 {
    std::env::var("AGENT_COMPOSER_PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(47800)
}

fn local_appdata() -> PathBuf {
    PathBuf::from(std::env::var("LOCALAPPDATA").unwrap_or_default())
}

/// Where AgentComposerSetup.exe put the app.
fn app_dir() -> PathBuf {
    std::env::var("AGENT_COMPOSER_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| local_appdata().join("Programs").join("Agent Composer"))
}

fn server_up() -> bool {
    let addr = std::net::SocketAddr::from(([127, 0, 0, 1], port()));
    std::net::TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

/// Start app/server.py with no window of its own, the same way start.bat does.
fn start_server() {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let dir = app_dir();
    let uv = PathBuf::from(std::env::var("USERPROFILE").unwrap_or_default()).join(".local\\bin\\uv.exe");
    let uv = if uv.is_file() { uv } else { PathBuf::from("uv") };
    let ok = std::process::Command::new(&uv)
        .args(["run", "--no-project", "--python", "3.12", "app\\server.py", "--no-open"])
        .current_dir(&dir)
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
        .is_ok();
    if !ok {
        let _ = std::process::Command::new("python")
            .args(["app\\server.py", "--no-open"])
            .current_dir(&dir)
            .creation_flags(CREATE_NO_WINDOW)
            .spawn();
    }
}

/// Shown while the app starts. It waits for the server, then swaps itself for the real page.
fn waiting_page(url: &str) -> String {
    format!(
        r#"<!doctype html><meta charset="utf-8"><body style="margin:0;background:#0b0d10;color:#c9d1d9;font:14px system-ui;display:grid;place-items:center;height:100vh">
<div style="text-align:center"><div style="font-weight:800;color:#8cc8f2;font-size:16px">Agent Composer</div>
<div id="t" style="margin-top:8px;color:#8b949e">Starting up…</div></div>
<script>let n=0;const go=()=>fetch("{url}api/health",{{mode:"no-cors"}}).then(()=>location.replace("{url}")).catch(()=>{{if(++n==40)document.getElementById("t").textContent="Still starting. If this stays, open Agent Composer from the Start menu once.";setTimeout(go,500)}});go()</script>"#
    )
}

struct Parent(NonZeroIsize);

impl HasWindowHandle for Parent {
    fn window_handle(&self) -> Result<WindowHandle<'_>, HandleError> {
        let raw = RawWindowHandle::Win32(Win32WindowHandle::new(self.0));
        Ok(unsafe { WindowHandle::borrow_raw(raw) })
    }
}

/// Keeps the webview alive while FL shows the plugin window; dropping it closes the page.
struct Open {
    _webview: wry::WebView,
    _context: wry::WebContext,
}
// The host creates and drops the editor on its GUI thread.
unsafe impl Send for Open {}

struct ChatEditor {
    scale: AtomicU32,
}

impl Editor for ChatEditor {
    fn spawn(&self, parent: ParentWindowHandle, _context: Arc<dyn GuiContext>) -> Box<dyn Any + Send> {
        let hwnd = match parent {
            ParentWindowHandle::Win32Hwnd(h) => h as isize,
            _ => 0,
        };
        let Some(hwnd) = NonZeroIsize::new(hwnd) else { return Box::new(()) };
        let url = format!("http://127.0.0.1:{}/", port());
        let up = server_up();
        if !up {
            start_server();
        }
        let scale = f32::from_bits(self.scale.load(Ordering::Relaxed));
        // WebView2 keeps its cache next to the exe by default, and FL lives in Program Files.
        let mut context = wry::WebContext::new(Some(local_appdata().join("Agent Composer").join("webview")));
        let bounds = wry::Rect {
            position: wry::dpi::PhysicalPosition::new(0, 0).into(),
            size: wry::dpi::PhysicalSize::new((WIDTH as f32 * scale) as u32, (HEIGHT as f32 * scale) as u32).into(),
        };
        let builder = wry::WebViewBuilder::new_with_web_context(&mut context).with_bounds(bounds);
        let builder = if up { builder.with_url(&url) } else { builder.with_html(waiting_page(&url)) };
        match builder.build_as_child(&Parent(hwnd)) {
            Ok(webview) => Box::new(Open { _webview: webview, _context: context }),
            Err(e) => {
                nih_error!("Agent Composer: couldn't open the webview: {e}");
                Box::new(())
            }
        }
    }

    fn size(&self) -> (u32, u32) {
        (WIDTH, HEIGHT)
    }

    fn set_scale_factor(&self, factor: f32) -> bool {
        self.scale.store(factor.to_bits(), Ordering::Relaxed);
        true
    }

    fn param_value_changed(&self, _id: &str, _normalized_value: f32) {}
    fn param_modulation_changed(&self, _id: &str, _modulation_offset: f32) {}
    fn param_values_changed(&self) {}
}

#[derive(Params, Default)]
struct NoParams {}

#[derive(Default)]
struct AgentComposer {
    params: Arc<NoParams>,
}

impl Plugin for AgentComposer {
    const NAME: &'static str = "Agent Composer";
    const VENDOR: &'static str = "Tech-Ants";
    const URL: &'static str = "https://github.com/MarkRoyal44/FL-Studio-Agent-Composer";
    const EMAIL: &'static str = "";
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");

    const AUDIO_IO_LAYOUTS: &'static [AudioIOLayout] = &[AudioIOLayout {
        main_input_channels: None,
        main_output_channels: NonZeroU32::new(2),
        aux_input_ports: &[],
        aux_output_ports: &[],
        names: PortNames::const_default(),
    }];
    const MIDI_INPUT: MidiConfig = MidiConfig::Basic;

    type SysExMessage = ();
    type BackgroundTask = ();

    fn params(&self) -> Arc<dyn Params> {
        self.params.clone()
    }

    fn editor(&mut self, _async_executor: AsyncExecutor<Self>) -> Option<Box<dyn Editor>> {
        Some(Box::new(ChatEditor { scale: AtomicU32::new(1.0f32.to_bits()) }))
    }

    fn process(&mut self, buffer: &mut Buffer, _aux: &mut AuxiliaryBuffers, _context: &mut impl ProcessContext<Self>) -> ProcessStatus {
        for channel in buffer.as_slice() {
            channel.fill(0.0); // makes no sound
        }
        ProcessStatus::Normal
    }
}

impl ClapPlugin for AgentComposer {
    const CLAP_ID: &'static str = "com.tech-ants.agent-composer";
    const CLAP_DESCRIPTION: Option<&'static str> = Some("Chat with an AI agent that works inside your FL Studio project");
    const CLAP_MANUAL_URL: Option<&'static str> = Some(Self::URL);
    const CLAP_SUPPORT_URL: Option<&'static str> = Some(Self::URL);
    const CLAP_FEATURES: &'static [ClapFeature] = &[ClapFeature::Instrument, ClapFeature::Stereo, ClapFeature::Utility];
}

nih_export_clap!(AgentComposer);
