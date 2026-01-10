import pyodbc
import streamlit as st
import pandas as pd


def get_mssql_connection():
    """Tworzy połączenie z serwerem wydziałowym MSSQL."""
    try:
        # Pobieramy dane z st.secrets
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={st.secrets['mssql']['server']};"
            f"DATABASE={st.secrets['mssql']['database']};"
            f"UID={st.secrets['mssql']['username']};"
            f"PWD={st.secrets['mssql']['password']}"
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        st.error(f"❌ Błąd połączenia z MSSQL: {e}")
        return None


# Przykład funkcji pobierającej dane ML
def fetch_ml_data_from_sql():
    conn = get_mssql_connection()
    if not conn: return []

    query = "SELECT Word, Clue, Language, Label FROM ML_TrainingData"
    df = pd.read_sql(query, conn)
    conn.close()

    # Zwracamy format gotowy dla modelu ML: [(word, clue, lang, label), ...]
    return list(df.itertuples(index=False, name=None))

def test_mssql_connection():
    """Funkcja testowa do sprawdzenia łączności z bazą danych."""
    try:
        conn = get_mssql_connection()
        if conn:
            cursor = conn.cursor()
            # Pobieramy wersję serwera - to najbezpieczniejszy test
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            conn.close()
            return True, f"Połączono pomyślnie! Wersja serwera: {row[0]}"
        return False, "Nie udało się nawiązać połączenia (conn is None)."
    except Exception as e:
        return False, str(e)

# Przykład funkcji zapisującej feedback ucznia
def save_ml_feedback_to_sql(word, clue, lang, label):
    conn = get_mssql_connection()
    if not conn: return

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ML_TrainingData (Word, Clue, Language, Label) VALUES (?, ?, ?, ?)",
        (word, clue, lang, label)
    )
    conn.commit()
    conn.close()