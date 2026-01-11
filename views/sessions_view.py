import streamlit as st
from utils.db_supabase import get_all_sessions_from_db, get_results_for_session_from_db
from utils.qr_manager import generate_qr_image
import urllib.parse

APP_BASE_URL = "https://systemyinformatycznedeploy-3crdjb98tkhzrmwgfuccaz.streamlit.app"


def show_sessions_view():
    st.title("Twoje Sesje i Wyniki")
    sessions = get_all_sessions_from_db()

    if not sessions:
        st.warning("Nie utworzono jeszcze żadnych sesji w bazie danych.")
        return

    for session in sessions:
        s_id = session['id']
        s_name = session['name']
        s_date = session['created_at'][:10]

        with st.expander(f"{s_date} | {s_name}"):
            tab_info, tab_results = st.tabs(["Kod i Link", "Wyniki Uczniów"])

            with tab_info:
                c1, c2 = st.columns([2, 1])
                with c1:
                    full_link = f"{APP_BASE_URL}/?session_id={s_id}"
                    st.write("**Link dla uczniów:**")
                    st.code(full_link, language="text")
                with c2:
                    qr_img = generate_qr_image(full_link)
                    st.image(qr_img, caption="Skanuj, aby grać", width=150)

            with tab_results:
                results = get_results_for_session_from_db(s_id)

                if not results:
                    st.info("Brak wyników. Uczniowie jeszcze nie przesłali rozwiązań.")
                    if st.button("Odśwież wyniki", key=f"refresh_{s_id}"):
                        st.rerun()
                else:
                    import pandas as pd
                    df = pd.DataFrame(results)

                    df = df.rename(columns={
                        "student_name": "Uczeń",
                        "time_taken": "Czas",
                        "hint_count": "Podpowiedzi",
                        "submitted_at": "Data przesłania"
                    })

                    df['Data przesłania'] = df['Data przesłania'].apply(lambda x: x.replace('T', ' ')[:16])

                    st.dataframe(
                        df,
                        hide_index=True,
                        use_container_width=True
                    )

                    best_time = results[0]['time_taken']
                    winner = results[0]['student_name']
                    st.success(f"Lider: **{winner}** z czasem **{best_time}**")