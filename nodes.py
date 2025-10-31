from scheduler import get_schedule, book_appointment
from speech_utils import speak, listen


def detect_intent(query: str) -> str:
    q = (query or "").lower()
    # Check for list/show commands with more variations
    if any(
        word in q
        for word in [
            "list",
            "show",
            "get",
            "view",
            "see",
            "check",
            "upcoming",
            "schedule",
            "appointments",
        ]
    ):
        return "list"

    # Check for booking commands
    if any(word in q for word in ["book", "add", "create", "new", "schedule", "make"]):
        return "book"

    if any(word in q for word in ["exit", "quit", "stop", "bye"]):
        return "exit"

    return "unknown"


def intent_node(state: dict) -> str:
    query = state.get("query", "")
    intent = detect_intent(query)
    state["intent"] = intent
    return intent + "_node"


def list_node(state: dict) -> dict:
    schedules = get_schedule()
    if not schedules:
        speak("You don't have any appointments scheduled.")
    else:
        speak("Here are your appointments:")
        for appt in schedules:
            title = appt.get("title", "Untitled")
            start = appt.get("start", "")
            duration = appt.get("duration_minutes", 60)
            location = appt.get("location", "No location specified")
            speak(f"{title} on {start} for {duration} minutes at {location}")
    return state


def book_node(state: dict) -> dict:
    speak("Sure — let's create an appointment. What is the title or short description?")
    title = listen(prompt="Please say the title or type it.")
    if not title:
        speak("I didn't get a title. Cancelling booking.")
        return state

    speak(
        "On which day or date should it be? You can say a weekday like Thursday or a date like 2025-11-05."
    )
    day = listen(prompt="Please say the day or date.")
    if not day:
        speak("I didn't get the day. Cancelling booking.")
        return state

    speak("What time should it start? For example, 3 pm or 15:30.")
    time_str = listen(prompt="Please say the start time.")
    if not time_str:
        speak("I didn't get the time. Cancelling booking.")
        return state

    speak(
        "How long will it be in minutes? Say a number, or say default for 60 minutes."
    )
    duration_text = listen(prompt="Duration in minutes or say default.")
    try:
        if duration_text and duration_text.strip().lower() not in ("default", ""):
            duration = int("".join(ch for ch in duration_text if ch.isdigit())) or 60
        else:
            duration = 60
    except Exception:
        duration = 60

    speak("Any location or leave blank?")
    location = listen(prompt="Location (optional).")
    if not location:
        location = None

    speak(
        f"Confirm: create '{title}' on {day} at {time_str} for {duration} minutes? Say yes to confirm."
    )
    confirm = listen(prompt="Say 'yes' to confirm, anything else to cancel.")
    if "yes" not in (confirm or "").lower():
        speak("Booking cancelled.")
        return state

    result = book_appointment(
        title, time_str, day, duration_minutes=duration, location=location
    )
    if isinstance(result, dict) and result.get("status") == "success":
        speak(f"Appointment '{title}' created for {day} at {time_str}.")
        state["last_booking"] = result
    else:
        msg = (
            result.get("message", "Unknown error")
            if isinstance(result, dict)
            else str(result)
        )
        speak(f"Could not create appointment: {msg}")

    return state


def unknown_node(state: dict) -> dict:
    speak("I can list or book schedules. Please say that again.")
    return state
