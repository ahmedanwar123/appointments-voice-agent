import time
import requests
from speech_utils import speak, listen, init_audio
import nodes
import os


def check_api():
    try:
        resp = requests.get("http://127.0.0.1:5000/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def main():
    if not check_api():
        speak("Error: API server is not running. Please start mock_api.py first")
        return

    # Initialize audio system
    audio_ok = init_audio()
    if not audio_ok:
        print("Warning: Audio system initialization failed. Using text input mode.")
        os.environ["FORCE_TEXT_INPUT"] = "1"

    speak("Hello! I am your voice assistant. You can book or list appointments.")
    while True:
        speak("What would you like to do?")
        query = listen(prompt="Please say 'book' or 'list' or type your command.")
        if not query:
            continue
        state = {"query": query}
        next_node = nodes.intent_node(state)
        if next_node == "book_node":
            nodes.book_node(state)
        elif next_node == "list_node":
            nodes.list_node(state)
        elif next_node == "exit_node":
            speak("Goodbye.")
            break
        else:
            nodes.unknown_node(state)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
