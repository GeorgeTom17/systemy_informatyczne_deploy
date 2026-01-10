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