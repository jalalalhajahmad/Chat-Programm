import socket, os, time, threading

DISCOVERY_PORT = None
MAX_UDP_SIZE = 65507

def send_image_via_tcp(config, dest_handle, filepath, peer_ip, peer_port):
    handle    = config["handle"]
    img_path  = config["imagepath"]
    data = open(filepath, "rb").read()
    size = len(data)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("", 0))
    server.listen(1)
    tcp_port = server.getsockname()[1]

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.sendto(f"IMG {handle} {dest_handle} {tcp_port} {size}".encode("utf-8"),
               (peer_ip, peer_port))
    udp.close()

    def serve():
        conn,  = server.accept()
        conn.sendall(data)
        conn.close()
        server.close()

    threading.Thread(target=serve, daemon=True).start()

def network_process(config, ui2net, net2ui):
    handle     = config["handle"]
    port       = config["port"][0]
    whoisport  = config["whoisport"]
    peers      = config["peers"]
    autoreply  = config["autoreply"]
    away       = config.get("away", False)
    img_path   = config["imagepath"]
    os.makedirs(img_path, exist_ok=True)

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind(("", port))
    udp_sock.setblocking(False)

    while True:
        if ui2net.poll():
            cmd, dest, payload = ui2net.recv()

            if cmd == "MSG":
                header = f"MSG {handle} {dest} {payload}".encode("utf-8")
                for _, ip, pt in peers:
                    udp_sock.sendto(header, (ip, pt))

            elif cmd == "IMG":
                for h, ip, pt in peers:
                    if h == dest:
                        send_image_via_tcp(config, dest, payload, ip, pt)

            elif cmd == "LEAVE":
                for h, ip, pt in peers:
                    udp_sock.sendto(f"LEAVE {handle}".encode("utf-8"), (ip, pt))

            elif cmd == "AFK":
                status = payload.strip().upper()
                away = (status == "ON")
                config["away"] = away
                print(f"[NETZWERK] AFK-Modus {'aktiviert' if away else 'deaktiviert'}.")

                afk_info = "[AFK] {} ist jetzt {}".format(handle, "abwesend" if away else "wieder verfügbar")
                for _, ip, pt in peers:
                    msg = f"MSG {handle} ALL {afk_info}"
                    udp_sock.sendto(msg.encode("utf-8"), (ip, pt))
                    print(f"[SEND] → {msg}")

        try:
            data, addr = udp_sock.recvfrom(MAX_UDP_SIZE)
        except BlockingIOError:
            time.sleep(0.01)
            continue

        try:
            text = data.decode("utf-8").strip()
        except UnicodeDecodeError:
            continue

        print(f"[RECV] Raw: {text}")

        parts = text.split()
        cmd = parts[0]
        time.sleep(0.01)