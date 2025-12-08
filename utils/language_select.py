# python
import streamlit as st
from typing import Dict, List

LANGUAGE_CONFIG: Dict[str, Dict[str, List[str]]] = {
    "Polski": {"code": "pl", "special_chars": ["Ą", "Ć", "Ę", "Ł", "Ń", "Ó", "Ś", "Ź", "Ż"]},
    "Angielski": {"code": "en", "special_chars": []},
    "Niemiecki": {"code": "de", "special_chars": ["Ä", "Ö", "Ü", "ß"]},
    "Hiszpański": {"code": "es", "special_chars": ["Ñ", "Á", "É", "Í", "Ó", "Ú", "Ü", "¡", "¿"]},
    "Francuski": {"code": "fr", "special_chars": ["À", "Â", "Ç", "É", "È", "Ê", "Ë", "Î", "Ï", "Ô", "Û", "Ù"]},
}

# Keys used in session_state (stored values)
SS_KEYS = {
    "src_name": "lang_src_name",
    "tgt_name": "lang_tgt_name",
    "src_code": "source_lang_code",
    "tgt_code": "target_lang_code",
    "tgt_chars": "target_special_chars",
}

# Widget keys (separate from stored session keys to avoid Streamlit API conflicts)
WIDGET_KEYS = {
    "src_name": "lang_src_widget",
    "tgt_name": "lang_tgt_widget",
}


def _init_defaults():
    """Ensure stored and widget session keys exist with safe defaults.

    Important:
    - We may set widget-owned session keys BEFORE creating the widget so Streamlit
      will use them as initial values. We must not modify widget keys after the
      corresponding widget is instantiated in the same run.
    - Stored keys (SS_KEYS) hold the authoritative values used by the app logic.
    """
    # Stored name defaults
    if SS_KEYS["src_name"] not in st.session_state:
        st.session_state[SS_KEYS["src_name"]] = "Polski"
    if SS_KEYS["tgt_name"] not in st.session_state:
        st.session_state[SS_KEYS["tgt_name"]] = "Angielski"

    # Stored derived defaults (codes and special chars)
    if SS_KEYS["src_code"] not in st.session_state:
        st.session_state[SS_KEYS["src_code"]] = LANGUAGE_CONFIG[st.session_state[SS_KEYS["src_name"]]]["code"]
    if SS_KEYS["tgt_code"] not in st.session_state:
        st.session_state[SS_KEYS["tgt_code"]] = LANGUAGE_CONFIG[st.session_state[SS_KEYS["tgt_name"]]]["code"]
    if SS_KEYS["tgt_chars"] not in st.session_state:
        st.session_state[SS_KEYS["tgt_chars"]] = LANGUAGE_CONFIG[st.session_state[SS_KEYS["tgt_name"]]]["special_chars"]

    # Initialize widget keys to reflect stored names, but only if widget keys are not present.
    # This sets the initial selection for selectboxes when they are created.
    if WIDGET_KEYS["src_name"] not in st.session_state:
        st.session_state[WIDGET_KEYS["src_name"]] = st.session_state[SS_KEYS["src_name"]]
    if WIDGET_KEYS["tgt_name"] not in st.session_state:
        st.session_state[WIDGET_KEYS["tgt_name"]] = st.session_state[SS_KEYS["tgt_name"]]


def apply_language_selection(src_name: str, tgt_name: str):
    """Apply derived language values (codes and special chars) to session state.

    We copy the widget-chosen names into the stored keys (SS_KEYS) and update
    derived values. We avoid modifying widget-owned keys here.
    """
    # Prevent applying identical languages (optional: allow but warn)
    if src_name == tgt_name:
        st.warning("Source and target language are the same. Consider choosing different languages.")

    # Validate names
    if src_name not in LANGUAGE_CONFIG or tgt_name not in LANGUAGE_CONFIG:
        st.error("Nieznany język - operacja przerwana.")
        return

    src = LANGUAGE_CONFIG[src_name]
    tgt = LANGUAGE_CONFIG[tgt_name]

    # Update stored values (safe; widget keys are separate)
    st.session_state[SS_KEYS["src_name"]] = src_name
    st.session_state[SS_KEYS["tgt_name"]] = tgt_name
    st.session_state[SS_KEYS["src_code"]] = src["code"]
    st.session_state[SS_KEYS["tgt_code"]] = tgt["code"]
    st.session_state[SS_KEYS["tgt_chars"]] = tgt["special_chars"]


