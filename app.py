import streamlit as st

# Importy
from views.main_menu import show_main_menu, open_random_generator_window
from views.crossword_view import show_crossword_view
from utils.export_code_manager import decode_crossword

st.set_page_config(
    page_title="krzyżGŁówkuj",
    layout="wide",
    page_icon="🧩"
)

# --- 0. DIAGNOSTYKA (Tylko do testów, usuń to później) ---
# Sprawdzamy co widzi aplikacja w linku
qp = st.query_params
if "data" in qp:
    # Wyświetlamy mały komunikat na górze, że wykryto kod
    # Jeśli to widzisz na telefonie, to znaczy, że link działa, a problem jest w decode()
    st.toast("📲 Wykryto tryb ucznia! Przetwarzanie...", icon="🚀")
# ---------------------------------------------------------

# --- 1. LOGIKA ROUTINGU (MÓZG APLIKACJI) ---

# Sprawdzamy parametr 'data' w URL
incoming_data = st.query_params.get("data")

# Jeśli jest kod w URL, a my nie jesteśmy jeszcze w trybie studenta -> Wchodzimy siłowo
if incoming_data:
    # Sprawdzamy, czy dane są już załadowane, żeby nie dekodować w kółko przy każdym kliknięciu
    # Ale jeśli widok to nie 'student_mode', to znaczy, że trzeba przeładować
    if st.session_state.get('current_view') != 'student_mode':

        decoded = decode_crossword(incoming_data)

        if decoded:
            st.session_state.crossword_data = decoded
            st.session_state.current_view = 'student_mode'
            # 🚨 KLUCZOWE: Rerun wymusza natychmiastowe przerysowanie ekranu z nowym widokiem
            st.rerun()
        else:
            st.error("❌ Błąd: Kod krzyżówki w linku jest uszkodzony.")
            st.stop()  # Zatrzymujemy dalsze ładowanie

# Inicjalizacja domyślnego widoku (tylko jeśli nie jesteśmy w trybie ucznia)
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main_menu'

# --- 2. WYŚWIETLANIE WIDOKÓW ---

if st.session_state.current_view == 'student_mode':
    # --- TRYB UCZNIA (CZYSTY) ---
    show_crossword_view(student_mode=True)

else:
    # --- TRYB NAUCZYCIELA (MENU) ---
    menu_col, main_col = st.columns([1, 4])

    with menu_col:
        st.title("🌟 Menu")

        if st.button("🏠 Główne", use_container_width=True):
            st.session_state.current_view = 'main_menu'
            st.rerun()

        st.markdown("---")

        if st.session_state.current_view != 'crossword':
            if st.button("🧩 Nowa krzyżówka", use_container_width=True):
                st.session_state.current_view = 'crossword'
                st.rerun()

            st.markdown("---")

            if st.button("🎲 Szybka Gra (Losowa)", type="primary", use_container_width=True):
                open_random_generator_window()

            st.markdown("---")

        if st.button("📊 Statystyki", use_container_width=True):
            st.session_state.current_view = 'stats'

    with main_col:
        if st.session_state.current_view == 'main_menu':
            show_main_menu()

        elif st.session_state.current_view == 'crossword':
            show_crossword_view(student_mode=False)

        elif st.session_state.current_view == 'stats':
            st.header("📊 Statystyki")
            st.info("Statystyki twoich gier pojawią się tutaj.")