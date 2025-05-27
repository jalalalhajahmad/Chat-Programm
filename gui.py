from PyQt5.QtWidgets import QApplication, QWidget, QTextEdit, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QTextCursor, QColor
import sys
from datetime import datetime

def ts():
    return datetime.now().strftime("[%H:%M:%S]")

def gui_process(config, to_network, from_network):
    handle = config['handle']

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle(f"Chat – {handle}")
    window.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
    window.resize(600, 450)

    chatbox = QTextEdit()
    chatbox.setReadOnly(True)
    chatbox.setStyleSheet("background-color: #2d2d2d; color: #d4d4d4; font-family: Courier;")

    entry = QLineEdit()
    entry.setStyleSheet("background-color: #333; color: #ffffff; font-family: Courier;")
    entry.setPlaceholderText("Nachricht eingeben...")

    send_button = QPushButton("Senden")
    send_button.setStyleSheet("background-color: #444; color: white;")

    layout = QVBoxLayout()
    layout.addWidget(chatbox)

    input_layout = QHBoxLayout()
    input_layout.addWidget(entry)
    input_layout.addWidget(send_button)
    layout.addLayout(input_layout)

    window.setLayout(layout)

    def append_message(text, color="#d4d4d4"):
        chatbox.setTextColor(QColor(color))
        chatbox.append(f"{ts()} {text}")
        chatbox.moveCursor(QTextCursor.End)

    def send_msg():
        msg = entry.text().strip()
        if msg:
            to_network.put(msg)
            entry.clear()

    def poll_messages():
        while not from_network.empty():
            text = from_network.get()
            if text == "__EXIT__":
                window.close()
                return
            color = "#d4d4d4"
            if f"[{handle}]" in text:
                color = "#4fc1ff"
            elif text.startswith("["):
                color = "#9cdcfe"
            if "hat den Chat verlassen" in text:
                color = "#c586c0"
            elif "Fehler" in text:
                color = "#ff6b6b"
            elif "Bild" in text:
                color = "#fce94f"
            append_message(text, color=color)

    send_button.clicked.connect(send_msg)
    entry.returnPressed.connect(send_msg)

    timer = QTimer()
    timer.timeout.connect(poll_messages)
    timer.start(500)

    append_message(f"Willkommen, {handle}!", color="#ffffff")

    window.show()
    sys.exit(app.exec_())