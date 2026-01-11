import streamlit as st
from views.main_menu import show_main_menu, open_random_generator_window
from views.crossword_view import show_crossword_view
from views.sessions_view import show_sessions_view
from utils.export_code_manager import decode_crossword
from views.ml_view import show_ml_view
from utils.db_supabase import test_supabase_connection, get_session_from_db

st.set_page_config(page_title="krzyżGŁówkuj", layout="wide", page_icon="🧩")

query_params = st.query_params
incoming_session_id = query_params.get("session_id")
incoming_data = query_params.get("data")
incoming_name = query_params.get("name")

if incoming_session_id:
    if st.session_state.get('current_view') != 'student_mode':
        with st.spinner("Pobieram dane sesji z bazy..."):
            session_data = get_session_from_db(incoming_session_id)
            if session_data:
                decoded = decode_crossword(session_data["raw_code"])
                if decoded:
                    st.session_state.crossword_data = decoded
                    st.session_state.session_name = session_data["name"]
                    st.session_state.active_session_id = incoming_session_id
                    st.session_state.current_view = 'student_mode'
                    if 'student_name' in st.session_state:
                        del st.session_state['student_name']
                    st.rerun()
            else:
                st.error("Nie znaleziono sesji w bazie danych.")
                st.stop()

elif incoming_data:
    if st.session_state.get('current_view') != 'student_mode':
        decoded = decode_crossword(incoming_data)
        if decoded:
            st.session_state.crossword_data = decoded
            st.session_state.current_view = 'student_mode'
            st.session_name = incoming_name if incoming_name else "Zadanie Domowe"

            if 'student_name' in st.session_state:
                del st.session_state['student_name']
            st.rerun()
        else:
            st.error("Błąd dekodowania kodu.")
            st.stop()

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main_menu'

if st.session_state.current_view == 'student_mode' and 'student_name' not in st.session_state:

    st.title("Witaj w Krzyżówce!")
    st.info(f"Sesja: {st.session_state.get('session_name', 'Zadanie')}")

    with st.form("student_login"):
        name_input = st.text_input("Podaj swoje imię lub nick:")
        if st.form_submit_button("Rozpocznij Rozwiązywanie"):
            if name_input.strip():
                st.session_state.student_name = name_input.strip()
                st.rerun()
            else:
                st.error("Musisz podać imię!")

elif st.session_state.current_view == 'student_mode':
    session_name = st.session_state.get('session_name', 'Krzyżówka')
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

        if st.button("Trening AI", use_container_width=True):
            st.session_state.current_view = 'ml_training'

        st.markdown("---")
        if st.button("Statystyki", use_container_width=True):
            st.session_state.current_view = 'stats'

        st.markdown("---")
        st.subheader("🛠️ Test Połączenia Supabase")
        if st.button("Uruchom test połączenia"):
            with st.spinner("Próbuję połączyć się z serwerem supabase..."):
                success, message = test_supabase_connection()
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error("❌ Połączenie nieudane")
                    st.code(message, language="text")

    with main_col:
        if st.session_state.current_view == 'main_menu':
            show_main_menu()
        elif st.session_state.current_view == 'crossword':
            show_crossword_view(student_mode=False)
        elif st.session_state.current_view == 'sessions':
            show_sessions_view()
        elif st.session_state.current_view == 'stats':
            st.header("Statystyki")
        elif st.session_state.current_view == 'ml_training':
            show_ml_view()