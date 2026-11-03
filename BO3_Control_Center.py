"""BO3 Control Center - local-only companion dashboard.

This application does not connect to game services, inspect game memory,
modify game/account data, or bypass platform protections.
"""

import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import queue
import socket
import subprocess
import threading
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "BO3 Control Center"
APP_VERSION = "0.3.1"
BG = "#0b0b10"
SIDEBAR = "#101018"
PANEL = "#171522"
PANEL_ALT = "#201b2d"
PURPLE = "#493072"
PURPLE_HI = "#7650b5"
TEXT = "#f3effa"
MUTED = "#aaa2b8"
GREEN = "#42c98a"
AMBER = "#e6b65c"
RED = "#e47777"
LOCAL_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                    "169.254.0.0/16", "127.0.0.0/8")
)


def is_valid_ipv4(value):
    """Return True only for a syntactically valid IPv4 address."""
    try:
        return ipaddress.ip_address(value.strip()).version == 4
    except (ValueError, AttributeError):
        return False


def is_local_ipv4_target(value):
    """Allow only loopback or private/link-local IPv4 targets for local diagnostics."""
    try:
        address = ipaddress.ip_address(value.strip())
        return address.version == 4 and any(address in network for network in LOCAL_IPV4_NETWORKS)
    except (ValueError, AttributeError):
        return False


def clean_log_text(value, max_length=300):
    """Keep user-supplied log entries on one printable, bounded line."""
    normalized = " ".join(str(value).split())
    printable = "".join(character for character in normalized if character.isprintable())
    return " ".join(printable.split())[:max(0, int(max_length))]


def build_ping_command(ip, system_name=None):
    """Build a safe argument-list ping command (never invokes a shell)."""
    system_name = (system_name or platform.system()).lower()
    if system_name == "windows":
        return ["ping", "-n", "2", "-w", "1200", ip]
    return ["ping", "-c", "2", "-W", "2", ip]


