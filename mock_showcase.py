import streamlit as st
from utils.mocks import StubTranslator, MockDifficultyAI


def run_showcase():
    st.title("Prezentacja Obiektów Mock/Stub")
    st.info("Ten ekran służy do prezentacji funkcjonalności, które są jeszcze w trakcie implementacji backendowej.")

    # --- SCENARIUSZ 1: Tłumacz ---
    st.header("1. Stub: Moduł Tłumaczenia")
    st.caption("Prawdziwe API jest płatne/wolne. Tutaj używamy Stuba ze sztywnym słownikiem.")

    col1, col2 = st.columns(2)
    with col1:
        word_input = st.text_input("Wpisz słowo (np. pies, dom, szkoła, cokolwiek):")

    if st.button("Przetłumacz (Symulacja)"):
        # Używamy obiektu STUB
        translator = StubTranslator()
        result = translator.translate(word_input)

        with col2:
            st.success(f"Tłumaczenie: **{result}**")
            if "[MOCK]" in result:
                st.warning("To słowo nie jest w bazie Stuba, zwrócono generowaną zaślepkę.")

    st.markdown("---")

    # --- SCENARIUSZ 2: ml Analiza ---
    st.header("2. Mock: Analiza Trudności")
    st.caption("Backend do NLP nie jest gotowy. Mock symuluje czas przetwarzania i zwraca strukturę danych.")

    # Lista słów do analizy
    example_words = st.multiselect(
        "Wybierz słowa do zestawu:",
        ["pies", "kot", "architektura", "konstantynopolitańczykowianeczka", "dom", "drzewo"],
        default=["pies", "kot"]
    )

    if st.button("🤖 Oblicz poziom trudności (AI)"):
        mock_ai = MockDifficultyAI()

        with st.spinner("AI analizuje strukturę gramatyczną... (udawane opóźnienie)"):
            report = mock_ai.analyze_complexity(example_words)

        # Wyświetlanie wyniku
        st.metric(label="Poziom Trudności", value=report['level'])
        st.progress(report['score'])
        st.write(f"**Szczegóły:** {report['details']}")
        st.info(f"💡 Sugestia AI: {report['suggestion']}")


if __name__ == "__main__":
    run_showcase()