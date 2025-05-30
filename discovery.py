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

                if parts[0] == "JOIN" and len(parts) == 3:
                    known_users[parts[1]] = (addr[0], parts[2])
                    print(f"[Discovery] {parts[1]} joined from {addr[0]}:{parts[2]}")

                elif parts[0] == "LEAVE" and len(parts) == 2:
                    leaver = parts[1]
                    if leaver in known_users:
                        del known_users[leaver]
                    print(f"[Discovery] {leaver} left.")
                    if to_ui:
                        to_ui.put(f"[{leaver}] hat den Chat verlassen.")

                elif parts[0] == "WHO" and len(parts) == 3:
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

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    thread.join()