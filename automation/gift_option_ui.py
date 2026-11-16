#!/usr/bin/env python3
"""
Gift Option UI — Option 24: Upload Gifts from Folder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TWO-STEP FLOW
  Step 1 ── Credentials screen
            • User enters Email + Password
            • Clicks "Connect & Fetch User Types"
            • App logs into portal, navigates to Gift Management,
              and fetches the REAL user-type list from the live dropdown
  Step 2 ── Gift form
            • One row per image in gift/ folder
            • Columns: Gift Label | Description | Points | Market Value
            •          + one CHECKBOX per fetched user type
            • Submit button runs the Selenium automation in a bg thread
"""

import re
import sys
import time
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
logger = logging.getLogger(__name__)

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0f0f1a"
CARD     = "#1a1a2e"
CARD2    = "#16213e"
ACCENT   = "#7c3aed"
ACCENT_H = "#6d28d9"
TEXT     = "#e2e8f0"
MUTED    = "#94a3b8"
IN_BG    = "#16213e"
IN_FG    = "#e2e8f0"
BORDER   = "#2d2d44"
SUCCESS  = "#10b981"
ERROR_C  = "#ef4444"
WARN     = "#f59e0b"

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_SUB    = ("Segoe UI", 11)
FONT_HEADER = ("Segoe UI", 10, "bold")
FONT_LABEL  = ("Segoe UI",  9)
FONT_INPUT  = ("Segoe UI",  9)
FONT_CHK    = ("Segoe UI",  9)
FONT_SMALL  = ("Segoe UI",  8)
FONT_BTN    = ("Segoe UI", 11, "bold")
FONT_LOG    = ("Consolas",  9)

VALID_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".svg"}


# ── File helpers ──────────────────────────────────────────────────────────────
def sort_key(p: Path):
    m = re.match(r"^(\d+)", p.stem)
    if m:
        return (0, int(m.group(1)), p.name.lower())
    nums = re.findall(r"\d+", p.stem)
    if nums:
        return (1, int(nums[0]), p.name.lower())
    return (2, 0, p.name.lower())


def find_gift_folder() -> Path:
    for c in [
        Path(__file__).resolve().parent.parent / "gift",
        Path(__file__).resolve().parent / "gift",
        Path("gift"),
    ]:
        if c.exists() and c.is_dir():
            return c
    default = Path(__file__).resolve().parent.parent / "gift"
    default.mkdir(parents=True, exist_ok=True)
    return default


def get_images(folder: Path):
    return sorted(
        [f for f in folder.iterdir()
         if f.is_file() and f.suffix.lower() in VALID_EXT],
        key=sort_key,
    )


# ── Widget helpers ────────────────────────────────────────────────────────────
def make_entry(parent, var, width=18, show=""):
    return tk.Entry(
        parent, textvariable=var, show=show,
        font=FONT_INPUT, bg=IN_BG, fg=IN_FG,
        insertbackground=TEXT, relief="flat", width=width,
        highlightthickness=1, highlightcolor=ACCENT,
        highlightbackground=BORDER,
    )


