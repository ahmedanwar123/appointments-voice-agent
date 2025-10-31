import logging
import os
import subprocess
import time

# Optional TTS backends
try:
    from langgraph.agents import speak_text

    HAS_LANGGRAPH = True
except Exception:
    speak_text = None
    HAS_LANGGRAPH = False

try:
    import pyttsx3

    HAS_PYTTSX3 = True
except Exception:
    pyttsx3 = None
    HAS_PYTTSX3 = False

# speech recognition
try:
    import speech_recognition as sr

    HAS_SPEECH_RECOG = True
except Exception:
    sr = None
    HAS_SPEECH_RECOG = False

VOICE_NAME = "alloy"
_engine = None
if not HAS_LANGGRAPH and HAS_PYTTSX3:
    try:
        _engine = pyttsx3.init()
    except Exception:
        _engine = None

logger = logging.getLogger(__name__)


def speak(text):
    print(f"Agent: {text}")
    if HAS_LANGGRAPH and speak_text:
        try:
            speak_text(text, voice=VOICE_NAME)
            return
        except Exception as e:
            logger.warning("LangGraph speak_text failed, falling back: %s", e)

    if _engine:
        try:
            _engine.say(text)
            _engine.runAndWait()
            return
        except Exception as e:
            logger.warning("pyttsx3 failed: %s", e)

    # fallback to espeak command
    try:
        subprocess.run(["espeak", text], check=False)
    except Exception:
        logger.debug("No TTS backend available.")


def init_audio():
    """Initialize audio system and test microphone"""
    if not HAS_SPEECH_RECOG:
        return False

    try:
        with sr.Microphone() as source:
            r = sr.Recognizer()
            r.adjust_for_ambient_noise(source, duration=1)
            return True
    except Exception as e:
        logger.error("Audio initialization failed: %s", e)
        return False


def listen(prompt=None, timeout=15, phrase_time_limit=10):
    """
    Returns lowercased string. Falls back to text input if audio fails.
    """
    # Always show prompt visually
    if prompt:
        print(f"\nPrompt: {prompt}")

    # Force text input if environment variable is set or no speech recognition
    if os.environ.get("FORCE_TEXT_INPUT", "0") == "1" or not HAS_SPEECH_RECOG:
        return input("Type your response: ").strip().lower()

    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\n Listening... (Ctrl+C to type instead)")
            # Reduce ambient noise impact
            r.adjust_for_ambient_noise(source, duration=1)
            # Get audio input
            audio = r.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )

            # Try to recognize
            try:
                text = r.recognize_google(audio)
                print(f" Heard: {text}")
                return text.lower()
            except sr and sr.UnknownValueError:
                print(" Could not understand audio")
            except sr and sr.RequestError:
                print(" Speech recognition service failed")

    except (KeyboardInterrupt, Exception) as e:
        print("\n Falling back to text input...")

    # Fallback to text input
    return input("Type your response: ").strip().lower()
