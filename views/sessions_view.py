import streamlit as st
import pandas as pd
import time
from utils.db_supabase import (
    get_all_sessions_from_db,
    get_results_for_session_from_db,
    get_realtime_scores_from_db
)
from utils.qr_manager import generate_qr_image


@st.fragment(run_every=1)
def render_live_ranking_fragment(s_id):
    live_scores = get_realtime_scores_from_db(s_id)

    if not live_scores:
        st.info("Brak aktywnych uczniów w tej sesji.")
    else:
        st.caption(f"Ostatnia aktualizacja: {time.strftime('%H:%M:%S')}")

        for player in live_scores:
            col_name, col_stats = st.columns([1, 3])

            with col_name:
                st.write(f"**{player['student_name']}**")
                st.caption(f"Punkty: {player['score']} | Podpowiedzi: {player['hint_count']}")

            with col_stats:
                progress_val = player['progress_percent'] / 100
                st.progress(progress_val, text=f"{player['progress_percent']}%")


@st.dialog("🔥 RANKING LIVE - TOP WYNIKI", width="large")
def show_leaderboard_modal(s_id):
    """Wyświetla ranking w dużym oknie typu modal."""
    st.write("Wyniki wszystkich aktywnych graczy w czasie rzeczywistym.")
    render_live_ranking_fragment(s_id)
    if st.button("Zamknij widok"):
        st.rerun()

def show_sessions_view():
    st.title("Twoje Sesje i Wyniki")

    sessions = get_all_sessions_from_db()

    if not sessions:
        st.warning("Nie utworzono jeszcze żadnych sesji.")
        return

    for session in sessions:
        s_id = session['id']
        s_name = session['name']
        s_date = session['created_at'][:10]

        with st.expander(f"{s_date} | {s_name}"):
            tab_info, tab_results, tab_live = st.tabs([
                "Kod i Link",
                "Wyniki Końcowe",
                "Ranking Live"
            ])

            with tab_info:
                full_link = f"https://systemyinformatycznedeploy-3crdjb98tkhzrmwgfuccaz.streamlit.app/?session_id={s_id}"
                st.code(full_link)
                st.image(generate_qr_image(full_link), width=150)

            with tab_results:
                results = get_results_for_session_from_db(s_id)
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Nikt jeszcze nie ukończył krzyżówki.")

            with tab_live:
                col_title, col_btn = st.columns([3, 1])
                with col_title:
                    st.subheader("Postęp uczniów na żywo")
                with col_btn:
                    if st.button("Widok Tablicy", key=f"btn_modal_{s_id}", use_container_width=True):
                        show_leaderboard_modal(s_id)
                render_live_ranking_fragment(s_id)