def get_data_directory():
    """Return the per-user application data directory."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".bo3_control_center"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} | v{APP_VERSION}")
        self.root.geometry("1080x720")
        self.root.minsize(920, 640)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.data_dir = get_data_directory()
        self.config_path = self.data_dir / "settings.json"
        self.log_path = self.data_dir / "events.log"
        self.config = self._load_config()
        self.log_enabled_var = tk.BooleanVar(value=self.config.get("log_enabled", True))
        self.console_ip = tk.StringVar(value=self.config.get("console_ip", ""))
        self.status = tk.StringVar(value="غير مفحوص")
        self.pc_ip = self.local_ip()
        self.hostname = socket.gethostname()
        self.ping_running = False
        self.ping_buttons = []
        self.ping_results = queue.Queue()
        self.ui_closed = False
        self.log_lines = deque(maxlen=1000)
        self.settings_save_error = None
        self.logging_error = None
        self.logger = logging.getLogger(f"bo3_control_center_{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self._configure_file_logging()

        self.nav_buttons = {}
        self.pages = {}
        self._style()
        self._layout()
        self.show_page("Dashboard")
        self.log(f"تم تشغيل {APP_NAME} v{APP_VERSION}")
        self.log("وضع التشغيل: مراقبة محلية فقط")
        self.log("عنوان الكمبيوتر المحلي: " + self.pc_ip)
        self.root.after(100, self._poll_ping_results)

    def _load_config(self):
        defaults = {"console_ip": "", "log_enabled": True}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults["console_ip"] = str(data.get("console_ip", ""))[:64]
                defaults["log_enabled"] = bool(data.get("log_enabled", True))
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return defaults

    def _save_settings(self):
        self.config["console_ip"] = self.console_ip.get().strip()
        self.config["log_enabled"] = bool(self.log_enabled_var.get())
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.config_path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temp_path.replace(self.config_path)
            self.settings_save_error = None
            self._refresh_storage_status()
            return True
        except OSError as exc:
            self.settings_save_error = str(exc)
            self.log_lines.append(f"تعذر حفظ الإعدادات: {exc}")
            self._refresh_storage_status()
            return False

    def _configure_file_logging(self):
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        self.logging_error = None
        if not self.log_enabled_var.get():
            self._refresh_storage_status()
            return
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                self.log_path, maxBytes=512 * 1024, backupCount=2, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            self.logger.addHandler(handler)
        except OSError as exc:
            # The app remains usable even if the profile directory is read-only.
            self.logging_error = str(exc)
        self._refresh_storage_status()

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TEntry", fieldbackground="#100e17", foreground=TEXT,
            insertcolor=TEXT, bordercolor=PURPLE, lightcolor=PURPLE,
            darkcolor=PURPLE, padding=9
        )
        style.configure(
            "Treeview", background=PANEL, foreground=TEXT,
            fieldbackground=PANEL, rowheight=28, borderwidth=0
        )
        style.configure(
            "Treeview.Heading", background=PANEL_ALT, foreground=TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat"
        )
        style.map("Treeview", background=[("selected", PURPLE)])

    def _layout(self):
        self.sidebar = tk.Frame(self.root, bg=SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(25, 25))
        tk.Label(brand, text="BO3", bg=SIDEBAR, fg="#c5a8ff",
                 font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(brand, text="CONTROL CENTER", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Frame(self.sidebar, bg="#2b2438", height=1).pack(fill="x", padx=16, pady=(0, 12))

        nav_items = [
            ("Dashboard", "لوحة التحكم"),
            ("Multiplayer", "اللعب الجماعي"),
            ("Zombies", "طور الزومبي"),
            ("Account", "الحساب"),
            ("Connection", "الاتصال"),
            ("Logs", "سجل الأحداث"),
            ("Settings", "الإعدادات"),
        ]
        for key, label in nav_items:
            button = tk.Button(
                self.sidebar, text="  " + label, anchor="w", relief="flat", bd=0,
                cursor="hand2", bg=SIDEBAR, fg=MUTED,
                activebackground=PURPLE, activeforeground="white",
                font=("Segoe UI", 10, "bold"), padx=14, pady=11,
                command=lambda selected=key: self.show_page(selected)
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button

        tk.Frame(self.sidebar, bg="#2b2438", height=1).pack(fill="x", padx=16, pady=(18, 12))
        tk.Label(self.sidebar, text="LOCAL NETWORK MODE", bg=SIDEBAR, fg="#8d7aa9",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=20)
        tk.Label(self.sidebar, text=f"v{APP_VERSION}  •  Windows 10", bg=SIDEBAR,
                 fg="#777184", font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(5, 15))

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=BG)
        self.header.pack(fill="x", padx=30, pady=(24, 16))
        self.page_title = tk.Label(self.header, text="لوحة التحكم", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 21, "bold"))
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(self.header, text="مركز متابعة BO3 والشبكة المحلية",
                                      bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.page_subtitle.pack(anchor="w", pady=(4, 0))
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self._build_pages()

    def _panel(self, parent, padx=18, pady=16):
        return tk.Frame(parent, bg=PANEL, padx=padx, pady=pady,
                        highlightthickness=1, highlightbackground="#2b2438")

    def _section_title(self, parent, title, subtitle=None):
        tk.Label(parent, text=title, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(parent, text=subtitle, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9), wraplength=720,
                     justify="left").pack(anchor="w", pady=(5, 0))

    def _card(self, parent, title, value, hint):
        card = tk.Frame(parent, bg=PANEL, padx=16, pady=14,
                        highlightthickness=1, highlightbackground="#2b2438")
        tk.Label(card, text=title, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, text=value, bg=PANEL, fg=TEXT,
                               font=("Segoe UI", 17, "bold"))
        value_label.pack(anchor="w", pady=(8, 3))
        tk.Label(card, text=hint, bg=PANEL, fg="#8f879e",
                 font=("Segoe UI", 8)).pack(anchor="w")
        return card, value_label

    def _action_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=PURPLE, fg="white",
                         activebackground=PURPLE_HI, activeforeground="white",
                         relief="flat", padx=16, pady=9,
                         font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _build_pages(self):
        # Dashboard
        page = tk.Frame(self.content, bg=BG)
        self.pages["Dashboard"] = page
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x")
        card, self.connection_card_value = self._card(cards, "حالة الاتصال", "غير مفحوص", "نتيجة آخر اختبار Ping")
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        card, self.ip_card_value = self._card(cards, "عنوان IP المحلي", self.pc_ip, "عنوان الكمبيوتر على الشبكة")
        card.pack(side="left", fill="x", expand=True, padx=8)
        card, _ = self._card(cards, "إصدار البرنامج", APP_VERSION, "نسخة الواجهة الحالية")
        card.pack(side="left", fill="x", expand=True, padx=(8, 0))

        panel = self._panel(page, 20, 18)
        panel.pack(fill="x", pady=17)
        self._section_title(panel, "اختبار اتصال PlayStation",
                            "أدخل عنوان IPv4 للجهاز على شبكتك المحلية. الاختبار يستخدم Ping فقط ولا يتصل بخدمات اللعبة.")
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x", pady=(13, 0))
        ttk.Entry(row, textvariable=self.console_ip).pack(side="left", fill="x", expand=True, ipady=2)
        self.dashboard_test_btn = self._action_button(row, "اختبار الاتصال", self.test)
        self.dashboard_test_btn.pack(side="left", padx=(10, 0))
        self.ping_buttons.append(self.dashboard_test_btn)
        self.dashboard_result = tk.Label(panel, text="لم يتم إجراء اختبار بعد.", bg=PANEL,
                                         fg=MUTED, font=("Segoe UI", 9))
        self.dashboard_result.pack(anchor="w", pady=(12, 0))

        note = tk.Frame(page, bg="#171321", padx=16, pady=13)
        note.pack(fill="x")
        tk.Label(note, text="حدود هذا الإصدار", bg="#171321", fg="#c5a8ff",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(note, text="مراقبة محلية وملاحظات جلسات فقط. لا يقرأ ذاكرة اللعبة، ولا يعدّل ملفاتها أو بيانات الحساب، ولا يتجاوز حماية المنصة.",
                 bg="#171321", fg=MUTED, font=("Segoe UI", 9),
                 wraplength=740, justify="left").pack(anchor="w", pady=(4, 0))

        # Multiplayer
        page = tk.Frame(self.content, bg=BG)
        self.pages["Multiplayer"] = page
        panel = self._panel(page, 20, 18)
        panel.pack(fill="x", pady=(0, 14))
        self._section_title(panel, "متابعة جلسة Multiplayer",
                            "سجل ملاحظاتك محليًا وجهّز قائمة التحقق قبل اللعب. لا توجد قراءة أو تحكم في اللعبة.")
        checklist = tk.Frame(panel, bg=PANEL)
        checklist.pack(fill="x", pady=(14, 10))
        self.mp_checks = {}
        for label in ("الشبكة جاهزة", "يد التحكم جاهزة", "الصوت جاهز"):
            variable = tk.BooleanVar(value=False)
            self.mp_checks[label] = variable
            tk.Checkbutton(checklist, text=label, variable=variable, bg=PANEL, fg=TEXT,
                           selectcolor=PURPLE, activebackground=PANEL,
                           activeforeground=TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(0, 18))
        self._action_button(panel, "تسجيل قائمة الجاهزية", self.record_mp_checklist).pack(anchor="w")

        note_panel = self._panel(page, 20, 16)
        note_panel.pack(fill="x")
        self._section_title(note_panel, "ملاحظة الجلسة")
        self.mp_note_var = tk.StringVar()
        ttk.Entry(note_panel, textvariable=self.mp_note_var).pack(fill="x", pady=(12, 10), ipady=2)
        self._action_button(note_panel, "حفظ الملاحظة في سجل الأحداث", self.record_mp_note).pack(anchor="w")

        # Zombies
        page = tk.Frame(self.content, bg=BG)
        self.pages["Zombies"] = page
        panel = self._panel(page, 20, 18)
        panel.pack(fill="x")
        self._section_title(panel, "متابعة جلسة Zombies",
                            "دوّن الخريطة والجولة وملاحظاتك يدويًا. لا يتصل التطبيق باللعبة ولا يستخرج بياناتها.")
        form = tk.Frame(panel, bg=PANEL)
        form.pack(fill="x", pady=(14, 8))
        tk.Label(form, text="الخريطة", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        tk.Label(form, text="رقم الجولة", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.z_map_var = tk.StringVar()
        self.z_round_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.z_map_var).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        ttk.Entry(form, textvariable=self.z_round_var).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 8))
        form.columnconfigure(0, weight=2)
        form.columnconfigure(1, weight=1)
        tk.Label(panel, text="ملاحظات الجلسة", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 4))
        self.z_note_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.z_note_var).pack(fill="x", pady=(0, 12), ipady=2)
        self._action_button(panel, "حفظ ملخص الجلسة", self.record_zombies_session).pack(anchor="w")

        # Account
        page = tk.Frame(self.content, bg=BG)
        self.pages["Account"] = page
        panel = self._panel(page, 22, 22)
        panel.pack(fill="x", anchor="n")
        self._section_title(panel, "معلومات الحساب", "صفحة معلومات عامة فقط.")
        tk.Label(panel, text="لا يطلب BO3 Control Center كلمات المرور أو رموز التحقق، ولا يخزن بيانات الدخول أو يعدّل الحساب.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=720,
                 justify="left").pack(anchor="w", pady=(12, 0))

        # Connection
        page = tk.Frame(self.content, bg=BG)
        self.pages["Connection"] = page
        self.connection_page = page
        panel = self._panel(page, 20, 18)
        panel.pack(fill="x")
        self._section_title(panel, "معلومات الشبكة المحلية", "المعلومات التالية تُجمع من إعدادات الشبكة المحلية في هذا الكمبيوتر.")
        self.ip_label = tk.Label(panel, text="عنوان IP المحلي: " + self.pc_ip, bg=PANEL,
                                 fg=MUTED, font=("Consolas", 10))
        self.ip_label.pack(anchor="w", pady=(13, 5))
        self.hostname_label = tk.Label(panel, text="اسم الكمبيوتر: " + self.hostname, bg=PANEL,
                                       fg=MUTED, font=("Consolas", 10))
        self.hostname_label.pack(anchor="w", pady=5)
        self.os_label = tk.Label(panel, text="النظام: " + platform.platform(), bg=PANEL,
                                 fg=MUTED, font=("Segoe UI", 9), wraplength=720, justify="left")
        self.os_label.pack(anchor="w", pady=5)
        self._action_button(panel, "تحديث معلومات الشبكة", self.refresh_network_info).pack(anchor="w", pady=(9, 16))
        tk.Label(panel, text="اختبار الوصول إلى جهاز على الشبكة", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 7))
        row = tk.Frame(panel, bg=PANEL)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.console_ip).pack(side="left", fill="x", expand=True, ipady=2)
        self.connection_test_btn = self._action_button(row, "اختبار", self.test)
        self.connection_test_btn.pack(side="left", padx=(10, 0))
        self.ping_buttons.append(self.connection_test_btn)
        self.connection_result = tk.Label(panel, text="بانتظار الاختبار.", bg=PANEL,
                                           fg=MUTED, font=("Segoe UI", 9))
        self.connection_result.pack(anchor="w", pady=(12, 0))

        # Logs
        page = tk.Frame(self.content, bg=BG)
        self.pages["Logs"] = page
        panel = self._panel(page, 14, 14)
        panel.pack(fill="both", expand=True)
        top = tk.Frame(panel, bg=PANEL)
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="سجل الأحداث المحلي", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        self._action_button(top, "تحديث", self.refresh_logs).pack(side="right", padx=(8, 0))
        tk.Button(top, text="مسح السجل", command=self.clear_logs, bg="#39202a", fg="white",
                  activebackground="#5a2b3b", relief="flat", padx=12, pady=8,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        log_frame = tk.Frame(panel, bg=PANEL)
        log_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(log_frame, bg="#100e17", fg=TEXT, insertbackground=TEXT,
                                relief="flat", wrap="word", font=("Consolas", 9),
                                yscrollcommand=scrollbar.set, padx=10, pady=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.log_text.yview)
        self.log_text.configure(state="disabled")
        self.refresh_logs()

        # Settings
        page = tk.Frame(self.content, bg=BG)
        self.pages["Settings"] = page
        panel = self._panel(page, 20, 18)
        panel.pack(fill="x")
        self._section_title(panel, "الإعدادات", "إعدادات محلية بسيطة تُحفظ في ملف المستخدم على هذا الكمبيوتر.")
        tk.Label(panel, text=f"الإصدار: {APP_VERSION}", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(13, 4))
        tk.Label(panel, text="النظام: " + platform.platform(), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), wraplength=720, justify="left").pack(anchor="w", pady=4)
        tk.Label(panel, text="مجلد بيانات التطبيق: " + str(self.data_dir), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=720, justify="left").pack(anchor="w", pady=4)
        tk.Checkbutton(panel, text="حفظ سجل الأحداث محليًا", variable=self.log_enabled_var,
                       command=self.toggle_logging, bg=PANEL, fg=TEXT, selectcolor=PURPLE,
                       activebackground=PANEL, activeforeground=TEXT,
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 8))
        self._action_button(panel, "فتح مجلد بيانات التطبيق", self.open_data_folder).pack(anchor="w")
        tk.Label(panel, text="لا يحتاج تشغيل النسخة النهائية إلى Python بعد بناء ملف EXE على Windows.",
                 bg=PANEL, fg="#c5a8ff", font=("Segoe UI", 9),
                 wraplength=720, justify="left").pack(anchor="w", pady=(16, 0))
        self.storage_status_label = tk.Label(panel, text="", bg=PANEL, fg=MUTED,
                                             font=("Segoe UI", 8), wraplength=720,
                                             justify="left")
        self.storage_status_label.pack(anchor="w", pady=(10, 0))
        self._refresh_storage_status()

    def _refresh_storage_status(self):
        if not hasattr(self, "storage_status_label"):
            return
        messages = []
        if self.logging_error:
            messages.append("تعذر فتح ملف السجل: " + self.logging_error)
        else:
            messages.append("حفظ السجل على القرص: " + ("مفعّل" if self.log_enabled_var.get() else "متوقف"))
        if self.settings_save_error:
            messages.append("تعذر حفظ الإعدادات: " + self.settings_save_error)
        else:
            messages.append("ملف الإعدادات المحلي جاهز للحفظ.")
        has_error = bool(self.logging_error or self.settings_save_error)
        self.storage_status_label.configure(
            text="\n".join(messages), fg=AMBER if has_error else MUTED
        )

    def show_page(self, key):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for name, button in self.nav_buttons.items():
            button.configure(bg=PURPLE if name == key else SIDEBAR,
                             fg="white" if name == key else MUTED)
        titles = {
            "Dashboard": ("لوحة التحكم", "نظرة عامة على BO3 Control Center"),
            "Multiplayer": ("Multiplayer", "ملاحظات وقائمة جاهزية محلية"),
            "Zombies": ("Zombies", "متابعة جلسات الزومبي يدويًا"),
            "Account": ("Account", "معلومات عامة دون بيانات دخول"),
            "Connection": ("Connection", "تشخيص الشبكة المحلية"),
            "Logs": ("سجل الأحداث", "الأحداث المسجلة محليًا على هذا الكمبيوتر"),
            "Settings": ("Settings", "إعدادات البرنامج والتخزين المحلي"),
        }
        self.page_title.configure(text=titles[key][0])
        self.page_subtitle.configure(text=titles[key][1])
        if key == "Logs":
            self.refresh_logs()

    def local_ip(self):
        # UDP connect selects the outgoing interface; it does not send a packet.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.0.2.1", 80))
            return sock.getsockname()[0]
        except OSError:
            try:
                addresses = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                for item in addresses:
                    address = item[4][0]
                    if not address.startswith("127."):
                        return address
            except OSError:
                pass
            return "غير متاح"
        finally:
            sock.close()

    def log(self, message):
        message = clean_log_text(message, 2000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} | {message}"
        self.log_lines.append(line)
        if self.log_enabled_var.get():
            try:
                self.logger.info(message)
            except OSError as exc:
                self.logging_error = str(exc)
                self._refresh_storage_status()
        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def refresh_logs(self):
        lines = []
        if self.log_enabled_var.get():
            try:
                if self.log_path.exists():
                    lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
            except OSError:
                lines = []
        if not lines:
            lines = list(self.log_lines)[-500:]
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(lines) if lines else "لا توجد أحداث مسجلة بعد.")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_logs(self):
        if not messagebox.askyesno("تأكيد المسح", "هل تريد مسح سجل الأحداث المحلي؟"):
            return
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        try:
            if self.log_path.exists():
                self.log_path.unlink()
        except OSError as exc:
            self._configure_file_logging()
            messagebox.showerror("تعذر المسح", str(exc))
            return
        self.log_lines.clear()
        self._configure_file_logging()
        self.log("تم مسح سجل الأحداث")
        self.refresh_logs()

    def toggle_logging(self):
        enabled = bool(self.log_enabled_var.get())
        self.config["log_enabled"] = enabled
        self._configure_file_logging()
        self._save_settings()
        self.log("تم تفعيل حفظ سجل الأحداث" if enabled else "تم إيقاف حفظ السجل على القرص")

    def open_data_folder(self):
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(self.data_dir))
            else:
                messagebox.showinfo("مجلد البيانات", str(self.data_dir))
        except OSError as exc:
            messagebox.showerror("تعذر فتح المجلد", str(exc))

    def refresh_network_info(self):
        self.pc_ip = self.local_ip()
        self.hostname = socket.gethostname()
        self.ip_label.configure(text="عنوان IP المحلي: " + self.pc_ip)
        self.hostname_label.configure(text="اسم الكمبيوتر: " + self.hostname)
        self.ip_card_value.configure(text=self.pc_ip)
        self.log("تم تحديث معلومات الشبكة المحلية")

    def _set_ping_busy(self, busy):
        self.ping_running = busy
        for button in self.ping_buttons:
            button.configure(state="disabled" if busy else "normal")

    def test(self):
        ip = self.console_ip.get().strip()
        if not is_local_ipv4_target(ip):
            messagebox.showerror(
                "عنوان غير صالح",
                "أدخل عنوان IPv4 محليًا فقط، مثل 192.168.1.25 أو 10.0.0.5."
            )
            return
        if self.ping_running:
            return
        self._set_ping_busy(True)
        self.dashboard_result.configure(text="جارٍ اختبار الاتصال...", fg=AMBER)
        if hasattr(self, "connection_result"):
            self.connection_result.configure(text="جارٍ الاختبار...", fg=AMBER)
        self.connection_card_value.configure(text="جارٍ الاختبار")
        self.log("بدء اختبار Ping إلى " + ip)
        threading.Thread(target=self.ping_worker, args=(ip,), daemon=True).start()

    def ping_worker(self, ip):
        """Run Ping off the UI thread; return results through a thread-safe queue."""
        try:
            command = build_ping_command(ip)
            result = subprocess.run(command, capture_output=True, text=True,
                                    errors="replace", timeout=7, check=False)
            ok = result.returncode == 0
            output = result.stdout or result.stderr or "لا يوجد نص ناتج من أمر Ping."
        except (OSError, subprocess.SubprocessError) as exc:
            ok, output = False, str(exc)
        self.ping_results.put((ip, ok, output))

    def _poll_ping_results(self):
        """Apply worker results on Tk's main thread only."""
        if self.ui_closed:
            return
        while True:
            try:
                result = self.ping_results.get_nowait()
            except queue.Empty:
                break
            self.finish_ping(*result)
        self.root.after(100, self._poll_ping_results)

    def finish_ping(self, ip, ok, output):
        self._set_ping_busy(False)
        if ok:
            detail = "نجح اختبار Ping إلى " + ip
            message, color = "يمكن الوصول للجهاز", GREEN
        else:
            detail = "لم يصل رد Ping إلى " + ip + "؛ قد يكون الرد محجوبًا من الجهاز أو الشبكة."
            message, color = "لم يصل رد Ping", AMBER
        self.status.set(message)
        self.connection_card_value.configure(text=message)
        self.dashboard_result.configure(text=detail, fg=color)
        if hasattr(self, "connection_result"):
            self.connection_result.configure(text=detail, fg=color)
        self.log(detail)
        self.log("نجاح Ping لا يثبت الاتصال بخدمات BO3 أو إمكانية التحكم باللعبة.")
        for line in output.splitlines()[:3]:
            cleaned = clean_log_text(line, 240)
            if cleaned:
                self.log(cleaned)
        self._save_settings()

    def record_mp_checklist(self):
        selected = [name for name, variable in self.mp_checks.items() if variable.get()]
        detail = "، ".join(selected) if selected else "لم يتم تحديد عناصر"
        self.log("قائمة جاهزية Multiplayer: " + detail)
        messagebox.showinfo("تم التسجيل", "تم تسجيل قائمة الجاهزية في سجل الأحداث المحلي.")

    def record_mp_note(self):
        note = clean_log_text(self.mp_note_var.get(), 300)
        if not note:
            messagebox.showinfo("ملاحظة فارغة", "اكتب ملاحظة قصيرة أولًا.")
            return
        self.log("ملاحظة Multiplayer: " + note)
        self.mp_note_var.set("")
        messagebox.showinfo("تم الحفظ", "تم حفظ الملاحظة في سجل الأحداث المحلي.")

    def record_zombies_session(self):
        map_name = clean_log_text(self.z_map_var.get(), 80) or "غير محددة"
        round_text = self.z_round_var.get().strip()
        if round_text:
            if not round_text.isdigit() or len(round_text) > 3:
                messagebox.showerror("رقم الجولة غير صالح", "أدخل رقم جولة بين 1 و999 أو اتركه فارغًا.")
                return
            round_number = int(round_text)
            if not 1 <= round_number <= 999:
                messagebox.showerror("رقم الجولة غير صالح", "أدخل رقم جولة بين 1 و999 أو اتركه فارغًا.")
                return
            round_label = str(round_number)
        else:
            round_label = "غير محددة"
        note = clean_log_text(self.z_note_var.get(), 300) or "بدون ملاحظات"
        self.log(f"ملخص Zombies | الخريطة: {map_name} | الجولة: {round_label} | {note}")
        self.z_note_var.set("")
        messagebox.showinfo("تم الحفظ", "تم حفظ ملخص الجلسة في سجل الأحداث المحلي.")

    def on_close(self):
        self.ui_closed = True
        self._save_settings()
        self.log("تم إغلاق التطبيق")
        for handler in list(self.logger.handlers):
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
