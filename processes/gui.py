##
# @file gui.py
# @brief Graphical User Interface (GUI) for SLCP Chat.
#
# This module provides a complete graphical frontend for the SLCP (Simple LAN Chat Protocol) client.
# It allows users to send and receive messages and images, manage peer visibility, toggle AFK (away-from-keyboard) mode,
# access configuration settings, and quit the session gracefully.
#
# Communication with the network and discovery processes is handled via multiprocessing pipes.
# Built using PyQt5 and styled optionally using QDarkStyle.
#
# Key GUI Features:
# - Display chat log with timestamps and color-coded messages
# - Input fields for recipient and message
# - Send image button (opens file dialog)
# - View active clients
# - AFK mode toggle with autoreply functionality
# - Dark mode toggle
# - In-app configuration management
#
# @author SLCP Team
# @date June 2025
#

import sys
import os
import subprocess
import platform
import socket
import toml
import qdarkstyle
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QDialog, QFormLayout
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QTextCursor, QColor

MAX_DISPLAY_CHUNK = 200  # Max characters per chat display chunk
CONFIG_FILE = "config.toml"  # Default path to config file

##
# @brief Generate a timestamp string for message labeling.
# @return Timestamp in the format [HH:MM:SS]
def ts():
    from datetime import datetime
    return datetime.now().strftime("[%H:%M:%S]")

##
# @brief Open a file with the default system application.
# @param path Path to the file to open.
def open_file(path):
    if platform.system() == 'Windows':
        os.startfile(path)
    elif platform.system() == 'Darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])

##
# @brief Get the current machine's local IP address.
#
# Attempts a connection to a public DNS server to infer outbound interface IP.
# Fallback is 127.0.0.1 if no internet connection exists.
#
# @return Local IP address as string.
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
# @class SettingsDialog
# @brief Dialog window for editing and saving user configuration.
#
# Provides editable fields for handle, port, autoreply message, and image directory.
# Saves updated values directly into the configuration TOML file and notifies the user.
class SettingsDialog(QDialog):
    ##
    # @brief Constructor for SettingsDialog.
    # @param config Reference to the active client configuration.
    # @param parent Parent QWidget, if any.
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QFormLayout(self)

        self.handle_field = QLineEdit(config["handle"])
        self.port_field = QLineEdit(str(config["port"][0]))
        self.autoreply_field = QLineEdit(config["autoreply"])
        self.imagepath_field = QLineEdit(config["imagepath"])

        layout.addRow("Handle:", self.handle_field)
        layout.addRow("Port:", self.port_field)
        layout.addRow("Autoreply:", self.autoreply_field)
        layout.addRow("Image-Ordner:", self.imagepath_field)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

        self.config = config

    ##
    # @brief Validate and persist user configuration to disk.
    #
    # Updates local config dictionary and re-writes the TOML file.
    # Informs user via message box on success or error.
    def save(self):
        try:
            self.config["handle"] = self.handle_field.text()
            self.config["port"][0] = int(self.port_field.text())
            self.config["autoreply"] = self.autoreply_field.text()
            self.config["imagepath"] = self.imagepath_field.text()
            os.makedirs(self.config["imagepath"], exist_ok=True)

            all_cfg = self.config["__cfg_all"]
            index = self.config["__cfg_index"]

            clean_config = {
                k: v for k, v in self.config.items()
                if k not in ("peers", "__cfg_all", "__cfg_index")
            }

            all_cfg["clients"][index] = clean_config
            with open("config.toml", "w") as f:
                toml.dump(all_cfg, f)

            QMessageBox.information(self, "Saved", "Configuration saved. Please restart the program.")
            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Invalid input: {e}")

