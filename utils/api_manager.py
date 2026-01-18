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