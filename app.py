import streamlit as st

# Importy
from views.main_menu import show_main_menu, open_random_generator_window
from views.crossword_view import show_crossword_view
from views.sessions_view import show_sessions_view
from utils.export_code_manager import decode_crossword

st.set_page_config(page_title="krzyżGŁówkuj", layout="wide", page_icon="🧩")

incoming_data = st.query_params.get("data")
incoming_name = st.query_params.get("name")

if incoming_data:
    if st.session_state.get('current_view') != 'student_mode':
        decoded = decode_crossword(incoming_data)
        if decoded:
            st.session_state.crossword_data = decoded
            st.session_state.current_view = 'student_mode'

            if incoming_name:
                st.session_state.student_session_name = incoming_name
            else:
                st.session_state.student_session_name = "Zadanie Domowe"

            if 'student_name' in st.session_state:
                del st.session_state['student_name']

            st.rerun()
        else:
            st.error("Błąd kodu.")
            st.stop()

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main_menu'

if st.session_state.current_view == 'student_mode' and 'student_name' not in st.session_state:

    st.title("Witaj w Krzyżówce!")
    st.info(f"Sesja: {st.session_state.get('student_session_name', 'Zadanie')}")

    with st.form("student_login"):
        name_input = st.text_input("Podaj swoje imię lub nick:")
        if st.form_submit_button("Rozpocznij Rozwiązywanie"):
            if name_input.strip():
                st.session_state.student_name = name_input.strip()
                st.rerun()
            else:
                st.error("Musisz podać imię!")

elif st.session_state.current_view == 'student_mode':
    session_name = st.session_state.get('student_session_name', 'Krzyżówka')
    student_name = st.session_state.get('student_name', 'Uczeń')

    show_crossword_view(student_mode=True, session_name=session_name, student_name=student_name)

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
            if st.button("Szybka Gra", use_container_width=True):
                open_random_generator_window()
            st.markdown("---")

        if st.button("Sesje", use_container_width=True):
            st.session_state.current_view = 'sessions'

        st.markdown("---")
        if st.button("Statystyki", use_container_width=True):
            st.session_state.current_view = 'stats'

    with main_col:
        if st.session_state.current_view == 'main_menu':
            show_main_menu()
        elif st.session_state.current_view == 'crossword':
            show_crossword_view(student_mode=False)
        elif st.session_state.current_view == 'sessions':
            show_sessions_view()
        elif st.session_state.current_view == 'stats':
            st.header("Statystyki")