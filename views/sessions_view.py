import streamlit as st
from utils.session_manager import load_sessions
from utils.qr_manager import generate_qr_image
import urllib.parse
from utils.results_manager import get_results_for_session

APP_BASE_URL = "https://systemyinformatycznedeploy-3crdjb98tkhzrmwgfuccaz.streamlit.app"


def show_sessions_view():
    st.title("Twoje Sesje i Wyniki")

    sessions = load_sessions()

    if not sessions:
        st.warning("Nie utworzono jeszcze żadnych sesji.")
        return

    for session in sessions:
        s_name = session['name']

        with st.expander(f"{session['date']} | {s_name}"):

            tab_info, tab_results = st.tabs(["Kod i Link", "Wyniki Uczniów"])

            with tab_info:
                c1, c2 = st.columns([2, 1])
                with c1:
                    safe_name = urllib.parse.quote(s_name)
                    full_link = f"{APP_BASE_URL}/?data={session['raw_code']}&name={safe_name}"
                    st.code(full_link, language="text")
                with c2:
                    qr_img = generate_qr_image(full_link)
                    st.image(qr_img, width=150)

            with tab_results:
                results = get_results_for_session(s_name)

                if not results:
                    st.info("Brak wyników. Uczniowie jeszcze nie przesłali rozwiązań.")
                    if st.button("Odśwież wyniki", key=f"refresh_{session['id']}"):
                        st.rerun()
                else:
                    st.dataframe(
                        results,
                        column_config={
                            "student": "Uczeń",
                            "time": "Czas",
                            "submitted_at": "Godzina przesłania"
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    best_time = results[0]['time']
                    winner = results[0]['student']
                    st.success(f"Lider: **{winner}** z czasem **{best_time}**")