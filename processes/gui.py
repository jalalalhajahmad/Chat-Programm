import sys
import os
import subprocess
import platform
import socket
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QInputDialog
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

    def send_message():
        dest = dest_input.text().strip()
        msg  = msg_input.text().strip()
        if not dest or not msg:
            return
        append(f"{handle}: {msg}", "#000000")
        to_network.send(("MSG", dest, msg))
        msg_input.clear()

    def send_image():
        path, _ = QFileDialog.getOpenFileName(wnd, "Bild auswählen", "", "Images (*.png *.jpg *.bmp)")
        if not path:
            return
        dest = dest_input.text().strip()
        if not dest:
            QMessageBox.warning(wnd, "Fehler", "Bitte Empfänger-Handle eingeben!")
            return
        append(f"{handle} → {dest} [Bild]", "#f2aeae")
        to_network.send(("IMG", dest, path))

    def show_clients():
        peers = [(h, ip, pt) for (h, ip, pt) in config['peers'] if h != handle]
        if not peers:
            QMessageBox.information(wnd, "Clients", "Keine anderen Clients gefunden.")
        else:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                local_ip = "unbekannt"
            local_port = config["port"][0]
            info = "\n".join(f"{h} ({ip}:{pt})" for (h, ip, pt) in peers)
            QMessageBox.information(
                wnd,
                "Clients",
                f"Du selbst: {handle} ({local_ip}:{local_port})\n\n🌐 Aktive Clients:\n{info}"
            )

    def leave_chat():
        to_network.send(("LEAVE", handle, ""))
        wnd.close()

    def toggle_afk():
        nonlocal afk_mode
        if btn_afk.isChecked():
            btn_afk.setText("Abwesend: EIN")
            btn_afk.setStyleSheet("background-color: #cc5500; color: white;")
            afk_mode = True
            to_network.send(("AFK", handle, "ON"))
            append("[System] Abwesenheitsmodus aktiviert", "#c22809")
        else:
            btn_afk.setText("Abwesend: AUS")
            btn_afk.setStyleSheet("background-color: #666; color: white;")
            afk_mode = False
            to_network.send(("AFK", handle, "OFF"))
            append("[System] Abwesenheitsmodus deaktiviert", "#31c209")

    btn_send.clicked.connect(send_message)
    msg_input.returnPressed.connect(send_message)
    btn_img.clicked.connect(send_image)
    btn_clients.clicked.connect(show_clients)
    btn_leave.clicked.connect(leave_chat)
    btn_afk.clicked.connect(toggle_afk)

    def poll_network():
        current = {h for (h, _, _) in config['peers'] if h != handle}
        newcomers = current - local_peers
        for h in sorted(newcomers):
            append(f"⚡ {h} hat den Chat betreten.", "#068218")
        local_peers.update(newcomers)

        while from_network.poll():
            typ, src, payload = from_network.recv()
            if typ == 'MSG':
                append(f"{src}: {payload}", "#951A1A")
            elif typ == 'IMG':
                append(f"{src} hat Bild → {payload}", "#f2aeae")
                open_file(payload)
            elif typ == 'LEAVE':
                append(f"⚠️ {src} hat den Chat verlassen.", "#ed2700")
                if src in local_peers:
                    local_peers.remove(src)
                config['peers'][:] = [p for p in config['peers'] if p[0] != src]

    timer = QTimer()
    timer.timeout.connect(poll_network)
    timer.start(200)

    append(f"👋 Willkommen, {handle}!", "#3e6948")
    wnd.show()
    app.exec_()
