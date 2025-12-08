import streamlit as st
from views.main_menu import show_main_menu, open_random_generator_window
from views.crossword_view import show_crossword_view
from utils.export_code_manager import decode_crossword

st.set_page_config(
    page_title="krzyżGŁówkuj",
    layout="wide")

qp = st.query_params
if "data" in qp:
    st.toast("📲 Wykryto tryb ucznia! Przetwarzanie...")
incoming_data = st.query_params.get("data")
if incoming_data:
    if st.session_state.get('current_view') != 'student_mode':

        decoded = decode_crossword(incoming_data)

        if decoded:
            st.session_state.crossword_data = decoded
            st.session_state.current_view = 'student_mode'
            st.rerun()
        else:
            st.error("Błąd: Kod krzyżówki w linku jest uszkodzony.")
            st.stop()

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main_menu'


if st.session_state.current_view == 'student_mode':
    show_crossword_view(student_mode=True)

else:
    menu_col, main_col = st.columns([1, 4])

    with menu_col:
        st.title("Menu")

        if st.button("Główne", use_container_width=True):
            st.session_state.current_view = 'main_menu'
            st.rerun()

        st.markdown("---")

        if st.session_state.current_view != 'crossword':
            if st.button("Nowa krzyżówka", use_container_width=True):
                st.session_state.current_view = 'crossword'
                st.rerun()

            st.markdown("---")

            if st.button("Szybka Gra (Losowa)", use_container_width=True):
                open_random_generator_window()

            st.markdown("---")

        if st.button("Statystyki", use_container_width=True):
            st.session_state.current_view = 'stats'

    with main_col:
        if st.session_state.current_view == 'main_menu':
            show_main_menu()

        elif st.session_state.current_view == 'crossword':
            show_crossword_view(student_mode=False)

        elif st.session_state.current_view == 'stats':
            st.header("📊 Statystyki")
            st.info("Statystyki twoich gier pojawią się tutaj.")