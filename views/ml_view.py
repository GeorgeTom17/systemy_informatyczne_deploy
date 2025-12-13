import streamlit as st
import pandas as pd
from utils.ml_engine import ai_engine, INITIAL_DATA, LANG_CHARSETS


def show_ml_view():
    st.title("Centrum AI (Multi-Language)")
    st.info("Naucz model rozpoznawać trudność słów w różnych językach.")

    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("1. Baza Wiedzy")
        if 'training_data' not in st.session_state:
            st.session_state.training_data = INITIAL_DATA.copy()

        df = pd.DataFrame(st.session_state.training_data, columns=["Słowo", "Tłumaczenie/Clue", "Język", "Trudność"])
        st.dataframe(df, height=300, use_container_width=True)

    with c2:
        st.subheader("2. Doucz Model")

        with st.form("add_training_sample"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_lang = st.selectbox("Język:", list(LANG_CHARSETS.keys()))
                new_word = st.text_input("Słowo:", placeholder="np. ORANGE")
            with col_b:
                new_clue = st.text_input("Tłumaczenie (Clue):", placeholder="np. Pomarańcza")
                new_label = st.selectbox("Ocena:", ["ŁATWE", "ŚREDNIE", "TRUDNE"])

            if st.form_submit_button("Dodaj i Przetrenuj"):
                if new_word and new_clue:
                    st.session_state.training_data.append((new_word, new_clue, new_lang, new_label))
                    acc = ai_engine.train(st.session_state.training_data)
                    st.success(f"Model nauczony! Dokładność: {acc * 100:.1f}%")
                    st.rerun()
                else:
                    st.error("Wpisz słowo i tłumaczenie.")

        st.divider()
        st.subheader("3. Testuj (Symulacja)")

        t_lang = st.selectbox("Język testu:", list(LANG_CHARSETS.keys()), key="test_lang")
        t_word = st.text_input("Słowo testowe:", key="t_word")
        t_clue = st.text_input("Tłumaczenie (dla sprawdzenia podobieństwa):", key="t_clue")

        if st.button("Przewiduj"):
            pred, conf, feat = ai_engine.predict(t_word, t_clue, t_lang)

            color = "green" if pred == "ŁATWE" else "orange" if pred == "ŚREDNIE" else "red"
            st.markdown(f"Ocena: :{color}[**{pred}**] ({conf * 100:.0f}%)")

            st.caption("Dlaczego?")
            cols_f = st.columns(4)
            cols_f[0].metric("Długość", feat[0])
            cols_f[1].metric("Znaki Spec.", feat[1])
            cols_f[2].metric("Samogłoski", f"{feat[2]:.2f}")
            cols_f[3].metric("Podobieństwo", f"{feat[3] * 100:.0f}%", help="Czy słowo jest podobne do tłumaczenia?")

            if feat[3] > 0.6:
                st.toast("💡 Wykryto 'Cognate' (słowo podobne do polskiego)!", icon="🔗")