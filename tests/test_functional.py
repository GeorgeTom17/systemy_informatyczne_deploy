import unittest
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
# -----------------------------------------


from utils.data_manager import create_set, save_word, load_words, DATA_DIR
from utils.crossword_generator import CrosswordGenerator
from utils.mocks import MockDifficultyAI


class TestCrosswordSystem(unittest.TestCase):

    # =========================================================================
    # 1. SMOKE TEST
    def test_smoke_data_manager_crud(self):
        print("\n--- [SMOKE TEST] Sprawdzanie operacji na plikach (CRUD) ---")
        test_set_name = "test_smoke_set"

        # 1. Czy tworzy plik?
        created = create_set(test_set_name)
        self.assertTrue(created, "Błąd: Nie udało się utworzyć zestawu danych.")

        # 2. Czy zapisuje słowo?
        saved = save_word("TEST", "To jest test", test_set_name)
        self.assertTrue(saved, "Błąd: Nie udało się zapisać słowa do zestawu.")

        # 3. Czy odczytuje słowo?
        words = load_words(test_set_name)
        self.assertEqual(len(words), 1, "Błąd: Zestaw powinien zawierać dokładnie 1 słowo.")
        self.assertEqual(words[0]['word'], "TEST", "Błąd: Odczytano błędne słowo.")

        # Sprzątanie po teście (usuwamy plik testowy)
        file_path = os.path.join(DATA_DIR, f"{test_set_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        print(">>> Smoke Test ZALICZONY: System plików działa poprawnie.")

    # =========================================================================
    # 2. SANITY TEST (Test Zdrowia/Poprawności)
    # =========================================================================
    def test_sanity_generator_core(self):
        print("\n--- [SANITY TEST] Sprawdzanie generowania krzyżówki ---")

        # Dane wejściowe: Prosta lista słów, które na pewno się krzyżują
        data = [
            {"word": "ALA", "clue": "Ma kota"},
            {"word": "LAMA", "clue": "Zwierzę"},
            {"word": "DOM", "clue": "Budynek"}
        ]

        # Uruchamiamy generator
        generator = CrosswordGenerator(data, size=10)
        grid, across, down = generator.generate()

        # Asercje: Sprawdzamy czy wynik nie jest pusty
        has_content = len(across) > 0 or len(down) > 0
        self.assertTrue(has_content, "Błąd: Generator zwrócił pustą listę haseł.")
        self.assertIsNotNone(grid, "Błąd: Grid jest None.")

        print(f">>> Sanity Test ZALICZONY: Wygenerowano {len(across) + len(down)} haseł.")

    # =========================================================================
    # 3. REGRESSION TEST (Test Regresji)
    # =========================================================================
    def test_regression_difficulty_logic(self):
        print("\n--- [REGRESSION TEST] Sprawdzanie logiki oceny trudności ---")

        mock_ai = MockDifficultyAI()

        # Przypadek A: Mało słów (<3) -> Powinno być A1
        words_a1 = ["pies", "kot"]
        # Zmieniamy sleep na 0, żeby test leciał szybko (hackujemy mocka na potrzeby testu)
        import time
        original_sleep = time.sleep
        time.sleep = lambda x: None

        result = mock_ai.analyze_complexity(words_a1)

        # Przywracamy sleep
        time.sleep = original_sleep

        # Sprawdzamy czy logika "Mało słów = A1" nadal działa
        self.assertIn("A1", result['level'], "REGRESJA! Poziom dla 2 słów powinien być A1.")
        self.assertEqual(result['score'], 15, "REGRESJA! Punktacja dla A1 powinna wynosić 15.")

        print(">>> Regression Test ZALICZONY: Logika oceniania trudności jest stabilna.")


if __name__ == '__main__':
    unittest.main()