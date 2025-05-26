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
            
    def schedule_autoreply(sender):
        if sender == handle or sender in autoreply_sent:
            return
        if sender not in known_users:
            send_udp_who(port)
            def wait_and_retry():
                for _ in range(5):
                    if sender in known_users:
                        schedule_autoreply(sender)
                        return
                    time.sleep(1)
                to_ui.put(f"{ts()} Autoreply an {sender} abgebrochen – Port unbekannt.")
            threading.Thread(target=wait_and_retry, daemon=True).start()
            return
        if sender in autoreply_timers:
            return
        ip, target_port = known_users[sender]
        def send_reply():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((ip, int(target_port)))
                    s.sendall(f"MSG {handle} {autoreply}".encode('utf-8'))
                    to_ui.put(f"{ts()} >>> Autoreply an {sender} gesendet.")
                    autoreply_sent.add(sender)
            except Exception:
                to_ui.put(f"{ts()} Autoreply an {sender} fehlgeschlagen.")
            finally:
                autoreply_timers.pop(sender, None)
        timer = threading.Timer(5.0, send_reply)
        autoreply_timers[sender] = timer
        timer.start()

    def cancel_autoreply_if_needed(target):
        if target in autoreply_timers:
            autoreply_timers[target].cancel()
            del autoreply_timers[target]
        autoreply_sent.add(target)

    def tcp_listener():
        while True:
            conn, addr = tcp_sock.accept()
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data += chunk
            header = data.decode("utf-8").strip()

            if header.startswith("KNOWNUSERS"):
                parts = header[len("KNOWNUSERS "):].split(", ")
                formatted_users = {}
                for entry in parts:
                    u, ip, p = entry.strip().split()
                    if u == handle:
                        continue
                    if u not in known_users:
                        known_users[u] = (ip, int(p))
                        formatted_users[u] = (ip, int(p))
                if formatted_users:
                    formatted = ", ".join(f"{u} ({ip}:{p})" for u, (ip, p) in formatted_users.items())
                    to_ui.put(f">>> Bekannt: {formatted}")        
