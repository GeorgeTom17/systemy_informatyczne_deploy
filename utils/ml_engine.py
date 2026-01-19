import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import difflib
import os
from utils.db_manager import fetch_training_data
from utils.db_supabase import fetch_ml_data_from_supabase

LANG_CHARSETS = {
    "Polski": "ĄĆĘŁŃÓŚŹŻąćęłńóśźż",
    "Niemiecki": "ÄÖÜßäöüß",
    "Francuski": "ÀÂÇÉÈÊËÎÏÔÛÙYàâçéèêëîïôûùy",
    "Hiszpański": "ÑÁÉÍÓÚÜñáéíóúü",
    "Włoski": "ÀÈÉÌÒÓÙàèéìòóù",
    "Angielski": ""
}

VOWELS = "AEOUYIaeouyiĄĘÓąęóÄÖÜäöüÉÈÊËéèêëÁÉÍÓÚáéíóúÀÈÌÒÙàèìòù"

INITIAL_DATA = [
    ("DOM", "Miejsce zamieszkania", "Polski", "ŁATWE"),
    ("COMPUTER", "Komputer", "Angielski", "ŁATWE"),
    ("DOG", "Pies", "Angielski", "ŁATWE"),
    ("BUTTERFLY", "Motyl", "Angielski", "TRUDNE"),
    ("SCHMETTERLING", "Motyl", "Niemiecki", "TRUDNE"),
    ("ORGANISM", "Organizm", "Angielski", "ŁATWE"),
    ("MAÑANA", "Jutro", "Hiszpański", "ŚREDNIE"),
    ("GARÇON", "Chłopiec", "Francuski", "ŚREDNIE")
]


class DifficultyModel:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False

    def calculate_similarity(self, word1, word2):
        """
        Oblicza podobieństwo (0.0 - 1.0) między słowem a jego tłumaczeniem.
        Używamy difflib.SequenceMatcher.
        """
        if not word2:
            return 0.0
        return difflib.SequenceMatcher(None, str(word1).lower(), str(word2).lower()).ratio()

    def extract_features(self, word, clue="", lang="Polski"):
        """
        Inżynieria cech:
        1. Długość słowa
        2. Liczba znaków specyficznych dla danego języka
        3. Stosunek samogłosek
        4. PODOBIEŃSTWO do definicji (jeśli definicja to tłumaczenie)
        """
        word = str(word).strip()
        clue = str(clue).strip()

        length = len(word)

        specific_chars = LANG_CHARSETS.get(lang, "")
        spec_count = sum(1 for char in word if char in specific_chars)

        vowel_count = sum(1 for char in word if char in VOWELS)
        vowel_ratio = vowel_count / length if length > 0 else 0

        similarity = self.calculate_similarity(word, clue)

        return [length, spec_count, vowel_ratio, similarity]

    def train(self):
        """Pobiera surowe dane o błędach i zamienia je na zestaw treningowy."""
        all_data = INITIAL_DATA.copy()

        # 1. Pobieramy logi błędów od uczniów
        raw_logs = fetch_ml_data_from_supabase()  # Musi zwracać listę słowników

        if raw_logs:
            # Agregujemy błędy per słowo
            df_logs = pd.DataFrame(raw_logs)
            if not df_logs.empty:
                # Grupowanie: suma błędów dla danej pary słowo-klucz
                agg_logs = df_logs.groupby(['word', 'clue', 'language'])['error_count'].sum().reset_index()

                for _, row in agg_logs.iterrows():
                    # LOGIKA ETYKIETOWANIA:
                    # > 10 błędów = TRUDNE, 3-10 = ŚREDNIE, < 3 = ŁATWE
                    if row['error_count'] > 10:
                        label = "TRUDNE"
                    elif row['error_count'] > 3:
                        label = "ŚREDNIE"
                    else:
                        label = "ŁATWE"

                    all_data.append((row['word'], row['clue'], row['language'], label))

        # 2. Trening modelu
        X, y = [], []
        for word, clue, lang, label in all_data:
            X.append(self.extract_features(word, clue, lang))
            y.append(label)

        if len(X) > 0:
            self.model.fit(X, y)
            self.is_trained = True
            return True
        return False

    def get_set_difficulty(self, words_list, lang="Polski"):
        """Ocenia cały zestaw słów."""
        if not self.is_trained: self.train()

        results = {"ŁATWE": 0, "ŚREDNIE": 0, "TRUDNE": 0}
        for item in words_list:
            pred, _, _ = self.predict(item['word'], item['clue'], lang)
            results[pred] += 1

        # Obliczamy średnią ważoną lub zwracamy dominującą kategorię
        total = len(words_list)
        if total == 0: return "Brak słów"

        # Prosta logika punktowa
        score = (results["ŁATWE"] * 1 + results["ŚREDNIE"] * 2 + results["TRUDNE"] * 3) / total
        if score < 1.5: return "ŁATWY"
        if score < 2.5: return "ŚREDNI"
        return "TRUDNY"

    def predict(self, word, clue="", lang="Polski"):
        if not self.is_trained:
            self.train(INITIAL_DATA)

        features = self.extract_features(word, clue, lang)
        prediction = self.model.predict([features])[0]
        proba = np.max(self.model.predict_proba([features]))

        return prediction, proba, features


ai_engine = DifficultyModel()
