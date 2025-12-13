import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

SHEET_NAME = "crossword_brain"


def get_db_connection():
    """Łączy się z Google Sheets używając sekretów ze Streamlit."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print(f"Błąd połączenia z bazą: {e}")
        return None


def fetch_training_data():
    """Pobiera wszystkie dane treningowe z arkusza."""
    sheet = get_db_connection()
    if not sheet:
        return []

    data = sheet.get_all_records()

    formatted_data = []
    for row in data:
        formatted_data.append((
            str(row['word']),
            str(row['clue']),
            str(row['lang']),
            str(row['label'])
        ))
    return formatted_data


def save_student_feedback(feedback_list):
    """
    feedback_list: lista krotek (word, clue, lang, label)
    Zapisuje nowe 'doświadczenia' do bazy.
    """
    sheet = get_db_connection()
    if not sheet:
        return

    rows_to_append = []
    for item in feedback_list:
        rows_to_append.append([item[0], item[1], item[2], item[3]])

    sheet.append_rows(rows_to_append)