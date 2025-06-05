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
 time.sleep(3)