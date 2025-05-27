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

            elif header.startswith("MSG"):
                try:
                    _, sender, text = header.split(" ", 2)
                    to_ui.put(f"[{sender}] {text}")
                    if autoreply:
                        schedule_autoreply(sender)
                except ValueError:
                    to_ui.put(f"{ts()} Ungültige MSG empfangen: {header}")

            elif header.startswith("IMG"):
                try:
                    parts = header.split()
                    sender = parts[1]
                    size = int(parts[2])
                    img_data = b""
                    while len(img_data) < size:
                        chunk = conn.recv(min(4096, size - len(img_data)))
                        if not chunk:
                            break
                        img_data += chunk
                    filename = os.path.join(imagepath, f"{sender}_bild.jpg")
                    with open(filename, "wb") as f:
                        f.write(img_data)
                    to_ui.put(f"{ts()} Bild von {sender} empfangen und gespeichert: {filename}")
                except Exception as e:
                    to_ui.put(f"{ts()} Fehler beim Empfangen eines Bildes: {e}")
            conn.close()

    threading.Thread(target=tcp_listener, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(f"JOIN {handle} {port}".encode('utf-8'), ('255.255.255.255', whoisport))

    while True:
        if not from_ui.empty():
            cmd = from_ui.get()
            if not cmd:
                continue
            if cmd.strip().upper() == "WHO":
                send_udp_who(port)
                continue
            elif cmd.startswith("MSG"):
                parts = cmd.split()
                if len(parts) < 3:
                    to_ui.put("Ungültiger MSG-Befehl. Format: MSG <Handle> <Nachricht>")
                    continue
                _, target, *text = parts
                msg = " ".join(text)
                if target not in known_users:
                    send_udp_who(port)
                    time.sleep(1)
                if target in known_users:
                    ip, p = known_users[target]
                    send_tcp_message(ip, p, f"MSG {handle} {msg}")
                    to_ui.put(f"[{handle}] {msg}")
                    cancel_autoreply_if_needed(target)
                else:
                    to_ui.put(f"{ts()} Handle {target} nicht gefunden.")
            elif cmd.startswith("IMG"):
                try:
                    _, target, filepath = cmd.split(maxsplit=2)
                    if not os.path.exists(filepath):
                        to_ui.put(f"Bilddatei nicht gefunden: {filepath}")
                        continue
                    if target not in known_users:
                        send_udp_who(port)
                        time.sleep(1)
                    if target in known_users:
                        ip, p = known_users[target]
                        filesize = os.path.getsize(filepath)
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((ip, p))
                            header = f"IMG {handle} {filesize}\n".encode('utf-8')
                            s.sendall(header)
                            with open(filepath, 'rb') as f:
                                s.sendfile(f)
                        to_ui.put(f"Bild erfolgreich an {target} gesendet.")
                    else:
                        to_ui.put(f"{ts()} Handle {target} nicht gefunden.")
                except Exception as e:
                    to_ui.put(f"Fehler beim Senden des Bildes: {e}")
            elif cmd.strip().upper() == "LEAVE":
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.sendto(f"LEAVE {handle}".encode('utf-8'), ('255.255.255.255', whoisport))
                to_ui.put("__EXIT__")
                break
