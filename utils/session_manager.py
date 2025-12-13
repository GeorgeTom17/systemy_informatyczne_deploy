import json
import os
from datetime import datetime
from utils.data_manager import DATA_DIR

SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")


def load_sessions():
    """Wczytuje listę sesji z pliku JSON."""
    if not os.path.exists(SESSIONS_FILE):
        return []
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_session(session_name, crossword_data, raw_code):
    """
    Zapisuje nową sesję.
    session_name: Nazwa podana przez nauczyciela
    crossword_data: Pełne dane krzyżówki (do podglądu)
    raw_code: Wygenerowany krótki kod string (do linku)
    """
    sessions = load_sessions()

    new_session = {
        "id": int(datetime.now().timestamp()),
        "name": session_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "raw_code": raw_code,
        "word_count": len(crossword_data[3]) if len(crossword_data) > 3 else 0
    }

    sessions.insert(0, new_session)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=4, ensure_ascii=False)