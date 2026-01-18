import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def fetch_ml_data_from_supabase():
    supabase = get_supabase_client()
    try:
        response = supabase.table("ml_training_data").select("word, clue, language, label").execute()
        data = response.data
        return [(r['word'], r['clue'], r['language'], r['label']) for r in data]
    except Exception as e:
        st.error(f"Błąd pobierania danych ML: {e}")
        return []

def save_ml_feedback_to_supabase(word, clue, lang, label):
    supabase = get_supabase_client()
    try:
        supabase.table("ml_training_data").insert({
            "word": word,
            "clue": clue,
            "language": lang,
            "label": label
        }).execute()
    except Exception as e:
        print(f"Błąd zapisu feedbacku: {e}")


def test_supabase_connection():
    try:
        supabase = get_supabase_client()
        response = supabase.table("sets").select("id").limit(1).execute()
        return True, "Połączono z Supabase! API odpowiada, a baza PostgreSQL jest dostępna."
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return False, "Błąd 401: Nieprawidłowy klucz (API Key)."
        elif "404" in error_msg:
            return False, "Błąd 404: Nieprawidłowy URL projektu lub brak tabeli 'sets'."
        return False, f"Wystąpił błąd: {error_msg}"


def get_all_sets_from_db():
    supabase = get_supabase_client()
    try:
        response = supabase.table("sets").select("name").execute()
        return [row['name'] for row in response.data]
    except Exception as e:
        st.error(f"Błąd pobierania zestawów: {e}")
        return []


def create_set_in_db(set_name):
    supabase = get_supabase_client()
    try:
        response = supabase.table("sets").insert({"name": set_name}).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        st.error(f"Błąd tworzenia zestawu: {e}")
        return None


def bulk_insert_words(set_id, words_list):
    supabase = get_supabase_client()
    try:
        to_insert = []
        seen_in_batch = set()

        for item in words_list:
            w = str(item["word"]).upper().strip()
            if w in seen_in_batch or not w:
                continue

            to_insert.append({
                "set_id": set_id,
                "word": w,
                "clue": str(item["clue"]).strip()
            })
            seen_in_batch.add(w)

        if to_insert:
            supabase.table("words").upsert(
                to_insert,
                on_conflict="set_id, word"
            ).execute()

        return True
    except Exception as e:
        st.error(f"Błąd masowego zapisu: {e}")
        return False


def load_words_from_db(set_name):
    supabase = get_supabase_client()
    try:
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        if not set_res.data:
            return []

        set_id = set_res.data['id']
        words_res = supabase.table("words").select("word, clue").eq("set_id", set_id).execute()
        return words_res.data
    except Exception as e:
        print(f"Błąd ładowania słów: {e}")
        return []


def save_word_to_db(word, clue, set_name):
    supabase = get_supabase_client()
    try:
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        set_id = set_res.data['id']

        supabase.table("words").insert({
            "set_id": set_id,
            "word": word.strip().upper(),
            "clue": clue.strip()
        }).execute()

        return True, "Dodano hasło!"
    except Exception as e:
        if "unique_word_per_set" in str(e):
            return False, "To słowo już istnieje w tym zestawie!"
        return False, f"Błąd bazy: {e}"


def update_set_content_in_db(set_name, new_data, source_lang, target_lang):
    supabase = get_supabase_client()
    try:
        # 1. Pobieramy ID zestawu
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        set_id = set_res.data['id']

        # 2. AKTUALIZACJA JĘZYKÓW (Metadane zestawu)
        supabase.table("sets").update({
            "source_lang": source_lang,
            "target_lang": target_lang
        }).eq("id", set_id).execute()

        # 3. Usuwamy stare słowa
        supabase.table("words").delete().eq("set_id", set_id).execute()

        # 4. Przygotowujemy nowe słowa do wstawienia
        to_insert = []
        for row in new_data:
            # Używamy Twoich kluczy: 'word' i 'clue'
            if row.get('word') and row.get('clue'):
                to_insert.append({
                    "set_id": set_id,
                    "word": str(row['word']).strip().upper(),
                    "clue": str(row['clue']).strip()
                })

        if to_insert:
            supabase.table("words").insert(to_insert).execute()

        return True
    except Exception as e:
        st.error(f"Błąd aktualizacji zestawu: {e}")
        return False

