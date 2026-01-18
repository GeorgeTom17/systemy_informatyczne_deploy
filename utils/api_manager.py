# utils/api_manager.py
import requests
import re
import streamlit as st

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
    """Pobiera definicję, czyści ją i tłumaczy."""
    wiki_url = f"https://{src_lang}.wiktionary.org/api/rest_v1/page/summary/{word.lower()}"
    definition = None

    try:
        res = requests.get(wiki_url, timeout=5)
        if res.status_code == 200:
            definition = res.json().get("extract")
    except:
        pass

    if not definition:
        # Próba z Wikipedii, jeśli Wikisłownik zawiedzie
        wiki_url = f"https://{src_lang}.wikipedia.org/api/rest_v1/page/summary/{word.lower()}"
        try:
            res = requests.get(wiki_url, timeout=5)
            if res.status_code == 200:
                definition = res.json().get("extract")
        except:
            pass

    if definition:
        # 1. Usuwamy hasło z początku (np. "Pies – gatunek...")
        # Szukamy myślnika, kropki lub nawiasu po słowie
        clean_def = re.sub(rf"^{word}\b.*?[—\-\.]\s*", "", definition, flags=re.IGNORECASE)

        # 2. Jeśli po czyszczeniu słowo nadal tam jest, zastępujemy je luką
        clean_def = re.sub(word, "________", clean_def, flags=re.IGNORECASE)

        # 3. Tłumaczymy na język docelowy
        final_clue = translate_text(clean_def, src_lang, tgt_lang)

        # Jeśli definicja jest zbyt krótka lub identyczna ze słowem po tłumaczeniu
        if len(final_clue) < 5 or final_clue.strip().upper() == word.upper():
            return f"Pytanie o: {word}"  # Lepiej dać prosty opis niż samo słowo

        return final_clue.capitalize()

    # Fallback: Jeśli wszystko zawiedzie, generujemy opisową podpowiedź
    translation = translate_text(word, src_lang, tgt_lang)
    return f"Przetłumacz na {tgt_lang}: {word}" if src_lang != tgt_lang else f"Słowo powiązane z tematem: {word}"


def get_words_from_wikipedia(category_name, lang_code, limit=50):
    CATEGORY_MAP = {
        "pl": {"Sport": "Kategoria:Dyscypliny_sportowe", "Jedzenie": "Kategoria:Potrawy",
               "Zwierzęta": "Kategoria:Zwierzęta", "Dom": "Kategoria:Wyposażenie_domu", "Praca": "Kategoria:Zawody",
               "Podróże": "Kategoria:Turystyka"},
        "en": {"Sport": "Category:Sports", "Jedzenie": "Category:Foods", "Zwierzęta": "Category:Animals",
               "Dom": "Category:Household_items", "Praca": "Category:Occupations", "Podróże": "Category:Travel"},
        "de": {"Sport": "Kategorie:Sportart", "Jedzenie": "Kategorie:Essen_und_Trinken", "Zwierzęta": "Kategorie:Tiere",
               "Dom": "Kategorie:Haushalt", "Praca": "Kategorie:Beruf", "Podróże": "Kategorie:Tourismus"},
        "es": {"Sport": "Categoría:Deportes", "Jedzenie": "Categoría:Platos_típicos", "Zwierzęta": "Categoría:Animales",
               "Dom": "Categoría:Utensilios_domésticos", "Praca": "Categoría:Ocupaciones",
               "Podróże": "Categoría:Turismo"},
        "fr": {"Sport": "Catégorie:Sport", "Jedzenie": "Catégorie:Aliment", "Zwierzęta": "Catégorie:Animal",
               "Dom": "Catégorie:Objet_domestique", "Praca": "Catégorie:Métier", "Podróże": "Catégorie:Tourisme"}
    }

    lang_map = CATEGORY_MAP.get(lang_code, CATEGORY_MAP['en'])
    cat_title = lang_map.get(category_name, f"Category:{category_name}")
    url = f"https://{lang_code}.wikipedia.org/w/api.php"

    headers = {"User-Agent": "KrzyzowkaEduApp/1.0 (kontakt@twoja_domena.com)"}

    # Lista na znalezione słowa
    collected_words = []
    # Lista kategorii do sprawdzenia (zaczynamy od głównej)
    categories_to_scan = [cat_title]
    # Zbiór sprawdzonych kategorii (żeby nie wpadać w pętle)
    seen_categories = set()

    try:
        # Skanujemy dopóki nie mamy limitu lub nie skończą się kategorie (max 10 kategorii, by nie trwało wiecznie)
        while len(collected_words) < limit and categories_to_scan and len(seen_categories) < 15:
            current_cat = categories_to_scan.pop(0)
            if current_cat in seen_categories: continue
            seen_categories.add(current_cat)

            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": current_cat,
                "cmlimit": 150,
                "cmtype": "page|subcat",  # Pobieramy strony ORAZ podkategorie
                "format": "json",
                "origin": "*"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            members = data.get("query", {}).get("categorymembers", [])

            for m in members:
                title = m['title']
                # Jeśli to podkategoria (ns 14), dodaj do listy skanowania
                if m['ns'] == 14:
                    if title not in seen_categories:
                        categories_to_scan.append(title)

                # Jeśli to strona (ns 0), sprawdź czy pasuje do krzyżówki
                elif m['ns'] == 0:
                    # FILTR: 3-12 liter, bez spacji, bez cyfr
                    if re.match(r"^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,12}$", title):
                        if ":" not in title:
                            collected_words.append(title.upper())

            # Usuwamy duplikaty na bieżąco
            collected_words = list(set(collected_words))

        # Losujemy finalną pulę, jeśli mamy ich więcej niż limit
        if len(collected_words) > limit:
            return random.sample(collected_words, limit)

        return collected_words

    except Exception as e:
        st.error(f"Błąd podczas głębokiego skanowania: {e}")
        return collected_words