from google import genai
import ollama
import os
import re

# Put your actual API key right here for Tara
API_KEY = "AIzaSyB4KpBZzrQTRqV8rGjx5qkIpDgblJF10Yg" 
client = genai.Client(api_key=API_KEY)

def clean_speech_text(text):
    """Strips Markdown formatting like asterisks, hashes, and underscores."""
    return re.sub(r'[*_`#]', '', text)

def query_tara(command):
    try:
        system_instruction = "You are a voice assistant. Reply in plain conversational text. Do NOT use markdown, asterisks, bullet points, or special formatting."
        full_prompt = f"{system_instruction}\n\nUser: {command}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt
        )
        return clean_speech_text(response.text)
    except Exception as e:
        return f"Tara encountered a network error: {e}"

def query_deva(command):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "personal_context.txt")
        
        context = ""
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                context = f.read()
        else:
            print(f"\n[DEBUG WARNING] Could not find memory file at: {file_path}")
        
        system_instruction = "You are a helpful voice assistant. Reply in plain, spoken conversational text without any markdown or special formatting."
        full_prompt = f"{system_instruction}\n\nSystem context about the user: {context}\n\nUser Question: {command}"
        
        # --- 100% OFFLINE LOCAL AI CALL ---
        response = ollama.chat(model='llama3.2:latest', messages=[
            {
                'role': 'user',
                'content': full_prompt
            }
        ])
        
        return clean_speech_text(response['message']['content'])
    except Exception as e:
        return f"Deva encountered a local error: {e}"