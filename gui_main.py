import sys
import os
import pygame
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

# Import your existing logic
from audio_io import listen, speak_deva, speak_tara, play_wake_sound
from brains import query_deva, query_tara
import speech_recognition as sr
from contextlib import contextmanager

# Initialize audio engine once at startup for total stability
pygame.mixer.init()

@contextmanager
def silence_linux_audio_errors():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

def listen_for_wake_word():
    r = sr.Recognizer()
    with silence_linux_audio_errors():
        try:
            with sr.Microphone() as source:
                r.pause_threshold = 0.5 
                audio = r.listen(source, timeout=1, phrase_time_limit=3)
        except Exception:
            return ""
    try:
        text = r.recognize_google(audio, language='en-in').lower()
        return text
    except Exception:
        return ""

# ==========================================
# 1. THE BACKGROUND WORKER THREAD
# ==========================================
class VoiceWorker(QThread):
    state_signal = pyqtSignal(str)
    transcript_signal = pyqtSignal(str, str) 

    def run(self):
        self.state_signal.emit("idle")
        self.transcript_signal.emit("SYSTEM", "Awaiting wake word ('Deva' or 'Tara')...")

        while True:
            text = listen_for_wake_word()
            
            # Route 1: Deva
            if any(w in text for w in ["deva", "diva", "daya", "eva", "they were", "govinda", "dora"]):
                self.state_signal.emit("deva_active")
                play_wake_sound()  # <-- WAKE SOUND TRIGGERED HERE
                
                with silence_linux_audio_errors():
                    command = listen()
                    
                if command:
                    self.transcript_signal.emit("USER", command)
                    self.state_signal.emit("deva_thinking")
                    response = query_deva(command)
                    self.transcript_signal.emit("DEVA", response)
                    speak_deva(response)
                    
                self.state_signal.emit("idle")

            # Route 2: Tara
            elif any(w in text for w in ["google", "tara", "there", "tera", "tora"]):
                self.state_signal.emit("tara_active")
                play_wake_sound()  # <-- WAKE SOUND TRIGGERED HERE
                
                with silence_linux_audio_errors():
                    command = listen()
                    
                if command:
                    self.transcript_signal.emit("USER", command)
                    self.state_signal.emit("tara_thinking")
                    response = query_tara(command)
                    self.transcript_signal.emit("TARA", response)
                    speak_tara(response)
                    
                self.state_signal.emit("idle")

# ==========================================
# 2. THE CYBERPUNK HUD WINDOW
# ==========================================
class CyberpunkUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 500)
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 420, 50)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 240);
                border: 1px solid rgba(0, 255, 255, 100);
                border-radius: 10px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        
        # --- TOP BAR ---
        top_bar = QHBoxLayout()
        
        self.status_label = QLabel("[ SYSTEM IDLE ]")
        self.status_label.setFont(QFont("Monospace", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 150); border: none;")
        
        self.stop_audio_btn = QPushButton("🛑 STOP")
        self.stop_audio_btn.setFixedSize(70, 30)
        self.stop_audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_audio_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 50, 50, 200);
                color: white;
                border-radius: 5px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: rgba(255, 50, 50, 255); }
        """)
        self.stop_audio_btn.clicked.connect(self.stop_speaking)

        self.min_btn = QPushButton("-")
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 170, 0, 150);  
                color: white;
                border-radius: 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: rgba(255, 170, 0, 255); }
        """)
        self.min_btn.clicked.connect(self.showMinimized)
        
        self.close_btn = QPushButton("X")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 50, 50, 150);  
                color: white;
                border-radius: 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: rgba(255, 50, 50, 255); }
        """)
        self.close_btn.clicked.connect(self.close_app)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.stop_audio_btn) 
        top_bar.addWidget(self.min_btn)   
        top_bar.addWidget(self.close_btn) 
        
        # --- TRANSCRIPT AREA ---
        self.transcript = QTextBrowser()
        self.transcript.setFont(QFont("Monospace", 10))
        self.transcript.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(10, 10, 15, 200);
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        
        container_layout.addLayout(top_bar)
        container_layout.addWidget(self.transcript)
        main_layout.addWidget(self.container)

        self.worker = VoiceWorker()
        self.worker.state_signal.connect(self.update_status)
        self.worker.transcript_signal.connect(self.append_text)
        self.worker.start()

    def stop_speaking(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            print(f"Audio stop error: {e}")

    def update_status(self, state):
        if state == "idle":
            self.status_label.setText("[ SYSTEM IDLE ]")
            self.status_label.setStyleSheet("color: rgba(255, 255, 255, 150); border: none;")
        elif state == "deva_active":
            self.status_label.setText("[ DEVA: LISTENING ]")
            self.status_label.setStyleSheet("color: #00FFFF; border: none;")
        elif state == "deva_thinking":
            self.status_label.setText("[ DEVA: PROCESSING ]")
            self.status_label.setStyleSheet("color: #00AAAA; border: none;")
        elif state == "tara_active":
            self.status_label.setText("[ TARA: LISTENING ]")
            self.status_label.setStyleSheet("color: #FF00FF; border: none;")
        elif state == "tara_thinking":
            self.status_label.setText("[ TARA: SEARCHING WEB ]")
            self.status_label.setStyleSheet("color: #AA00AA; border: none;")

    def append_text(self, speaker, text):
        if speaker == "SYSTEM":
            color = "#00FF00"
        elif speaker == "USER":
            color = "#FFFFFF"
        elif speaker == "DEVA":
            color = "#00FFFF"
        elif speaker == "TARA":
            color = "#FF00FF"
            
        html = f'<b style="color:{color};">[{speaker}]</b> <span style="color:#DDDDDD;">{text}</span><br>'
        self.transcript.append(html)

    def close_app(self):
        self.stop_speaking()
        self.worker.terminate()
        QApplication.quit()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.oldPos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # --- TASKBAR ICON FIX ---
    # 1. Get the absolute path to your image
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "app_icon.png") # Ensure this is your actual image name!
    
    # 2. Force the icon globally for the whole app
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 3. KDE Wayland specifically needs this to link the taskbar to your .desktop file
    app.setDesktopFileName("Deva") 
    # ------------------------

    ui = CyberpunkUI()
    ui.show()
    sys.exit(app.exec())