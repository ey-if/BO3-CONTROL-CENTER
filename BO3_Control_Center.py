import tkinter as tk
from tkinter import ttk, messagebox
import socket, subprocess, platform, threading
from datetime import datetime

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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("BO3 Control Center | v0.2")
        self.root.geometry("1040x680")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self.status = tk.StringVar(value="غير مفحوص")
        self.console_ip = tk.StringVar()
        self.pc_ip = self.local_ip()
        self.nav_buttons = {}
        self.pages = {}
        self._style()
        self._layout()
        self.show_page("Dashboard")
        self.log("تم تشغيل BO3 Control Center v0.2")
        self.log("عنوان الكمبيوتر المحلي: " + self.pc_ip)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TEntry", fieldbackground="#100e17", foreground=TEXT,
                        insertcolor=TEXT, bordercolor=PURPLE, lightcolor=PURPLE,
                        darkcolor=PURPLE, padding=9)
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT,
                        font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", PURPLE)])

    def _layout(self):
        self.sidebar = tk.Frame(self.root, bg=SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(25, 28))
        tk.Label(brand, text="BO3", bg=SIDEBAR, fg="#c5a8ff",
                 font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(brand, text="CONTROL CENTER", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Frame(self.sidebar, bg="#2b2438", height=1).pack(fill="x", padx=16, pady=(0, 16))
        nav_items = [("Dashboard", "لوحة التحكم"), ("Multiplayer", "اللعب الجماعي"),
                     ("Zombies", "الزومبي"), ("Account", "الحساب"),
                     ("Connection", "الاتصال"), ("Settings", "الإعدادات")]
        for key, label in nav_items:
            b = tk.Button(self.sidebar, text="  " + label, anchor="w", relief="flat",
                          bd=0, cursor="hand2", bg=SIDEBAR, fg=MUTED,
                          activebackground=PURPLE, activeforeground="white",
                          font=("Segoe UI", 10, "bold"), padx=14, pady=12,
                          command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = b
        tk.Frame(self.sidebar, bg="#2b2438", height=1).pack(fill="x", padx=16, pady=(20, 12))
        tk.Label(self.sidebar, text="LOCAL NETWORK MODE", bg=SIDEBAR, fg="#8d7aa9",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=20)
        tk.Label(self.sidebar, text="v0.2  •  Windows 10", bg=SIDEBAR, fg="#777184",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(5, 15))

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=BG)
        self.header.pack(fill="x", padx=30, pady=(25, 18))
        self.page_title = tk.Label(self.header, text="لوحة التحكم", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 21, "bold"))
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(self.header, text="مركز متابعة BO3 والشبكة المحلية",
                                      bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.page_subtitle.pack(anchor="w", pady=(4, 0))
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=30, pady=(0, 25))
        self._build_pages()

    def _card(self, parent, title, value, hint):
        card = tk.Frame(parent, bg=PANEL, padx=18, pady=16,
                        highlightthickness=1, highlightbackground="#2b2438")
        tk.Label(card, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text=value, bg=PANEL, fg=TEXT, font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(8, 3))
        tk.Label(card, text=hint, bg=PANEL, fg="#8f879e", font=("Segoe UI", 8)).pack(anchor="w")
        return card

    def _build_pages(self):
        # Dashboard
        p = tk.Frame(self.content, bg=BG); self.pages["Dashboard"] = p
        cards = tk.Frame(p, bg=BG); cards.pack(fill="x")
        self._card(cards, "حالة الاتصال", "غير مفحوص", "نتيجة آخر اختبار للشبكة").pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._card(cards, "عنوان IP المحلي", self.pc_ip, "عنوان الكمبيوتر على الشبكة").pack(side="left", fill="x", expand=True, padx=10)
        self._card(cards, "إصدار البرنامج", "0.2", "نسخة الواجهة المطوّرة").pack(side="left", fill="x", expand=True, padx=(10, 0))
        box = tk.Frame(p, bg=PANEL, padx=20, pady=18); box.pack(fill="x", pady=18)
        tk.Label(box, text="اختبار اتصال PlayStation", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(box, text="أدخل عنوان IPv4 الخاص بجهازك على الشبكة المحلية.", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 12))
        row = tk.Frame(box, bg=PANEL); row.pack(fill="x")
        ttk.Entry(row, textvariable=self.console_ip).pack(side="left", fill="x", expand=True, ipady=2)
        self.test_btn = tk.Button(row, text="اختبار الاتصال", command=self.test,
                                  bg=PURPLE, fg="white", activebackground=PURPLE_HI,
                                  activeforeground="white", relief="flat", padx=18, pady=9,
                                  font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.test_btn.pack(side="left", padx=(10, 0))
        self.dashboard_result = tk.Label(box, text="لم يتم إجراء اختبار بعد.", bg=PANEL,
                                         fg=MUTED, font=("Segoe UI", 9))
        self.dashboard_result.pack(anchor="w", pady=(12, 0))
        note = tk.Frame(p, bg="#171321", padx=16, pady=13); note.pack(fill="x")
        tk.Label(note, text="ملاحظة", bg="#171321", fg="#c5a8ff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(note, text="هذا الإصدار يراقب الاتصال المحلي فقط. لا يعدّل ملفات اللعبة أو بيانات الحساب، ولا يتجاوز حماية المنصة.",
                 bg="#171321", fg=MUTED, font=("Segoe UI", 9), wraplength=700, justify="left").pack(anchor="w", pady=(4, 0))

        # Placeholder pages
        placeholders = {
            "Multiplayer": ("اللعب الجماعي", "سيُضاف هنا عرض أدوات ومعلومات مساعدة غير تدخلية تخص طور Multiplayer."),
            "Zombies": ("طور الزومبي", "سيُضاف هنا محتوى وملاحظات وأدوات متابعة محلية تخص طور Zombies."),
            "Account": ("الحساب", "هذه الصفحة مخصصة لمعلومات عامة وروابط الحساب. لا يتم تخزين كلمات المرور أو تعديل بيانات الحساب."),
        }
        for key, (title, desc) in placeholders.items():
            page = tk.Frame(self.content, bg=BG); self.pages[key] = page
            panel = tk.Frame(page, bg=PANEL, padx=22, pady=22); panel.pack(fill="x", anchor="n")
            tk.Label(panel, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
            tk.Label(panel, text=desc, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=700,
                     justify="left").pack(anchor="w", pady=(10, 0))
            tk.Label(panel, text="قيد التطوير", bg=PANEL, fg="#c5a8ff", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(18, 0))

        # Connection
        page = tk.Frame(self.content, bg=BG); self.pages["Connection"] = page
        panel = tk.Frame(page, bg=PANEL, padx=20, pady=18); panel.pack(fill="x")
        tk.Label(panel, text="معلومات الشبكة", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.ip_label = tk.Label(panel, text="عنوان IP المحلي: " + self.pc_ip, bg=PANEL, fg=MUTED, font=("Consolas", 10))
        self.ip_label.pack(anchor="w", pady=(12, 6))
        tk.Label(panel, text="اختبار الوصول إلى جهاز PlayStation", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 6))
        row = tk.Frame(panel, bg=PANEL); row.pack(fill="x")
        ttk.Entry(row, textvariable=self.console_ip).pack(side="left", fill="x", expand=True, ipady=2)
        tk.Button(row, text="اختبار", command=self.test, bg=PURPLE, fg="white", relief="flat",
                  padx=16, pady=8, cursor="hand2").pack(side="left", padx=(10, 0))
        self.connection_result = tk.Label(panel, text="بانتظار الاختبار.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.connection_result.pack(anchor="w", pady=(12, 0))

        # Settings
        page = tk.Frame(self.content, bg=BG); self.pages["Settings"] = page
        panel = tk.Frame(page, bg=PANEL, padx=20, pady=18); panel.pack(fill="x")
        tk.Label(panel, text="الإعدادات", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(panel, text="المظهر الحالي: بنفسجي وأسود", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 5))
        tk.Label(panel, text="النظام: Windows " + platform.release(), bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=5)
        tk.Label(panel, text="لغة الواجهة: العربية", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=5)
        tk.Label(panel, text="الإصدار: 0.2 Prototype", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=5)

    def show_page(self, key):
        for page in self.pages.values(): page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for name, button in self.nav_buttons.items():
            button.configure(bg=PURPLE if name == key else SIDEBAR,
                             fg="white" if name == key else MUTED)
        titles = {"Dashboard": ("لوحة التحكم", "نظرة عامة على BO3 Control Center"),
                  "Multiplayer": ("Multiplayer", "اللعب الجماعي"), "Zombies": ("Zombies", "طور الزومبي"),
                  "Account": ("Account", "معلومات الحساب"), "Connection": ("Connection", "الشبكة والاتصال"),
                  "Settings": ("Settings", "إعدادات البرنامج")}
        self.page_title.configure(text=titles[key][0]); self.page_subtitle.configure(text=titles[key][1])

    def local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("192.0.2.1", 80)); return s.getsockname()[0]
        except OSError:
            try: return socket.gethostbyname(socket.gethostname())
            except OSError: return "غير متاح"
        finally: s.close()

    def log(self, msg):
        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            self.log_text.see("end"); self.log_text.configure(state="disabled")
        if hasattr(self, "log_lines"): self.log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def test(self):
        ip = self.console_ip.get().strip()
        try: socket.inet_aton(ip)
        except OSError:
            messagebox.showerror("عنوان غير صالح", "أدخل IPv4 صحيحاً، مثال: 192.168.1.25"); return
        self.test_btn.configure(state="disabled")
        self.dashboard_result.configure(text="جارٍ اختبار الاتصال...", fg=AMBER)
        if hasattr(self, "connection_result"): self.connection_result.configure(text="جارٍ الاختبار...", fg=AMBER)
        self.log("بدء اختبار Ping إلى " + ip)
        threading.Thread(target=self.ping_worker, args=(ip,), daemon=True).start()

    def ping_worker(self, ip):
        flag = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            p = subprocess.run(["ping", flag, "2", ip], capture_output=True, text=True, timeout=8)
            ok, output = p.returncode == 0, p.stdout or p.stderr
        except Exception as exc: ok, output = False, str(exc)
        self.root.after(0, self.finish, ip, ok, output)

    def finish(self, ip, ok, output):
        self.test_btn.configure(state="normal")
        if ok:
            msg, color = "يمكن الوصول للجهاز", GREEN
            detail = "نجح اختبار Ping إلى " + ip
        else:
            msg, color = "لم يصل رد Ping", AMBER
            detail = "لم يصل رد Ping؛ قد يكون الرد محجوباً من الجهاز أو الشبكة."
        self.status.set(msg)
        self.dashboard_result.configure(text=detail, fg=color)
        if hasattr(self, "connection_result"): self.connection_result.configure(text=detail, fg=color)
        self.log(detail)
        self.log("نجاح Ping لا يثبت الاتصال بخدمات BO3 أو إمكانية التحكم باللعبة.")
        for line in output.splitlines()[:3]:
            if line.strip(): self.log(line.strip())

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
