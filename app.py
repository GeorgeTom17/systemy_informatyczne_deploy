import streamlit as st

from views.main_menu import show_main_menu, open_random_generator_window
from views.crossword_view import show_crossword_view

st.set_page_config(
    page_title="krzyżGŁówkuj",
    layout="wide",
    page_icon="🧩"
)

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main_menu'

menu_col, main_col = st.columns([1, 4])

with menu_col:
    st.title("🌟 Menu")

    if st.session_state.current_view != 'main_menu':

        if st.button("Główne", use_container_width=True):
            st.session_state.current_view = 'main_menu'
            st.rerun()

        st.markdown("---")

    if st.session_state.current_view != 'crossword':

        if st.button("Nowa krzyżówka (z zestawu)", use_container_width=True):
            st.session_state.current_view = 'crossword'
            st.rerun()

        st.markdown("---")

        if st.button("Szybka Gra (losowa)", use_container_width=True):
            open_random_generator_window()

        st.markdown("---")

    if st.button("Statystyki", use_container_width=True):
        st.session_state.current_view = 'stats'

with main_col:
    if st.session_state.current_view == 'main_menu':
        show_main_menu()

    elif st.session_state.current_view == 'crossword':
        show_crossword_view()

    elif st.session_state.current_view == 'stats':
        st.header("Statystyki")
        st.info("Tutaj w przyszłości pojawią się statystyki twoich gier!")