##
# @brief Launches the SLCP GUI as a separate process.
#
# Connects user inputs and received messages through inter-process communication (IPC) with the network process.
# Implements all chat interface elements (send, AFK toggle, image sending, client listing, etc.).
# Polls for incoming network data and handles state updates accordingly.
#
# @param config A dictionary containing client state and runtime configuration.
# @param to_network A pipe object to send data to the network process.
# @param from_network A pipe object to receive data from the network process.
def gui_process(config, to_network, from_network):
    handle = config['handle']
    img_path = config['imagepath']
    os.makedirs(img_path, exist_ok=True)

    app = QApplication(sys.argv)
    wnd = QWidget()
    wnd.setWindowTitle(f"SLCP Chat – {handle}")

    # Main layout
    vlayout = QVBoxLayout()
    chat = QTextEdit(); chat.setReadOnly(True)
    vlayout.addWidget(chat)

    # Control layout (buttons + inputs)
    controls = QHBoxLayout()
    dest_input = QLineEdit(); dest_input.setPlaceholderText("Recipient handle")
    msg_input = QLineEdit(); msg_input.setPlaceholderText("Message…")
    btn_send = QPushButton("Send")
    btn_img = QPushButton("Send Image")
    btn_clients = QPushButton("Clients")
    btn_leave = QPushButton("Leave Chat")
    btn_afk = QPushButton("AFK: OFF"); btn_afk.setCheckable(True)
    btn_afk.setStyleSheet("background-color: #666; color: white;")
    btn_dark = QPushButton("Dark Mode"); btn_dark.setCheckable(True)
    btn_settings = QPushButton("Settings")

    for w in (dest_input, msg_input, btn_send, btn_img, btn_clients, btn_settings, btn_leave, btn_afk, btn_dark):
        controls.addWidget(w)
    vlayout.addLayout(controls)
    wnd.setLayout(vlayout)

    local_peers = set()
    afk_mode = False

    ##
    # @brief Append message to chat window with color and timestamp.
    # @param text The message content.
    # @param color The HTML hex color string for the message text.
    def append(text, color="#010202"):
        chat.setTextColor(QColor(color))
        chat.append(f"{ts()} {text}")
        chat.moveCursor(QTextCursor.End)

    ##
    # @brief Sends a text message to a specified recipient.
    def send_message():
        dest = dest_input.text().strip()
        msg = msg_input.text().strip()
        if not dest or not msg:
            return
        append(f"{handle}: {msg}", "#2A8940")
        to_network.send(("MSG", dest, msg))
        msg_input.clear()

    ##
    # @brief Opens a file dialog and sends an image file to the specified recipient.
    def send_image():
        path, _ = QFileDialog.getOpenFileName(wnd, "Select image", "", "Images (*.png *.jpg *.bmp *.webp)")
        if not path:
            return
        dest = dest_input.text().strip()
        if not dest:
            QMessageBox.warning(wnd, "Error", "Please enter recipient handle!")
            return
        append(f"{handle} → {dest} [Image]", "#2A8940")
        to_network.send(("IMG", dest, path))

    ##
    # @brief Displays a list of active known peers.
    def show_clients():
        peers = [(h, ip, pt) for (h, ip, pt) in config['peers'] if h != handle]
        if not peers:
            QMessageBox.information(wnd, "Clients", "No other clients found.")
        else:
            local_ip = get_local_ip()
            local_port = config["port"][0]
            info = "\n".join(f"{h} ({ip}:{pt})" for (h, ip, pt) in peers)
            QMessageBox.information(wnd, "Clients", f"You: {handle} ({local_ip}:{local_port})\n\nActive clients:\n{info}")

    already_closing = False

    ##
    # @brief Sends LEAVE and EXIT signals and closes the application.
    def leave_chat():
        nonlocal already_closing
        if already_closing:
            return
        already_closing = True
        to_network.send(("LEAVE", handle, ""))
        to_network.send(("EXIT", "", ""))
        wnd.close()

    ##
    # @brief Toggles AFK (away-from-keyboard) mode and updates GUI/network.
    def toggle_afk():
        nonlocal afk_mode
        if btn_afk.isChecked():
            btn_afk.setText("AFK: ON")
            btn_afk.setStyleSheet("background-color: #cc5500; color: white;")
            afk_mode = True
            to_network.send(("AFK", handle, "ON"))
            append("[System] AFK mode enabled", "#c22809")
        else:
            btn_afk.setText("AFK: OFF")
            btn_afk.setStyleSheet("background-color: #666; color: white;")
            afk_mode = False
            to_network.send(("AFK", handle, "OFF"))
            append("[System] AFK mode disabled", "#31c209")

    ##
    # @brief Toggles between light and dark UI themes.
    def toggle_dark():
        if btn_dark.isChecked():
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            btn_dark.setText("Light Mode")
        else:
            app.setStyleSheet("")
            btn_dark.setText("Dark Mode")

    ##
    # @brief Opens the settings dialog for editing user config.
    def open_settings():
        dlg = SettingsDialog(config)
        dlg.exec_()

    # Connect GUI controls to functionality
    btn_send.clicked.connect(send_message)
    msg_input.returnPressed.connect(send_message)
    btn_img.clicked.connect(send_image)
    btn_clients.clicked.connect(show_clients)
    btn_leave.clicked.connect(leave_chat)
    btn_afk.clicked.connect(toggle_afk)
    btn_dark.clicked.connect(toggle_dark)
    btn_settings.clicked.connect(open_settings)
    
    already_left = set()

    ##
    # @brief Polls the pipe from the network process for new messages/events.
    def poll_network():
        current = {h for (h, _, _) in config['peers'] if h != handle}
        newcomers = current - local_peers
        for h in sorted(newcomers):
            append(f"{h} joined the chat.", "#2A8940")
        local_peers.update(newcomers)

        while from_network.poll():
            typ, src, payload = from_network.recv()
            if typ == 'MSG':
                append(f"{src}: {payload}", "#204EB4")
            elif typ == 'IMG':
                append(f"{src} sent image → {payload}", "#204EB4")
                open_file(payload)
            elif typ == 'LEAVE':
                if src in already_left:
                    return
                already_left.add(src)
                append(f"⚠️ {src} left the chat.", "#D60C0C")
                if src in local_peers:
                    local_peers.remove(src)
                config['peers'][:] = [p for p in config['peers'] if p[0] != src]

    append(f"👋 Welcome, {handle}!", "#000000")

    ##
    # @brief Triggered on window close event – clean exit handler.
    # @param event Qt close event.
    def on_close_event(event):
        nonlocal already_closing
        if not already_closing:
            to_network.send(("LEAVE", handle, ""))
            to_network.send(("EXIT", "", ""))
        already_closing = True
        event.accept()

    # Use QTimer instead of threads to poll for new data
    timer = QTimer()
    timer.timeout.connect(poll_network)
    timer.start(50)

    wnd.show()
    app.exec_()