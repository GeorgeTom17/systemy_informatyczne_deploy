import streamlit as st
import json
import os
from utils.data_manager import save_word, load_words, get_all_sets, create_set, import_file_to_db, DATA_DIR, update_set_content
from utils.export_code_manager import decode_crossword
from utils.language_select import render_language_selector
# Importujemy naszego nowego dostawcę słów
from utils.random_provider import fetch_random_words
import pandas as pd
from utils.db_supabase import (
    get_all_sets_from_db,
    create_set_in_db,
    load_words_from_db,
    save_word_to_db,
    update_set_content_in_db,
    get_set_metadata
)
from utils.api_manager import get_complex_suggestions
from utils.api_manager import translate_text, fetch_words_for_category, get_automated_clue
import random


@st.dialog("Generator Losowej Krzyżówki")
def open_random_generator_window():
    st.write("Wybierz kategorię, a ja przygotuję unikalny zestaw do nauki!")

    LANG_MAP = {"Polski": "pl", "Angielski": "en", "Niemiecki": "de", "Hiszpański": "es", "Francuski": "fr"}
    CATEGORIES = {
        "Zwierzęta": "animals",
        "Jedzenie": "food",
        "Podróże": "travel",
        "Technologia": "technology",
        "Przyroda": "nature",
        "Sport": "sport",
        "Zdrowie": "health"
    }

    c1, c2 = st.columns(2)
    with c1:
        src_lang = st.selectbox("Język haseł (do wpisania)", list(LANG_MAP.keys()), index=1)
    with c2:
        tgt_lang = st.selectbox("Język podpowiedzi", list(LANG_MAP.keys()), index=0)

    selected_category = st.selectbox("Wybierz kategorię tematyczną:", list(CATEGORIES.keys()))
    limit = st.slider("Liczba słów w krzyżówce", 5, 15, 8)

    st.markdown("---")

    if st.button("Generuj i Graj", type="primary", use_container_width=True):
        src_code = LANG_MAP[src_lang]
        tgt_code = LANG_MAP[tgt_lang]
        category_en = CATEGORIES[selected_category]

        with st.spinner("Przeszukuję bazę wiedzy i buduję definicje..."):
            # 1. Pobieramy dużą pulę słów po angielsku dla kategorii
            raw_en_words = fetch_words_for_category(category_en, limit=40)

            if not raw_en_words:
                st.error("Błąd bazy danych słów. Spróbuj później.")
                return

            # 2. Losujemy podzbiór słów
            chosen_en_words = random.sample(raw_en_words, min(len(raw_en_words), limit))

            words_data = []
            progress_bar = st.progress(0)

            for i, en_word in enumerate(chosen_en_words):
                # Tłumaczymy słowo na język haseł (np. en -> es)
                word_in_src = translate_text(en_word, 'en', src_code).upper()

                # Generujemy definicję (most angielski -> tgt_code)
                clue = get_automated_clue(word_in_src, src_code, tgt_code)

                words_data.append({"word": word_in_src, "clue": clue})
                progress_bar.progress((i + 1) / len(chosen_en_words))

            if words_data:
                # Zapisujemy do pliku tymczasowego dla sesji
                target_filename = "random_generated"
                file_path = os.path.join(DATA_DIR, f"{target_filename}.json")
                os.makedirs(DATA_DIR, exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(words_data, f, indent=4, ensure_ascii=False)

                st.session_state.active_set = target_filename
                st.session_state.current_view = 'crossword'
                if 'crossword_data' in st.session_state:
                    del st.session_state['crossword_data']
                st.rerun()


def show_main_menu():
    # --- Sidebar: Wybór zestawu ---
    LANG_MAP = {
        "Polski": "pl",
        "Angielski": "en",
        "Niemiecki": "de",
        "Francuski": "fr",
        "Hiszpański": "es",
        "Włoski": "it"
    }
    lang_names = list(LANG_MAP.keys())
    lang_codes = list(LANG_MAP.values())
    with st.sidebar:
        st.header("Zarządzanie Zestawami")

        # Tworzenie nowego zestawu w DB
        new_set = st.text_input("Nowy zestaw:")
        if st.button("Utwórz zestaw"):
            if new_set:
                if create_set_in_db(new_set):
                    st.success(f"Utworzono {new_set}")
                    st.rerun()

        st.divider()

        # 2. Wgrywanie pliku (NOWA LOKALIZACJA)
        st.subheader("Wgraj plik")
        uploaded_file = st.file_uploader(
            "Wybierz plik (JSON, CSV, XLSX, TXT)",
            type=["json", "csv", "xlsx", "txt"],
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            # Zabezpieczenie przed wielokrotnym wgrywaniem
            if 'last_uploaded' not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
                with st.spinner("Importowanie do bazy danych..."):
                    success, message = import_file_to_db(uploaded_file)

                    if success:
                        st.session_state.last_uploaded = uploaded_file.name
                        # Automatycznie wybieramy nowo wgrany zestaw
                        new_name = os.path.splitext(uploaded_file.name)[0]
                        st.session_state.active_set = new_name
                        st.toast(message, icon="✅")
                        st.rerun()
                    else:
                        st.error(message)

        st.divider()

        sets = get_all_sets_from_db()
        if sets:
            current_set = st.selectbox("Wybierz zestaw do edycji:", sets)
        else:
            st.warning("Brak zestawów w bazie.")
            current_set = None

    if current_set:

        if 'last_set' not in st.session_state or st.session_state.last_set != current_set:
            words_data = load_words_from_db(current_set)
            st.session_state.table_data = words_data if words_data else []
            st.session_state.last_set = current_set

        st.header(f"Edytujesz zestaw: {current_set.upper()}")
        st.subheader("Podgląd zawartości")
        set_meta = get_set_metadata(current_set)
        db_source = set_meta.get('source_lang', 'pl')
        db_target = set_meta.get('target_lang', 'en')
        try:
            source_index = lang_codes.index(db_source)
        except ValueError:
            source_index = 0

        try:
            target_index = lang_codes.index(db_target)
        except ValueError:
            target_index = 1  # Domyślnie Angielski
        words_data = load_words_from_db(current_set)
        df = pd.DataFrame(words_data)

        if df.empty:
            df = pd.DataFrame(columns=["word", "clue"])



        st.subheader("Konfiguracja Językowa")
        with st.container(border=True):
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                src_lang_name = st.selectbox(
                    "Słowa w języku:",
                    options=lang_names,
                    index=source_index,
                    key=f"src_sel_{current_set}"
                )
            with col_l2:
                tgt_lang_name = st.selectbox(
                    "Definicje w języku:",
                    options=lang_names,
                    index=target_index,
                    key=f"tgt_sel_{current_set}"
                )
            # --- TUTAJ DODAJEMY MAPOWANIE NA KODY ISO ---
            source_lang_code = LANG_MAP[src_lang_name]
            target_lang_code = LANG_MAP[tgt_lang_name]
            # --------------------------------------------

            st.caption(
                f"Kierunek nauki: **{src_lang_name}** ({source_lang_code}) ➡️ **{tgt_lang_name}** ({target_lang_code})")

        st.divider()

        with st.expander("Asystent Definicji", expanded=False):
            word_to_check = st.text_input("Wpisz słowo z tabeli:", placeholder="np. Jabłko")

            if word_to_check:
                with st.spinner("Generuję definicje przez most angielski..."):
                    # Używamy naszych kodów source_lang_code i target_lang_code
                    results = get_complex_suggestions(word_to_check, source_lang_code, target_lang_code)

                if results:
                    st.write(f"Sugerowane definicje w języku **{tgt_lang_name}**:")
                    for i, res in enumerate(results):
                        col_text, col_btn = st.columns([4, 1])

                        with col_text:
                            label = res['pos']  # np. noun, verb
                            st.markdown(f"**[{label}]** {res['text']}")

                        with col_btn:
                            # PRZYCISK DODAWANIA
                            if st.button("Dodaj", key=f"add_sug_{i}"):
                                # Dodajemy nowy wiersz do stanu sesji
                                new_row = {
                                    "word": word_to_check.upper(),
                                    "clue": res['text']
                                }
                                st.session_state.table_data.append(new_row)
                                success = update_set_content_in_db(
                                    current_set,
                                    st.session_state.table_data,
                                    source_lang_code,
                                    target_lang_code
                                )
                                if success:
                                    st.success("Dodano do tabeli!")
                                    st.rerun()  # Odświeżamy, by editor zobaczył nowy wiersz
                                else:
                                    st.error("Słowo zostało dodane lokalnie, ale wystąpił błąd zapisu w bazie.")
                else:
                    st.warning("Brak propozycji.")

        st.divider()
        st.info("Kliknij w komórkę, aby edytować. Zaznacz wiersz i naciśnij Delete, aby usunąć.")
        edited_df = st.data_editor(
            st.session_state.table_data,
            column_config={
                "word": st.column_config.TextColumn("Słowo", required=True),
                "clue": st.column_config.TextColumn("Podpowiedź / Definicja", required=True)
            },
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{current_set}",
            hide_index=True
        )

        col_save, col_info = st.columns([1, 4])
        with col_save:
            if st.button("Zapisz zmiany w tabeli", type="primary"):
                new_data = edited_df.to_dict('records')
                # Teraz source_lang_code i target_lang_code są już zdefiniowane!
                if update_set_content_in_db(current_set, new_data, source_lang_code, target_lang_code):
                    st.session_state.table_data = new_data  # Aktualizujemy stan lokalny
                    st.toast("Zestaw oraz języki zostały zaktualizowane!")
                else:
                    st.error("Wystąpił błąd podczas zapisu.")
        st.divider()