# utils/api_manager.py
import requests
import re

def get_word_suggestions(word):
    """Pobiera definicję z polskiej Wikipedii/Wikisłownika przez nowoczesne REST API."""
    if not word or len(word) < 2:
        return []

    # Próbujemy najpierw Wikisłownik, potem Wikipedię (lepsza dla pojęć)
    sources = [
        f"https://pl.wiktionary.org/api/rest_v1/page/summary/{word.lower()}",
        f"https://pl.wikipedia.org/api/rest_v1/page/summary/{word.lower()}"
    ]

    suggestions = []

    headers = {
        'User-Agent': 'CrosswordApp/1.0 (contact: jertom1@st.amu.edu.pl)'
    }

    for url in sources:
        try:
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                extract = data.get("extract")
                if extract:
                    # Czyścimy tekst i bierzemy tylko pierwsze zdanie
                    first_sentence = extract.split('.')[0] + "."
                    if first_sentence not in suggestions:
                        suggestions.append(first_sentence)
        except:
            continue

    return suggestions[:3]


def translate_text(text, from_lang, to_lang):
    """Pomocnicza funkcja do tłumaczenia tekstu przez MyMemory API."""
    if from_lang == to_lang:
        return text
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={from_lang}|{to_lang}"
    try:
        res = requests.get(url, timeout=5).json()
        return res.get("responseData", {}).get("translatedText", text)
    except:
        return text


def get_complex_suggestions(word, source_lang, target_lang):
    """
    Łańcuch:
    1. Słowo (Source) -> English
    2. English -> Definicje (English Dictionary)
    3. Definicje -> Target Language
    """
    if not word: return []

    # 1. Tłumaczenie na angielski (jeśli to nie jest angielski)
    en_word = translate_text(word, source_lang, 'en') if source_lang != 'en' else word

    suggestions = []

    # 2. Pobieranie definicji z angielskiego słownika
    dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{en_word}"
    try:
        response = requests.get(dict_url, timeout=5)
        if response.status_code == 200:
            data = response.json()[0]
            # Przeszukujemy znaczenia (noun, verb, adjective)
            for meaning in data.get('meanings', []):
                part_of_speech = meaning.get('partOfSpeech')
                # Bierzemy pierwszą definicję dla każdej części mowy
                raw_def = meaning.get('definitions', [{}])[0].get('definition')

                if raw_def:
                    # 3. Tłumaczenie definicji na język docelowy (Target)
                    final_def = translate_text(raw_def, 'en', target_lang)

                    # Formatuje wynik: [Rzeczownik] Definicja...
                    suggestions.append({
                        "pos": part_of_speech,
                        "text": final_def
                    })

        # Zwracamy top 3
        return suggestions[:3]
    except Exception as e:
        print(f"Błąd API: {e}")
        return []


def fetch_words_for_category(category_en, limit=50):
    """Pobiera listę słów powiązanych z tematem z Datamuse API (po angielsku)."""
    # ml = 'means like' - szuka słów powiązanych znaczeniowo
    url = f"https://api.datamuse.com/words?ml={category_en}&max={limit}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return [item['word'] for item in response.json() if ' ' not in item['word']]
    except:
        return []
    return []


def get_automated_clue(word_source, src_lang_code, tgt_lang_code):
    """
    Automatycznie generuje definicję:
    1. Słowo -> Angielski
    2. Angielski -> Definicja (English Dictionary)
    3. Definicja -> Target Language
    Jeśli krok 2 zawiedzie, zwraca po prostu tłumaczenie słowa.
    """
    from utils.api_manager import translate_text  # Twoja funkcja z poprzedniego kroku

    # 1. Tłumaczymy słowo na angielski (pivot)
    en_word = translate_text(word_source, src_lang_code, 'en')

    # 2. Próbujemy pobrać pełną definicję po angielsku
    clue = None
    dict_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{en_word}"
    try:
        dict_res = requests.get(dict_url, timeout=3)
        if dict_res.status_code == 200:
            data = dict_res.json()[0]
            # Bierzemy pierwszą dostępną definicję
            raw_def = data.get('meanings', [{}])[0].get('definitions', [{}])[0].get('definition')
            if raw_def:
                # 3. Tłumaczymy definicję na język docelowy
                clue = translate_text(raw_def, 'en', tgt_lang_code)
    except:
        pass

    # Jeśli nie udało się uzyskać pełnej definicji, dajemy samo tłumaczenie
    if not clue or len(clue) < 3:
        clue = translate_text(word_source, src_lang_code, tgt_lang_code)

    return clue.capitalize()


