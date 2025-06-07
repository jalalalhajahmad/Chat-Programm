import socket, os, time, threading

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

    def _serve():
        conn, _ = server.accept()
        conn.sendall(data)
        conn.close()
        server.close()

    threading.Thread(target=_serve, daemon=True).start()

def network_process(config, ui2net, net2ui):
    handle     = config["handle"]
    port       = config["port"][0]
    whoisport  = config["whoisport"]
    peers      = config["peers"]
    autoreply  = config["autoreply"]
    away       = config.get("away", False)
    img_path   = config["imagepath"]
    os.makedirs(img_path, exist_ok=True)

    afk_replied_to = set()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(("", port))
    udp_sock.setblocking(False)

    def send_periodic_join():
        while True:
            try:
                msg = f"JOIN {handle} {port}".encode("utf-8")
                udp_sock.sendto(msg, ("255.255.255.255", whoisport))
            except Exception as e:
                print(f"[JOIN] Fehler beim Senden: {e}")
            time.sleep(5)

    def send_periodic_who():
        while True:
            try:
                udp_sock.sendto(b"WHO", ("255.255.255.255", whoisport))
            except Exception as e:
                print(f"[WHO] Fehler beim Senden: {e}")
            time.sleep(5)

    threading.Thread(target=send_periodic_join, daemon=True).start()
    threading.Thread(target=send_periodic_who, daemon=True).start()

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
                if not away:
                    afk_replied_to.clear()
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

        if not text:
            continue

        parts = text.split()
        cmd = parts[0]

        if cmd != "KNOWUSERS":
            print(f"[RECV] Raw: {text}")

        if cmd == "MSG" and len(parts) >= 4:
            src, dest = parts[1], parts[2]
            msg = ' '.join(parts[3:])
            if dest == handle or dest == "ALL":
                net2ui.send(("MSG", src, msg))
                if away and dest == handle:
                    if src not in afk_replied_to:
                        udp_sock.sendto(
                            f"MSG {handle} {src} {autoreply}".encode("utf-8"),
                            addr
                        )
                        afk_replied_to.add(src)

        elif cmd == "IMG" and len(parts) == 5:
            src, dest, tcp_port_s, size_s = parts[1], parts[2], parts[3], parts[4]
            if dest != handle:
                continue

            tcp_port = int(tcp_port_s)
            size     = int(size_s)

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((addr[0], tcp_port))

            buf = b""
            while len(buf) < size:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
            client.close()

            fn = os.path.join(img_path, f"{src}_{int(time.time())}.png")
            with open(fn, "wb") as f:
                f.write(buf)
            net2ui.send(("IMG", src, fn))

        elif cmd == "LEAVE" and len(parts) == 2:
            leaver = parts[1]
            net2ui.send(("LEAVE", leaver, ""))
            peers[:] = [p for p in peers if p[0] != leaver]

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
                        print(f"[KNOWUSERS] Neuer Peer: {entry}")
                except ValueError:
                    continue

        time.sleep(0.01)
