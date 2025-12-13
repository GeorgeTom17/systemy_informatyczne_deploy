import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import difflib
import os
from utils.db_manager import fetch_training_data

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

    def train(self, local_data=None):
        """
        Teraz łączy dane startowe (wbudowane) z danymi z BAZY (Google Sheets).
        """
        all_data = INITIAL_DATA.copy()

        try:
            cloud_data = fetch_training_data()
            if cloud_data:
                all_data.extend(cloud_data)
        except Exception:
            pass

        X = []
        y = []

        for word, clue, lang, label in all_data:
            features = self.extract_features(word, clue, lang)
            X.append(features)
            y.append(label)

        self.model.fit(X, y)
        self.is_trained = True
        return self.model.score(X, y)

    def predict(self, word, clue="", lang="Polski"):
        if not self.is_trained:
            self.train(INITIAL_DATA)

        features = self.extract_features(word, clue, lang)
        prediction = self.model.predict([features])[0]
        proba = np.max(self.model.predict_proba([features]))

        return prediction, proba, features


ai_engine = DifficultyModel()