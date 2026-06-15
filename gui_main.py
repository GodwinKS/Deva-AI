from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QPushButton, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
import sys
import os
import pygame
# Import your existing logic
from audio_io import listen, speak_deva, speak_tara, play_wake_sound
from brains import query_deva, query_tara
import speech_recognition as sr
import actions
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize audio engine once at startup for total stability
pygame.mixer.init()
import requests

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

def check_personal_memory(command_text):
    """Uses local Ollama AI to understand personal memory context (Local RAG)."""
    memory_file = os.path.join(BASE_DIR, "personal_memory.txt")
    
    if not os.path.exists(memory_file):
        print(f"[GATE 2 ERROR] Cannot find memory file at: {memory_file}")
        return None

    # 1. Read all your personal data into memory
    with open(memory_file, "r") as file:
        personal_data = file.read()
        
    # 2. Build the strict logic prompt for Ollama
        system_prompt = f"""You are Deva, a highly intelligent reading comprehension AI.
        
        PASSAGE:
        {personal_data}
        
        USER QUESTION: "{command_text}"
        
        CRITICAL RULES:
        1. Answer the question using ONLY the information provided in the PASSAGE. 
        2. You MUST understand synonyms, twisted phrasing, and context. (For example, if the passage mentions 'VIT', you know that means 'college'. If it says 'GPA', it means 'CGPA').
        3. Never use outside world knowledge. Never answer questions about politicians, celebrities, or current events.
        4. If the concept asked in the question is completely missing from the PASSAGE, you must output exactly one word: NOT_FOUND. Do not apologize or explain.
        
        ANSWER:"""
    
    print("[GATE 2] Scanning personal data via local AI...")
    
    try:
        # 3. Send it to your local Ollama server
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3.2",   
            "prompt": system_prompt,
            "stream": False
        }, timeout=45)
        
        if response.status_code == 200:
            answer = response.json().get("response", "").strip()
            
            # 4. The Handoff Check
            if "NOT_FOUND" in answer:
                return None 
                
            return answer
        else:
            print(f"[GATE 2 ERROR] Ollama Server returned status {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("[GATE 2 ERROR] Cannot connect to local Ollama. Is the Ollama app running?")
        return None
    except Exception as e:
        print(f"[GATE 2 ERROR] AI processing failed: {e}")
        return None


def listen_for_command():
    """Listens to the user's voice after the wake word and converts it to text."""
    recognizer = sr.Recognizer()
    
    with silence_linux_audio_errors():
        with sr.Microphone(chunk_size=1280) as source:
            print("[DEVA IS LISTENING...]")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("[SYSTEM] Processing audio...")
                
                command_text = recognizer.recognize_google(audio)
                print(f"> YOU SAID: '{command_text}'")
                return command_text.lower()
                
            except sr.WaitTimeoutError:
                print("[SYSTEM] Listening timed out. No speech detected.")
                return None
            except sr.UnknownValueError:
                print("[SYSTEM] Could not understand the audio.")
                return None
            except Exception as e:
                print(f"[SYSTEM] Speech Recognition Error: {e}")
                return None

def listen_for_wake_word():
    """Uses Google Cloud Speech-to-Text to listen for the wake word continuously."""
    recognizer = sr.Recognizer()
    
    with silence_linux_audio_errors():
        with sr.Microphone() as source:
            recognizer.dynamic_energy_threshold = True 
            
            try:
                audio = recognizer.listen(source) 
                text = recognizer.recognize_google(audio).lower()
                print(f"\n[CLOUD HEARD]: '{text}'")
                return text
                
            except sr.UnknownValueError:
                return ""
            except sr.RequestError:
                print("[SYSTEM ERROR] Google Cloud unreachable. Check internet connection.")
                return ""
            except Exception as e:
                return ""

# ==========================================
# 1. THE BACKGROUND WORKER THREAD (AGENTIC HANDOFF)
# ==========================================
class VoiceWorker(QThread):
    state_signal = pyqtSignal(str)
    transcript_signal = pyqtSignal(str, str) 

    def run(self):
        self.state_signal.emit("idle")
        self.transcript_signal.emit("SYSTEM", "Awaiting wake word via Google Cloud...")

        while True:
            # 1. Listen via Google Cloud continuously
            text = listen_for_wake_word() 
            
            # ==========================================
            # ROUTE 1: DEVA (Local/Personal Manager)
            # ==========================================
            if text and any(w in text for w in ["deva", "diva", "daya", "eva", "they were", "baba", "dora"]):
                self.state_signal.emit("deva_active")
                play_wake_sound()  
                
                with silence_linux_audio_errors():
                    command = listen_for_command()
                    
                if command:
                    self.transcript_signal.emit("USER", command)
                    
                    # --- GATE 1: ACTIONS ---
                    if actions.execute_command(command):
                        self.transcript_signal.emit("SYSTEM", "Executing system action...")
                        self.state_signal.emit("idle")
                        continue 

                    # --- GATE 2: PERSONAL MEMORY ---
                    memory_response = check_personal_memory(command)
                    if memory_response:
                        self.transcript_signal.emit("DEVA", memory_response)
                        speak_deva(memory_response)
                        self.state_signal.emit("idle")
                        continue 
                        
                    # --- GATE 3: THE TARA HANDOFF ---
                    handoff_msg = "I'm not sure, let me ask Tara."
                    self.transcript_signal.emit("DEVA", handoff_msg)
                    speak_deva(handoff_msg)
                    
                    self.state_signal.emit("tara_thinking")
                    tara_response = query_tara(command)
                    self.transcript_signal.emit("TARA", tara_response)
                    speak_tara(tara_response)
                    
                self.state_signal.emit("idle")

            # ==========================================
            # ROUTE 2: TARA (Direct Web/Search AI)
            # ==========================================
            elif text and any(w in text for w in ["google", "tara", "there", "tera", "tora"]):
                self.state_signal.emit("tara_active")
                play_wake_sound()  
                
                with silence_linux_audio_errors():
                    command = listen_for_command()
                    
                if command:
                    self.transcript_signal.emit("USER", command)
                    
                    self.state_signal.emit("tara_thinking")
                    response = query_tara(command)
                    self.transcript_signal.emit("TARA", response)
                    speak_tara(response)
                    
                self.state_signal.emit("idle")

# ==========================================
# 2. THE CYBERPUNK HUD (WITH AVATARS)
# ==========================================
class CyberpunkUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen_geo = QApplication.primaryScreen().geometry()
        width, height = 400, 600
        center_x = (screen_geo.width() - width) // 2
        center_y = (screen_geo.height() - height) // 2
        self.setGeometry(center_x, center_y, width, height)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #111116;
                border-radius: 8px;
                border: 1px solid #1F1F2E;
            }
        """)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- HEADER (Title Bar) ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        self.status_label = QLabel("[ SYSTEM: IDLE ]", self)
        self.status_label.setFont(QFont("Courier", 13, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #00E5FF; border: none; background: transparent;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()

        # --- NEW STOP BUTTON ---
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setStyleSheet("QPushButton { background-color: #FF8C00; border-radius: 12px; padding: 5px; font-weight:bold; }")
        self.btn_stop.clicked.connect(self.stop_audio)
        header_layout.addWidget(self.btn_stop)
        # -----------------------
        
        self.btn_min = QPushButton("-")
        self.btn_min.setStyleSheet("QPushButton { background-color: #B8860B; border-radius: 12px; min-width: 24px; min-height: 24px; font-weight:bold; }")
        self.btn_close = QPushButton("X")
        self.btn_close.setStyleSheet("QPushButton { background-color: #B71C1C; border-radius: 12px; min-width: 24px; min-height: 24px; color: white; font-weight:bold; }")
        self.btn_close.clicked.connect(QApplication.quit)
        self.btn_min.clicked.connect(self.showMinimized)
        
        header_layout.addWidget(self.btn_min)
        header_layout.addWidget(self.btn_close)
        frame_layout.addLayout(header_layout)
        
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedHeight(150)
        frame_layout.addWidget(self.avatar_label)
        self.set_avatar("IDLE") 
        
        self.console = QTextBrowser(self)
        self.console.setFont(QFont("Courier", 11))
        self.console.setStyleSheet("QTextBrowser { background-color: #0A0A0F; color: #E0E0E0; border: none; border-radius: 5px; padding: 10px; }")
        self.console.setHtml("<span style='color: #00FF00; font-weight: bold;'>[SYSTEM]</span> Awaiting wake word ('Deva' or 'Tara')...<br>")
        
        frame_layout.addWidget(self.console)
        main_layout.addWidget(self.frame)
        
        self.worker = VoiceWorker()
        self.worker.state_signal.connect(self.update_status)
        self.worker.transcript_signal.connect(self.update_transcript)
        self.worker.start()

    def set_avatar(self, character):
        """Loads the correct image based on who is active."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if character == "DEVA":
            image_path = os.path.join(base_dir, "deva.png")
        elif character == "TARA":
            image_path = os.path.join(base_dir, "tara.png")
        else:
            image_path = None 
            
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            
            # --- THE SAFETY CHECK FIX ---
            if not pixmap.isNull():
                # The image is healthy, resize and show it
                scaled_pixmap = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
                self.avatar_label.setPixmap(scaled_pixmap)
                self.avatar_label.show()
            else:
                # The image is corrupted or the wrong format (like a WebP)
                self.avatar_label.setText(f"[ {character}.png FORMAT ERROR ]")
                self.avatar_label.setStyleSheet("color: red; font-weight: bold;")
                self.avatar_label.show()
            # ----------------------------
                
        else:
            self.avatar_label.clear()
            if character == "IDLE":
                self.avatar_label.hide()
            else:
                self.avatar_label.setText(f"[ {character}.png MISSING ]")
                self.avatar_label.setStyleSheet("color: red; font-weight: bold;")
                self.avatar_label.show()
    def update_status(self, state):
        """Updates the cyan title bar text AND swaps the avatar."""
        if state == "idle":
            self.status_label.setText("[ SYSTEM: IDLE ]")
            self.status_label.setStyleSheet("color: #00E5FF;")
            self.set_avatar("IDLE")
            
        elif state in ["deva_active", "deva_speaking"]:
            self.status_label.setText("[ DEVA: ACTIVE ]")
            self.status_label.setStyleSheet("color: #00FF9D;")
            self.set_avatar("DEVA")
            
        elif state == "deva_thinking":
            self.status_label.setText("[ DEVA: PROCESSING ]")
            self.status_label.setStyleSheet("color: #FFB000;")
            self.set_avatar("DEVA")
            
        elif state in ["tara_active", "tara_speaking", "tara_thinking"]:
            # THE FIX IS SUCCESSFULLY APPLIED HERE!
            self.status_label.setText(f"[ TARA: {state.split('_')[1].upper()} ]")
            self.status_label.setStyleSheet("color: #FF00FF;")
            self.set_avatar("TARA")

    def update_transcript(self, speaker, text):
        """Prints text to the console with color-coded tags."""
        color = "#00E5FF" 
        if speaker == "SYSTEM": color = "#00FF00"
        elif speaker == "DEVA": color = "#00FF9D"
        elif speaker == "TARA": color = "#FF00FF"
        elif speaker == "USER" or "HEARD" in speaker: color = "#FFB000"
        
        self.console.append(f"<span style='color: {color}; font-weight: bold;'>[{speaker}]</span> {text}")
    def stop_audio(self):
        """Instantly halts any playing voice audio and resets to idle."""
        pygame.mixer.stop()
        pygame.mixer.music.stop()
        
        # Log it in the console so you know it worked
        self.console.append("<span style='color: #FF4444; font-weight: bold;'>[SYSTEM]</span> Audio playback forcefully stopped.")
        
        # Reset the UI face back to idle
        self.update_status("idle")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setDesktopFileName("DeOne") 
    ui = CyberpunkUI()
    ui.show()
    sys.exit(app.exec())