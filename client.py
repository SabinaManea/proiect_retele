import socket, threading
import time
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk
from protocol import *
from utils import send_msg, recv_msg
from screenshot import capture_screenshot

SERVER = ('127.0.0.1', 9000)
INTERVAL = 0.5  # seconds

class ClientApp:
    def __init__(self, username):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(SERVER)
        send_msg(self.sock, {'type': type_messages['REGISTER'], 'username': username})
        msg, _ = recv_msg(self.sock)
        if msg['type'] == type_messages['REGISTER_FAIL']:
            print('Name taken'); return
        self.users = msg['users']
        # Build UI
        self.root = tk.Tk()
        self.root.title(f"Viewer: {username}")
        # Listbox for users
        self.listbox = tk.Listbox(self.root)
        self.listbox.pack(side='left', fill='y')
        for u in self.users:
            if u != username: self.listbox.insert('end', u)
        self.listbox.bind('<<ListboxSelect>>', self.select_user)
        # Canvas for image
        self.canvas = tk.Label(self.root)
        self.canvas.pack()
        # Start listener thread
        threading.Thread(target=self.listen, daemon=True).start()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()

    def select_user(self, evt):
        sel = self.listbox.get(self.listbox.curselection())
        send_msg(self.sock, {'type': type_messages['SELECT_USER'], 'target': sel})

    def listen(self):
        while True:
            msg, raw = recv_msg(self.sock)
            print("CLIENT RECEIVED:", msg)
            if not msg: break
            t = msg['type']
            if t == type_messages['USER_JOINED']:
                self.listbox.insert('end', msg['username'])
            elif t == type_messages['USER_LEFT']:
                idx = self.listbox.get(0, 'end').index(msg['username'])
                self.listbox.delete(idx)
            elif t == type_messages['START_STREAM']:
                viewer = msg['viewer']
                threading.Thread(target=self.stream_to, args=(viewer,), daemon=True).start()
            elif t == type_messages['IMAGE_DATA']:
                img = Image.open(BytesIO(raw))
                photo = ImageTk.PhotoImage(img)
                self.canvas.config(image=photo)
                self.canvas.image = photo
            elif t == type_messages['STOP_STREAM']:
                # handle stop
                pass

    def stream_to(self, viewer):
        # send screenshots periodically
        while True:
            img = capture_screenshot()
            send_msg(self.sock, {'type': type_messages['IMAGE_DATA'], 'size': len(img), 'viewer': viewer}, raw_data=img)
            time.sleep(INTERVAL)

    def on_close(self):
        send_msg(self.sock, {'type': type_messages['STOP_STREAM'], 'target': None})
        self.sock.close()
        self.root.destroy()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python client.py <username>')
    else:
        ClientApp(sys.argv[1])