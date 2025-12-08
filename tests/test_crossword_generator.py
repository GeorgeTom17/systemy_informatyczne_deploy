import pytest
import sys
import os
import numpy as np

# Dodajemy katalog projektu do ścieżki, żeby widzieć pliki
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.crossword_generator import CrosswordGenerator


def test_single_word_placement():
    """
    TEST 1: Sprawdza, czy pojedyncze słowo jest poprawnie umieszczane na planszy.
    Weryfikuje logikę: [NUMER] -> [L] -> [I] -> [T] -> [E] -> [R] -> [A]
    """
    # 1. Dane wejściowe - jedno słowo
    data = [{"word": "KOT", "clue": "Mały ssak"}]

    # 2. Generowanie
    generator = CrosswordGenerator(data, size=10)
    grid, clues_across, clues_down = generator.generate()

    # 3. Szukamy komórki startowej (tej "pomarańczowej" ze słownikiem)
    start_cell = None
    start_r, start_c = -1, -1

    for r in range(10):
        for c in range(10):
            cell = grid[r, c]
            # Sprawdzamy czy to słownik (czyli numer zadania)
            if isinstance(cell, dict):
                start_cell = cell
                start_r, start_c = r, c
                break
        if start_cell:
            break

    # ASERCJA: Czy znaleziono numer startowy?
    assert start_cell is not None, "Nie znaleziono pola startowego (numeru) na planszy!"
    assert start_cell['number'] == 1
    assert start_cell['clue'] == "Mały ssak"

    # 4. Sprawdzamy, czy LITERY są tuż obok numeru
    direction = start_cell['direction']

    if direction == 'across':
        # Dla 'across' litery powinny być w prawo: (r, c+1), (r, c+2), (r, c+3)
        assert grid[start_r, start_c + 1] == 'K'
        assert grid[start_r, start_c + 2] == 'O'
        assert grid[start_r, start_c + 3] == 'T'
    else:
        # Dla 'down' litery powinny być w dół: (r+1, c), (r+2, c), (r+3, c)
        assert grid[start_r + 1, start_c] == 'K'
        assert grid[start_r + 2, start_c] == 'O'
        assert grid[start_r + 3, start_c] == 'T'


def test_multiple_words_integration():
    """
    TEST 2: Sprawdza, czy algorytm potrafi umieścić więcej słów
    i czy generuje listy podpowiedzi (across/down).
    """
    data = [
        {"word": "ALA", "clue": "Imię"},
        {"word": "DOM", "clue": "Budynek"},
        {"word": "LAS", "clue": "Drzewa"}
    ]

    generator = CrosswordGenerator(data, size=15)
    grid, c_across, c_down = generator.generate()

    # 1. Sprawdzamy czy cokolwiek się wygenerowało w podpowiedziach
    total_clues = len(c_across) + len(c_down)

    # Oczekujemy, że udało się wstawić przynajmniej 2 słowa (algorytm jest losowy,
    # ale przy tak małych słowach i dużej planszy powinien zmieścić wszystko).
    assert total_clues >= 2, f"Zmieściło się za mało słów: {total_clues}"

    # 2. Sprawdzamy czy na planszy są litery (stringi)
    letter_count = 0
    for row in grid:
        for cell in row:
            if isinstance(cell, str):
                letter_count += 1

    assert letter_count > 0, "Plansza jest pusta (brak liter)!"