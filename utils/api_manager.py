# utils/api_manager.py
import requests


def get_word_suggestions(word):
    """Pobiera krótkie definicje z polskiego Wikisłownika."""
    if not word or len(word) < 2:
        return []

    # API MediaWiki dla polskiego Wiktionary
    url = "https://pl.wiktionary.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": word.lower(),
        "format": "json"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        suggestions = []
        for page_id in pages:
            extract = pages[page_id].get("extract", "")
            if extract:
                # Wiktionary podaje definicje po numerach (np. 1.1, 1.2)
                # Wyciągamy pierwsze kilka krótkich zdań
                lines = [line.strip() for line in extract.split('\n') if line.strip()]
                # Szukamy linii zaczynających się od znaczeń (np. "znaczenia: (1.1)...")
                for line in lines:
                    if "(1.1)" in line or "(1.2)" in line:
                        clean_line = line.replace("(1.1)", "").replace("(1.2)", "").strip()
                        if len(clean_line) > 5:
                            suggestions.append(clean_line[:100] + "...")

        return suggestions[:3]  # Zwracamy max 3 propozycje
    except:
        return []