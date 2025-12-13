import json
import os
from datetime import datetime
from utils.data_manager import DATA_DIR

RESULTS_FILE = os.path.join(DATA_DIR, "results.json")


def load_results():
    if not os.path.exists(RESULTS_FILE):
        return {}
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_result(session_name, student_name, time_str):
    """
    Zapisuje wynik ucznia.
    Struktura: { "Klasa 4B": [ {"name": "Janek", "time": "02:15", "timestamp": ...} ] }
    """
    results = load_results()

    if session_name not in results:
        results[session_name] = []

    new_entry = {
        "student": student_name,
        "time": time_str,
        "submitted_at": datetime.now().strftime("%H:%M:%S")
    }

    results[session_name].append(new_entry)

    results[session_name].sort(key=lambda x: x['time'])

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)


def get_results_for_session(session_name):
    all_results = load_results()
    return all_results.get(session_name, [])