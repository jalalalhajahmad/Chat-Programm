import sys
import os
import subprocess
import platform
import socket
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore    import QTimer
from PyQt5.QtGui     import QTextCursor, QColor

MAX_DISPLAY_CHUNK = 200

def ts():
    from datetime import datetime
    return datetime.now().strftime("[%H:%M:%S]")

def open_file(path):
    if platform.system() == 'Windows':
        os.startfile(path)
    elif platform.system() == 'Darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])

def gui_process(config, to_network, from_network):
    handle   = config['handle']
    img_path = config['imagepath']
    os.makedirs(img_path, exist_ok=True)

    app = QApplication(sys.argv)
    wnd = QWidget()
    wnd.setWindowTitle(f"SLCP Chat – {handle}")

    vlayout = QVBoxLayout()
    chat = QTextEdit()
    chat.setReadOnly(True)
    vlayout.addWidget(chat)

    controls = QHBoxLayout()
    dest_input   = QLineEdit(); dest_input.setPlaceholderText("Empfänger-Handle")
    msg_input    = QLineEdit(); msg_input.setPlaceholderText("Nachricht…")
    btn_send     = QPushButton("Senden")
    btn_img      = QPushButton("Bild senden")
    btn_clients  = QPushButton("Clients")
    btn_leave    = QPushButton("Chat verlassen")
    btn_afk      = QPushButton("Abwesend: AUS")
    btn_afk.setCheckable(True)
    btn_afk.setStyleSheet("background-color: #666; color: white;")

    for w in (dest_input, msg_input, btn_send, btn_img, btn_clients,btn_leave, btn_afk):
        controls.addWidget(w)
    vlayout.addLayout(controls)
    wnd.setLayout(vlayout)

    local_peers = set()
    afk_mode = False

    def append(text, color="#010202"):
        if isinstance(text, str) and len(text) > MAX_DISPLAY_CHUNK:
            text = text[:MAX_DISPLAY_CHUNK] + '...'
        chat.setTextColor(QColor(color))
        chat.append(f"{ts()} {text}")
        chat.moveCursor(QTextCursor.End)

    def pollnetwork():
        current = {h for (h, , _) in config['peers'] if h != handle}
        newcomers = current - local_peers
        for h in sorted(newcomers):
            append(f"{h} hat den Chat betreten.", "#068218")
        local_peers.update(newcomers)

        while from_network.poll():
            typ, src, payload = from_network.recv()
            if typ == 'MSG':
                append(f"{src}: {payload}", "#951A1A")
            elif typ == 'IMG':
                append(f"{src} hat Bild → {payload}", "#f2aeae")
                open_file(payload)
            elif typ == 'LEAVE':
                append(f"{src} hat den Chat verlassen.", "#ed2700")
                if src in local_peers:
                    local_peers.remove(src)
                config['peers'][:] = [p for p in config['peers'] if p[0] != src]

    timer = QTimer()
    timer.timeout.connect(pollnetwork)
    timer.start(200)

    append(f"Willkommen, {handle}!", "#3e6948")
    wnd.show()
    app.exec() 