def save_session_to_db(name, raw_code):
    supabase = get_supabase_client()
    try:
        response = supabase.table("sessions").insert({
            "name": name,
            "raw_code": raw_code
        }).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        st.error(f"Błąd zapisu sesji do bazy: {e}")
        return None

def get_session_from_db(session_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table("sessions").select("name, raw_code").eq("id", session_id).single().execute()
        if response.data:
            return response.data
        return None
    except Exception as e:
        st.error(f"Nie znaleziono sesji o ID {session_id}: {e}")
        return None

def get_all_sessions_from_db():
    supabase = get_supabase_client()
    try:
        response = supabase.table("sessions").select("id, name, created_at").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd pobierania sesji: {e}")
        return []

def get_results_for_session_from_db(session_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table("results").select("student_name, time_taken, hint_count, submitted_at").eq("session_id", session_id).order("time_taken").execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd pobierania wyników: {e}")
        return []

def save_result_to_db(session_id, student_name, time_taken, hint_count):
    supabase = get_supabase_client()
    try:
        supabase.table("results").insert({
            "session_id": session_id,
            "student_name": student_name,
            "time_taken": time_taken,
            "hint_count": hint_count # Zapisujemy realną liczbę!
        }).execute()
        return True
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

def get_realtime_scores_from_db(session_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table("realtime_scores")\
            .select("student_name, score, progress_percent, hint_count, last_updated")\
            .eq("session_id", session_id)\
            .order("score", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd pobierania rankingu live: {e}")
        return []

def get_student_rank(session_id, student_name):
    """Oblicza aktualną pozycję ucznia w rankingu sesji."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("realtime_scores") \
            .select("student_name, score") \
            .eq("session_id", session_id) \
            .order("score", desc=True) \
            .execute()

        scores = response.data
        if not scores:
            return None

        for index, record in enumerate(scores):
            if record['student_name'] == student_name:
                return index + 1

        return None
    except Exception as e:
        return None

def update_session_status(session_id, status):
    """Aktualizuje status sesji (waiting, active, finished)."""
    supabase = get_supabase_client()
    try:
        supabase.table("sessions").update({"status": status}).eq("id", session_id).execute()
        return True
    except Exception as e:
        st.error(f"Błąd zmiany statusu: {e}")
        return False

def get_session_status(session_id):
    """Pobiera aktualny status sesji."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("sessions").select("status").eq("id", session_id).single().execute()
        return response.data["status"] if response.data else "waiting"
    except:
        return "waiting"

# utils/db_supabase.py

def get_set_metadata(set_name):
    """Pobiera informacje o językach przypisanych do zestawu."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("sets").select("source_lang, target_lang").eq("name", set_name).single().execute()
        return res.data if res.data else {"source_lang": "pl", "target_lang": "en"}
    except:
        return {"source_lang": "pl", "target_lang": "en"} # Wartości domyślne


# utils/db_supabase.py

def create_empty_set_in_db(set_name, source_lang, target_lang):
    """Tworzy nowy wpis w tabeli sets i zwraca jego ID."""
    supabase = get_supabase_client()
    try:
        # Sprawdzamy czy nazwa już istnieje, żeby uniknąć duplikatów
        existing = supabase.table("sets").select("id").eq("name", set_name).execute()
        if existing.data:
            return existing.data[0]['id']

        res = supabase.table("sets").insert({
            "name": set_name,
            "source_lang": source_lang,
            "target_lang": target_lang
        }).execute()
        return res.data[0]['id'] if res.data else None
    except Exception as e:
        st.error(f"Błąd tworzenia zestawu: {e}")
        return None


def delete_set_from_db(set_name):
    """Usuwa zestaw i wszystkie powiązane z nim słowa."""
    supabase = get_supabase_client()
    try:
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        if not set_res.data:
            return False
        set_id = set_res.data['id']

        # 1. Usuwamy słowa przypisane do zestawu
        supabase.table("words").delete().eq("set_id", set_id).execute()
        # 2. Usuwamy sam zestaw
        supabase.table("sets").delete().eq("id", set_id).execute()
        return True
    except Exception as e:
        st.error(f"Błąd podczas usuwania: {e}")
        return False