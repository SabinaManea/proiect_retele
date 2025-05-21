import socket
import threading
from protocol import *
from utils import send_msg, recv_msg

class Server:
    def __init__(self, host='0.0.0.0', port=9000):
        self.addr = (host, port)
        self.clients = {}  # username -> socket
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.addr)
        self.sock.listen()
        print(f"Server listening on {host}:{port}")

    def start(self):
        while True:
            conn, _ = self.sock.accept()
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def handle_client(self, conn: socket.socket):
        try:
            msg, _ = recv_msg(conn)
            if msg['type'] != type_messages['REGISTER']:
                conn.close(); return
            username = msg['username']
            with self.lock:
                if username in self.clients:
                    send_msg(conn, {'type': type_messages['REGISTER_FAIL'], 'reason': 'Username taken'})
                    conn.close(); return
                # Accept new user
                self.clients[username] = conn
                # Notify existing
                for user, csock in self.clients.items():
                    if user != username:
                        send_msg(csock, {'type': type_messages['USER_JOINED'], 'username': username})
                # Send success + current list
                user_list = list(self.clients.keys())
                send_msg(conn, {'type': type_messages['REGISTER_OK'], 'users': user_list})

            # Main loop
            while True:
                msg, raw = recv_msg(conn)
                if msg is None:
                    break
                t = msg['type']
                if t == type_messages['SELECT_USER']:
                    target = msg['target']
                    # Instruct target to start streaming
                    send_msg(self.clients[target], {'type': type_messages['START_STREAM'], 'viewer': username})
                elif t == type_messages['IMAGE_DATA']:
                    # Forward to viewer
                    viewer = msg['viewer']
                    send_msg(self.clients[viewer], msg, raw_data=raw)
                elif t == type_messages['STOP_STREAM']:
                    target = msg['target']
                    send_msg(self.clients[target], {'type': type_messages['STOP_STREAM'], 'viewer': username})
        finally:
            # Cleanup on disconnect
            with self.lock:
                to_remove = None
                for user, csock in list(self.clients.items()):
                    if csock == conn:
                        to_remove = user; del self.clients[user]
                if to_remove:
                    for csock in self.clients.values():
                        send_msg(csock, {'type': type_messages['USER_LEFT'], 'username': to_remove})
            conn.close()

if __name__ == '__main__':
    Server().start()