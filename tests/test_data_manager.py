import pytest
import os
import json
import io  # Biblioteka do udawania plików w pamięci
from utils import data_manager


#  KONFIGURACJA TESTÓW

@pytest.fixture
def setup_temp_data(tmp_path):
    """
    To jest funkcja pomocnicza (fixture).
    Uruchamia się AUTOMATYCZNIE przed każdym testem.

    1. tmp_path: To folder tymczasowy tworzony przez pytest.
       Po testach sam się kasuje.
    2. Podmieniamy ścieżkę DATA_DIR w kodzie na ten tymczasowy folder.
       Dzięki temu testy nie zaśmiecają prawdziwego folderu data
    """
    # Zmieniamy ścieżkę w module na folder tymczasowy
    original_dir = data_manager.DATA_DIR
    data_manager.DATA_DIR = str(tmp_path)

    # Oddajemy sterowanie do testu
    yield

    # Po teście przywracamy starą ścieżkę (dla porządku)
    data_manager.DATA_DIR = original_dir


# TESTY WŁAŚCIWE

def test_create_and_get_sets(setup_temp_data):
    """TEST 1: Czy potrafimy stworzyć zestaw i czy pojawia się na liście?"""

    # Krok 1: Tworzymy nowy zestaw o nazwie 'historia'
    result = data_manager.create_set("historia")

    # SPRAWDZENIE: Czy funkcja zwróciła True (sukces)?
    assert result is True

    # Krok 2: Pobieramy listę wszystkich zestawów
    sets = data_manager.get_all_sets()

    # SPRAWDZENIE: Czy na liście jest nasza 'historia'?
    assert "historia" in sets
    # SPRAWDZENIE: Czy jest dokładnie jeden zestaw?
    assert len(sets) == 1


def test_save_and_load_words(setup_temp_data):
    """TEST 2: Czy zapisywanie słów i ich odczyt działa?"""

    set_name = "biologia"
    data_manager.create_set(set_name)

    # Krok 1: Dodajemy słowo
    # Uwaga: Twoja funkcja zamienia słowa na wielkie litery (upper)
    data_manager.save_word("komórka", "podstawowa jednostka", set_name)

    # Krok 2: Wczytujemy słowa z pliku
    words = data_manager.load_words(set_name)

    # SPRAWDZENIE: Czy lista nie jest pusta?
    assert len(words) > 0

    # SPRAWDZENIE: Czy pierwsze słowo to to, które dodaliśmy?
    # Pamiętamy, że Twój kod robi .upper(), więc oczekujemy "KOMÓRKA"
    assert words[0]["word"] == "KOMÓRKA"
    assert words[0]["clue"] == "podstawowa jednostka"


def test_save_uploaded_set_valid(setup_temp_data):
    """TEST 3: Czy działa wgrywanie poprawnego pliku JSON?"""

    # Symulujemy plik - tworzymy "sztuczny" plik w pamięci komputera
    # To tak, jakby użytkownik wgrał plik 'import.json'
    file_content = [
        {"word": "PIES", "clue": "Szczeka"},
        {"word": "KOT", "clue": "Miauczy"}
    ]

    # Udajemy plik Streamlita (musi mieć metodę read() i atrybut name)
    fake_file = io.StringIO(json.dumps(file_content))
    fake_file.name = "zwierzeta.json"  # Nadajemy nazwę pliku

    # Wywołujemy Twoją funkcję
    success, message = data_manager.save_uploaded_set(fake_file)

    # SPRAWDZENIE: Czy funkcja zwróciła sukces?
    assert success is True
    assert "pomyślnie" in message

    # SPRAWDZENIE: Czy plik faktycznie powstał i czy da się go odczytać?
    # Nazwa zestawu to nazwa pliku bez .json -> "zwierzeta"
    loaded_words = data_manager.load_words("zwierzeta")
    assert len(loaded_words) == 2
    assert loaded_words[0]["word"] == "PIES"


def test_save_uploaded_set_invalid(setup_temp_data):
    """TEST 4: Czy system odrzuci błędny plik (walidacja)?"""

    # Przypadek: Plik JSON, ale zły format (nie ma klucza 'clue')
    bad_content = [
        {"word": "AUTO", "cos_innego": "Jedzie"}
    ]

    fake_file = io.StringIO(json.dumps(bad_content))
    fake_file.name = "zly_plik.json"

    # Wywołujemy funkcję
    success, message = data_manager.save_uploaded_set(fake_file)

    # SPRAWDZENIE: Oczekujemy porażki (False)
    assert success is False
    # SPRAWDZENIE: Czy komunikat błędu jest sensowny?
    assert "Każdy element musi mieć klucze" in message