def hline(parent, pady=(6, 6)):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=24, pady=pady)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — Credentials / Connect screen
# ═════════════════════════════════════════════════════════════════════════════
class CredentialScreen(tk.Frame):
    """
    Shown first. User enters email + password then clicks
    'Connect & Fetch User Types'. The frame calls back
    with (email, password, user_types, is_multiple, gift_auto_context)
    when login + fetch succeeds.
    """

    def __init__(self, master, on_success):
        super().__init__(master, bg=BG)
        self.on_success = on_success
        self._auto_ctx  = None   # VendorPortalAutomation context kept alive
        self._build()

    def _build(self):
        # ── Centre card ──
        card = tk.Frame(self, bg=CARD, bd=0, relief="flat",
                        highlightthickness=1, highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=480)

        # Title
        tk.Label(card, text="🎁  Gift Upload — Option 24",
                 font=FONT_TITLE, bg=CARD, fg=ACCENT
                 ).pack(pady=(32, 4))
        tk.Label(card,
                 text="Enter your vendor portal credentials.\n"
                      "The app will login, fetch available User Types,\n"
                      "then show the gift form.",
                 font=FONT_SUB, bg=CARD, fg=MUTED, justify="center"
                 ).pack(pady=(0, 24))

        # Fields
        fields_frame = tk.Frame(card, bg=CARD)
        fields_frame.pack(padx=40, fill="x")

        self.v_email = tk.StringVar()
        self.v_pass  = tk.StringVar()

        for row, (lbl, var, show) in enumerate([
            ("Email", self.v_email, ""),
            ("Password", self.v_pass, "•"),
        ]):
            tk.Label(fields_frame, text=lbl, font=FONT_LABEL,
                     bg=CARD, fg=MUTED, anchor="w"
                     ).grid(row=row * 2, column=0, sticky="w", pady=(8, 2))
            e = make_entry(fields_frame, var, width=36, show=show)
            e.grid(row=row * 2 + 1, column=0, sticky="ew", ipady=6)
            if row == 0:
                e.focus_set()

        # Status label
        self.status_lbl = tk.Label(card, text="", font=FONT_LABEL,
                                   bg=CARD, fg=MUTED, wraplength=400)
        self.status_lbl.pack(pady=(16, 4))

        # Connect button
        self.connect_btn = tk.Button(
            card,
            text="🔗  Connect & Fetch User Types",
            font=FONT_BTN,
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            relief="flat", cursor="hand2",
            padx=20, pady=12,
            command=self._on_connect,
        )
        self.connect_btn.pack(pady=(8, 32))

        # Bind Enter
        self.master.bind("<Return>", lambda e: self._on_connect())

    def _set_status(self, msg, colour=MUTED):
        self.status_lbl.configure(text=msg, fg=colour)
        self.update_idletasks()

    def _on_connect(self):
        email    = self.v_email.get().strip()
        password = self.v_pass.get().strip()

        if not email or not password:
            self._set_status("⚠  Please enter both email and password.", WARN)
            return

        self.connect_btn.configure(state="disabled", text="⏳  Connecting…")
        self._set_status("Logging in to vendor portal…", WARN)

        threading.Thread(
            target=self._fetch_user_types,
            args=(email, password),
            daemon=True,
        ).start()

    def _fetch_user_types(self, email, password):
        """Runs in background thread: login → navigate → fetch user types."""
        try:
            from gift_management import GiftManagementAutomation
            from dashboard_automation import VendorPortalAutomation

            self._after(self._set_status, "Launching browser…", WARN)

            # We open a persistent browser session that will be reused for upload
            auto = VendorPortalAutomation(email, password, headless=False)
            auto.__enter__()

            self._after(self._set_status, "Logging in…", WARN)
            if not auto.login():
                auto.__exit__(None, None, None)
                self._after(self._set_status, "✗  Login failed. Check credentials.", ERROR_C)
                self._after(self.connect_btn.configure,
                            state="normal", text="🔗  Connect & Fetch User Types")
                return

            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)

            self._after(self._set_status, "Navigating to Gift Management…", WARN)
            if not gift_auto.navigate():
                auto.__exit__(None, None, None)
                self._after(self._set_status, "✗  Could not navigate to Gift Management.", ERROR_C)
                self._after(self.connect_btn.configure,
                            state="normal", text="🔗  Connect & Fetch User Types")
                return

            self._after(self._set_status, "Fetching user types from portal…", WARN)
            user_types, is_multiple = gift_auto.get_available_user_types()

            if not user_types:
                auto.__exit__(None, None, None)
                self._after(self._set_status,
                            "✗  Could not fetch user types from portal.\n"
                            "Make sure gift items exist in the portal.", ERROR_C)
                self._after(self.connect_btn.configure,
                            state="normal", text="🔗  Connect & Fetch User Types")
                return

            # Success — pass context to parent window
            self._after(
                self.on_success,
                email, password, user_types, is_multiple, auto, gift_auto
            )

        except Exception as exc:
            import traceback
            msg = f"✗  Error: {exc}"
            self._after(self._set_status, msg, ERROR_C)
            self._after(self.connect_btn.configure,
                        state="normal", text="🔗  Connect & Fetch User Types")
            traceback.print_exc()

    def _after(self, fn, *args, **kwargs):
        self.after(0, lambda: fn(*args, **kwargs))


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — Gift form with real checkboxes
# ═════════════════════════════════════════════════════════════════════════════
class GiftFormScreen(tk.Frame):
    def __init__(self, master, email, password,
                 user_types, is_multiple, auto_ctx, gift_auto):
        super().__init__(master, bg=BG)
        self.email       = email
        self.password    = password
        self.user_types  = user_types      # list[str] — REAL from portal
        self.is_multiple = is_multiple
        self.auto_ctx    = auto_ctx        # VendorPortalAutomation (already logged in)
        self.gift_auto   = gift_auto       # GiftManagementAutomation

        self.gift_folder = find_gift_folder()
        self.images      = get_images(self.gift_folder)
        self.rows        = []

        self._build()

    def _build(self):
        self._build_header()
        self._build_form()
        self._build_bottom()

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        f = tk.Frame(self, bg=BG)
        f.pack(fill="x", padx=24, pady=(18, 0))

        tk.Label(f, text="🎁  Gift Upload — Configure Gifts",
                 font=FONT_TITLE, bg=BG, fg=ACCENT).pack(side="left")

        info_parts = [
            f"Folder: {self.gift_folder.name}/",
            f"Images: {len(self.images)}",
            f"User Types: {len(self.user_types)}",
        ]
        tk.Label(f, text="   |   ".join(info_parts),
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left", padx=16)

        hline(self, pady=(10, 0))

        # Show fetched user types as coloured pills
        pills_frame = tk.Frame(self, bg=BG)
        pills_frame.pack(fill="x", padx=24, pady=(8, 0))
        tk.Label(pills_frame, text="Fetched User Types ✓ ",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left")
        colours = [ACCENT, "#0ea5e9", SUCCESS, "#f97316", "#ec4899", "#84cc16"]
        for i, ut in enumerate(self.user_types):
            c = colours[i % len(colours)]
            tk.Label(pills_frame, text=f" {ut} ",
                     font=FONT_SMALL, bg=c, fg="white",
                     relief="flat", padx=6, pady=2
                     ).pack(side="left", padx=3)

        hline(self, pady=(8, 0))

    # ── Scrollable form ───────────────────────────────────────────────────────
    def _build_form(self):
        wrapper = tk.Frame(self, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=24, pady=8)

        self._canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrapper, orient="vertical", command=self._canvas.yview)
        self.form_frame = tk.Frame(self._canvas, bg=BG)

        self.form_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 * int(e.delta / 120), "units")
        )

        # Column headers
        n_cols  = 5 + len(self.user_types)  # #, image, label, desc, pts, value, + one per ut
        headers = ["#", "Image", "Gift Label *", "Description", "Points *", "Value"]
        widths  = [3,    18,      20,             20,            9,          10]
        for col, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(self.form_frame, text=h, font=FONT_HEADER,
                     bg=BG, fg=MUTED, width=w, anchor="w"
                     ).grid(row=0, column=col, padx=5, pady=(4, 8), sticky="w")

        # User-type headers
        for i, ut in enumerate(self.user_types):
            tk.Label(self.form_frame, text=ut, font=FONT_HEADER,
                     bg=BG, fg=MUTED, anchor="w"
                     ).grid(row=0, column=6 + i, padx=5, pady=(4, 8), sticky="w")

        # Rows
        if not self.images:
            tk.Label(
                self.form_frame,
                text=f"⚠  No images found in:\n{self.gift_folder.absolute()}\n\n"
                     "Place numbered images (1.jpg, 2.png …) in the gift/ folder and reopen.",
                font=FONT_LABEL, bg=BG, fg=WARN, justify="left"
            ).grid(row=1, column=0, columnspan=n_cols, padx=12, pady=24, sticky="w")
        else:
            for idx, img in enumerate(self.images):
                self._add_row(idx, img)

    def _add_row(self, idx: int, img_path: Path):
        r   = idx + 1
        rbg = CARD if idx % 2 == 0 else CARD2

        def lbl(text, col, width=None, fg=MUTED):
            kw = dict(bg=rbg, fg=fg, font=FONT_LABEL, anchor="w")
            if width:
                kw["width"] = width
            tk.Label(self.form_frame, text=text, **kw).grid(
                row=r, column=col, padx=5, pady=5, sticky="w")

        lbl(str(r), col=0, width=3)
        name = img_path.name if len(img_path.name) <= 18 else img_path.name[:15] + "…"
        lbl(name, col=1, width=18)

        v_label  = tk.StringVar()
        v_desc   = tk.StringVar()
        v_points = tk.StringVar()
        v_value  = tk.StringVar(value="0")

        for var, col, w in [(v_label, 2, 20), (v_desc, 3, 20),
                             (v_points, 4, 9), (v_value, 5, 10)]:
            e = make_entry(self.form_frame, var, width=w)
            e.grid(row=r, column=col, padx=5, pady=5, sticky="ew")

        # One checkbox per user type — all ticked by default
        cb_vars = {}
        for i, ut in enumerate(self.user_types):
            var = tk.BooleanVar(value=True)
            cb_vars[ut] = var
            colours_list = [ACCENT, "#0ea5e9", SUCCESS, "#f97316", "#ec4899", "#84cc16"]
            sel_col = colours_list[i % len(colours_list)]
            cb = tk.Checkbutton(
                self.form_frame,
                text="✓",
                variable=var,
                font=FONT_CHK,
                bg=rbg, fg=TEXT,
                selectcolor=sel_col,
                activebackground=rbg,
                activeforeground=TEXT,
                relief="flat",
                cursor="hand2",
            )
            cb.grid(row=r, column=6 + i, padx=5, pady=5)

        self.rows.append({
            "img_path": img_path,
            "label":    v_label,
            "desc":     v_desc,
            "points":   v_points,
            "value":    v_value,
            "cb_vars":  cb_vars,
        })

    # ── Bottom bar ────────────────────────────────────────────────────────────
    def _build_bottom(self):
        hline(self, pady=(4, 10))

        btn_bar = tk.Frame(self, bg=BG)
        btn_bar.pack(fill="x", padx=24, pady=(0, 8))

        self.submit_btn = tk.Button(
            btn_bar,
            text="🚀  Submit & Start Automation",
            font=FONT_BTN,
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            relief="flat", cursor="hand2", padx=24, pady=10,
            command=self._on_submit,
        )
        self.submit_btn.pack(side="left")

        self.status_lbl = tk.Label(btn_bar, text="", font=FONT_LABEL, bg=BG, fg=MUTED)
        self.status_lbl.pack(side="left", padx=16)

        # Log panel
        lf = tk.LabelFrame(self, text=" Log ", font=FONT_SMALL,
                            bg=BG, fg=MUTED, bd=1, relief="flat")
        lf.pack(fill="both", expand=False, padx=24, pady=(0, 14))

        self.log_box = scrolledtext.ScrolledText(
            lf, height=9, font=FONT_LOG,
            bg="#0a0a14", fg=TEXT, insertbackground=TEXT,
            relief="flat", state="disabled", wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)

    # ── Validation & submit ───────────────────────────────────────────────────
    def _on_submit(self):
        if not self.rows:
            messagebox.showerror("No Images",
                                 f"No gift images found in:\n{self.gift_folder.absolute()}")
            return

        gifts_data = []
        errors = []

        for i, row in enumerate(self.rows, 1):
            label  = row["label"].get().strip()
            desc   = row["desc"].get().strip()
            points = row["points"].get().strip().replace(",", "")
            value  = row["value"].get().strip().replace(",", "") or "0"
            selected = [ut for ut, bv in row["cb_vars"].items() if bv.get()]

            if not label:
                errors.append(f"Row {i} ({row['img_path'].name}): Gift Label is required.")
            if not points or not points.isdigit():
                errors.append(f"Row {i} ({row['img_path'].name}): Redeem Points must be a number.")
            if not selected:
                errors.append(f"Row {i} ({row['img_path'].name}): Tick at least one Target Audience.")

            if not errors:
                gifts_data.append({
                    "name":              label,
                    "description":       desc or label,
                    "points":            points,
                    "value":             value,
                    "target_user_types": selected,
                    "image_path":        str(row["img_path"].absolute()),
                    "image_name":        row["img_path"].name,
                })

        if errors:
            messagebox.showerror("Validation Errors", "\n".join(errors))
            return

        # Confirm dialog
        lines = [
            f"  {i}. {g['name']}  |  {g['image_name']}  |  "
            f"{g['points']} pts  →  {', '.join(g['target_user_types'])}"
            for i, g in enumerate(gifts_data, 1)
        ]
        if not messagebox.askyesno(
            "Confirm Upload",
            f"Ready to upload {len(gifts_data)} gift(s):\n\n" +
            "\n".join(lines) + "\n\nProceed?"
        ):
            return

        self.submit_btn.configure(state="disabled", text="⏳  Running…")
        self._set_status("Automation running…", WARN)

        threading.Thread(
            target=self._run_automation,
            args=(gifts_data,),
            daemon=True,
        ).start()

    # ── Automation thread (reuses already-open browser) ──────────────────────
    def _run_automation(self, gifts_data):
        try:
            successful = 0
            failed     = 0

            if self.is_multiple:
                total = len(gifts_data)
                for idx, gift in enumerate(gifts_data, 1):
                    uts = ", ".join(gift["target_user_types"])
                    self._log(f"  [{idx}/{total}] '{gift['name']}' → [{uts}]…")
                    ok = self.gift_auto.add_new_gift(
                        gift, target_user_types=gift["target_user_types"]
                    )
                    if ok:
                        successful += 1
                        self._log(f"  ✓  '{gift['name']}' uploaded!", "green")
                    else:
                        failed += 1
                        self._log(f"  ✗  '{gift['name']}' failed.", "red")
                    time.sleep(1.5)
            else:
                # Single-select: one upload per gift × user-type
                ops = [(g, ut) for g in gifts_data for ut in g["target_user_types"]]
                for i, (gift, utype) in enumerate(ops, 1):
                    self._log(f"  [{i}/{len(ops)}] '{gift['name']}' → '{utype}'…")
                    ok = self.gift_auto.add_new_gift(gift, target_user_types=[utype])
                    if ok:
                        successful += 1
                        self._log(f"  ✓  Done.", "green")
                    else:
                        failed += 1
                        self._log(f"  ✗  Failed.", "red")
                    time.sleep(1.5)

            self._log(f"\n{'━'*50}", "yellow")
            self._log(f"  🎁 SUMMARY", "yellow")
            self._log(f"  ✓ Successful : {successful}", "green")
            self._log(f"  ✗ Failed     : {failed}", "red" if failed else "green")
            self._log(f"{'━'*50}\n", "yellow")

            # Close the browser session
            try:
                self.auto_ctx.__exit__(None, None, None)
            except Exception:
                pass

            self._finish(failed == 0)

        except Exception as exc:
            import traceback
            self._log(f"✗  Error: {exc}", "red")
            self._log(traceback.format_exc(), "red")
            try:
                self.auto_ctx.__exit__(None, None, None)
            except Exception:
                pass
            self._finish(False)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg: str, colour="normal"):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.tag_configure("green",  foreground=SUCCESS)
            self.log_box.tag_configure("red",    foreground=ERROR_C)
            self.log_box.tag_configure("yellow", foreground=WARN)
            self.log_box.tag_configure("normal", foreground=TEXT)
            self.log_box.insert("end", msg + "\n", colour)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _do)

    def _set_status(self, msg, colour=TEXT):
        self.after(0, lambda: self.status_lbl.configure(text=msg, fg=colour))

    def _finish(self, success: bool):
        msg    = "✅  All uploaded successfully!" if success else "❌  Finished with errors — see log."
        colour = SUCCESS if success else ERROR_C
        self.after(0, lambda: self.submit_btn.configure(
            state="normal", text="🚀  Submit & Start Automation"))
        self._set_status(msg, colour)


