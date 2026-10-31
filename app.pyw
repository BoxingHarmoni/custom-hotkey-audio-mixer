import os
import sys
import threading
import ctypes
from ctypes import wintypes
from PIL import Image, ImageDraw
import pystray
import customtkinter as ctk
import comtypes
from pycaw.pycaw import AudioUtilities
import keyboard

# Safe stdio for pythonw
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

FRIENDLY_NAMES = {
    "millidaminecraft.exe": "Minecraft",
    "minecraft.exe": "Minecraft",
    "javaw.exe": "Minecraft",
    "java.exe": "Minecraft",
    "firefox.exe": "Firefox",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "opera.exe": "Opera",
    "brave.exe": "Brave",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "telegram.exe": "Telegram",
    "steam.exe": "Steam",
    "vlc.exe": "VLC Media Player",
    "obs64.exe": "OBS Studio",
    "yandexmusic.exe": "Яндекс Музыка",
    "browser.exe": "Яндекс Браузер",
    "antigravity.exe": "Antigravity",
    "windhawk.exe": "Windhawk",
}

APP_ICONS = {
    "minecraft": "🎮",
    "firefox": "🦊",
    "chrome": "🌐",
    "edge": "🌐",
    "opera": "🌐",
    "brave": "🦁",
    "discord": "💬",
    "spotify": "🎵",
    "telegram": "✈️",
    "steam": "🕹️",
    "vlc": "🎬",
    "музыка": "🎵",
    "music": "🎵",
    "obs": "📹"
}

def get_app_display(name_lower):
    for k, v in FRIENDLY_NAMES.items():
        if k in name_lower:
            return v
    return name_lower.replace(".exe", "").capitalize()

def get_app_icon(display_name):
    d_lower = display_name.lower()
    for k, icon in APP_ICONS.items():
        if k in d_lower:
            return icon
    return "🔊"

def get_startup_shortcut_path():
    return os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AltMixer.lnk")

def is_autostart_active():
    return os.path.exists(get_startup_shortcut_path())

def set_autostart(enable=True):
    lnk = get_startup_shortcut_path()
    if enable:
        if not os.path.exists(lnk):
            try:
                # Copy from app folder
                src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AltMixer.lnk")
                if os.path.exists(src):
                    import shutil
                    shutil.copyfile(src, lnk)
            except Exception:
                pass
    else:
        if os.path.exists(lnk):
            try:
                os.remove(lnk)
            except Exception:
                pass


class QuickMixerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AltMixer")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Window properties
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Transparent background trick for smooth rounded corners
        TRANS_COLOR = "#000001"
        self.wm_attributes("-transparentcolor", TRANS_COLOR)
        self.configure(fg_color=TRANS_COLOR)

        self.width = 410
        self.height = 510
        self.is_visible = False
        self.is_updating_ui = False

        # Build UI layout
        self.setup_ui()

        # Keyboard shortcuts inside window
        self.bind("<Escape>", lambda e: self.hide_window())

        # Low-level keyboard hook
        self.start_keyboard_hook()

        # Tray icon
        self.start_tray()

        # Apply Windows 11 DWM rounded corners
        self.after(50, self.apply_dwm_rounding)

        # Ensure autostart shortcut exists
        if not is_autostart_active():
            set_autostart(True)

    def apply_dwm_rounding(self):
        try:
            hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            preference = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference)
            )
        except Exception:
            pass

    def setup_ui(self):
        # Outer Card with rounded border & smooth dark background
        self.card = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color="#181820",
            border_width=1,
            border_color="#2e2e3d"
        )
        self.card.pack(fill="both", expand=True, padx=6, pady=6)

        # Header Frame
        header = ctk.CTkFrame(self.card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text="🔊  Микшер звука",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f4f4f5"
        )
        title_lbl.pack(side="left")

        close_btn = ctk.CTkButton(
            header,
            text="✕",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#242430",
            hover_color="#ef4444",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.hide_window
        )
        close_btn.pack(side="right")

        # Master Volume Card
        self.master_frame = ctk.CTkFrame(
            self.card,
            corner_radius=14,
            fg_color="#20202a",
            border_width=1,
            border_color="#323242"
        )
        self.master_frame.pack(fill="x", padx=14, pady=6)

        m_top = ctk.CTkFrame(self.master_frame, fg_color="transparent")
        m_top.pack(fill="x", padx=12, pady=(8, 2))

        m_title = ctk.CTkLabel(
            m_top,
            text="🎧  Общая громкость",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e4e4e7"
        )
        m_title.pack(side="left")

        self.master_pct_lbl = ctk.CTkLabel(
            m_top,
            text="100%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        self.master_pct_lbl.pack(side="right")

        m_bot = ctk.CTkFrame(self.master_frame, fg_color="transparent")
        m_bot.pack(fill="x", padx=10, pady=(2, 8))

        self.master_mute_btn = ctk.CTkButton(
            m_bot,
            text="🔊",
            width=36,
            height=32,
            corner_radius=8,
            fg_color="#2d2d3c",
            hover_color="#3b82f6",
            font=ctk.CTkFont(size=14),
            command=self.toggle_master_mute
        )
        self.master_mute_btn.pack(side="left", padx=(0, 8))

        self.master_slider = ctk.CTkSlider(
            m_bot,
            from_=0,
            to=100,
            number_of_steps=100,
            progress_color="#38bdf8",
            button_color="#0284c7",
            button_hover_color="#38bdf8",
            command=self.on_master_slider_change
        )
        self.master_slider.pack(side="left", fill="x", expand=True)
        self.master_slider.bind("<MouseWheel>", lambda e: self.on_slider_wheel(self.master_slider, e, self.on_master_slider_change))

        # Apps Section Title
        apps_title_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        apps_title_frame.pack(fill="x", padx=16, pady=(10, 4))

        apps_lbl = ctk.CTkLabel(
            apps_title_frame,
            text="ПРИЛОЖЕНИЯ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa"
        )
        apps_lbl.pack(side="left")

        # Scrollable App List
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.card,
            fg_color="transparent",
            corner_radius=10
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=4)

        # Footer hint
        footer = ctk.CTkFrame(self.card, fg_color="transparent")
        footer.pack(fill="x", padx=14, pady=(4, 10))

        hint_lbl = ctk.CTkLabel(
            footer,
            text="[Правый Alt] или [F8] — открыть / скрыть | [Esc] — закрыть",
            font=ctk.CTkFont(size=11),
            text_color="#71717a"
        )
        hint_lbl.pack(side="left")

    def get_screen_position(self):
        rect = RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        x = rect.right - self.width - 16
        y = rect.bottom - self.height - 16
        return x, y

    def show_window(self):
        try:
            comtypes.CoInitialize()
            self.refresh_audio_sessions()
        except Exception:
            pass
        x, y = self.get_screen_position()
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.is_visible = True
        self.apply_dwm_rounding()

    def hide_window(self):
        self.withdraw()
        self.is_visible = False

    def toggle_window(self):
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()

    def on_slider_wheel(self, slider, event, callback):
        delta = 4 if event.delta > 0 else -4
        new_val = max(0, min(100, slider.get() + delta))
        slider.set(new_val)
        callback(new_val)

    # --- Master Volume Controls ---
    def toggle_master_mute(self):
        try:
            comtypes.CoInitialize()
            speakers = AudioUtilities.GetSpeakers()
            muted = speakers.EndpointVolume.GetMute()
            speakers.EndpointVolume.SetMute(not muted, None)
            self.update_master_ui()
        except Exception:
            pass

    def on_master_slider_change(self, val):
        if self.is_updating_ui:
            return
        try:
            comtypes.CoInitialize()
            speakers = AudioUtilities.GetSpeakers()
            scalar = max(0.0, min(1.0, float(val) / 100.0))
            speakers.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)
            self.master_pct_lbl.configure(text=f"{int(val)}%")
            if scalar > 0 and speakers.EndpointVolume.GetMute():
                speakers.EndpointVolume.SetMute(0, None)
                self.master_mute_btn.configure(text="🔊", fg_color="#2d2d3c")
        except Exception:
            pass

    def update_master_ui(self):
        try:
            comtypes.CoInitialize()
            speakers = AudioUtilities.GetSpeakers()
            vol = round(speakers.EndpointVolume.GetMasterVolumeLevelScalar() * 100)
            muted = bool(speakers.EndpointVolume.GetMute())
            self.is_updating_ui = True
            self.master_slider.set(vol)
            self.master_pct_lbl.configure(text=f"{vol}%")
            self.master_mute_btn.configure(
                text="🔇" if muted else "🔊",
                fg_color="#ef4444" if muted else "#2d2d3c"
            )
            self.is_updating_ui = False
        except Exception:
            pass

    # --- App Volume Controls ---
    def toggle_app_mute(self, proc_name, s_list, btn):
        try:
            comtypes.CoInitialize()
            is_muted = False
            for s in s_list:
                try:
                    if s.SimpleAudioVolume.GetMute():
                        is_muted = True
                        break
                except Exception:
                    pass
            new_mute = not is_muted
            for s in s_list:
                try:
                    s.SimpleAudioVolume.SetMute(new_mute, None)
                except Exception:
                    pass
            btn.configure(
                text="🔇" if new_mute else "🔊",
                fg_color="#ef4444" if new_mute else "#262635"
            )
        except Exception:
            pass

    def on_app_slider_change(self, val, proc_name, s_list, lbl, mute_btn):
        if self.is_updating_ui:
            return
        try:
            comtypes.CoInitialize()
            scalar = max(0.0, min(1.0, float(val) / 100.0))
            for s in s_list:
                try:
                    s.SimpleAudioVolume.SetMasterVolume(scalar, None)
                    if scalar > 0 and s.SimpleAudioVolume.GetMute():
                        s.SimpleAudioVolume.SetMute(0, None)
                except Exception:
                    pass
            lbl.configure(text=f"{int(val)}%")
            mute_btn.configure(text="🔊", fg_color="#262635")
        except Exception:
            pass

    def refresh_audio_sessions(self):
        self.update_master_ui()
        try:
            comtypes.CoInitialize()
            sessions = AudioUtilities.GetAllSessions()
            grouped = {}
            for s in sessions:
                if s.Process:
                    try:
                        pname = s.Process.name()
                        pname_lower = pname.lower()
                        if pname_lower not in grouped:
                            grouped[pname_lower] = {"name": pname, "sessions": []}
                        grouped[pname_lower]["sessions"].append(s)
                    except Exception:
                        pass

            for widget in self.scroll_frame.winfo_children():
                widget.destroy()

            if not grouped:
                no_apps = ctk.CTkLabel(
                    self.scroll_frame,
                    text="Нет активных приложений с аудио",
                    font=ctk.CTkFont(size=12),
                    text_color="#71717a"
                )
                no_apps.pack(pady=20)
                return

            self.is_updating_ui = True
            for pname_lower, data in grouped.items():
                s_list = data["sessions"]
                display_name = get_app_display(pname_lower)
                icon = get_app_icon(display_name)

                vols = []
                for s in s_list:
                    try:
                        vols.append(s.SimpleAudioVolume.GetMasterVolume())
                    except Exception:
                        pass
                avg_vol = int((sum(vols) / len(vols)) * 100) if vols else 100
                is_muted = any(s.SimpleAudioVolume.GetMute() for s in s_list if hasattr(s, 'SimpleAudioVolume'))

                app_card = ctk.CTkFrame(
                    self.scroll_frame,
                    corner_radius=12,
                    fg_color="#1f1f2a",
                    border_width=1,
                    border_color="#2e2e3e"
                )
                app_card.pack(fill="x", pady=4, padx=2)

                top_row = ctk.CTkFrame(app_card, fg_color="transparent")
                top_row.pack(fill="x", padx=10, pady=(6, 2))

                lbl_name = ctk.CTkLabel(
                    top_row,
                    text=f"{icon}  {display_name}",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#e4e4e7"
                )
                lbl_name.pack(side="left")

                pct_lbl = ctk.CTkLabel(
                    top_row,
                    text=f"{avg_vol}%",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#a1a1aa"
                )
                pct_lbl.pack(side="right")

                bot_row = ctk.CTkFrame(app_card, fg_color="transparent")
                bot_row.pack(fill="x", padx=8, pady=(2, 6))

                mute_btn = ctk.CTkButton(
                    bot_row,
                    text="🔇" if is_muted else "🔊",
                    width=32,
                    height=28,
                    corner_radius=6,
                    fg_color="#ef4444" if is_muted else "#262635",
                    hover_color="#3b82f6",
                    font=ctk.CTkFont(size=12)
                )
                mute_btn.configure(command=lambda pn=pname_lower, sl=s_list, mb=mute_btn: self.toggle_app_mute(pn, sl, mb))
                mute_btn.pack(side="left", padx=(0, 6))

                slider = ctk.CTkSlider(
                    bot_row,
                    from_=0,
                    to=100,
                    number_of_steps=100,
                    progress_color="#6366f1",
                    button_color="#4f46e5",
                    button_hover_color="#818cf8"
                )
                slider.set(avg_vol)
                slider.configure(command=lambda v, pn=pname_lower, sl=s_list, pl=pct_lbl, mb=mute_btn: self.on_app_slider_change(v, pn, sl, pl, mb))
                slider.pack(side="left", fill="x", expand=True)

                slider.bind("<MouseWheel>", lambda e, s=slider, pn=pname_lower, sl=s_list, pl=pct_lbl, mb=mute_btn: 
                    self.on_slider_wheel(s, e, lambda v: self.on_app_slider_change(v, pn, sl, pl, mb)))
                app_card.bind("<MouseWheel>", lambda e, s=slider, pn=pname_lower, sl=s_list, pl=pct_lbl, mb=mute_btn: 
                    self.on_slider_wheel(s, e, lambda v: self.on_app_slider_change(v, pn, sl, pl, mb)))

            self.is_updating_ui = False
        except Exception:
            pass

    # --- Global Keyboard Hook via keyboard library ---
    def start_keyboard_hook(self):
        is_ralt_down = [False]
        combo_detected = [False]

        def on_key(e):
            name = (e.name or "").lower()
            is_trigger = name in ("right alt", "alt gr") or (e.scan_code in (0x38, 0x138) and "alt" in name)

            if e.event_type == "down":
                if is_trigger:
                    if not is_ralt_down[0]:
                        is_ralt_down[0] = True
                        combo_detected[0] = False
                elif name == "f8":
                    self.after(0, self.toggle_window)
                else:
                    if is_ralt_down[0] and name not in ("ctrl", "left ctrl", "right ctrl"):
                        combo_detected[0] = True

            elif e.event_type == "up":
                if is_trigger:
                    is_ralt_down[0] = False
                    if not combo_detected[0]:
                        self.after(0, self.toggle_window)

        keyboard.hook(on_key)

    # --- System Tray Icon ---
    def start_tray(self):
        t = threading.Thread(target=self._run_tray, daemon=True)
        t.start()

    def _create_tray_image(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((2, 2, 62, 62), radius=16, fill=(24, 24, 32))
        draw.polygon([(14, 26), (24, 26), (36, 16), (36, 48), (24, 38), (14, 38)], fill=(59, 130, 246))
        draw.arc((32, 22, 48, 42), start=-50, end=50, fill=(255, 255, 255), width=3)
        return img

    def toggle_autostart_action(self, icon, item):
        currently_on = is_autostart_active()
        set_autostart(not currently_on)

    def quit_app(self, icon, item):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        icon.stop()
        self.after(0, self.destroy)

    def _run_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("🔊 Открыть микшер", lambda icon, item: self.after(0, self.show_window), default=True),
            pystray.MenuItem("⚙️ Запуск с Windows", self.toggle_autostart_action, checked=lambda item: is_autostart_active()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Выход", self.quit_app)
        )
        self.tray_icon = pystray.Icon("AltVolumeMixer", self._create_tray_image(), "AltMixer (Правый Alt / F8)", menu)
        self.tray_icon.run()


if __name__ == "__main__":
    app = QuickMixerApp()
    app.mainloop()
