from dateutil import parser
from datetime import datetime, timedelta
import os
import json
import uuid
from typing import Optional, Tuple, Dict, List

USE_REMOTE_API = os.environ.get("USE_REMOTE_API", "1") == "1"
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")
APPOINTMENTS_JSON = os.path.join(os.path.dirname(__file__), "appointments.json")
APPOINTMENTS_MD = os.path.join(os.path.dirname(__file__), "appointments.md")


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return dt


def parse_datetime(day_str: str, time_str: str) -> datetime:
    combined = f"{day_str} {time_str}".strip()
    default = datetime.now()
    dt = parser.parse(combined, fuzzy=True, default=default)
    return _ensure_tz(dt)


def _load_local_events() -> List[Dict]:
    if not os.path.exists(APPOINTMENTS_JSON):
        return []
    try:
        with open(APPOINTMENTS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_local_events(events: List[Dict]) -> None:
    with open(APPOINTMENTS_JSON, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def _append_to_markdown(
    summary, start_iso, end_iso, description="", event_id=None, location=None
):
    lines = [
        "\n---\n",
        f'title: "{summary}"\n',
        f'start: "{start_iso}"\n',
        f'end: "{end_iso}"\n',
        f'description: "{description}"\n',
    ]
    if location:
        lines.append(f'location: "{location}"\n')
    if event_id:
        lines.append(f'event_id: "{event_id}"\n')
    with open(APPOINTMENTS_MD, "a", encoding="utf-8") as f:
        f.writelines(lines)


def _events_overlap(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> bool:
    return start_a < end_b and end_a > start_b


def _events_from_local() -> List[Dict]:
    return _load_local_events()


def check_conflict(
    start_dt: datetime, duration_minutes: int = 60
) -> Tuple[bool, Optional[Dict]]:
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    events = _events_from_local()
    for ev in events:
        try:
            s = parser.parse(ev["start"])
            e = parser.parse(ev["end"])
            s = _ensure_tz(s)
            e = _ensure_tz(e)
        except Exception:
            continue
        if _events_overlap(start_dt, end_dt, s, e):
            return True, ev
    return False, None


def _call_remote_create(payload: Dict) -> Dict:
    if not USE_REMOTE_API:
        return {
            "ok": False,
            "error": "API must be enabled. Please start the API server first.",
        }
    try:
        import requests

        url = API_BASE.rstrip("/") + "/appointments"
        try:
            resp = requests.get(f"{API_BASE}/health", timeout=2)
            if resp.status_code != 200:
                return {"ok": False, "error": "API server is not responding correctly"}
        except Exception:
            return {
                "ok": False,
                "error": "API server is not running. Please start mock_api.py first",
            }

        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code in (200, 201):
            data = resp.json() if resp.content else {}
            return {
                "ok": True,
                "id": data.get("id") or data.get("appointment_id") or None,
                "data": data,
            }
        return {"ok": False, "error": f"HTTP {resp.status_code} {resp.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def book_appointment(
    desc: str,
    time_str: str,
    day_str: str,
    duration_minutes: int = 60,
    location: Optional[str] = None,
) -> Dict:
    try:
        start_dt = parse_datetime(day_str, time_str)
    except Exception as e:
        return {"status": "failed", "message": f"Could not parse date/time: {e}"}

    start_dt = _ensure_tz(start_dt)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    conflict, ev = check_conflict(start_dt, duration_minutes=duration_minutes)
    if conflict:
        return {
            "status": "failed",
            "message": f"Requested time conflicts with '{ev.get('title')}' at {ev.get('start')}",
        }

    event_id = None
    remote_result = _call_remote_create(
        {
            "title": desc,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "description": desc,
            "location": location,
        }
    )
    if remote_result.get("ok"):
        event_id = remote_result.get("id")

    new_id = uuid.uuid4().hex
    ev_obj = {
        "id": new_id,
        "title": desc,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "description": desc,
        "location": location,
        "event_id": event_id,
        "source": "remote" if event_id else "local",
    }
    events = _load_local_events()
    events.append(ev_obj)
    _save_local_events(events)
    _append_to_markdown(
        desc,
        start_dt.isoformat(),
        end_dt.isoformat(),
        description=desc,
        event_id=event_id,
        location=location,
    )

    return {
        "status": "success",
        "id": new_id,
        "event_id": event_id,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
    }


def get_schedule(day: str = None) -> List[Dict]:
    """Get all appointments or filter by day if specified"""
    try:
        events = _events_from_local()
        if not day:
            return events

        # Filter by date if day is specified
        filtered = []
        for event in events:
            event_date = parser.parse(event["start"]).strftime("%Y-%m-%d")
            if event_date == day:
                filtered.append(event)
        return filtered

    except Exception as e:
        print(f"Error getting schedule: {e}")
        return []
