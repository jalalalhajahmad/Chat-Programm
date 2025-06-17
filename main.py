import sys
import toml
import multiprocessing
import socket
import os
from processes.discovery import discovery_process
from processes.network   import network_process
from processes.gui       import gui_process

# Helper function to check if a UDP port is already in use
def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("", port))  # Try to bind to the port
            return False        # Success: port not in use
        except OSError:
            return True         # Port already in use

# Save updated configuration to file
def save_config_to_file(cfg_all):
    with open("config.toml", "w") as f:
        toml.dump(cfg_all, f)

def main():
    # Load configuration from TOML file
    cfg_all = toml.load("config.toml")
    clients = cfg_all.get("clients", [])
    if not clients:
        print("No [[clients]] section found in config.toml.")
        sys.exit(1)

    # Ensure a handle argument is provided
    if len(sys.argv) != 2:
        handles = [c["handle"] for c in clients]
        print("Usage: python main.py <Handle>")
        print("Available handles:", ", ".join(handles))
        sys.exit(1)

    # Match provided handle to a client config
    chosen = sys.argv[1]
    client_index = next((i for i, c in enumerate(clients) if c["handle"] == chosen), None)
    if client_index is None:
        print(f"Handle '{chosen}' not found.")
        sys.exit(1)

    config = clients[client_index]
    manager = multiprocessing.Manager()
    config["peers"] = manager.list()  # Shared list of known peers  
    config["__cfg_all"] = cfg_all # For saving updated config
    config["__cfg_index"] = clients.index(config)


    # Create pipes for inter-process communication
    ui2net_p, ui2net_c = multiprocessing.Pipe()     # GUI → Network
    net2ui_p, net2ui_c = multiprocessing.Pipe()     # Network → GUI
    disc_ctrl_parent, disc_ctrl_child = multiprocessing.Pipe()  # Main → Discovery

    # Start discovery process only if port is free
    if not port_in_use(config["whoisport"]):
        p_disc = multiprocessing.Process(target=discovery_process, args=(config, disc_ctrl_child))
        p_disc.start()
        print(f"[INFO] Discovery service started on port {config['whoisport']}")
    else:
        p_disc = None
        print(f"[INFO] Discovery service already running on port {config['whoisport']}, not starting again.")

    # Start network and GUI processes
    p_net = multiprocessing.Process(target=network_process, args=(config, ui2net_c, net2ui_p))
    p_gui = multiprocessing.Process(target=gui_process,       args=(config, ui2net_p, net2ui_c))

    p_net.start()
    p_gui.start()

    # Wait for GUI process to exit (user closed window)
    p_gui.join()

    # Stop discovery process if we started it
    if p_disc:
        disc_ctrl_parent.send("STOP")
        p_disc.join()

    # Notify network process to exit cleanly
    ui2net_p.send(("EXIT", "", ""))
    p_net.join()

# Entry point
if __name__ == "__main__":
    main()
    