import time
import random
from supabase import create_client

SUPABASE_URL = "https://toikofbukborcdoyknwd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvaWtvZmJ1a2JvcmNkb3lrbndkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgwMjIwOTUsImV4cCI6MjA4MzU5ODA5NX0.6whLhwnmUOroPgllsAF3HvLwx1pZueWLWuWnIMmp3y0"
SESSION_ID = "21"  # Musi być to samo co u nauczyciela

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

STUDENTS = [
    {"name": "Jerzy", "speed": random.randrange(8, 13, 1) / 10, "accuracy": random.randrange(45, 80, 1) / 100},
    {"name": "Michał", "speed": random.randrange(8, 13, 1) / 10, "accuracy": random.randrange(45, 80, 1) / 100},
    {"name": "Jakub", "speed": random.randrange(8, 13, 1) / 10, "accuracy": random.randrange(45, 80, 1) / 100},
    {"name": "Dominik", "speed": random.randrange(8, 13, 1) / 10, "accuracy": random.randrange(45, 80, 1) / 100},
    {"name": "Uladzimir", "speed": random.randrange(8, 13, 1) / 10, "accuracy": random.randrange(45, 80, 1) / 100}
]

def reset_session():
    """Usuwa stare wyniki dla tej sesji, aby demo zaczęło się od zera."""
    print(f"🧹 Czyszczenie danych dla sesji {SESSION_ID}...")
    supabase.table("realtime_scores").delete().eq("session_id", SESSION_ID).execute()
    # Opcjonalnie usuwamy też z results, jeśli chcesz "czysty ranking"
    supabase.table("results").delete().eq("session_id", SESSION_ID).execute()


def simulate_progress():
    reset_session()
    print(f"🚀 Uruchamiam symulację dla sesji: {SESSION_ID}")

    for s in STUDENTS:
        s['progress'] = 0
        s['hints'] = 0
        s['finished'] = False

    while any(not s['finished'] for s in STUDENTS):
        for s in STUDENTS:
            if s['finished']: continue

            # Postęp
            s['progress'] = min(100, s['progress'] + random.randint(3, 12) * s['speed'])

            # Szansa na podpowiedź
            if random.random() > s['accuracy']:
                s['hints'] += 1

            # Uproszczona punktacja dla demo
            current_score = int((s['progress'] * 10) - (s['hints'] * 5))
            is_done = s['progress'] >= 100

            data = {
                "session_id": SESSION_ID,
                "student_name": s['name'],
                "score": current_score,
                "progress_percent": int(s['progress']),
                "hint_count": s['hints'],
                "is_finished": is_done,
                "last_updated": "now()"
            }

            if is_done:
                data["completion_time"] = "01:30"
                s['finished'] = True

            # POPRAWKA: Dodane on_conflict
            try:
                supabase.table("realtime_scores").upsert(
                    data,
                    on_conflict="session_id,student_name"
                ).execute()
                print(f"📡 {s['name']}: {int(s['progress'])}% | Score: {current_score}")
            except Exception as e:
                print(f"❌ Błąd zapisu dla {s['name']}: {e}")

        time.sleep(3)  # Prędkość odświeżania na filmiku


if __name__ == "__main__":
    simulate_progress()