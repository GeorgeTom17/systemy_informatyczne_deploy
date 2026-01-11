import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicjalizuje klienta Supabase."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# --- FUNKCJE DLA UCZENIA MASZYNOWEGO ---

def fetch_ml_data_from_supabase():
    """Pobiera dane treningowe dla modelu ML."""
    supabase = get_supabase_client()
    try:
        # Pobieramy wszystkie rzędy z tabeli ml_training_data
        response = supabase.table("ml_training_data").select("word, clue, language, label").execute()
        data = response.data
        # Konwersja na format krotek dla modelu: [(word, clue, lang, label), ...]
        return [(r['word'], r['clue'], r['language'], r['label']) for r in data]
    except Exception as e:
        st.error(f"Błąd pobierania danych ML: {e}")
        return []

def save_ml_feedback_to_supabase(word, clue, lang, label):
    """Zapisuje feedback ucznia do bazy Supabase."""
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
    """Wykonuje praktyczny test łączności z API Supabase i bazą danych."""
    try:
        supabase = get_supabase_client()
        # Wykonujemy najprostsze zapytanie: sprawdzenie czy tabela 'sets' istnieje
        # (nawet jeśli jest pusta, zapytanie powinno zwrócić sukces)
        response = supabase.table("sets").select("id").limit(1).execute()

        # Jeśli nie rzuciło wyjątku, połączenie i klucze są poprawne
        return True, "✅ Połączono z Supabase! API odpowiada, a baza PostgreSQL jest dostępna."
    except Exception as e:
        # Wyciągamy szczegóły błędu (np. Invalid Key, Connection Timeout)
        error_msg = str(e)
        if "401" in error_msg:
            return False, "❌ Błąd 401: Nieprawidłowy klucz (API Key)."
        elif "404" in error_msg:
            return False, "❌ Błąd 404: Nieprawidłowy URL projektu lub brak tabeli 'sets'."
        return False, f"❌ Wystąpił błąd: {error_msg}"


def get_all_sets_from_db():
    """Pobiera listę nazw wszystkich zestawów."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("sets").select("name").execute()
        return [row['name'] for row in response.data]
    except Exception as e:
        st.error(f"Błąd pobierania zestawów: {e}")
        return []


def create_set_in_db(set_name):
    """Tworzy nowy zestaw w bazie."""
    supabase = get_supabase_client()
    try:
        supabase.table("sets").insert({"name": set_name}).execute()
        return True
    except Exception as e:
        st.error(f"Błąd tworzenia zestawu: {e}")
        return False


def load_words_from_db(set_name):
    """Pobiera słowa dla konkretnego zestawu używając JOIN."""
    supabase = get_supabase_client()
    try:
        # Najpierw pobieramy ID zestawu
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        if not set_res.data:
            return []

        set_id = set_res.data['id']
        # Pobieramy słowa przypisane do tego ID
        words_res = supabase.table("words").select("word, clue").eq("set_id", set_id).execute()
        return words_res.data
    except Exception as e:
        print(f"Błąd ładowania słów: {e}")
        return []


def save_word_to_db(word, clue, set_name):
    """Zapisuje pojedyncze słowo do zestawu."""
    supabase = get_supabase_client()
    try:
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        set_id = set_res.data['id']

        supabase.table("words").insert({
            "set_id": set_id,
            "word": word.strip().upper(),
            "clue": clue.strip()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Błąd zapisu słowa: {e}")
        return False


def update_set_content_in_db(set_name, new_data):
    """
    Synchronizuje zawartość zestawu.
    Najprostsza metoda: usuń stare i wstaw nowe (w obrębie danego zestawu).
    """
    supabase = get_supabase_client()
    try:
        # 1. Pobierz ID zestawu
        set_res = supabase.table("sets").select("id").eq("name", set_name).single().execute()
        set_id = set_res.data['id']

        # 2. Usuń wszystkie obecne słowa dla tego zestawu
        supabase.table("words").delete().eq("set_id", set_id).execute()

        # 3. Przygotuj nowe dane do wstawienia
        to_insert = []
        for row in new_data:
            if row.get('word') and row.get('clue'):
                to_insert.append({
                    "set_id": set_id,
                    "word": str(row['word']).strip().upper(),
                    "clue": str(row['clue']).strip()
                })

        # 4. Wstaw nowe dane hurtowo
        if to_insert:
            supabase.table("words").insert(to_insert).execute()

        return True
    except Exception as e:
        st.error(f"Błąd aktualizacji zestawu: {e}")
        return False