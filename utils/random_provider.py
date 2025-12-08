import requests
import random
from deep_translator import GoogleTranslator

LANG_CODES = {
    "Angielski": "en",
    "Niemiecki": "de",
    "Francuski": "fr",
    "Hiszpański": "es",
    "Włoski": "it",
    "Polski": "pl"
}

CATEGORY_KEYWORDS = {
    "Zwierzęta": "animal",
    "Jedzenie": "food",
    "Podróże": "travel",
    "Dom": "home",
    "Praca": "office",
    "Szkoła": "school",
    "Sport": "sports",
    "Ciało": "body"
}


def get_english_concepts(mode, category, limit=15):
    """
    Pobiera listę RZECZOWNIKÓW (nouns) powiązanych z tematem.
    """
    concepts = []

    try:
        if mode == "Top 100 najczęstszych słów":
            concepts = [
                "time", "year", "people", "way", "day", "man", "thing", "woman", "life", "child",
                "world", "school", "state", "family", "student", "group", "country", "problem",
                "hand", "part", "place", "case", "week", "company", "system", "program",
                "question", "work", "government", "number", "night", "point", "home", "water",
                "room", "mother", "area", "money", "story", "fact", "month", "right",
                "study", "book", "eye", "job", "word", "business", "issue", "side",
                "head", "house", "service", "friend", "father", "power", "hour", "game",
                "line", "end", "member", "law", "car", "city", "community", "name", "president",
                "team", "minute", "idea", "kid", "body", "information", "back", "parent",
                "face", "level", "office", "door", "health", "person", "art", "war",
                "history", "party", "result", "change", "morning", "reason", "research",
                "girl", "guy", "moment", "air", "teacher", "force", "education"
            ]
            random.shuffle(concepts)
            return concepts[:limit + 10]

        else:
            keyword = CATEGORY_KEYWORDS.get(category, "thing")
            url = f"https://api.datamuse.com/words?rel_jja={keyword}&topics={keyword}&md=p&max=100"

            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()

                for item in data:
                    word = item['word']
                    tags = item.get('tags', [])

                    if 'n' in tags:
                        if " " not in word and len(word) > 2:
                            concepts.append(word)

                        if len(concepts) >= limit + 10:
                            break

            random.shuffle(concepts)
            return concepts[:limit]

    except Exception as e:
        print(f"Błąd Datamuse API: {e}")
        return []


def translate_batch(words, target_lang_code):
    """
    Tłumaczy listę słów.
    """
    translator = GoogleTranslator(source='auto', target=target_lang_code)
    try:
        translated = translator.translate_batch(words)
        return translated
    except Exception as e:
        print(f"Błąd tłumaczenia: {e}")
        res = []
        for w in words:
            try:
                res.append(translator.translate(w))
            except:
                res.append(w)
        return res


def fetch_random_words(src_lang_name, tgt_lang_name, mode, category=None, limit=10):
    """
    Główna funkcja orkiestrująca.
    """
    src_code = LANG_CODES.get(src_lang_name, "en")
    tgt_code = LANG_CODES.get(tgt_lang_name, "pl")

    english_concepts = get_english_concepts(mode, category, limit * 2)

    if not english_concepts:
        return []

    if src_code == "en":
        words_src = english_concepts
    else:
        words_src = translate_batch(english_concepts, src_code)

    if tgt_code == "en":
        words_tgt = english_concepts
    else:
        words_tgt = translate_batch(english_concepts, tgt_code)

    final_data = []
    seen_clues = set()
    seen_words = set()

    safe_limit = min(len(words_src), len(words_tgt))

    for i in range(safe_limit):
        if len(final_data) >= limit:
            break

        word = words_src[i].upper().strip()
        clue = words_tgt[i].strip()

        if " " not in word and len(word) > 1:
            if word.lower() != clue.lower():
                if clue.lower() not in seen_clues and word not in seen_words:
                    final_data.append({
                        "word": word,
                        "clue": clue
                    })

                    seen_clues.add(clue.lower())
                    seen_words.add(word)

    return final_data