import pyodbc
import streamlit as st
import pandas as pd
from sshtunnel import SSHTunnelForwarder

def get_mssql_connection():
    # 1. Konfiguracja tunelu SSH
    # Dane pobieramy z st.secrets
    ssh_host = st.secrets["ssh"]["host"]  # np. lab.wmi.amu.edu.pl
    ssh_user = st.secrets["ssh"]["username"]  # Twój login (s464981)
    ssh_pwd = st.secrets["ssh"]["password"]  # Twoje hasło do systemów WMI

    db_server = st.secrets["mssql"]["server"]  # Wewnętrzny adres IP/host bazy w sieci WMI
    db_port = 1433  # Standardowy port MSSQL

    try:
        # Tworzymy tunel
        server = SSHTunnelForwarder(
            (ssh_host, 22),
            ssh_username=ssh_user,
            ssh_password=ssh_pwd,
            remote_bind_address=(db_server, db_port)
        )

        server.start()

        # 2. Połączenie ODBC przez lokalny port tunelu
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=127.0.0.1;"  # Łączymy się z lokalnym końcem tunelu
            f"PORT={server.local_bind_port};"
            f"DATABASE={st.secrets['mssql']['database']};"
            f"UID={st.secrets['mssql']['username']};"
            f"PWD={st.secrets['mssql']['password']};"
        )

        conn = pyodbc.connect(conn_str)
        # Musimy zachować obiekt 'server', żeby tunel nie zamknął się za szybko
        st.session_state.ssh_tunnel = server
        return conn

    except Exception as e:
        st.error(f"Błąd tunelu/bazy: {e}")
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