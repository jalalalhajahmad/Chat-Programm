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
