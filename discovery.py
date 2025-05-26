import socket
import threading

def discovery_process(config, to_ui=None):
    handle = config['handle']
    port = config['whoisport']
    local_port = config['port']
    local_ip = socket.gethostbyname(socket.gethostname())

    known_users = {
        handle: (local_ip, str(local_port))
    }

    def listen():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', port))
        print(f"[Discovery] Listening on UDP {port}")
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode('utf-8').strip()
                parts = msg.split()

                if parts[0] == "WHO" and len(parts) == 3:
                    target_port = int(parts[2])
                    reply = "KNOWNUSERS " + ", ".join(
                        f"{u} {ip} {p}" for u, (ip, p) in known_users.items()
                    )
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(2)
                            s.connect((addr[0], target_port))
                            s.sendall((reply + "\n").encode('utf-8'))
                    except:
                        pass
            except:
                pass
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    thread.join()
