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
                                new_df = pd.DataFrame([new_row])
                                st.session_state.table_data = pd.concat([st.session_state.table_data, new_df],
                                                                        ignore_index=True)
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

        raw_words = load_words_from_db(current_set)

        # 2. Inicjalizacja table_data jako DataFrame - to zapobiegnie błędowi .empty
        if raw_words:
            st.session_state.table_data = pd.DataFrame(raw_words)[["word", "clue"]]
        else:
            # Tworzymy pusty DF z odpowiednimi kolumnami, jeśli zestaw jest nowy/pusty
            st.session_state.table_data = pd.DataFrame(columns=["word", "clue"])

        # 3. Teraz sprawdzenie .empty zadziała poprawnie

        current_lang = st.session_state.get('crossword_language', 'Polski')





        # 2. PANEL ANALITYCZNY AI (wyświetlany nad edytorem)
        # Obliczamy trudność na podstawie tego, co jest obecnie w sesji
        if not st.session_state.table_data.empty:
            # Wywołujemy ocenę całego zestawu
            # Konwertujemy dataframe na listę słowników dla modelu
            words_list = st.session_state.table_data.to_dict('records')
            set_difficulty = ai_engine.get_set_difficulty(words_list, current_lang)

            # Wyświetlenie metryki
            col_ai, col_info = st.columns([1, 3])
            with col_ai:
                st.metric("Trudność zestawu (AI)", set_difficulty)
            with col_info:
                st.caption("Model analizuje długość słów, unikalne znaki oraz definicje, "
                           "ucząc się na błędach uczniów zapisanych w bazie.")

        st.subheader(f"Edycja zestawu: {current_set}")
        # 3. TWÓJ EDYTOR
        metric_placeholder = st.empty()

        # 2. Wyświetlamy edytor (używamy table_data jako bazy)
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

        # 3. AKTUALIZACJA ANALIZY AI (na żywo na podstawie edited_df)
        if not edited_df.empty:
            words_list = edited_df.to_dict('records')
            # Pobieramy język z metadanych zestawu lub sesji
            lang_to_analyze = st.session_state.get('crossword_language', 'Polski')

            difficulty = ai_engine.get_set_difficulty(words_list, lang_to_analyze)

            # Wypełniamy placeholder na górze
            with metric_placeholder:
                col_ai, col_info = st.columns([1, 3])
                with col_ai:
                    st.metric("Trudność zestawu (AI)", difficulty)
                with col_info:
                    st.caption("Analiza na żywo: model ocenia słowa i definicje widoczne w tabeli.")

        # 4. Usunięto blok 'if not edited_df.equals... st.rerun()' - to on powodował błąd!

        col_save, col_delete, col_info_btn = st.columns([1, 1, 3])
        with col_save:
            if st.button("Zapisz zmiany w tabeli", type="primary"):
                # Przy zapisie bierzemy dane z edytora i synchronizujemy z sesją
                new_data_list = edited_df.to_dict('records')

                # Wyciągamy kody języków (musisz mieć je dostępne w tej części kodu)
                if update_set_content_in_db(current_set, new_data_list, source_lang_code, target_lang_code):
                    st.session_state.table_data = edited_df  # Synchronizacja stanu
                    st.toast("Zestaw został zapisany pomyślnie!")
                else:
                    st.error("Wystąpił błąd podczas zapisu do bazy.")
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