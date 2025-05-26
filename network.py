import socket
import threading
import os
import time
from datetime import datetime

def ts():
    return datetime.now().strftime("[%H:%M:%S]")

def network_process(config, from_ui, to_ui):
    handle = config['handle']
    port = config['port']
    imagepath = config['imagepath']
    autoreply = config['autoreply']
    whoisport = config['whoisport']
    autoreply_timers = {}
    autoreply_sent = set()

    os.makedirs(imagepath, exist_ok=True)
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind(('', port))
    tcp_sock.listen()

    known_users = {}
    local_ip = socket.gethostbyname(socket.gethostname())
    known_users[handle] = (local_ip, port)

    def send_udp_who(listen_port):
        msg = f"WHO {handle} {listen_port}"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(msg.encode('utf-8'), ('255.255.255.255', whoisport))

    def send_tcp_message(ip, port, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(message.encode('utf-8'))
        except Exception:
            to_ui.put(f"{ts()} [Error] TCP zu {ip}:{port} fehlgeschlagen.")
