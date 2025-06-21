# ChatProgramm_Final

A decentralized, peer-to-peer chat application developed in Python for the **Betriebssysteme und Rechnernetze** (Operating Systems and Computer Networks) course.  
This project implements a custom protocol called SLCP (Simple Local Chat Protocol) to demonstrate real-time communication over local networks without relying on central servers.

## Project Overview

The application enables direct communication between clients in the same network, supporting both text messaging and image transfer. Peers are discovered dynamically via UDP broadcasting. The system combines lightweight protocols (UDP for control/data, TCP for binary files) and provides both a graphical and terminal-based user interface.

Typical use cases:
- Real-time 1:1 peer messaging
- Reliable image file transfer
- Away-from-keyboard (AFK) status with autoreplies
- Auto-discovery of connected clients in the network
- GUI and CLI interface options

---

## Features

- **Peer Discovery:** Broadcast-based peer discovery using `JOIN`, `WHO`, and `KNOWUSERS` messages.
- **Message Exchange:** Real-time message delivery over UDP.
- **Image Transfer:** TCP-based file transfer with UDP notification handshakes.
- **AFK Mode:** Automatic autoreplies when a user is away.
- **Graphical Interface:** Built using PyQt5 with dark/light theme support.
- **Settings Dialog:** Runtime configuration for user handle, port, autoreply message, and image folder.
- **CLI Interface:** Text-based command-line chat interface with full feature parity.
- **Fully Documented:** Comprehensive technical documentation generated using Doxygen.

---

## Architecture

```
┌──────────────┐       ┌────────────────┐       ┌────────────┐
│  discovery   │──────▶│  peer registry │◀──────│  network   │
└──────────────┘       └────────────────┘       └────────────┘
       │                         ▲                      ▲
       ▼                         │                      │
 ┌────────────┐           ┌────────────┐          ┌────────────┐
 │ UDP socket │           │ config.toml│          │   GUI / CLI│
 └────────────┘           └────────────┘          └────────────┘
```

### Core Modules

| Module        | Description                                  |
|---------------|----------------------------------------------|
| `main.py`     | Application entry point with GUI interface   |
| `cli.py`      | Alternative CLI-based interface              |
| `discovery.py`| Broadcast-based peer discovery logic         |
| `network.py`  | Handles UDP messaging, AFK logic, TCP images |
| `gui.py`      | PyQt5-based user interface logic             |
| `config.toml` | TOML configuration for clients and settings  |

---

## Team and Responsibilities

| Name                        | Matrikelnummer | Responsibilities                                                                   |
|-----------------------------|----------------|------------------------------------------------------------------------------------|
| **Aashir Ahtisham**         | 1447390        | Main developer for `discovery.py`, contributed to `network.py`                     |
| **Bratli Metuka**           | 1505429        | Main contributor to `network.py`, helped with `gui.py`                             |
| **Jalal Eddin Alhaj Ahmad** | 1428348        | Main contributor to `cli.py` and `gui.py`, also worked on `discovery.py`           |
| **Joseph Bolaños Beyloune** | 1534591        | Main contributor to documentation, contributed to `cli.py`, `gui.py`, `network.py` |
| **Ömer Faruk Capraz**       | 1522507        | Main contributor to documentation, helped with `discovery.py` and `cli.py`         |

---

## Installation & Setup

### 1. Install Dependencies

Ensure Python 3.10+ is installed. Then install:

```bash
pip install PyQt5 toml qdarkstyle
```

Or using `requirements.txt` if provided:

```bash
pip install -r requirements.txt
```

---

### 2. Configure Clients

Update the `config.toml` file to define your client settings:

```toml
[[clients]]
handle = "Aashir"
port = [5008, 6000]
whoisport = 4000
autoreply = "Back in one hour"
away = false
imagepath = "./images/aashir"
```

Each client must have a unique `handle`, and ports must not conflict.

---

### 3. Launch the Application

To run with the GUI:

```bash
python3 main.py Aashir
```

To run via CLI:

```bash
python3 cli.py Aashir
```

Replace `"Aashir"` with any configured handle in `config.toml`.

---

### 4. GUI Controls

- **Send Message**: Press Enter or click "Send"
- **Send Image**: Select an image via "Send Image" button
- **Clients**: Show connected peers
- **AFK Toggle**: Enable/disable AFK autoreply
- **Settings**: Edit configuration interactively
- **Leave Chat**: Graceful exit

---

## Testing

You can simulate multiple clients by:
- Opening multiple terminal sessions with different handles
- Running on separate machines in the same LAN
- Observing image transfers and peer join/leave messages

---

## Documentation

Doxygen documentation is located at:

```
docs/html/index.html
```

To regenerate:

```bash
doxygen Doxyfile
```

The documentation includes:
- Function and class reference
- Namespace and file structure
- Inline code documentation

---

## Technologies

- **Python 3.10+**
- **PyQt5**
- **TOML**
- **Socket Programming (UDP/TCP)**
- **Doxygen**

---

## Security Notice

This application is designed for academic purposes only.  
It does **not** implement encryption, authentication, or secure transport mechanisms.  
Use only on trusted local networks.

---

## License

MIT License – For educational use only.