import sys
import toml
import multiprocessing
import socket
from processes.discovery import discovery_process
from processes.network   import network_process
from processes.gui       import gui_process

def main():
    cfg_all = toml.load("config.toml")
    clients = cfg_all.get("clients", [])
    if not clients:
        print("Keine [[clients]] in config.toml.")
        sys.exit(1)

    if len(sys.argv) != 2:
        handles = [c["handle"] for c in clients]
        print("Verwendung: python main.py <Handle>")
        print("Verfügbare Handles:", ", ".join(handles))
        sys.exit(1)

    chosen = sys.argv[1]
    client_conf = next((c for c in clients if c["handle"] == chosen), None)
    if client_conf is None:
        print(f"Handle '{chosen}' nicht gefunden.")
        sys.exit(1)

    config = client_conf
    manager = multiprocessing.Manager()
    config["peers"] = manager.list()

    ui2net_p, ui2net_c = multiprocessing.Pipe()
    net2ui_p, net2ui_c = multiprocessing.Pipe()

    p_net  = multiprocessing.Process(target=network_process, args=(config, ui2net_c, net2ui_p))
    p_gui  = multiprocessing.Process(target=gui_process,       args=(config, ui2net_p, net2ui_c))

    p_net.start()
    p_gui.start()

    # GUI läuft im Vordergrund
    p_gui.join()

    # Prozesse korrekt beenden
    p_net.terminate()
    p_net.join()

if __name__ == "__main__":
    main()