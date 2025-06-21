##
# @file discovery.py
# @brief Peer discovery module for SLCP (Simple LAN Chat Protocol)
#
# This module implements the decentralized peer discovery mechanism used by the SLCP chat application.
# It uses UDP broadcasting to detect other clients on the same network via `JOIN`, `WHO`, and `KNOWUSERS` messages.
# One process takes the role of a WHO responder and provides a list of all known clients upon request.
#
# The discovery process is run in a separate process and periodically sends discovery messages to update the local peer list.
#
# @author Group SLCP
# @date June 2025
#

import socket
import time

##
# @brief Get the local machine's IP address.
#
# This utility function connects to a known external IP (Google DNS) to determine the outbound interface.
# If no connection is possible, falls back to loopback.
#
# @return A string representing the local IP address.
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

##
# @brief Main discovery process function.
#
# This function is designed to run in its own multiprocessing process. It listens and sends UDP broadcasts
# to discover peers on the network. It maintains a list of active peers by interpreting SLCP commands like:
# - `JOIN` (a peer has joined),
# - `LEAVE` (a peer has left),
# - `WHO` (a peer is asking who is online),
# - `KNOWUSERS` (a reply containing known peers).
#
# One client that successfully binds to the discovery port acts as the WHO responder.
# The process listens to a control pipe for termination.
#
# @param config A shared dictionary (Manager.dict) containing client configuration and a shared peer list.
#        Required fields: `handle`, `port`, `whoisport`, `peers`.
# @param ctrl_pipe A multiprocessing pipe used by the main process to send control signals (e.g., "STOP").
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

    ##
    # @brief Broadcast a UTF-8 encoded message over the discovery UDP socket.
    # @param msg The message string to broadcast.
    def broadcast(msg: str):
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

    while True:
        # Handle stop command from main process
        if ctrl_pipe.poll():
            cmd = ctrl_pipe.recv()
            if cmd == "STOP":
                print("[Discovery] Terminated by main process.")
                break

        # Broadcast JOIN and WHO messages
        broadcast(f"JOIN {handle} {port}\n")
        broadcast("WHO\n")

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

            # Handle JOIN message: add new peer
            if cmd == "JOIN" and len(parts) == 3:
                peer, pport = parts[1], int(parts[2])
                entry = (peer, addr[0], pport)
                if peer != handle and entry not in peers:
                    peers.append(entry)
                    print(f"[Discovery] New peer detected: {entry}")

            # Handle LEAVE message: remove peer
            elif cmd == "LEAVE" and len(parts) == 2:
                peer = parts[1]
                peers[:] = [p for p in peers if p[0] != peer]

            # Handle WHO request: respond with known users
            elif cmd == "WHO" and responder:
                all_known = [(handle, get_local_ip(), port)] + list(peers)
                payload = ",".join(f"{h} {ip} {pt}" for h, ip, pt in all_known)
                sock.sendto(f"KNOWUSERS {payload}".encode("utf-8"), addr)

            # Handle KNOWUSERS response: merge peer list
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