import socket
import time

def discovery_process(config):
    handle    = config["handle"]
    port      = config["port"][0]
    whoisport = config["whoisport"]
    peers     = config["peers"]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", whoisport))
    except OSError as e:
        print(f"[Discovery] ⚠️ Port {whoisport} belegt: {e}")
        return
    sock.settimeout(1.0)

    def broadcast(msg: str):
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

    while True:
        # Regelmäßig JOIN + WHO senden
        broadcast(f"JOIN {handle} {port}")
        broadcast("WHO")

        # Antworten empfangen
        start = time.time()
        while time.time() - start < 1.0:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                break

            try:
                text = data.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue

            if not text:
                continue

            parts = text.split()
            cmd = parts[0]

            time.sleep(3)