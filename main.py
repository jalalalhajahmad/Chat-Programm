import toml
import multiprocessing
import sys
from processes.discovery import discovery_process
from processes.network import network_process
from processes.gui import gui_process as ui_process

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python main.py <Handle>")
        sys.exit(1)

    handle = sys.argv[1]
    config_file = 'config.toml'

    with open(config_file, 'r') as f:
        all_clients = toml.load(f)['clients']
        match = [c for c in all_clients if c['handle'] == handle]

        if not match:
            print(f"Kein Eintrag für Handle '{handle}' in config.toml gefunden.")
            sys.exit(1)

        config = match[0]

    ipc_ui_to_net = multiprocessing.Queue()
    ipc_net_to_ui = multiprocessing.Queue()

    discovery_proc = multiprocessing.Process(target=discovery_process, args=(config, ipc_net_to_ui))
    network_proc = multiprocessing.Process(target=network_process, args=(config, ipc_ui_to_net, ipc_net_to_ui))

    discovery_proc.start()
    network_proc.start()

    ui_process(config, ipc_ui_to_net, ipc_net_to_ui)

    discovery_proc.terminate()
    network_proc.terminate()
    discovery_proc.join()
    network_proc.join()

if __name__ == "__main__":
 main()
