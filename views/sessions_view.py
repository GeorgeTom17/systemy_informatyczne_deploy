import streamlit as st
import pandas as pd
import time
from utils.db_supabase import (
    get_all_sessions_from_db,
    get_results_for_session_from_db,
    get_realtime_scores_from_db
)
from utils.qr_manager import generate_qr_image


@st.fragment(run_every=2)
def render_results_table_fragment(s_id):
    """Odświeża tabelę oficjalnych wyników, sortując ich po punktach Fair Play."""
    from utils.db_supabase import get_results_for_session_from_db
    import pandas as pd

    results = get_results_for_session_from_db(s_id)
    if results:
        df = pd.DataFrame(results)

        # 1. Sortowanie po punktach (malejąco - najwyższy wynik na górze)
        if "score" in df.columns:
            df = df.sort_values(by="score", ascending=False)

        # 2. Wybieramy i układamy kolumny w logicznej kolejności
        # Dodajemy 'score' do widoku
        display_cols = {
            "student_name": "Uczeń",
            "score": "Punkty (Fair Play)",
            "time_taken": "Czas",
            "hint_count": "Podpowiedzi",
            "created_at": "Data ukończenia"
        }

        # Filtrujemy tylko istniejące kolumny (zabezpieczenie)
        existing_cols = [c for c in display_cols.keys() if c in df.columns]
        df = df[existing_cols]

        # 3. Zmiana nazw na ładniejsze
        df = df.rename(columns=display_cols)

        # Wyświetlenie tabeli jako rankingu
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=False  # Pokażemy indeks jako "miejsce" w rankingu (opcjonalnie)
        )

        # Mały dodatek: Wyświetlenie zwycięzcy w formie sukcesu
        winner = df.iloc[0]["Uczeń"]
        st.success(f"Obecny lider: **{winner}**")

    else:
        st.info("Nikt jeszcze nie ukończył krzyżówki. Czekam na pierwszych graczy...")

@st.fragment(run_every=3)
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
    st.markdown(
        """
        <style>
            div[data-testid="stDialog"] div[role="dialog"] {
                width: 95vw !important;
                max-width: 95vw !important;
                height: 80vh !important;
            }
            div[data-testid="stDialog"] h1 { font-size: 3rem !important; }
        </style>
        """,
        unsafe_allow_html=True
    )
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
                st.subheader("Oficjalna tabela wyników")
                render_results_table_fragment(s_id)

            with tab_live:
                col_status, col_actions = st.columns([1, 1])
                from utils.db_supabase import get_session_status, update_session_status
                current_status = get_session_status(s_id)
                with col_status:
                    if current_status == 'waiting':
                        st.info("Stan: Oczekiwanie")
                    elif current_status == 'active':
                        st.success("Stan: Aktywna")
                    else:
                        st.error("Stan: Zakończona")

                with col_actions:
                    if current_status == 'waiting':
                        if st.button("ROZPOCZNIJ", key=f"start_{s_id}", type="primary", use_container_width=True):
                            update_session_status(s_id, 'active')
                            st.rerun()
                    elif current_status == 'active':
                        if st.button("ZAKOŃCZ", key=f"stop_{s_id}", type="secondary", use_container_width=True):
                            update_session_status(s_id, 'finished')
                            st.rerun()
                    else:
                        if st.button("Resetuj do Poczekalni", key=f"reset_{s_id}", use_container_width=True):
                            update_session_status(s_id, 'waiting')
                            st.rerun()
                st.divider()
                col_title, col_btn = st.columns([3, 1])
                with col_title:
                    st.subheader("Postęp uczniów na żywo")
                with col_btn:
                    if st.button("Widok Tablicy", key=f"btn_modal_{s_id}", use_container_width=True):
                        show_leaderboard_modal(s_id)
                render_live_ranking_fragment(s_id)