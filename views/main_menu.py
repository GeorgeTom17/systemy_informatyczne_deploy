import streamlit as st
import json
import os
from utils.data_manager import save_word, load_words, get_all_sets, create_set, save_uploaded_set, DATA_DIR
from utils.export_code_manager import decode_crossword
from utils.language_select import render_language_selector
# Importujemy naszego nowego dostawcę słów
from utils.random_provider import fetch_random_words


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
    st.title("Zarządzanie Zestawami")


    st.sidebar.header("Twoje Zestawy")

    st.sidebar.subheader("➕ Nowy zestaw")
    new_set_name = st.sidebar.text_input("Nazwa:", label_visibility="collapsed", placeholder="Nazwa np. Historia...")

    if st.sidebar.button("Utwórz puste"):
        if new_set_name:
            create_set(new_set_name)
            st.session_state.active_set = new_set_name
            st.success(f"Utworzono: {new_set_name}!")
            st.rerun()

    st.sidebar.subheader("📂 Wgraj gotowy plik")
    uploaded_file = st.sidebar.file_uploader("Wybierz plik", type=["json", "csv", "xlsx", "txt"],
                                             label_visibility="collapsed")

    if uploaded_file is not None:
        if 'last_uploaded' not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:

            success, message = save_uploaded_set(uploaded_file)

            if success:
                st.session_state.last_uploaded = uploaded_file.name

                new_name = uploaded_file.name.replace(".json", "")
                st.session_state.active_set = new_name

                st.session_state.current_view = 'crossword'
                st.rerun()
            else:
                st.sidebar.error(message)

    st.sidebar.markdown("---")

    available_sets = get_all_sets()

    if not available_sets:
        st.info("Brak zestawów. Wgraj lub stwórz coś w pasku bocznym! 👈")
        current_set = "default"
    else:
        if 'active_set' in st.session_state and st.session_state.active_set in available_sets:
            index_to_select = available_sets.index(st.session_state.active_set)
        else:
            index_to_select = 0

        current_set = st.sidebar.selectbox(
            "Wybierz zestaw do edycji:",
            available_sets,
            index=index_to_select
        )
        st.session_state.active_set = current_set

    # --- Główna część ---
    st.header(f"Edytujesz zestaw: {current_set.upper()}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dodaj hasło ręcznie")
        with st.form("add_word_form", clear_on_submit=True):
            new_word = st.text_input("Słowo")
            new_clue = st.text_input("Podpowiedź")
            submitted = st.form_submit_button("Zapisz hasło")

            if submitted:
                if new_word and new_clue:
                    save_word(new_word, new_clue, current_set)
                    st.success(f"Dodano do '{current_set}'")
                    st.rerun()
                else:
                    st.error("Wypełnij oba pola.")

    with col2:
        st.subheader("Podgląd zawartości")
        words = load_words(current_set)
        if words:
            st.dataframe(words, hide_index=True, use_container_width=True)
            st.caption(f"Liczba haseł: {len(words)}")
        else:
            st.info("Pusto. Dodaj coś!")

    st.markdown("---")
    st.subheader("Import Krzyżówki z Kodu")
    st.caption("Masz wygenerowany kod (ciąg znaków)? Wklej go tutaj, aby odtworzyć układ.")

    with st.expander("Kliknij, aby rozwinąć panel importu"):
        import_code = st.text_area(
            "Wklej kod eksportu tutaj:",
            height=100,
            placeholder="np. eNpKy8xLzVEoyc9Lzy8oiQbSChkGqSkKpZm5qUWKBUWZ..."
        )

        if st.button("Wczytaj Krzyżówkę"):
            if not import_code.strip():
                st.warning("⚠️ Pole kodu jest puste.")
            else:
                decoded_data = decode_crossword(import_code)
                if decoded_data:
                    st.session_state.crossword_data = decoded_data
                    st.session_state.last_set = "Imported"
                    st.success("✅ Pomyślnie wczytano! Przenoszenie...")
                    st.session_state.current_view = 'crossword'
                    st.rerun()