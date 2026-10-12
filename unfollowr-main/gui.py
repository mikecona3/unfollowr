#!/usr/bin/env python3
"""
Simple desktop GUI for the Unfollower Tracker.

Usage:
    python -m unfollower_tracker.gui
"""

import contextlib
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, simpledialog

from . import auth, unfollower_list
from .main import run_x, unfollow_x


class _QueueWriter:
    """File-like object that forwards print() output to a queue."""

    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, text: str) -> None:
        if text:
            self.q.put(text)

    def flush(self) -> None:
        pass


class _Done:
    """Queue marker that a background task finished, carrying its return value."""

    def __init__(self, result):
        self.result = result


class UnfollowrsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.output = queue.Queue()
        self.on_done = None
        self.unfollowers = []
        self.login = None

        root.title("Unfollowrs")
        root.geometry("540x620")
        root.minsize(440, 460)

        tk.Label(root, text="Unfollowrs", font=("Helvetica", 28, "bold")).pack(pady=(30, 10))

        # Account bar: "Sign in with X" when signed out, "Sign Out" when signed in
        account_bar = tk.Frame(root)
        account_bar.pack(pady=(0, 15))
        self.account_label = tk.Label(account_bar)
        self.account_label.pack(side="left")
        self.sign_in_button = tk.Button(account_bar, text="Sign in with X", command=self.sign_in)
        self.sign_out_button = tk.Button(account_bar, text="Sign Out", command=self.sign_out)

        self.x_button = tk.Button(
            root, text="Find Unfollowers on X", font=("Helvetica", 14),
            padx=16, pady=6, command=self.find_x,
        )
        self.x_button.pack()

        # Saved unfollower list — only shown when there's someone on it
        self.list_frame = tk.Frame(root)
        tk.Label(self.list_frame, text="Unfollowed you (saved between checks):").pack(anchor="w")
        list_row = tk.Frame(self.list_frame)
        list_row.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_row, selectmode="extended", height=8)
        scrollbar = tk.Scrollbar(list_row, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        list_buttons = tk.Frame(self.list_frame)
        list_buttons.pack(fill="x", pady=(6, 0))
        self.select_all_button = tk.Button(
            list_buttons, text="Select All",
            command=lambda: self.listbox.select_set(0, "end"),
        )
        self.select_all_button.pack(side="left")
        self.remove_button = tk.Button(
            list_buttons, text="Remove from List", command=self.remove_selected,
        )
        self.remove_button.pack(side="left", padx=6)
        self.unfollow_button = tk.Button(
            list_buttons, text="Unfollow Selected", command=self.unfollow_selected,
        )
        self.unfollow_button.pack(side="right")

        self.log = scrolledtext.ScrolledText(root, height=8, state="disabled", wrap="word")
        self.log.pack(side="bottom", fill="both", expand=True, padx=16, pady=16)

        self.buttons = {
            b: b.cget("text")
            for b in (self.sign_in_button, self.sign_out_button, self.x_button,
                      self.select_all_button, self.remove_button, self.unfollow_button)
        }

        # Pick up a saved login so the user doesn't have to sign in every launch
        try:
            self.login = auth.load_login()
        except (OSError, ValueError) as e:
            self._write_log(f"Couldn't load saved login: {e}\n")
        self._update_account()
        if self.login:
            try:
                self.show_unfollowers(unfollower_list.load(self.login["user_id"]))
            except (OSError, ValueError) as e:
                self._write_log(f"Couldn't load saved unfollower list: {e}\n")

    # --- Account ---

    def sign_in(self) -> None:
        self.start(self.sign_in_button, auth.start_sign_in, on_done=self._ask_for_pin)

    def _ask_for_pin(self, result) -> None:
        handler, url = result
        webbrowser.open(url)
        self._write_log(f"Opened X sign-in in your browser. If it didn't open, go to:\n{url}\n")
        pin = simpledialog.askstring(
            "Sign in with X",
            "Log in on X in your browser and click \"Authorize app\".\n"
            "Then enter the PIN that X shows you:",
            parent=self.root,
        )
        if not pin or not pin.strip():
            self._write_log("Sign-in cancelled.\n")
            return

        def finish():
            try:
                login = auth.finish_sign_in(handler, pin)
            except Exception as e:
                print(f"Sign-in failed. Check the PIN and try again. ({e})")
                return None
            print(f"Signed in as @{login['username']}.")
            return login

        self.start(self.sign_in_button, finish, on_done=self._signed_in, clear_log=False)

    def _signed_in(self, login: dict) -> None:
        self.login = login
        self._update_account()
        self.show_unfollowers(unfollower_list.load(login["user_id"]))

    def sign_out(self) -> None:
        if not messagebox.askyesno(
            "Sign out?",
            f"Sign out of @{self.login['username']}?\n\n"
            "You'll need to sign in with X again to check for unfollowers. "
            "Your saved list stays on this computer.",
        ):
            return
        auth.sign_out()
        self.login = None
        self.show_unfollowers([])
        self._update_account()
        self._write_log("Signed out.\n")

    def _update_account(self) -> None:
        if self.login:
            self.account_label.config(text=f"Signed in as @{self.login['username']}")
            self.sign_in_button.pack_forget()
            self.sign_out_button.pack(side="left", padx=(8, 0))
            self.x_button.config(state="normal")
        else:
            self.account_label.config(text="Not signed in")
            self.sign_out_button.pack_forget()
            self.sign_in_button.pack(side="left", padx=(8, 0))
            self.x_button.config(state="disabled")

    # --- Unfollowers ---

    def find_x(self) -> None:
        login = self.login
        self.start(self.x_button, lambda: run_x(login), on_done=self.show_unfollowers)

    def unfollow_selected(self) -> None:
        users = [self.unfollowers[i] for i in self.listbox.curselection()]
        if not users:
            messagebox.showinfo("Unfollowrs", "Select at least one account to unfollow.")
            return

        names = ", ".join(f"@{u['username']}" for u in users[:10])
        if len(users) > 10:
            names += f" and {len(users) - 10} more"
        if not messagebox.askyesno(
            "Unfollow on X?",
            f"Unfollow {len(users)} account(s) from @{self.login['username']}?\n\n{names}\n\n"
            "You'd have to follow them again manually to undo this.",
        ):
            return

        login = self.login
        self.start(self.unfollow_button, lambda: unfollow_x(login, users),
                   on_done=lambda _: self.show_unfollowers(unfollower_list.load(login["user_id"])),
                   clear_log=False)

    def remove_selected(self) -> None:
        users = [self.unfollowers[i] for i in self.listbox.curselection()]
        if not users:
            messagebox.showinfo("Unfollowrs", "Select at least one account to remove.")
            return
        if not messagebox.askyesno(
            "Remove from list?",
            f"Remove {len(users)} account(s) from the saved list without unfollowing them?",
        ):
            return
        self.show_unfollowers(
            unfollower_list.remove(self.login["user_id"], (u["user_id"] for u in users))
        )
        self._write_log(f"Removed {len(users)} account(s) from the saved list.\n")

    def show_unfollowers(self, unfollowers: list) -> None:
        self.unfollowers = list(unfollowers)
        self.listbox.delete(0, "end")
        for u in self.unfollowers:
            since = u.get("detected_at", "")[:10]
            self.listbox.insert("end", f"@{u['username']}" + (f"   (since {since})" if since else ""))
        if self.unfollowers:
            self.list_frame.pack(fill="both", expand=True, padx=16, pady=(16, 0))
        else:
            self.list_frame.pack_forget()

    # --- Background task plumbing ---

    def start(self, clicked: tk.Button, task, on_done=None, clear_log: bool = True) -> None:
        # Disable every button so only one task runs at a time
        for button in self.buttons:
            button.config(state="disabled")
        clicked.config(text="Working...")
        if clear_log:
            self.log.config(state="normal")
            self.log.delete("1.0", "end")
            self.log.config(state="disabled")
        self.on_done = on_done
        threading.Thread(target=self._run, args=(task,), daemon=True).start()
        self.root.after(100, self._drain_output)

    def _write_log(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def _run(self, task) -> None:
        writer = _QueueWriter(self.output)
        result = None
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            try:
                result = task()
            except Exception as e:  # show failures in the window instead of crashing
                print(f"Error: {e}")
        self.output.put(_Done(result))

    def _drain_output(self) -> None:
        done = None
        while True:
            try:
                item = self.output.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, _Done):
                done = item
                break
            self._write_log(item)

        if done is None:
            self.root.after(100, self._drain_output)
            return

        for button, text in self.buttons.items():
            button.config(state="normal", text=text)
        self._update_account()
        if self.on_done and done.result is not None:
            self.on_done(done.result)


def main() -> None:
    root = tk.Tk()
    UnfollowrsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
