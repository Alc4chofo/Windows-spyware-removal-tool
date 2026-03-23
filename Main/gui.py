import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys

from tweaks import TWEAKS, get_categories, get_tweaks_by_category, is_admin

FONT = "Segoe UI"


class PrivacyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Privacy Tool by alcachofo")
        self.root.geometry("860x620")
        self.root.minsize(750, 500)

        # maps tweak name -> BooleanVar for its checkbox
        self.tweak_vars = {}
        # maps tweak name -> dict with the row frame, status label, etc
        self.tweak_widgets = {}
        # maps category name -> its label widget (so we can show/hide them)
        self.category_labels = {}
        self.current_category = None

        self._build_ui()
        self._scan_status()

    def _build_ui(self):
        style = ttk.Style()
        # vista looks the most native on win10/11, fall back to clam otherwise
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")

        self._build_menubar()
        self._build_toolbar()
        self._build_main_layout()
        self._build_statusbar()

    def _build_menubar(self):
        menubar = tk.Menu(self.root)

        actions_menu = tk.Menu(menubar, tearoff=0)
        actions_menu.add_command(label="Apply Selected", command=self._apply_selected)
        actions_menu.add_command(label="Apply All", command=self._apply_all)
        actions_menu.add_separator()
        actions_menu.add_command(label="Revert Selected", command=self._revert_selected)
        actions_menu.add_command(label="Revert All", command=self._revert_all)
        actions_menu.add_separator()
        actions_menu.add_command(label="Rescan", command=self._scan_status)
        actions_menu.add_separator()
        actions_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="Actions", menu=actions_menu)

        sel_menu = tk.Menu(menubar, tearoff=0)
        sel_menu.add_command(label="Select All", command=self._select_all)
        sel_menu.add_command(label="Deselect All", command=self._deselect_all)
        sel_menu.add_separator()
        sel_menu.add_command(label="Select Only Unapplied", command=self._select_unapplied)
        sel_menu.add_command(label="Select Only Applied", command=self._select_applied)
        menubar.add_cascade(label="Selection", menu=sel_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=6, pady=(4, 0))

        self.btn_apply = ttk.Button(toolbar, text="Apply Selected",
                                     command=self._apply_selected)
        self.btn_apply.pack(side="left", padx=(0, 3))

        ttk.Button(toolbar, text="Apply All",
                   command=self._apply_all).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)

        self.btn_revert = ttk.Button(toolbar, text="Revert Selected",
                                      command=self._revert_selected)
        self.btn_revert.pack(side="left", padx=(0, 3))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)

        ttk.Button(toolbar, text="Select All",
                   command=self._select_all).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Deselect All",
                   command=self._deselect_all).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)

        ttk.Button(toolbar, text="Rescan",
                   command=self._scan_status).pack(side="left", padx=3)

        # show admin status on the right side of the toolbar
        if is_admin():
            admin_lbl = ttk.Label(toolbar, text="Administrator",
                                   foreground="#2a7d2e", font=(FONT, 8))
        else:
            admin_lbl = ttk.Label(toolbar, text="Not Administrator!",
                                   foreground="#c0392b", font=(FONT, 8, "bold"))
        admin_lbl.pack(side="right", padx=6)

    def _build_main_layout(self):
        # horizontal split: sidebar for categories, right side for the tweak list
        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=4)

        # --- sidebar ---
        sidebar = ttk.Frame(paned, width=200)
        paned.add(sidebar, weight=0)

        ttk.Label(sidebar, text="Categories", font=(FONT, 9, "bold")).pack(
            anchor="w", padx=8, pady=(6, 2))

        self.cat_listbox = tk.Listbox(
            sidebar, font=(FONT, 9), activestyle="none",
            selectbackground="#0078d4", selectforeground="white",
            relief="flat", bd=0, highlightthickness=1,
            highlightcolor="#0078d4", highlightbackground="#ccc",
        )
        self.cat_listbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # first entry shows everything
        self.cat_listbox.insert("end", "  All")
        for cat in get_categories():
            self.cat_listbox.insert("end", f"  {cat}")

        self.cat_listbox.selection_set(0)
        self.cat_listbox.bind("<<ListboxSelect>>", self._on_category_select)

        # --- right side content ---
        content = ttk.Frame(paned)
        paned.add(content, weight=1)

        self.content_header = ttk.Label(content, text="All", font=(FONT, 11, "bold"))
        self.content_header.pack(anchor="w", padx=8, pady=(6, 2))

        self.content_desc = ttk.Label(content, text=f"{len(TWEAKS)} tweaks",
                                       font=(FONT, 8), foreground="#666")
        self.content_desc.pack(anchor="w", padx=8, pady=(0, 4))

        ttk.Separator(content, orient="horizontal").pack(fill="x", padx=4)

        # tkinter doesn't have a scrollable frame out of the box so we
        # gotta do the classic canvas-with-frame-inside trick
        list_container = ttk.Frame(content)
        list_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_container, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # keep the inner frame as wide as the canvas so stuff doesn't float left
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._populate_tweaks()

    def _build_statusbar(self):
        status_bar = ttk.Frame(self.root, relief="sunken")
        status_bar.pack(fill="x", side="bottom")

        self.status_label = ttk.Label(status_bar, text="Scanning...", font=(FONT, 8),
                                       foreground="#555", padding=(6, 2))
        self.status_label.pack(side="left")

        self.restart_label = ttk.Label(status_bar, text="Some tweaks need a restart",
                                        font=(FONT, 8), foreground="#888", padding=(6, 2))
        self.restart_label.pack(side="right")

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _populate_tweaks(self):
        """creates all the tweak rows grouped under their categories.
        we build everything once and just show/hide later when the user
        picks a category from the sidebar."""

        # wipe any existing stuff (shouldn't happen but just in case)
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.tweak_widgets.clear()

        for cat in get_categories():
            # category header + separator line
            cat_label = ttk.Label(self.inner, text=cat, font=(FONT, 9, "bold"),
                                   foreground="#444", padding=(4, 8, 4, 2))
            cat_label.pack(fill="x", anchor="w")
            self.category_labels[cat] = cat_label

            cat_sep = ttk.Separator(self.inner, orient="horizontal")
            cat_sep.pack(fill="x", padx=4, pady=(0, 2))

            for t in get_tweaks_by_category(cat):
                row = ttk.Frame(self.inner)
                row.pack(fill="x", padx=2, pady=0)

                var = tk.BooleanVar(value=False)
                self.tweak_vars[t["name"]] = var

                cb = ttk.Checkbutton(row, variable=var)
                cb.pack(side="left", padx=(8, 4), pady=3)

                # tweak name + description stacked vertically
                txt = ttk.Frame(row)
                txt.pack(side="left", fill="x", expand=True, pady=2)

                ttk.Label(txt, text=t["name"], font=(FONT, 9)).pack(anchor="w")
                ttk.Label(txt, text=t["description"],
                          font=(FONT, 8), foreground="#777").pack(anchor="w")

                # status text on the right (gets filled in by _update_status)
                status_lbl = ttk.Label(row, text="...", font=(FONT, 8),
                                        foreground="#999", width=12, anchor="e")
                status_lbl.pack(side="right", padx=(4, 10))

                self.tweak_widgets[t["name"]] = {
                    "row": row, "status": status_lbl,
                    "cat": cat, "cat_label": cat_label, "cat_sep": cat_sep,
                }

    def _on_category_select(self, event=None):
        """when user clicks a category in the sidebar, filter the tweak list"""
        sel = self.cat_listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        categories = get_categories()

        if idx == 0:
            # "All" selected
            cat_name = "All"
            self.current_category = None
        else:
            cat_name = categories[idx - 1]
            self.current_category = cat_name

        self.content_header.configure(text=cat_name)

        if self.current_category is None:
            self.content_desc.configure(text=f"{len(TWEAKS)} tweaks")
        else:
            tweaks = get_tweaks_by_category(self.current_category)
            self.content_desc.configure(text=f"{len(tweaks)} tweaks")

        # show/hide tweak rows based on which category is active
        for name, w in self.tweak_widgets.items():
            if self.current_category is None or w["cat"] == self.current_category:
                w["row"].pack(fill="x", padx=2, pady=0)
            else:
                w["row"].pack_forget()

        # only show the category headers/separators when viewing "All"
        for cat, lbl in self.category_labels.items():
            if self.current_category is None:
                lbl.pack(fill="x", anchor="w")
            else:
                lbl.pack_forget()

        for name, w in self.tweak_widgets.items():
            if self.current_category is None:
                w["cat_sep"].pack(fill="x", padx=4, pady=(0, 2))
            else:
                w["cat_sep"].pack_forget()

        # scroll back to top
        self.canvas.yview_moveto(0)

    # ---- scanning / applying ----

    def _scan_status(self):
        """checks which tweaks are already applied. runs in a thread
        so the ui doesn't freeze while we poke at the registry"""
        self.status_label.configure(text="Scanning current state...")
        self.root.update()

        def do_scan():
            results = {}
            for t in TWEAKS:
                try:
                    results[t["name"]] = t["check"]()
                except Exception:
                    results[t["name"]] = False
            self.root.after(0, lambda: self._update_status(results))

        threading.Thread(target=do_scan, daemon=True).start()

    def _update_status(self, results):
        """callback after scan finishes - update all the labels and
        auto-select anything that hasn't been applied yet"""
        applied = 0
        for name, ok in results.items():
            w = self.tweak_widgets.get(name)
            if not w:
                continue
            if ok:
                w["status"].configure(text="Applied", foreground="#2a7d2e")
                applied += 1
            else:
                w["status"].configure(text="Not applied", foreground="#c0392b")
                # pre-check stuff thats not applied so the user can just hit go
                self.tweak_vars[name].set(True)

        self.status_label.configure(
            text=f"{applied}/{len(TWEAKS)} tweaks applied")

        # update the counts next to each category in the sidebar
        for i, cat in enumerate(get_categories()):
            tweaks = get_tweaks_by_category(cat)
            n = sum(1 for t in tweaks if results.get(t["name"], False))
            self.cat_listbox.delete(i + 1)
            self.cat_listbox.insert(i + 1, f"  {cat}  ({n}/{len(tweaks)})")

    def _apply_selected(self):
        if not is_admin():
            messagebox.showerror("Admin Required",
                                 "Restart the application as Administrator.\n"
                                 "Right-click > Run as administrator.")
            return

        selected = [t for t in TWEAKS if self.tweak_vars.get(t["name"], tk.BooleanVar()).get()]
        if not selected:
            messagebox.showinfo("Nothing Selected", "Select at least one tweak.")
            return

        if not messagebox.askyesno(
            "Confirm",
            f"Apply {len(selected)} tweaks?\n\n"
            "This modifies the registry and system services.\n"
            "Some changes need a restart."):
            return

        self.btn_apply.configure(state="disabled")
        self.btn_revert.configure(state="disabled")
        self.status_label.configure(text=f"Applying {len(selected)} tweaks...")
        self.root.update()

        def do_apply():
            results = {}
            for t in selected:
                try:
                    results[t["name"]] = t["apply"]()
                except Exception:
                    results[t["name"]] = False
            self.root.after(0, lambda: self._apply_done(results))

        threading.Thread(target=do_apply, daemon=True).start()

    def _apply_all(self):
        self._select_all()
        self._apply_selected()

    def _apply_done(self, results):
        self.btn_apply.configure(state="normal")
        self.btn_revert.configure(state="normal")

        ok = sum(1 for v in results.values() if v)
        fail = len(results) - ok

        msg = f"{ok} tweaks applied."
        if fail:
            failed = [n for n, v in results.items() if not v]
            msg += f"\n\n{fail} failed:\n" + "\n".join(f"  - {n}" for n in failed)

        messagebox.showinfo("Done", msg + "\n\nRestart may be needed.")
        self._scan_status()

    def _select_all(self):
        for var in self.tweak_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.tweak_vars.values():
            var.set(False)

    def _select_unapplied(self):
        """only tick the ones that arent applied yet"""
        for name, w in self.tweak_widgets.items():
            status_text = w["status"].cget("text")
            self.tweak_vars[name].set(status_text == "Not applied")

    def _select_applied(self):
        """only tick the ones that are already applied (for reverting)"""
        for name, w in self.tweak_widgets.items():
            status_text = w["status"].cget("text")
            self.tweak_vars[name].set(status_text == "Applied")

    def _revert_selected(self):
        if not is_admin():
            messagebox.showerror("Admin Required",
                                 "Restart the application as Administrator.\n"
                                 "Right-click > Run as administrator.")
            return

        selected = [t for t in TWEAKS if self.tweak_vars.get(t["name"], tk.BooleanVar()).get()]
        if not selected:
            messagebox.showinfo("Nothing Selected", "Select at least one tweak to revert.")
            return

        if not messagebox.askyesno(
            "Confirm Revert",
            f"Revert {len(selected)} tweaks to Windows defaults?\n\n"
            "This will restore the original system settings.\n"
            "Some changes need a restart."):
            return

        self.btn_apply.configure(state="disabled")
        self.btn_revert.configure(state="disabled")
        self.status_label.configure(text=f"Reverting {len(selected)} tweaks...")
        self.root.update()

        def do_revert():
            results = {}
            for t in selected:
                try:
                    results[t["name"]] = t["revert"]()
                except Exception:
                    results[t["name"]] = False
            self.root.after(0, lambda: self._revert_done(results))

        threading.Thread(target=do_revert, daemon=True).start()

    def _revert_all(self):
        self._select_applied()
        self._revert_selected()

    def _revert_done(self, results):
        self.btn_apply.configure(state="normal")
        self.btn_revert.configure(state="normal")

        ok = sum(1 for v in results.values() if v)
        fail = len(results) - ok

        msg = f"{ok} tweaks reverted."
        if fail:
            failed = [n for n, v in results.items() if not v]
            msg += f"\n\n{fail} failed:\n" + "\n".join(f"  - {n}" for n in failed)

        messagebox.showinfo("Done", msg + "\n\nRestart may be needed.")
        self._scan_status()


def main():
    # try to get admin, most tweaks need it for registry access
    if not is_admin():
        try:
            import ctypes
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{__file__}"', None, 1
            )
            if result > 32:
                sys.exit(0)
        except Exception:
            pass
        # if elevation failed just run anyway, user will see the warning

    root = tk.Tk()
    app = PrivacyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