# ═════════════════════════════════════════════════════════════════════════════
# Root window — orchestrates Step 1 → Step 2
# ═════════════════════════════════════════════════════════════════════════════
class GiftOptionApp(tk.Tk):
    def __init__(self, email="", password=""):
        super().__init__()
        self.title("Option 24 — Gift Upload from Folder")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._center(580, 520)

        # Show Step 1
        self._cred_screen = CredentialScreen(self, on_success=self._on_fetch_success)
        self._cred_screen.pack(fill="both", expand=True)

        # Pre-fill if creds provided
        if email:
            self._cred_screen.v_email.set(email)
        if password:
            self._cred_screen.v_pass.set(password)

    def _on_fetch_success(self, email, password, user_types, is_multiple, auto_ctx, gift_auto):
        """Called (on main thread) after Step 1 succeeds."""
        # Destroy Step 1
        self._cred_screen.pack_forget()
        self._cred_screen.destroy()

        # Resize for form
        self._center(1400, 860)
        self.resizable(True, True)

        # Show Step 2
        form = GiftFormScreen(
            self,
            email=email,
            password=password,
            user_types=user_types,
            is_multiple=is_multiple,
            auto_ctx=auto_ctx,
            gift_auto=gift_auto,
        )
        form.pack(fill="both", expand=True)

    def _center(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(w, sw - 60)
        h  = min(h, sh - 60)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


# ── Entry-point ───────────────────────────────────────────────────────────────
def launch_gift_ui(email="", password="", available_user_types=None):
    """Called from run_automation.py option 24."""
    app = GiftOptionApp(email=email, password=password)
    app.mainloop()


if __name__ == "__main__":
    import os
    launch_gift_ui(
        email=os.getenv("VENDOR_EMAIL", ""),
        password=os.getenv("VENDOR_PASSWORD", ""),
    )
