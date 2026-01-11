import json
import os
import glob
import pandas as pd
from io import StringIO
from utils.db_supabase import create_set_in_db, bulk_insert_words

DATA_DIR = "data"


def update_set_content(set_name, new_data):
    """
    Nadpisuje zawartość zestawu nowymi danymi.
    new_data: lista słowników [{'word': '...', 'clue': '...'}, ...]
    """
    file_path = os.path.join(DATA_DIR, f"{set_name}.json")

    # Zabezpieczenie: upewnij się, że dane mają odpowiedni format
    cleaned_data = []
    for item in new_data:
        # Ignorujemy puste wiersze, które mogły powstać przy edycji
        if item.get('word') and item.get('clue'):
            cleaned_data.append({
                'word': str(item['word']).strip().upper(),  # Wymuszamy UPPERCASE dla słów
                'clue': str(item['clue']).strip()
            })

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Błąd zapisu zestawu: {e}")
        return False


def get_all_sets():
    if not os.path.exists(DATA_DIR):
        return []
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    return [os.path.splitext(os.path.basename(f))[0] for f in files]


def create_set(set_name):
    if not set_name: return False
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, f"{set_name}.json")
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f: json.dump([], f)
        return True
    return False


def load_words(set_name):
    file_path = os.path.join(DATA_DIR, f"{set_name}.json")
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_word(word, clue, set_name):
    words = load_words(set_name)
    new_entry = {"word": word.upper().strip(), "clue": clue.strip()}
    if new_entry not in words:
        words.append(new_entry)
        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"{set_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(words, f, indent=4, ensure_ascii=False)
        return True
    return False


def normalize_data_frame(df):
    df = df.dropna(how='all')
    df.columns = [str(col).lower().strip() for col in df.columns]

    word_col = None;
    clue_col = None
    possible_word_headers = ['word', 'słowo', 'hasło', 'term']
    possible_clue_headers = ['clue', 'definicja', 'opis', 'definition']

    for col in df.columns:
        if col in possible_word_headers:
            word_col = col
        elif col in possible_clue_headers:
            clue_col = col

    if not word_col and len(df.columns) >= 1: word_col = df.columns[0]
    if not clue_col and len(df.columns) >= 2: clue_col = df.columns[1]

    if not word_col or not clue_col:
        return None, "Nie rozpoznano kolumn (wymagane 2 kolumny lub nagłówki 'word'/'clue')."

    result = []
    for _, row in df.iterrows():
        w = str(row[word_col]).strip()
        c = str(row[clue_col]).strip()
        if w and c and w.lower() != 'nan' and c.lower() != 'nan':
            result.append({"word": w, "clue": c})
    return result, None


def normalize_data_frame(df):
    """Pomocnicza funkcja do standaryzacji kolumn DataFrame."""
    # Szukamy kolumn bez względu na wielkość liter
    df.columns = [c.lower().strip() for c in df.columns]
    if 'word' in df.columns and 'clue' in df.columns:
        return df[['word', 'clue']].to_dict('records'), None
    return [], "Błąd: Plik musi zawierać kolumny 'word' oraz 'clue'."


def import_file_to_db(uploaded_file):
    """Parsuje plik i wysyła go do Supabase."""
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()
    set_name = os.path.splitext(filename)[0]

    content_list = []
    error_msg = None

    try:
        # --- PARSOWANIE (Formaty bez zmian) ---
        if ext == '.json':
            content_list = json.load(uploaded_file)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(uploaded_file)
            content_list, error_msg = normalize_data_frame(df)
        elif ext == '.csv':
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='cp1250')

            # Autodetekcja separatora jeśli tylko jedna kolumna
            if len(df.columns) < 2:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')

            content_list, error_msg = normalize_data_frame(df)
        elif ext == '.txt':
            string_data = uploaded_file.read().decode("utf-8")
            for line in string_data.split('\n'):
                line = line.strip()
                if not line: continue
                for sep in [';', ':', '-', ',']:
                    if sep in line:
                        parts = line.split(sep, 1)
                        content_list.append({"word": parts[0].strip(), "clue": parts[1].strip()})
                        break

        if error_msg: return False, error_msg
        if not content_list: return False, "Nie znaleziono danych w pliku."

        # --- ZAPIS DO BAZY (NOWOŚĆ) ---
        # 1. Tworzymy zestaw
        set_id = create_set_in_db(set_name)
        if not set_id:
            return False, "Nie udało się utworzyć zestawu (może już istnieje?)"

        # 2. Wstawiamy słowa masowo
        success = bulk_insert_words(set_id, content_list)

        if success:
            return True, f"Zaimportowano {len(content_list)} haseł do bazy!"
        return False, "Błąd podczas wstawiania rekordów do bazy."

    except Exception as e:
        return False, f"Błąd krytyczny: {str(e)}"
