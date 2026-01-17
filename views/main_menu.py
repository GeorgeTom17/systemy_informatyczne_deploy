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
    update_set_content_in_db
)


@st.dialog("🎲 Generator Losowej Krzyżówki")
def open_random_generator_window():
    st.write("Wybierz parametry, a my stworzymy dla Ciebie unikalną krzyżówkę!")

    c1, c2 = st.columns(2)
    with c1:
        src_lang = st.selectbox("Język słów (Baza)", ["Angielski", "Niemiecki", "Francuski", "Hiszpański"])
    with c2:
        tgt_lang = st.selectbox("Język podpowiedzi", ["Polski", "Angielski"])

    st.markdown("---")

    mode = st.radio("Tryb generowania:", ["Kategorie tematyczne", "Top 100 najczęstszych słów"])

    selected_category = None
    if mode == "Kategorie tematyczne":
        selected_category = st.selectbox("Wybierz kategorię:", ["Zwierzęta", "Jedzenie", "Podróże", "Dom", "Praca"])

    limit = st.slider("Ile słów pobrać?", 5, 20, 10)

    st.markdown("---")

    if st.button("🚀 Generuj i Graj", type="primary", use_container_width=True):
        st.session_state.crossword_language = src_lang
        with st.spinner("Pobieram słowa i tłumaczę..."):
            words_data = fetch_random_words(src_lang, tgt_lang,
                                            "category" if mode == "Kategorie tematyczne" else "top100",
                                            selected_category, limit)

            if not words_data:
                st.error("Nie udało się pobrać słów. Spróbuj innej konfiguracji.")
            else:
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
    with st.sidebar:
        st.header("📂 Zarządzanie Zestawami")

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
        st.header(f"Edytujesz zestaw: {current_set.upper()}")
        st.subheader("Podgląd zawartości")
        words_data = load_words_from_db(current_set)
        df = pd.DataFrame(words_data)

        if df.empty:
            df = pd.DataFrame(columns=["word", "clue"])

        st.info("Kliknij w komórkę, aby edytować. Zaznacz wiersz i naciśnij Delete, aby usunąć.")

        edited_df = st.data_editor(
            df,
            column_config={
                "word": st.column_config.TextColumn(
                    "Słowo",
                    help="Hasło do krzyżówki",
                    max_chars=20,
                    required=True
                ),
                "clue": st.column_config.TextColumn(
                    "Podpowiedź / Definicja",
                    help="Opis wyświetlany graczowi",
                    required=True
                )
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
                if update_set_content_in_db(current_set, new_data):
                    st.toast("Zestaw został zaktualizowany!")
                else:
                    st.error("Wystąpił błąd podczas zapisu.")
        st.divider()