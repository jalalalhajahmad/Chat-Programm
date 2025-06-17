import socket
import time

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def discovery_process(config, ctrl_pipe):
    handle    = config["handle"]
    port      = config["port"][0]
    whoisport = config["whoisport"]
    peers     = config["peers"]

    responder = False  # Only one client becomes WHO responder

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind(("", whoisport))
        responder = True
        print(f"[Discovery] WHO responder active on {whoisport}")
    except OSError as e:
        print(f"[Discovery] Not WHO responder – {e}")

    sock.settimeout(1.0)

    def broadcast(msg: str):
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

    while True:
        if ctrl_pipe.poll():
            cmd = ctrl_pipe.recv()
            if cmd == "STOP":
                print("[Discovery] Terminated by main process.")
                break

        broadcast(f"JOIN {handle} {port}")
        broadcast("WHO")

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

            if cmd == "JOIN" and len(parts) == 3:
                peer, pport = parts[1], int(parts[2])
                entry = (peer, addr[0], pport)
                if peer != handle and entry not in peers:
                    peers.append(entry)
                    print(f"[Discovery] New peer detected: {entry}")

            elif cmd == "LEAVE" and len(parts) == 2:
                peer = parts[1]
                peers[:] = [p for p in peers if p[0] != peer]

            elif cmd == "WHO" and responder:
                all_known = [(handle, get_local_ip(), port)] + list(peers)
                payload = ",".join(f"{h} {ip} {pt}" for h, ip, pt in all_known)
                sock.sendto(f"KNOWUSERS {payload}".encode("utf-8"), addr)

            elif cmd == "KNOWUSERS":
                rest = text[len("KNOWUSERS "):]
                for chunk in rest.split(','):
                    if not chunk.strip():
                        continue
                    try:
                        h, ip, pt = chunk.strip().split()
                        entry = (h, ip, int(pt))
                        if h != handle and entry not in peers:
                            peers.append(entry)
                    except ValueError:
                        continue

        time.sleep(3)
