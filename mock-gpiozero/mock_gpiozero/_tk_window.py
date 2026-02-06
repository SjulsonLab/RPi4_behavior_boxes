#!/usr/bin/env python3
"""Standalone tkinter window for keyboard-driven GPIO simulation.

Launched as a subprocess by KeyboardSimulator. Sends key events to the
parent process via stdout (one line per event: "pin,action\n").
"""

import sys
import json
import tkinter as tk


def main():
    key_map = json.loads(sys.argv[1])

    root = tk.Tk()
    root.title("GPIO Keyboard Simulator")
    root.geometry("420x340")
    root.configure(bg='#2b2b2b')

    # Header
    header = tk.Label(root, text="GPIO Keyboard Simulator",
                      font=('Helvetica', 14, 'bold'),
                      fg='#ffffff', bg='#2b2b2b')
    header.pack(pady=(10, 5))

    subtitle = tk.Label(root, text="Press keys below to simulate GPIO events.\n"
                                   "This window must be focused.",
                        font=('Helvetica', 10),
                        fg='#aaaaaa', bg='#2b2b2b')
    subtitle.pack(pady=(0, 10))

    # Key mapping display
    mapping_frame = tk.Frame(root, bg='#2b2b2b')
    mapping_frame.pack(padx=20, fill='x')

    for key_name in sorted(key_map.keys()):
        info = key_map[key_name]
        row = tk.Frame(mapping_frame, bg='#2b2b2b')
        row.pack(fill='x', pady=1)
        key_label = tk.Label(row, text="  {}  ".format(key_name),
                             font=('Courier', 12, 'bold'),
                             fg='#000000', bg='#ffcc00',
                             width=3)
        key_label.pack(side='left', padx=(0, 10))
        desc_label = tk.Label(row, text=info['label'],
                              font=('Helvetica', 11),
                              fg='#cccccc', bg='#2b2b2b',
                              anchor='w')
        desc_label.pack(side='left', fill='x')

    # Status bar
    status_var = tk.StringVar(value="Ready")
    status_bar = tk.Label(root, textvariable=status_var,
                          font=('Helvetica', 10),
                          fg='#00ff00', bg='#1a1a1a',
                          anchor='w', padx=10)
    status_bar.pack(side='bottom', fill='x', pady=(10, 0))

    # Track held keys to avoid key-repeat spam
    held_keys = set()

    def send_event(pin, action):
        """Send event to parent process via stdout."""
        sys.stdout.write("{},{}\n".format(pin, action))
        sys.stdout.flush()

    def on_key_press(event):
        key = event.keysym.lower()
        if key in held_keys:
            return
        held_keys.add(key)
        if key in key_map:
            info = key_map[key]
            send_event(info['pin'], info['on_keydown'])
            status_var.set("Key '{}': {} (pin {})".format(
                key, info['on_keydown'], info['pin']))

    def on_key_release(event):
        key = event.keysym.lower()
        held_keys.discard(key)
        if key in key_map:
            info = key_map[key]
            if info.get('on_keyup'):
                send_event(info['pin'], info['on_keyup'])
                status_var.set("Key '{}': {} (pin {})".format(
                    key, info['on_keyup'], info['pin']))

    root.bind('<KeyPress>', on_key_press)
    root.bind('<KeyRelease>', on_key_release)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
