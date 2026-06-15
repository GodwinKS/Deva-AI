from google import genai
from google.genai import types
import ollama
from ddgs import DDGS
import os
import re
from dotenv import load_dotenv

# 1. Get the absolute path of the DeOne folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 2. Force python-dotenv to look at that exact file
load_dotenv(dotenv_path=ENV_PATH)

# 3. Grab the key securely
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print(f"\n[SYSTEM ERROR] Python looked here: {ENV_PATH}")
    print("But it could not find the GOOGLE_API_KEY variable inside!\n")

# 4. Configure the AI 
client = genai.Client(api_key=GOOGLE_API_KEY)

def clean_speech_text(text):
# ... (the rest of your functions stay exactly the same below here)
    """Strips Markdown formatting like asterisks, hashes, and underscores."""
    return re.sub(r'[*_`#]', '', text)

def query_tara(command):
    try:
        # 1. Fetch live search results using your local internet connection (100% Free)
        with DDGS() as ddgs:
            search_results = [r for r in ddgs.text(command, max_results=3)]
        
        live_web_data = "\n".join([result["body"] for result in search_results])
        
        prompt_with_context = f"""User Question: {command}
        
        Live Internet Search Context:
        {live_web_data}"""
        
        # 2. Try Cloud Gemini First
        try:
            config = types.GenerateContentConfig(
                system_instruction="You are Tara, an advanced voice assistant. The current date is June 2026. Use the provided live web data to answer the user accurately. Reply in plain conversational text. Do NOT use markdown, asterisks, bullet points, or special formatting."
            )
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt_with_context,
                config=config
            )
            return clean_speech_text(response.text)
            
        except Exception as cloud_error:
            # 3. CLOUD FAILED (429 Quota Limit / 503 Outage) -> Switch instantly to Local GPU!
            print(f"\n[SYSTEM] Gemini API quota limits hit. Switching Tara to local backup engine...")
            
            local_system_instruction = f"""You are Tara, an advanced voice assistant. The current date is June 2026. 
            Use the following live web data context to answer the user's question accurately.
            
            Live Internet Search Context:
            {live_web_data}
            
            RULES: Keep your answer short, conversational, and do NOT use markdown, asterisks, or formatting."""
            
            local_response = ollama.chat(
                model='llama3.2:1b',  # Processes the internet data entirely on your local GPU!
                messages=[
                    {'role': 'system', 'content': local_system_instruction},
                    {'role': 'user', 'content': command}
                ]
            )
            return clean_speech_text(local_response['message']['content'])
        
    except Exception as e:
        return f"Tara encountered a critical web search error: {e}"
# ... (Make sure to paste your local query_deva logic down here!) ...

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