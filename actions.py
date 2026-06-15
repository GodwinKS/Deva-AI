import os
import subprocess
import pywhatkit

def execute_command(command_text):
    """Parses text and executes system-level Linux commands."""
    command = command_text.lower()
    print(f"[ACTION ENGINE] Processing command: {command}")

    # ==========================================
    # 1. YOUTUBE MUSIC CONTROLS
    # ==========================================
    if "play" in command and "on youtube" in command:
        # Extract the song name from the command
        song = command.replace("play", "").replace("on youtube", "").strip()
        print(f"[SYSTEM] Launching YouTube for: {song}")
        pywhatkit.playonyt(song)
        return True

    # ==========================================
    # 2. LINUX MEDIA & VIDEO CONTROLS (playerctl)
    # ==========================================
    elif "pause" in command or "stop video" in command:
        os.system("playerctl pause")
        print("[SYSTEM] Media paused.")
        return True
        
    elif "resume" in command or "play video" in command:
        os.system("playerctl play")
        print("[SYSTEM] Media resumed.")
        return True
        
    elif "next" in command or "skip" in command:
        os.system("playerctl next")
        print("[SYSTEM] Skipped to next track/video.")
        return True

    # ==========================================
    # 3. SYSTEM VOLUME (PipeWire Native)
    # ==========================================
    elif "increase volume" in command:
        # wpctl is the native PipeWire volume controller
        os.system("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%+")
        print("[SYSTEM] Volume increased by 10%.")
        return True
        
    elif "decrease volume" in command:
        os.system("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%-")
        print("[SYSTEM] Volume decreased by 10%.")
        return True

    # ==========================================
    # 4. OPENING KDE APPLICATIONS
    # ==========================================
    elif "open browser" in command or "open brave" in command:
        # Use subprocess so it doesn't freeze the Python script while the app is open
        subprocess.Popen(["brave-browser"]) # Change to "google-chrome" or "brave-browser" if needed
        print("[SYSTEM] Browser launched.")
        return True
        
    elif "open terminal" in command:
        subprocess.Popen(["kitty"])
        print("[SYSTEM] Kitty launched.")
        return True
        
    elif "open files" in command:
        subprocess.Popen(["dolphin"])
        print("[SYSTEM] Dolphin File Manager launched.")
        return True

    print("[SYSTEM] Command not recognized by Action Engine.")
    return False