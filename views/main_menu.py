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
    get_set_metadata,
    create_empty_set_in_db,
    get_supabase_client,
    delete_set_from_db

)
from utils.api_manager import get_complex_suggestions
from utils.api_manager import translate_text, fetch_words_for_category, get_automated_clue, get_words_from_conceptnet, get_refined_clue, get_words_from_wikipedia
import random
from utils.ml_engine import ai_engine

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
        from datetime import datetime
        src_code = LANG_MAP[src_lang]
        tgt_code = LANG_MAP[tgt_lang]

        # Nazwa zestawu sugerująca dużą pulę
        new_set_name = f"Pakiet: {selected_category} ({datetime.now().strftime('%H:%M')})"

        with st.spinner(f"Szukam słówek dla kategorii {selected_category}..."):
            all_possible_words = get_words_from_wikipedia(selected_category, src_code)

            if not all_possible_words:
                st.error(
                    f"Wikipedia nie zwróciła żadnych słów dla kategorii '{selected_category}' w języku '{src_code}'.")
                st.info("Spróbuj zmienić kategorię lub język haseł.")
                st.stop()  # Zatrzymuje dalsze wykonywanie

            # Jeśli znaleźliśmy słowa, losujemy pulę
            chosen_words = random.sample(all_possible_words, min(len(all_possible_words), 45))
            st.write(f"Znaleziono {len(chosen_words)} słów. Rozpoczynam generowanie definicji...")

            set_id = create_empty_set_in_db(new_set_name, src_code, tgt_code)

            if set_id:
                to_insert = []  # Lista na wszystkie słowa
                progress_bar = st.progress(0)

                for i, word in enumerate(all_possible_words):
                    # Pobieramy definicję używając nowego 'description'
                    clue = get_refined_clue(word, src_code, tgt_code)

                    # DODAJEMY DO LISTY (nie nadpisujemy!)
                    to_insert.append({
                        "set_id": set_id,
                        "word": word.upper(),
                        "clue": clue
                    })

                    progress_bar.progress((i + 1) / len(all_possible_words))

                # ZAPISUJEMY CAŁĄ LISTĘ NA RAZ POZA PĘTLĄ
                if to_insert:
                    try:
                        supabase = get_supabase_client()
                        # Wstawiamy całą tablicę obiektów
                        result = supabase.table("words").insert(to_insert).execute()

                        if result.data:
                            st.success(f"Zapisano pomyślnie {len(result.data)} słów!")
                            st.session_state.active_set = new_set_name
                            st.session_state.current_view = 'crossword'
                            st.rerun()
                        else:
                            st.error("Baza danych nie zwróciła potwierdzenia zapisu.")
                    except Exception as e:
                        st.error(f"Błąd zapisu zbiorczego: {e}")


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

    if "table_df" not in st.session_state:
        st.session_state.table_df = pd.DataFrame(columns=["word", "clue"])

    if "last_loaded_set" not in st.session_state:
        st.session_state.last_loaded_set = None

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
            current_set = st.selectbox(
                "Wybierz zestaw do edycji:",
                sets,
                key="selected_set"
            )
        else:
            st.warning("Brak zestawów w bazie.")
            current_set = None

    if current_set and st.session_state.last_loaded_set != current_set:
        data = load_words_from_db(current_set) or []
        st.session_state.table_df = pd.DataFrame(
            data,
            columns=["word", "clue"]
        )
        st.session_state.last_loaded_set = current_set


        st.header(f"Edytujesz zestaw: {current_set.upper()}")
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
                                    word_to_check = ""
                                    st.rerun()  # Odświeżamy, by editor zobaczył nowy wiersz
                                else:
                                    st.error("Słowo zostało dodane lokalnie, ale wystąpił błąd zapisu w bazie.")
                else:
                    st.warning("Brak propozycji.")

        st.divider()
        st.info("Kliknij w komórkę, aby edytować. Zaznacz wiersz i naciśnij Delete, aby usunąć.")

        edited_df = st.data_editor(
            st.session_state.table_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{current_set}"
        )

        col_save, col_delete, col_info = st.columns([1, 1, 3])
        with col_save:
            if st.button("Zapisz zmiany w tabeli", type="primary"):
                clean_df = edited_df.dropna(subset=["word", "clue"])

                new_data = [
                    {
                        "word": str(row["word"]).strip().upper(),
                        "clue": str(row["clue"]).strip()
                    }
                    for _, row in clean_df.iterrows()
                    if row["word"] and row["clue"]
                ]

                success = update_set_content_in_db(
                    current_set,
                    new_data,
                    source_lang_code,
                    target_lang_code
                )

                if success:
                    st.session_state.table_df = clean_df
                    st.success("Zapisano zmiany w bazie danych.")
                    st.rerun()
                else:
                    st.error("Błąd zapisu do bazy danych.")
        with col_delete:
            # Dodajemy przycisk usuwania z potwierdzeniem
            if st.button("🗑️ Usuń zestaw", type="secondary", use_container_width=True):
                if delete_set_from_db(current_set):
                    st.toast(f"Zestaw '{current_set}' został usunięty.")
                    # Czyścimy stan i odświeżamy
                    st.session_state.selected_set_name = None
                    if 'table_data' in st.session_state:
                        del st.session_state.table_data
                    st.rerun()