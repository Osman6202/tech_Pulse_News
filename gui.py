import os
import sys
import queue
import logging
import threading
import subprocess
import datetime

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
import httpx

import runner
from scheduler import Scheduler
from logger import get_logger, add_gui_handler
from config import validate_config

logger = get_logger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GUILogHandler(logging.Handler):
    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self._q = q

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._q.put_nowait(self.format(record))
        except Exception:
            pass


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tech Pulse News")
        self.geometry("820x620")
        self.minsize(700, 500)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._ui_queue: queue.Queue[tuple] = queue.Queue()
        self._full_lock = threading.Event()
        self._alert_lock = threading.Event()
        self._log_lines: list[str] = []
        self._MAX_LINES = 200

        self._scheduler = Scheduler()
        self._bot_proc: subprocess.Popen | None = None
        self._tray_icon: pystray.Icon | None = None
        self._lm_ok = False
        self._bot_ok = False

        self._build_ui()
        add_gui_handler(GUILogHandler(self._log_queue))

        warnings = validate_config()
        for w in warnings:
            logger.warning(f"Config: {w}")

        self._start_bot_listener()
        self._scheduler.start(on_full=self._run_full_worker, on_alert=self._run_alert_worker)
        self._start_tray_icon()
        threading.Thread(target=self._status_poll_loop, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._drain_queues)

    # ── UI layout ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Status bar
        status_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        status_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        status_frame.grid_columnconfigure(0, weight=1)
        self._lm_label = ctk.CTkLabel(status_frame, text="● LM Studio: checking…", text_color="gray")
        self._lm_label.grid(row=0, column=0, sticky="w", padx=12)
        self._bot_label = ctk.CTkLabel(status_frame, text="● Bot: starting…", text_color="gray")
        self._bot_label.grid(row=0, column=1, sticky="e", padx=12)

        # Schedule panel
        sched_frame = ctk.CTkFrame(self, corner_radius=6)
        sched_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 4))
        sched_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sched_frame, text="SCHEDULE", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(6, 0)
        )
        self._next_full_label = ctk.CTkLabel(sched_frame, text="Next briefing: —")
        self._next_full_label.grid(row=1, column=0, sticky="w", padx=10)
        self._next_alert_label = ctk.CTkLabel(sched_frame, text="Next alert scan: —")
        self._next_alert_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))

        # Controls
        ctrl_frame = ctk.CTkFrame(self, corner_radius=6)
        ctrl_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkLabel(ctrl_frame, text="CONTROLS", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0)
        )
        self._full_btn = ctk.CTkButton(ctrl_frame, text="▶ Run Full Briefing", command=self._on_run_full)
        self._full_btn.grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self._alert_btn = ctk.CTkButton(ctrl_frame, text="▶ Run Alert Scan", command=self._on_run_alert)
        self._alert_btn.grid(row=1, column=1, padx=4, pady=6, sticky="w")

        # Activity log
        log_frame = ctk.CTkFrame(self, corner_radius=6)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=4)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="ACTIVITY LOG", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(6, 0)
        )
        self._log_box = ctk.CTkTextbox(
            log_frame, state="disabled", wrap="none",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Bottom bar
        bottom_frame = ctk.CTkFrame(self, height=36, corner_radius=0)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        env_path = os.path.join(PROJECT_ROOT, ".env")
        ctk.CTkButton(
            bottom_frame, text="Open .env", width=100,
            command=lambda: os.startfile(env_path) if os.path.exists(env_path) else None
        ).pack(side="left", padx=10, pady=4)
        ctk.CTkButton(
            bottom_frame, text="Minimize to Tray", width=140,
            command=self._on_close
        ).pack(side="right", padx=10, pady=4)

    # ── Queue draining (main-thread only) ──────────────────────────────────

    def _drain_queues(self) -> None:
        lines_added = 0
        while not self._log_queue.empty() and lines_added < 50:
            try:
                msg = self._log_queue.get_nowait()
                self._log_lines.append(msg)
                lines_added += 1
            except queue.Empty:
                break

        if lines_added:
            self._log_box.configure(state="normal")
            self._log_box.insert("end", "\n".join(self._log_lines[-lines_added:]) + "\n")
            total = int(self._log_box.index("end-1c").split(".")[0])
            if total > self._MAX_LINES:
                self._log_box.delete("1.0", f"{total - self._MAX_LINES}.0")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")

        while not self._ui_queue.empty():
            try:
                cmd, *args = self._ui_queue.get_nowait()
                if cmd == "lm_status":
                    ok, model_id = args
                    self._lm_ok = ok
                    color = "#28a745" if ok else "#dc3545"
                    self._lm_label.configure(text=f"● LM Studio: {model_id}", text_color=color)
                    self._update_tray_color()
                elif cmd == "bot_status":
                    self._bot_ok = args[0]
                    self._bot_label.configure(
                        text="● Bot: running" if self._bot_ok else "● Bot: stopped",
                        text_color="#28a745" if self._bot_ok else "#dc3545",
                    )
                    self._update_tray_color()
                elif cmd == "schedule":
                    self._next_full_label.configure(text=args[0])
                    self._next_alert_label.configure(text=args[1])
                elif cmd == "enable_btn":
                    btn = self._full_btn if args[0] == "full" else self._alert_btn
                    btn.configure(state="normal")
                elif cmd == "show":
                    self._show_window()
                elif cmd == "exit":
                    self.destroy()
            except queue.Empty:
                break

        self.after(200, self._drain_queues)

    # ── Status polling (daemon thread) ─────────────────────────────────────

    def _status_poll_loop(self) -> None:
        while True:
            self._poll_lm_status()
            self._poll_bot_status()
            self._poll_schedule()
            threading.Event().wait(10)

    def _poll_lm_status(self) -> None:
        try:
            r = httpx.get("http://localhost:1234/v1/models", timeout=2)
            models = r.json().get("data", [])
            if models:
                self._ui_queue.put(("lm_status", True, models[0]["id"]))
            else:
                self._ui_queue.put(("lm_status", False, "running — no model loaded"))
        except Exception:
            self._ui_queue.put(("lm_status", False, "unreachable"))

    def _poll_bot_status(self) -> None:
        alive = self._bot_proc is not None and self._bot_proc.poll() is None
        self._ui_queue.put(("bot_status", alive))

    def _poll_schedule(self) -> None:
        now = datetime.datetime.now()

        def fmt(dt: datetime.datetime | None) -> str:
            if dt is None:
                return "—"
            delta = dt - now
            total = int(delta.total_seconds())
            if total < 0:
                return dt.strftime("%H:%M")
            h, rem = divmod(total, 3600)
            m = rem // 60
            return f"{dt.strftime('%H:%M')} (in {h}h {m:02d}m)"

        full_label = "Next briefing: " + fmt(self._scheduler.next_full_run())
        alert_label = "Next alert scan: " + fmt(self._scheduler.next_alert_run())
        self._ui_queue.put(("schedule", full_label, alert_label))

    # ── Tray icon ──────────────────────────────────────────────────────────

    def _make_tray_image(self, color: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((8, 8, 56, 56), fill=color)
        return img

    def _update_tray_color(self) -> None:
        if self._tray_icon is None:
            return
        if self._lm_ok and self._bot_ok:
            color = "#28a745"
        elif not self._lm_ok and not self._bot_ok:
            color = "#dc3545"
        else:
            color = "#fd7e14"
        self._tray_icon.icon = self._make_tray_image(color)

    def _start_tray_icon(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda icon, item: self._ui_queue.put(("show",))),
            pystray.MenuItem("Exit", lambda icon, item: self._ui_queue.put(("exit",))),
        )
        icon = pystray.Icon(
            "TechPulse",
            self._make_tray_image("#fd7e14"),
            "Tech Pulse News",
            menu,
        )
        self._tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()

    # ── Bot subprocess ─────────────────────────────────────────────────────

    def _start_bot_listener(self) -> None:
        script = os.path.join(PROJECT_ROOT, "bot_listener.py")
        if not os.path.exists(script):
            logger.warning("bot_listener.py not found — bot disabled")
            return
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._bot_proc = subprocess.Popen([sys.executable, script], creationflags=flags)
        logger.info("Bot listener subprocess started")

    # ── Run buttons & workers ──────────────────────────────────────────────

    def _on_run_full(self) -> None:
        if self._full_lock.is_set():
            return
        self._full_btn.configure(state="disabled")
        threading.Thread(target=self._run_full_worker, daemon=True).start()

    def _on_run_alert(self) -> None:
        if self._alert_lock.is_set():
            return
        self._alert_btn.configure(state="disabled")
        threading.Thread(target=self._run_alert_worker, daemon=True).start()

    def _run_full_worker(self) -> None:
        if self._full_lock.is_set():
            return
        self._full_lock.set()
        try:
            runner.run_full()
        finally:
            self._full_lock.clear()
            self._ui_queue.put(("enable_btn", "full"))

    def _run_alert_worker(self) -> None:
        if self._alert_lock.is_set():
            return
        self._alert_lock.set()
        try:
            runner.run_alert()
        finally:
            self._alert_lock.clear()
            self._ui_queue.put(("enable_btn", "alert"))

    # ── Window lifecycle ───────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.withdraw()

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def destroy(self) -> None:
        if self._tray_icon:
            self._tray_icon.stop()
        if self._bot_proc and self._bot_proc.poll() is None:
            self._bot_proc.terminate()
        self._scheduler.stop()
        super().destroy()
