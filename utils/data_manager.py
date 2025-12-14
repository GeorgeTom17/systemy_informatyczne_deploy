import json
import os
import glob
import pandas as pd
from io import StringIO

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



def save_uploaded_set(uploaded_file):
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()
    target_name = os.path.splitext(filename)[0] + ".json"
    target_path = os.path.join(DATA_DIR, target_name)

    content_list = []
    error_msg = None

    try:
        if ext == '.json':
            content_list = json.load(uploaded_file)
        elif ext in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(uploaded_file)
                content_list, error_msg = normalize_data_frame(df)
            except Exception as e:
                return False, f"Błąd Excela: {str(e)}"
        elif ext == '.csv':
            try:
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='cp1250')

                if len(df.columns) < 2:
                    uploaded_file.seek(0)
                    try:
                        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=';', encoding='cp1250')

                content_list, error_msg = normalize_data_frame(df)
            except Exception as e:
                return False, f"Błąd CSV: {str(e)}"
        elif ext == '.txt':
            try:
                string_data = uploaded_file.read().decode("utf-8")
                lines = string_data.split('\n')

                for line in lines:
                    line = line.strip()
                    if not line: continue

                    parts = []

                    if ';' in line:
                        parts = line.split(';', 1)
                    elif ':' in line:
                        parts = line.split(':', 1)
                    elif '-' in line:
                        parts = line.split('-', 1)
                    elif ',' in line:
                        parts = line.split(',', 1)
                    else:
                        continue

                    if len(parts) == 2:
                        content_list.append({
                            "word": parts[0].strip(),
                            "clue": parts[1].strip()
                        })

                if not content_list:
                    return False, "Plik TXT pusty lub zły format (użyj separatora: ; : - lub ,)"

            except Exception as e:
                return False, f"Błąd TXT: {str(e)}"

        else:
            return False, f"Nieobsługiwany format: {ext}"

        if error_msg: return False, error_msg
        if not isinstance(content_list, list): return False, "Dane muszą być listą."

        final_data = []
        for item in content_list:
            if "word" in item and "clue" in item:
                final_data.append({
                    "word": str(item["word"]).upper().strip(),
                    "clue": str(item["clue"]).strip()
                })

        if not final_data: return False, "Nie znaleziono poprawnych par."

        os.makedirs(DATA_DIR, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)

        return True, f"Zaimportowano {len(final_data)} słów!"

    except Exception as e:
        return False, f"Błąd: {str(e)}"
