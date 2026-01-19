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
        """Pobiera dane z tabeli ml_training_data i trenuje model."""
        # 1. Startujemy od danych bazowych
        all_data = INITIAL_DATA.copy()

        # 2. Pobieramy dane z Supabase (tabela: ml_training_data)
        try:
            cloud_data = fetch_ml_data_from_supabase() # Musi zwracać listę (word, clue, lang, label)
            if cloud_data:
                # cloud_data to lista słowników: [{'word': '...', 'label': '...'}, ...]
                for record in cloud_data:
                    all_data.append((
                        record['word'],
                        record['clue'],
                        record['language'],
                        record['label']
                    ))
        except Exception as e:
            print(f"Błąd pobierania danych treningowych: {e}")

        if not all_data:
            return 0

        X = []
        y = []

        for word, clue, lang, label in all_data:
            features = self.extract_features(word, clue, lang)
            X.append(features)
            y.append(label)

        self.model.fit(X, y)
        self.is_trained = True
        return self.model.score(X, y)

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
