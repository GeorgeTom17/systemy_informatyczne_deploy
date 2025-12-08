import time
import random


# --- PRZYKŁAD 1: STUB (Sztywna odpowiedź) ---
class StubTranslator:
    """
    Ten obiekt udaje zaawansowany moduł tłumaczący.
    W rzeczywistości ma tylko kilka wpisanych na sztywno słów.
    Służy do testowania UI generowania krzyżówki bez internetu.
    """

    def __init__(self):
        self._dictionary = {
            "pies": "dog",
            "kot": "cat",
            "dom": "house",
            "szkoła": "school",
            "okno": "window"
        }

    def translate(self, word):
        # Symulujemy małe opóźnienie, jak w prawdziwym API
        time.sleep(0.1)

        word_lower = word.lower().strip()
        # Jeśli znamy słowo, zwracamy tłumaczenie
        if word_lower in self._dictionary:
            return self._dictionary[word_lower]

        # Jeśli nie znamy, zwracamy fałszywy wynik (żeby interfejs się nie sypał)
        return f"[MOCK] {word} (en)"


# --- PRZYKŁAD 2: MOCK  ---
class MockDifficultyAI:
    """
    Ten obiekt udaje model, który analizuje
    poziom trudności słownictwa w zestawie.
    """

    def analyze_complexity(self, words_list):
        """
        Zwraca udawany raport o poziomie trudności (A1-C2).
        """
        # Udajemy, że 'myślimy' (dla efektu w UI)
        time.sleep(1.5)

        count = len(words_list)

        # Prosta logika mocka: mało słów -> A1, dużo słów -> B2/C1
        if count < 3:
            level = "A1 (Początkujący)"
            score = 15
        elif count < 6:
            level = "B1 (Średniozaawansowany)"
            score = 55
        else:
            level = "C1 (Ekspert)"
            score = 85

        return {
            "level": level,
            "score": score,  # 0-100
            "details": f"Przeanalizowano {count} słów pod kątem rzadkości występowania.",
            "suggestion": "Dodaj więcej czasowników, aby utrudnić zestaw."
        }