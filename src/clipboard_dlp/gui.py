"""Simple clipboard history GUI using Tkinter and sqlite3.

Features:
- Background monitor (polling) that stores clipboard text into sqlite
- List view of recent entries with preview
- Buttons: Copy back to clipboard, Delete entry, Clear all, Pause/Resume
- Export to CSV

Notes: pyperclip is optional; if missing the GUI will still run but copy actions will be disabled.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import datetime
import csv
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

try:
    import pyperclip
except Exception:
    pyperclip = None


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "clipboard_history.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


class ClipboardHistoryDB:
    def __init__(self, path: str = DB_PATH):
        self.path = os.path.abspath(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._ensure()

    def _ensure(self):
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add(self, text: str):
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        cur = self._conn.cursor()
        cur.execute("INSERT INTO history (timestamp, content) VALUES (?, ?)", (ts, text))
        self._conn.commit()
        return cur.lastrowid

    def list(self, limit: int = 200):
        cur = self._conn.cursor()
        cur.execute("SELECT id, timestamp, content FROM history ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()

    def get(self, rowid: int) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT content FROM history WHERE id = ?", (rowid,))
        r = cur.fetchone()
        return r[0] if r else None

    def delete(self, rowid: int):
        cur = self._conn.cursor()
        cur.execute("DELETE FROM history WHERE id = ?", (rowid,))
        self._conn.commit()

    def clear(self):
        cur = self._conn.cursor()
        cur.execute("DELETE FROM history")
        self._conn.commit()


class ClipboardMonitor(threading.Thread):
    def __init__(self, db: ClipboardHistoryDB, out_q: queue.Queue, interval: float = 0.6):
        super().__init__(daemon=True)
        self.db = db
        self.interval = interval
        self.out_q = out_q
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._last = None

    def run(self):
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.2)
                continue
            try:
                if pyperclip:
                    text = pyperclip.paste()
                else:
                    text = None
            except Exception:
                text = None

            if text and isinstance(text, str):
                if text.strip() and text != self._last:
                    rowid = self.db.add(text)
                    self._last = text
                    self.out_q.put((rowid, text))

            time.sleep(self.interval)

    def stop(self):
        self._stop.set()

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def toggle(self):
        if self._paused.is_set():
            self.resume()
        else:
            self.pause()


class ClipboardGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clipboard History")
        self.db = ClipboardHistoryDB()
        self.q: queue.Queue = queue.Queue()

        self._build()
        self.monitor = ClipboardMonitor(self.db, self.q)
        self.monitor.start()
        self._poll_queue()

    def _build(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(frm)
        top.pack(fill=tk.X)

        self.pause_btn = ttk.Button(top, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side=tk.LEFT)

        ttk.Button(top, text="Copy Selected", command=self._copy_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Delete", command=self._delete_selected).pack(side=tk.LEFT)
        ttk.Button(top, text="Clear All", command=self._clear_all).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT)

        self.listbox = tk.Listbox(frm, height=18)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=8)
        self.listbox.bind('<Double-1>', lambda e: self._copy_selected())

        self._reload_list()

    def _format_preview(self, row):
        rowid, ts, content = row
        preview = content.replace('\n', ' ')[:120]
        return f"{rowid} | {ts[:19]} | {preview}"

    def _reload_list(self):
        self.listbox.delete(0, tk.END)
        for row in self.db.list(300):
            self.listbox.insert(tk.END, self._format_preview(row))

    def _poll_queue(self):
        try:
            while True:
                rowid, text = self.q.get_nowait()
                # insert at top
                ts = datetime.datetime.utcnow().isoformat() + "Z"
                display = f"{rowid} | {ts[:19]} | {text.replace('\n', ' ')[:120]}"
                self.listbox.insert(0, display)
        except queue.Empty:
            pass
        self.root.after(300, self._poll_queue)

    def _selected_rowid(self) -> Optional[int]:
        sel = self.listbox.curselection()
        if not sel:
            return None
        text = self.listbox.get(sel[0])
        try:
            rowid = int(text.split('|', 1)[0].strip())
            return rowid
        except Exception:
            return None

    def _copy_selected(self):
        rowid = self._selected_rowid()
        if rowid is None:
            messagebox.showinfo("Clipboard History", "No entry selected")
            return
        content = self.db.get(rowid)
        if content is None:
            messagebox.showerror("Clipboard History", "Entry not found")
            return
        if not pyperclip:
            messagebox.showwarning("pyperclip missing", "pyperclip not installed; copy disabled")
            return
        try:
            pyperclip.copy(content)
            messagebox.showinfo("Clipboard History", "Copied to clipboard")
        except Exception as e:
            messagebox.showerror("Clipboard History", f"Failed to copy: {e}")

    def _delete_selected(self):
        rowid = self._selected_rowid()
        if rowid is None:
            messagebox.showinfo("Clipboard History", "No entry selected")
            return
        if not messagebox.askyesno("Delete", "Delete selected entry?"):
            return
        self.db.delete(rowid)
        self._reload_list()

    def _clear_all(self):
        if not messagebox.askyesno("Clear All", "Delete ALL clipboard history? This cannot be undone."):
            return
        self.db.clear()
        self._reload_list()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        rows = self.db.list(10000)
        try:
            with open(path, "w", newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["id", "timestamp", "content"])
                for r in rows:
                    w.writerow(r)
            messagebox.showinfo("Export", f"Exported {len(rows)} rows to {path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to export: {e}")

    def _toggle_pause(self):
        self.monitor.toggle()
        if self.monitor._paused.is_set():
            self.pause_btn.config(text="Resume")
        else:
            self.pause_btn.config(text="Pause")


def main():
    root = tk.Tk()
    app = ClipboardGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.monitor.stop(), root.destroy()))
    root.mainloop()


if __name__ == '__main__':
    main()
