import socket
import os
import multiprocessing
import sys
import threading
import time
from datetime import datetime

import toml
from processes.discovery import discovery_process
from processes.network import network_process

CONFIG_FILE = "config.toml"

# Farben
COLOR_RESET  = "\033[0m"
COLOR_GREEN  = "\033[92m"
COLOR_RED    = "\033[91m"
COLOR_YELLOW = "\033[93m"

def ts():
    return datetime.now().strftime("[%H:%M:%S]")

def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("", port))
            return False
        except OSError:
            return True

def main():
    cfg_all = toml.load(CONFIG_FILE)
    clients = cfg_all.get("clients", [])
    if not clients:
        print("No [[clients]] section found in config.toml.")
        sys.exit(1)

    if len(sys.argv) != 2:
        handles = [c["handle"] for c in clients]
        print("Usage: python cli.py <Handle>")
        print("Available handles:", ", ".join(handles))
        sys.exit(1)

    chosen = sys.argv[1]
    client_index = next((i for i, c in enumerate(clients) if c["handle"] == chosen), None)
    if client_index is None:
        print(f"Handle '{chosen}' not found.")
        sys.exit(1)

    config = clients[client_index]
    manager = multiprocessing.Manager()
    config["peers"] = manager.list()
    config["__cfg_all"] = cfg_all
    config["__cfg_index"] = clients.index(config)

    ui2net_p, ui2net_c = multiprocessing.Pipe()
    net2ui_p, net2ui_c = multiprocessing.Pipe()
    disc_ctrl_parent, disc_ctrl_child = multiprocessing.Pipe()

    p_disc = None
    if not port_in_use(config["whoisport"]):
        p_disc = multiprocessing.Process(target=discovery_process, args=(config, disc_ctrl_child))
        p_disc.start()
        print(f"[INFO] Discovery service started on port {config['whoisport']}")
    else:
        print(f"[INFO] Discovery already running on port {config['whoisport']}")

    p_net = multiprocessing.Process(target=network_process, args=(config, ui2net_c, net2ui_p))
    p_net.start()

    left_peers = set()

    def poll_network():
        while True:
            while net2ui_c.poll():
                typ, src, payload = net2ui_c.recv()
                if typ == 'MSG':
                    print(f"\n{COLOR_GREEN}{ts()} [{src}] {payload}{COLOR_RESET}\n")
                elif typ == 'IMG':
                    print(f"\n{COLOR_YELLOW}{ts()} [{src}] sent image → {payload}{COLOR_RESET}\n")
                elif typ == 'LEAVE':
                    if src not in left_peers:
                        print(f"\n{COLOR_RED}{ts()} [{src}] left the chat.{COLOR_RESET}\n")
                        left_peers.add(src)
                    config['peers'][:] = [p for p in config['peers'] if p[0] != src]
            time.sleep(0.05)

    threading.Thread(target=poll_network, daemon=True).start()