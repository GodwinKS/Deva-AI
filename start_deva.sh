#!/bin/bash

# 1. Start Ollama silently in the background (if it isn't running already)
pgrep -x "ollama" > /dev/null || ollama serve &

# 2. Skip the 'activate' command and just force it to use your virtual environment's Python directly!
/home/godwin/assistant_env/bin/python3 /home/godwin/Downloads/DeOne/gui_main.py
