import pyttsx3
from gtts import gTTS
import pygame
import speech_recognition as sr
import os
import asyncio
import edge_tts

# --- THE FIX: Get the absolute coordinates to your DeOne folder ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def speak_deva(text):
    # Lock the output to the exact folder
    output_path = os.path.join(BASE_DIR, "deva_output.mp3")
    
    # 'en-IN-PrabhatNeural' is a highly realistic Indian masculine voice
    communicate = edge_tts.Communicate(text, "en-GB-RyanNeural")
    asyncio.run(communicate.save(output_path))
    
    pygame.mixer.init()
    pygame.mixer.music.load(output_path)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
    if os.path.exists(output_path):
        os.remove(output_path)

def speak_tara(text):
    # Lock the output to the exact folder
    output_path = os.path.join(BASE_DIR, "tara_output.mp3")
    
    # Tara remains the female Google voice
    tts = gTTS(text=text, lang='en', tld='co.in')
    tts.save(output_path)
    
    pygame.mixer.init()
    pygame.mixer.music.load(output_path)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
    if os.path.exists(output_path):
        os.remove(output_path)

def listen():
    r = sr.Recognizer()
    
    # Increase the silence tolerance
    # Default is 0.8. Setting to 2.0 gives you a full 2 seconds to pause or say "umm"
    r.pause_threshold = 2.0 
    
    with sr.Microphone() as source:
        # Optional but highly recommended: let the mic calibrate to room noise for half a second
        r.adjust_for_ambient_noise(source, duration=0.5)
        
        print("Listening...")
        # We can also add a timeout so it doesn't hang forever if you walk away
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("Listening timed out.")
            return None

    try:
        text = r.recognize_google(audio, language='en-in')
        print("You said: " + text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None

def play_wake_sound():
    """Plays a quick chime so the user knows the mic is active."""
    # Use the absolute path to your wake.wav file!
    sound_path = os.path.join(BASE_DIR, "wake.wav")
    
    if os.path.exists(sound_path):
        pygame.mixer.init()
        # THE FIX: Use Sound() instead of music() so it doesn't conflict with the Stop button!
        chime = pygame.mixer.Sound(sound_path)
        chime.play()
        # Notice we removed the "while loop" here. 
        # This allows the chime to play instantly without freezing the app!
    else:
        print(f"[AUDIO ERROR] Could not find sound file at: {sound_path}")