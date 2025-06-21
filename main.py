##
# @file main.py
# @brief Main graphical launcher for the SLCP (Simple Local Chat Protocol) peer-to-peer chat application.
#
# This script serves as the entry point for launching the GUI version of the SLCP client.
# It reads configuration from a TOML file, initializes inter-process communication pipes,
# and starts three key processes:
# - `discovery_process` (UDP broadcast peer discovery)
# - `network_process`   (handles SLCP messages, AFK state, and file/image transfers)
# - `gui_process`       (PyQt5 graphical chat interface)
#
# Main responsibilities:
# - Validates user input and config structure
# - Manages subprocess startup and shutdown
# - Coordinates inter-process communication
# - Persists updated configuration settings to `config.toml`
#
# Usage:
# ```
# python main.py <Handle>
# ```
# where `<Handle>` corresponds to a user listed in `config.toml` under [[clients]].
#
# @date June 2025
# @author SLCP
#

import sys
import toml
import multiprocessing
import socket
import os
from processes.discovery import discovery_process
from processes.network   import network_process
from processes.gui       import gui_process

##
# @brief Checks whether the specified UDP port is already in use.
#
# This function attempts to bind to the given port to detect conflicts.
#
# @param port UDP port number to test.
# @return True if the port is currently in use, False if available.
def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("", port))  # Try to bind to the port
            return False        # Success: port not in use
        except OSError:
            return True         # Port already in use

##
# @brief Saves the full client configuration back to the TOML file.
#
# Used when users update settings via the GUI's configuration dialog.
#
# @param cfg_all Full configuration dictionary (includes all [[clients]]).
def save_config_to_file(cfg_all):
    with open("config.toml", "w") as f:
        toml.dump(cfg_all, f)

##
# @brief Entry point for launching the GUI-based SLCP chat client.
#
# Loads user configuration, initializes inter-process pipes, and spawns child processes.
# Waits for the GUI to terminate before performing graceful shutdown.
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
    config["peers"] = manager.list()         # Shared list of known peers
    config["__cfg_all"] = cfg_all            # Full config for saving later
    config["__cfg_index"] = clients.index(config)  # Index of this client in the TOML file

    # Create pipes for inter-process communication
    ui2net_p, ui2net_c = multiprocessing.Pipe()     # GUI → Network
    net2ui_p, net2ui_c = multiprocessing.Pipe()     # Network → GUI
    disc_ctrl_parent, disc_ctrl_child = multiprocessing.Pipe()  # Main → Discovery (for stopping)

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

##
# @brief Main Python entry point.
#
# Parses user input and launches the SLCP GUI chat application.
if __name__ == "__main__":
    main()