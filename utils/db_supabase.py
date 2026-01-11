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


def update_set_content_in_db(set_name, new_data):
    supabase = get_supabase_client()
    try:
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        set_id = set_res.data['id']
        supabase.table("words").delete().eq("set_id", set_id).execute()
        to_insert = []
        for row in new_data:
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