def get_words_from_conceptnet(category_name, lang_code, limit=40):
    CAT_MAP = {
        "Zwierzęta": "animal", "Jedzenie": "food", "Podróże": "travel",
        "Dom": "house", "Praca": "job", "Sport": "sport"
    }

    tag = CAT_MAP.get(category_name, "object")

    # Używamy endpointu /search, który pozwala lepiej filtrować relacje i języki
    # Szukamy słów, które mają relację 'RelatedTo' z naszym tagiem w konkretnym języku
    url = f"http://api.conceptnet.io/search?rel=/r/RelatedTo&node=/c/en/{tag}&limit=100"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []

        res = response.json()
        raw_words = []

        for edge in res.get('edges', []):
            # Szukamy słowa w języku lang_code w krawędziach grafu
            for node_type in ['start', 'end']:
                node = edge[node_type]
                if node.get('language') == lang_code:
                    word = node.get('label')
                    # Czyścimy słowo i sprawdzamy filtry (brak spacji, długość)
                    if word and re.match(r"^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,12}$", word):
                        if word.lower() != tag.lower():
                            raw_words.append(word.upper())

        return list(set(raw_words))
    except Exception as e:
        print(f"DEBUG: Błąd ConceptNet: {e}")
        return []

def get_direct_wiktionary_definition(word, lang_code):
    """Pobiera definicję bezpośrednio z Wikisłownika w danym języku."""
    url = f"https://{lang_code}.wiktionary.org/api/rest_v1/page/summary/{word.lower()}"
    try:
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            extract = data.get("extract")
            if extract and len(extract) > 10:
                return extract
    except:
        pass
    return None


def get_refined_clue(word, src_lang, tgt_lang):
    """Pobiera definicję z Wikisłownika (src) i tłumaczy na (tgt)."""

    # 1. Próba pobrania definicji bezpośrednio z Wikisłownika
    wiki_url = f"https://{src_lang}.wiktionary.org/api/rest_v1/page/summary/{word.lower()}"
    definition = None

    try:
        res = requests.get(wiki_url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            definition = data.get("extract")
    except:
        pass

    # 2. Jeśli brak definicji w Wikisłowniku, używamy Wikipedii
    if not definition:
        wiki_url = f"https://{src_lang}.wikipedia.org/api/rest_v1/page/summary/{word.lower()}"
        try:
            res = requests.get(wiki_url, timeout=5)
            if res.status_code == 200:
                definition = res.json().get("extract")
        except:
            pass

    # 3. Tłumaczenie i czyszczenie
    if definition:
        # Usuwamy ewentualne wystąpienia szukanego słowa w definicji (ukrywamy hasło)
        clean_def = re.sub(word, "________", definition, flags=re.IGNORECASE)
        # Tłumaczymy na język docelowy
        return translate_text(clean_def, src_lang, tgt_lang)

    # 4. Fallback: Jeśli wszystko inne zawiedzie – proste tłumaczenie słowa
    return translate_text(word, src_lang, tgt_lang)


def get_words_from_wikipedia(category_name, lang_code, limit=50):
    """Pobiera listę haseł z konkretnej kategorii Wikipedii w danym języku."""

    # Mapowanie prostych nazw na oficjalne nazwy kategorii w różnych językach
    CATEGORY_MAP = {
        "pl": {
            "Sport": "Kategoria:Sport", "Jedzenie": "Kategoria:Kulinaria",
            "Zwierzęta": "Kategoria:Zwierzęta", "Dom": "Kategoria:Dom", "Praca": "Kategoria:Zawody"
        },
        "en": {
            "Sport": "Category:Sports", "Jedzenie": "Category:Foods",
            "Zwierzęta": "Category:Animals", "Dom": "Category:Home", "Praca": "Category:Occupations"
        },
        "de": {
            "Sport": "Kategorie:Sport", "Jedzenie": "Kategorie:Essen und Trinken",
            "Zwierzęta": "Kategorie:Tiere", "Dom": "Kategorie:Haushalt", "Praca": "Kategorie:Beruf"
        },
        "es": {
            "Sport": "Categoría:Deporte", "Jedzenie": "Categoría:Gastronomía",
            "Zwierzęta": "Categoría:Animales", "Dom": "Categoría:Hogar", "Praca": "Categoría:Ocupaciones"
        }
    }

    # Pobieramy nazwę kategorii dla danego języka (domyślnie EN jeśli brak)
    lang_map = CATEGORY_MAP.get(lang_code, CATEGORY_MAP['en'])
    cat_title = lang_map.get(category_name, f"Category:{category_name}")

    url = f"https://{lang_code}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": cat_title,
        "cmlimit": 150,  # Pobieramy więcej, żeby mieć z czego filtrować
        "format": "json",
        "origin": "*"
    }

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        members = data.get("query", {}).get("categorymembers", [])

        valid_words = []
        for m in members:
            word = m['title']
            # FILTRY JAKOŚCIOWE:
            # 1. Tylko pojedyncze słowa (brak spacji, myślników, nawiasów)
            if re.match(r"^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,12}$", word):
                # 2. Wykluczamy nazwy techniczne Wikipedii
                if ":" not in word:
                    valid_words.append(word.upper())

        return list(set(valid_words))
    except Exception as e:
        print(f"Błąd Wikipedia API: {e}")
        return []