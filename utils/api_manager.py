# utils/api_manager.py
import requests


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