def build_special_char_keyboard(special_chars: List[str], prefix_key: str = ""):
    if not special_chars:
        st.markdown(r"\*No special characters for this language.")
        return
    max_cols = 10
    # split into rows of up to max_cols
    rows = [special_chars[i : i + max_cols] for i in range(0, len(special_chars), max_cols)]
    for row_idx, row in enumerate(rows):
        cols = st.columns(len(row))
        for i, ch in enumerate(row):
            key = f"spec_{prefix_key}_{row_idx}_{i}"
            cols[i].button(ch, key=key)


def run_test_module():
    st.title("Test Modułu: KAN-15 (Wybór Języka)")
    st.markdown("To jest izolowane środowisko testowe. Tutaj sprawdzamy logikę wyboru języka przed wdrożeniem do głównej aplikacji.")

    _init_defaults()

    lang_names = list(LANGUAGE_CONFIG.keys())

    # Use a sidebar form so changes are applied explicitly
    with st.sidebar.form("lang_config_form"):
        st.header("Konfiguracja Językowa")
        # Use widget keys (separate from stored keys); on submit we copy to stored keys
        st.selectbox("Język podpowiedzi (Pytania)", lang_names, key=WIDGET_KEYS["src_name"])
        st.selectbox("Język nauki (Hasła)", lang_names, key=WIDGET_KEYS["tgt_name"])
        apply = st.form_submit_button("Apply")
        if apply:
            # Read the widget values and apply to stored keys
            src_sel = st.session_state[WIDGET_KEYS["src_name"]]
            tgt_sel = st.session_state[WIDGET_KEYS["tgt_name"]]
            apply_language_selection(src_sel, tgt_sel)
            st.success("Ustawienia zaktualizowane!")

    # Debug / status view
    st.divider()
    st.subheader("Co widzi system?")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Język Źródłowy:** {st.session_state[SS_KEYS['src_name']]}")
        st.write(f"Kod ISO: `{st.session_state[SS_KEYS['src_code']]}`")
        st.caption("W tym języku będą wyświetlane pytania.")
    with col2:
        st.success(f"**Język Docelowy:** {st.session_state[SS_KEYS['tgt_name']]}")
        st.write(f"Kod ISO: `{st.session_state[SS_KEYS['tgt_code']]}`")
        st.caption("W tym języku użytkownik musi wpisać hasło.")

    st.divider()
    st.subheader("⌨️ Generowanie klawiatury (Symulacja)")
    build_special_char_keyboard(st.session_state[SS_KEYS["tgt_chars"]], prefix_key=st.session_state[SS_KEYS["tgt_code"]])

    st.divider()
    st.subheader("Test dynamicznych etykiet")
    with st.form("test_form"):
        st.text_input(f"Wpisz słowo po: {st.session_state[SS_KEYS['tgt_name']].upper()}")
        st.text_input(f"Wpisz podpowiedź po: {st.session_state[SS_KEYS['src_name']].upper()}")
        st.form_submit_button("Testuj przycisk")


def render_language_selector():
    """Render a compact language selection widget in the sidebar.

    - Uses widget keys (separate from stored keys) so Streamlit won't raise when we
      update stored values on submit.
    - Copies widget selections into stored keys when the user submits the form.
    """
    _init_defaults()

    lang_names = list(LANGUAGE_CONFIG.keys())

    with st.sidebar.form("lang_config_form"):
        st.header("Ustawienia Języka")
        st.selectbox("Język podpowiedzi (Pytania)", lang_names, key=WIDGET_KEYS["src_name"])
        st.selectbox("Język nauki (Hasła)", lang_names, key=WIDGET_KEYS["tgt_name"])
        submit = st.form_submit_button("Zastosuj język")
        if submit:
            src = st.session_state[WIDGET_KEYS["src_name"]]
            tgt = st.session_state[WIDGET_KEYS["tgt_name"]]
            apply_language_selection(src, tgt)
            st.success("Języki zaktualizowane!")


if __name__ == "__main__":
    run_test_module()
