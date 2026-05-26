import speech_recognition as sr
import os
import sys
from contextlib import contextmanager

from audio_io import listen, speak_deva, speak_tara, play_wake_sound
from brains import query_deva, query_tara

@contextmanager
def silence_linux_audio_errors():
    """A context manager to temporarily gag C-level ALSA/JACK warnings on Linux."""
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
    
    # We wrap the ENTIRE microphone opening sequence so ALSA stays quiet
    with silence_linux_audio_errors():
        try:
            with sr.Microphone() as source:
                r.pause_threshold = 0.5 
                audio = r.listen(source, timeout=1, phrase_time_limit=3)
        except Exception:
            return ""
            
    # The Google translation happens outside the silencer
    try:
        text = r.recognize_google(audio, language='en-in').lower()
        return text
    except Exception:
        return ""

def main():
    print("\n=== SYSTEM ONLINE ===")
    print("Listening silently for 'deva' or 'tara'...")

    try:
        while True:
            text = listen_for_wake_word()
            
            if text:
                print(f"[Debug] Heard: '{text}'")

            # Route 1: Deva
            if "deva" in text or "diva" in text or "baba" in text or "eva" in text or "they were" in text:
                print("\n[DEVA ACTIVATED - LOCAL MODE]")
                play_wake_sound()
                with silence_linux_audio_errors():
                    command = listen()
                    
                if command:
                    response = query_deva(command)
                    print(f"\n[Deva says]: {response}")
                    speak_deva(response)
                print("\nListening silently for 'deva' or 'tara'...")

            # Route 2: Tara
            elif "tara" in text or "tora" in text or "tera" in text or "google" in text:
                print("\n[TARA ACTIVATED - WEB MODE]")
                play_wake_sound()
                with silence_linux_audio_errors():
                    command = listen()
                    
                if command:
                    response = query_tara(command)
                    print(f"\n[Tara says]: {response}")
                    speak_tara(response)
                print("\nListening silently for 'deva' or 'tara'...")

    except KeyboardInterrupt:
        print("\nShutting down assistant...")

if __name__ == "__main__":
    main()