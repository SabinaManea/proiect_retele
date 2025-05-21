import socket
import struct
import json

from protocol import HEADER_SIZE

def send_msg(sock: socket.socket, msg: dict, raw_data: bytes = None):
    payload = json.dumps(msg).encode('utf-8')
    length = len(payload)
    sock.sendall(struct.pack('!I', length) + payload)
    if raw_data:
        sock.sendall(raw_data)


def recv_msg(sock: socket.socket):
    # Read header
    header = sock.recv(HEADER_SIZE)
    if not header:
        return None, None
    length = struct.unpack('!I', header)[0]
    # Read JSON payload
    data = sock.recv(length)
    msg = json.loads(data.decode('utf-8'))
    raw = None
    if msg.get('type') == 'IMAGE_DATA':
        # Next 'size' bytes contain the image
        size = msg['size']
        raw = sock.recv(size)
    return msg, raw