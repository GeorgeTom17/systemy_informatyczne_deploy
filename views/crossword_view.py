import json

import streamlit as st
import streamlit.components.v1 as components
from utils.crossword_generator import CrosswordGenerator
from utils.db_manager import save_student_feedback
# Usunięto importy z data_manager
from utils.db_supabase import (
    get_all_sets_from_db,
    load_words_from_db,
    save_session_to_db,
    save_result_to_db, get_supabase_client
)
from utils.export_code_manager import encode_crossword
from utils.ml_engine import ai_engine
from utils.qr_manager import generate_qr_image
import random

# Adres URL aplikacji - nie zmieniać!
APP_BASE_URL = "https://systemyinformatycznedeploy-3crdjb98tkhzrmwgfuccaz.streamlit.app"

SPECIAL_CHARACTERS = {
    "Polski": "ĄĆĘŁŃÓŚŹŻ",
    "Niemiecki": "ÄÖÜß",
    "Francuski": "ÀÂÇÉÈÊËÎÏÔÛÙY",
    "Hiszpański": "ÑÁÉÍÓÚÜ",
    "Włoski": "ÀÈÉÌÒÓÙ",
    "Angielski": ""
}


@st.fragment(run_every=2)
def student_auto_finalizer(s_id, s_name):
    """
    To jest 'most'. Sprawdza czy w tabeli LIVE pojawił się status 'is_finished'.
    Jeśli tak - kopiuje dane do tabeli RESULTS i kasuje rekord z LIVE.
    """
    from utils.db_supabase import get_supabase_client, save_result_to_db

    supabase = get_supabase_client()

    # Pobieramy rekord ucznia z tabeli LIVE
    res = supabase.table("realtime_scores") \
        .select("is_finished, completion_time, hint_count") \
        .eq("session_id", s_id) \
        .eq("student_name", s_name) \
        .execute()

    if res.data and len(res.data) > 0:
        data = res.data[0]

        # JEŚLI JS OZNACZYŁ JAKO ZAKOŃCZONE
        if data.get('is_finished') == True:
            final_time = data.get('completion_time')
            hints = data.get('hint_count', 0)

            # 1. Zapisujemy w oficjalnej tabeli wyników
            success = save_result_to_db(s_id, s_name, final_time, hints)

            if success:
                # 2. Usuwamy z tabeli LIVE (żeby czujka nie kręciła się w nieskończoność)
                supabase.table("realtime_scores").delete() \
                    .eq("session_id", s_id) \
                    .eq("student_name", s_name).execute()

                # 3. Zmieniamy stan aplikacji, co wyłączy iframe i pokaże gratulacje
                st.session_state.result_submitted = True
                st.rerun()


@st.fragment(run_every=2)
def render_student_rank_badge(s_id, s_name):
    """Wyświetla pozycję ucznia w rankingu, odświeżaną co 2 sekundy."""
    from utils.db_supabase import get_student_rank

    rank = get_student_rank(s_id, s_name)

    if rank:
        st.markdown(
            f"""
            <div style="
                background-color: #FF8C00;
                color: white;
                padding: 10px 20px;
                border-radius: 50px;
                text-align: center;
                font-weight: bold;
                font-size: 1.2rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                display: inline-block;
            ">
                🏆 Twoja pozycja: {rank}
            </div>
            """,
            unsafe_allow_html=True
        )


def show_crossword_view(student_mode=False, session_name=None, student_name=None):
    if not student_mode:
        st.title("Generator Krzyżówek")

    # ==================================================
    # 1. LOGIKA ZARZĄDZANIA (TYLKO DLA NAUCZYCIELA)
    # ==================================================
    if not student_mode:
        # Pobieranie zestawów wyłącznie z bazy danych Supabase
        available_sets = get_all_sets_from_db()
        is_imported = st.session_state.get('last_set') == "Imported"

        if not available_sets:
            st.warning("Baza zestawów jest pusta. Stwórz lub wgraj zestaw w Menu Głównym.")
            if st.button("Wróć do Menu"):
                st.session_state.current_view = 'main_menu'
                st.rerun()
            return

        target_set = st.session_state.get('active_set')
        if not target_set or target_set not in available_sets:
            target_set = st.session_state.get('last_set')

        default_index = 0
        if target_set and target_set in available_sets:
            default_index = available_sets.index(target_set)

        col_sel, col_empty = st.columns([3, 1])
        with col_sel:
            selected_set = st.selectbox(
                "Zestaw z bazy danych:",
                available_sets,
                index=default_index,
                key="set_selector"
            )
        st.session_state.active_set = selected_set

        col_gen, col_export, col_back = st.columns([3, 2, 1])
        with col_gen:
            # Slider dla nauczyciela, domyślnie sugeruje limit z sesji jeśli istnieje
            suggested_limit = st.session_state.get('game_word_limit', 10)
            target_count = st.slider("Liczba słów na planszy:", 3, 40, suggested_limit)
            generate_clicked = st.button("Generuj Nową", type="primary")

        if is_imported and not generate_clicked:
            st.info("To jest zaimportowana/wczytana krzyżówka.")
            should_generate = False
        else:
            should_generate = (
                    generate_clicked or
                    'crossword_data' not in st.session_state or
                    (st.session_state.get('last_set') != selected_set and not is_imported)
            )

        if should_generate:
            current_set = st.session_state.get('active_set')

            with st.spinner(f'Pobieram słowa i układam krzyżówkę...'):
                # 1. Pobieramy pełną pulę (np. 50 słów) z bazy
                all_words_pool = load_words_from_db(current_set)

                if not all_words_pool:
                    st.error("Wybrany zestaw jest pusty!")
                    return

                # 2. Ustalamy ile słów faktycznie chcemy na planszy
                # Bierzemy mniejszą wartość: (to co chce użytkownik) vs (to co jest w bazie)
                final_limit = min(target_count, len(all_words_pool))

                # 3. LOSOWANIE: Wybieramy losowy podzbiór z dużej puli
                # To dzieje się TYLKO wewnątrz bloku should_generate
                selection = random.sample(all_words_pool, final_limit)
                selection = sorted(selection, key=lambda x: len(x['word']), reverse=True)
                # 4. Generowanie układu
                generator = CrosswordGenerator(selection)
                grid, clues_across, clues_down = generator.generate()

                word_starts = {}
                rows, cols = grid.shape
                for r in range(rows):
                    for c in range(cols):
                        cell = grid[r, c]
                        if isinstance(cell, dict) and 'number' in cell:
                            word_starts[(r, c)] = cell['number']

                # Zapisujemy wygenerowane dane do stanu sesji
                st.session_state.crossword_data = (grid, clues_across, clues_down, word_starts)
                st.session_state.last_set = selected_set

                # Czyścimy dane AI, aby przeliczyły się dla nowego zestawu


    else:
        if 'crossword_data' not in st.session_state:
            st.error("Brak danych krzyżówki. Użyj poprawnego kodu QR.")
            return

    if student_mode:
        display_name = session_name if session_name else "Zadanie"
        st.title(f"{display_name}")
        s_id = st.session_state.get('active_session_id')
        if s_id and student_name:
            if not st.session_state.get('result_submitted'):
                student_auto_finalizer(s_id, student_name)
                # Pokazujemy też badge z pozycją (można to połączyć w jeden fragment)
                render_student_rank_badge(s_id, student_name)
            else:
                st.success("🎉 Gratulacje! Twoje zadanie zostało przesłane.")
                st.balloons()
        st.caption(f"Powodzenia, **{student_name}**! Twoje wyniki są aktualizowane na żywo.")

    # ==================================================
    # 3. RENDEROWANIE
    # ==================================================

    current_lang = st.session_state.get('crossword_language', 'Polski')
    chars_to_show = SPECIAL_CHARACTERS.get(current_lang, SPECIAL_CHARACTERS['Polski'])

    if 'crossword_data' in st.session_state:
        grid, clues_across, clues_down, word_starts = st.session_state.crossword_data
        ROWS, COLS = grid.shape

        cell_parents = {}
        all_words_list = []
        for r in range(ROWS):
            for c in range(COLS):
                cell = grid[r, c]
                if isinstance(cell, dict) and 'number' in cell:
                    if c + 1 < COLS and isinstance(grid[r, c + 1], str):
                        all_words_list.append({'r': r, 'c': c, 'dir': 'across'})
                        curr_r, curr_c = r, c + 1
                        parent_id = f"num-{r}-{c}"
                        while curr_c < COLS and isinstance(grid[curr_r, curr_c], str):
                            if (curr_r, curr_c) not in cell_parents: cell_parents[(curr_r, curr_c)] = {}
                            cell_parents[(curr_r, curr_c)]['across'] = parent_id
                            curr_c += 1
                    if r + 1 < ROWS and isinstance(grid[r + 1, c], str):
                        all_words_list.append({'r': r, 'c': c, 'dir': 'down'})
                        curr_r, curr_c = r + 1, c
                        parent_id = f"num-{r}-{c}"
                        while curr_r < ROWS and isinstance(grid[curr_r, curr_c], str):
                            if (curr_r, curr_c) not in cell_parents: cell_parents[(curr_r, curr_c)] = {}
                            cell_parents[(curr_r, curr_c)]['down'] = parent_id
                            curr_r += 1

        downs = sorted([w for w in all_words_list if w['dir'] == 'down'], key=lambda x: (x['c'], x['r']))
        acrosses = sorted([w for w in all_words_list if w['dir'] == 'across'], key=lambda x: (x['r'], x['c']))
        sorted_words_for_js = downs + acrosses
        json_words = json.dumps(sorted_words_for_js)

        grid_html = ""
        for r in range(ROWS):
            for c in range(COLS):
                cell = grid[r, c]
                if cell is None:
                    grid_html += '<div class="cell block"></div>'
                elif isinstance(cell, dict) and 'number' in cell:
                    num = cell['number']
                    clue = str(cell['clue']).replace('"', '&quot;').replace("'", "&#39;")
                    grid_html += f'<div class="cell number-cell" id="num-{r}-{c}">{num}<div class="tooltip">{clue}</div></div>'
                else:
                    correct_letter = str(cell).upper()
                    parents = cell_parents.get((r, c), {})
                    p_across = parents.get('across', '')
                    p_down = parents.get('down', '')
                    grid_html += f'<div class="cell input-cell"><input type="text" maxlength="1" id="input-{r}-{c}" data-row="{r}" data-col="{c}" data-correct="{correct_letter}" data-parent-across="{p_across}" data-parent-down="{p_down}" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></div>'

        cell_size = (700 / ROWS) * 1.2
        full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
                <style>
                    :root {{
                        --cell-size: 35px;
                        --font-size: 20px;
                        --gap-size: 2px;
                        --btn-check: #28a745;
                        --btn-hint: #ffc107;
                        --hint-text-color: #6f42c1;
                    }}

                    @media (max-width: 600px) {{
                        :root {{
                            --cell-size: 26px;
                            --font-size: 14px;
                            --gap-size: 1px;
                        }}
                    }}

                    body {{
                        font-family: sans-serif;
                        background-color: transparent;
                        margin: 0; padding: 0; width: 100%; box-sizing: border-box;
                        touch-action: manipulation;
                    }}

                    .controls-bar {{
                        display: flex; justify-content: center; align-items: center;
                        gap: 10px; margin-bottom: 10px; padding: 5px; flex-wrap: wrap;
                    }}

                    .timer-display {{
                        font-size: 18px; font-weight: bold; color: #333;
                        background: #f0f0f0; padding: 5px 10px; border-radius: 4px;
                        min-width: 60px; text-align: center; border: 1px solid #ccc;
                    }}

                    .btn {{
                        border: none; padding: 8px 12px; font-size: 16px;
                        border-radius: 4px; cursor: pointer; font-weight: bold;
                        color: white; transition: filter 0.2s;
                    }}
                    .btn:active {{ transform: scale(0.98); }}

                    .check-btn {{ background-color: var(--btn-check); }}
                    .check-btn:hover {{ filter: brightness(0.9); }}

                    .hint-btn {{ 
                        background-color: var(--btn-hint); 
                        color: #000;
                    }}
                    .hint-btn:hover {{ filter: brightness(0.9); }}

                    .hint-counter {{
                        font-size: 12px; color: #555; margin-left: 5px;
                    }}

                    .scroll-wrapper {{
                        width: 100%; overflow-x: auto; display: flex;
                        justify-content: safe center; padding-bottom: 20px;
                    }}
                    @supports not (justify-content: safe center) {{ .scroll-wrapper {{ display: block; text-align: center; }} }}

                    .main-container {{ display: inline-block; padding: 0 10px; }}

                    .crossword {{
                        display: grid;
                        grid-template-columns: repeat({COLS}, var(--cell-size));
                        grid-template-rows: repeat({ROWS}, var(--cell-size));
                        gap: var(--gap-size);
                        background: #222; padding: 4px; border-radius: 4px;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.2); margin: 0 auto;
                    }}

                    .cell {{ width: var(--cell-size); height: var(--cell-size); position: relative; box-sizing: border-box; }}
                    .block {{ background: #000; }}

                    .number-cell {{
                        background-color: #FF8C00; color: white; font-weight: bold;
                        display: flex; justify-content: center; align-items: center;
                        font-size: calc(var(--cell-size) * 0.5); cursor: help; position: relative;
                    }}

                    .tooltip {{
                        visibility: hidden; opacity: 0; background-color: #333; color: #fff;
                        text-align: center; padding: 8px; border-radius: 5px;
                        position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%);
                        z-index: 2000; width: max-content; max-width: 250px;
                        font-size: 14px; font-weight: normal; 
                        box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
                        transition: opacity 0.2s; pointer-events: none; white-space: normal;
                    }}
                    .tooltip::after {{
                        content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px;
                        border-width: 5px; border-style: solid; border-color: #333 transparent transparent transparent;
                    }}
                    .number-cell:hover .tooltip, .tooltip.force-visible {{ visibility: visible; opacity: 1; }}

                    .input-cell {{ background: #fff; }}
                    .input-cell input {{
                        width: 100%; height: 100%; padding: 0; margin: 0;
                        font-size: var(--font-size); color: black; text-align: center; border: none;
                        background: #fff; font-weight: bold; text-transform: uppercase; 
                        display: block; border-radius: 0; -webkit-appearance: none;
                    }}
                    .input-cell input:focus {{ outline: 2px solid #1e90ff; background-color: #e8f0fe; }}
                    .input-cell input.valid {{ background-color: #d4edda; color: #155724; }}
                    .input-cell input.invalid {{ background-color: #f8d7da; color: #721c24; }}

                    .input-cell input.hint-used {{
                        color: var(--hint-text-color);
                        background-color: #fcf8e3; /* Lekko żółte tło */
                    }}
                    .input-cell input.highlight-word {{
                        background-color: #90caf9 !important; /* Jasny niebieski (Blue 200) */
                        transition: background-color 0.2s;
                    }}
                    
                    /* Intensywny kolor dla komórki, w której jest kursor */
                    .input-cell input:focus {{
                        background-color: #1e88e5 !important; /* Mocny niebieski (Blue 600) */
                        color: white !important;             /* Biała czcionka dla kontrastu */
                        outline: 3px solid #0d47a1;          /* Bardzo ciemna ramka */
                        caret-color: white;                  /* Kolor migającego kursora */
                    }}
                    
                    /* Zachowanie czytelności liter w podświetlonym słowie */
                    .input-cell input.highlight-word:not(:focus) {{
                        color: #0d47a1 !important;           /* Ciemniejszy tekst dla słowa */
                    }}
                </style>
                </head>
                <body>
                    <div class="controls-bar">
                        <div class="timer-display" id="timer">00:00</div>
                        <button class="btn check-btn" onclick="checkAnswers()">Sprawdź</button>
                        <button class="btn hint-btn" onclick="revealLetter()">Podpowiedź</button>
                        <span class="hint-counter" id="hint-count">Użyto: 0</span>
                    </div>

                    <div class="scroll-wrapper">
                        <div class="main-container">
                            <div class="crossword">
                                {grid_html}
                            </div>
                        </div>
                    </div>

                    <script>
                        const wordOrder = {json_words};

                        let currentDirection = 'across';
                        let lastFocusedInput = null;
                        let hintCount = 0;

                        let startTime = Date.now();
                        let timerInterval;
                        let isSolved = false;
                        
                        const supabaseUrl = "{st.secrets['supabase']['url']}";
                        const supabaseKey = "{st.secrets['supabase']['key']}";
                        const sessionId = {st.session_state.get('active_session_id', 0)};
                        const studentName = "{student_name}";
                        const isAlreadySubmitted = {"true" if st.session_state.get('result_submitted') else "false"};
                        
                        let currentScore = 0;
                        let correctLettersSet = new Set();
                        
                        async function logEasyWords() {{
                            const inputs = document.querySelectorAll('input');
                            const easyWords = new Set();
                        
                            inputs.forEach(input => {{
                                // Jeśli pole jest wypełnione i NIE ma klasy 'hint-used'
                                if (input.value.toUpperCase() === input.getAttribute("data-correct") && 
                                    !input.classList.contains('hint-used')) {{
                                    
                                    // Pobieramy ID startowe słowa (nadrzędną komórkę z numerem)
                                    const parentId = currentDirection === 'across' ? 
                                                     input.getAttribute('data-parent-across') : 
                                                     input.getAttribute('data-parent-down');
                                    
                                    if (parentId) {{
                                        const numCell = document.getElementById(parentId);
                                        const word = input.getAttribute("data-correct"); // Uproszczenie: logujemy litery jako część słowa
                                        const clue = numCell ? numCell.querySelector('.tooltip').innerText : "";
                                        
                                        // Wysyłamy do tabeli ML jako ŁATWE
                                        reportDifficulty(word, clue, "ŁATWE");
                                    }}
                                }}
                            }});
                        }}
                        
                        async function logWordDifficulty(word, clue, label) {{
                            try {{
                                const url = `${{supabaseUrl}}/rest/v1/ml_training_data`;
                                await fetch(url, {{
                                    method: 'POST',
                                    headers: {{
                                        'apikey': supabaseKey,
                                        'Authorization': `Bearer ${{supabaseKey}}`,
                                        'Content-Type': 'application/json',
                                        'Prefer': 'return=minimal'
                                    }},
                                    body: JSON.stringify({{
                                        word: word.toUpperCase(),
                                        clue: clue,
                                        language: "{{current_lang}}",
                                        error_count: label // Każda podpowiedź to punkt trudności
                                    }})
                                }});
                            }} catch (e) {{ console.error("ML Log Error:", e); }}
                        }}
                        
                        async function finalizeSessionAuto(finalTime) {{
                            // Musimy przeliczyć poprawne odpowiedzi na miejscu, by mieć pewność danych
                            const inputs = document.querySelectorAll('input');
                            const totalCells = inputs.length;
                            let correctCount = 0;
                            inputs.forEach(input => {{
                                if (input.value.toUpperCase() === input.getAttribute("data-correct")) correctCount++;
                            }});
                        
                            try {{
                                const url = `${{supabaseUrl}}/rest/v1/realtime_scores?on_conflict=session_id,student_name`;
                                const response = await fetch(url, {{
                                    method: 'POST',
                                    headers: {{
                                        'apikey': supabaseKey,
                                        'Authorization': `Bearer ${{supabaseKey}}`,
                                        'Content-Type': 'application/json',
                                        'Prefer': 'resolution=merge-duplicates'
                                    }},
                                    body: JSON.stringify({{
                                        session_id: sessionId,
                                        student_name: studentName,
                                        score: (correctCount * 10) - (hintCount * 5),
                                        progress_percent: 100,
                                        hint_count: hintCount,
                                        is_finished: true,
                                        completion_time: finalTime,
                                        last_updated: new Date().toISOString()
                                    }})
                                }});
                                
                                if(response.ok) console.log("Dane końcowe wysłane");
                            }} catch (e) {{
                                console.error("Błąd wysyłki końcowej:", e);
                            }}
                        }}
                        
                        async function syncRealtimeScore() {{
                        
                            if (isAlreadySubmitted || isSolved) {{
                                console.log("Synchronizacja wstrzymana: wynik już wysłany lub rozwiązano.");
                                return; 
                            }}
                        
                            if (!sessionId || !studentName) return;

                            const inputs = document.querySelectorAll('input');
                            const totalCells = inputs.length;
                            let correctCount = 0;
                        
                            inputs.forEach(input => {{
                                if (input.value.toUpperCase() === input.getAttribute("data-correct")) {{
                                    correctCount++;
                                }}
                            }});
                            const progressPercent = Math.round((correctCount / totalCells) * 100);
                            const score = (correctCount * 10) - (hintCount * 5);
                            if (correctCount === 0 && hintCount === 0) {{
                                return;
                            }}
                            try {{
                                const url = `${{supabaseUrl}}/rest/v1/realtime_scores?on_conflict=session_id,student_name`;

                                const response = await fetch(url, {{
                                    method: 'POST',
                                    headers: {{
                                        'apikey': supabaseKey,
                                        'Authorization': `Bearer ${{supabaseKey}}`,
                                        'Content-Type': 'application/json',
                                        'Prefer': 'return=minimal,resolution=merge-duplicates' 
                                    }},
                                    body: JSON.stringify({{
                                        session_id: sessionId,
                                        student_name: studentName,
                                        score: score,
                                        progress_percent: progressPercent,
                                        hint_count: hintCount,
                                        last_updated: new Date().toISOString()
                                    }})
                                }});
                            }} catch(e) {{
                                console.error("Błąd synchronizacji:", e);
                            }}
                        }}
                        
                        setInterval(syncRealtimeScore, 2000);

                        function updateTimer() {{
                            if (isSolved) return;
                            const now = Date.now();
                            const diff = now - startTime;
                            const seconds = Math.floor((diff / 1000) % 60);
                            const minutes = Math.floor((diff / (1000 * 60)));
                            const fmtSec = seconds < 10 ? "0" + seconds : seconds;
                            const fmtMin = minutes < 10 ? "0" + minutes : minutes;
                            document.getElementById("timer").innerText = fmtMin + ":" + fmtSec;
                        }}
                        timerInterval = setInterval(updateTimer, 1000);

                        function revealLetter() {{
                            if (isSolved) return;

                            if (!lastFocusedInput) {{
                                alert("Najpierw kliknij w puste pole, które chcesz odkryć!");
                                return;
                            }}

                            const correct = lastFocusedInput.getAttribute("data-correct");
                            const wordText = lastFocusedInput.getAttribute("data-parent-across") || lastFocusedInput.getAttribute("data-parent-down");
                            const wordClue = lastFocusedInput.closest('.cell').querySelector('.tooltip')?.innerText || "";
                            logWordDifficulty(correct, wordClue, "TRUDNE");
                            if (lastFocusedInput.value.toUpperCase() === correct) {{
                                return;
                            }}

                            lastFocusedInput.value = correct;

                            lastFocusedInput.classList.add("hint-used");
                            lastFocusedInput.classList.remove("invalid");
                            lastFocusedInput.classList.remove("valid");

                            hintCount++;
                            syncRealtimeScore()
                            document.getElementById("hint-count").innerText = "Użyto: " + hintCount;

                            const input = lastFocusedInput;
                            let r = parseInt(input.getAttribute('data-row'));
                            let c = parseInt(input.getAttribute('data-col'));
                            let dr = (currentDirection === 'across') ? 0 : 1;
                            let dc = (currentDirection === 'across') ? 1 : 0;
                            let foundNextInWord = false;
                            let nextR = r; 
                            let nextC = c;
                            while (true) {{
                                nextR += dr; 
                                nextC += dc;
                                const nextTarget = document.getElementById("input-" + nextR + "-" + nextC);
                                if (!nextTarget) break;
                                if (nextTarget.value.length === 0) {{
                                    nextTarget.focus();
                                    foundNextInWord = true;
                                    break;
                                }}
                            }}
                            if (!foundNextInWord) {{
                                checkAndJumpToNextWord();
                            }}
                        }}

                        function checkAnswers() {{
                            if (isSolved) return;
                            const inputs = document.querySelectorAll('input');
                            let errors = 0; 
                            let empty = 0;
                        
                            // Najpierw kolorujemy wszystko
                            inputs.forEach(input => {{
                                const val = input.value.toUpperCase();
                                const correct = input.getAttribute("data-correct");
                                input.classList.remove("valid", "invalid");
                        
                                if (val.length === 0) {{
                                    empty++; 
                                }} else if (val === correct) {{
                                    input.classList.add("valid"); // LUDZIE WIDZĄ ZIELONY
                                }} else {{
                                    input.classList.add("invalid"); // LUDZIE WIDZĄ CZERWONY
                                    errors++; 
                                }}
                            }});
                        
                            // Jeśli wszystko jest OK
                            if (errors === 0 && empty === 0) {{
                                isSolved = true;
                                clearInterval(timerInterval);
                                logEasyWords();
                                const finalTime = document.getElementById("timer").innerText;
                                
                                // WYŚLIJ DO BAZY
                                finalizeSessionAuto(finalTime);
                                
                                // Alert dajemy z małym opóźnieniem, żeby przeglądarka zdążyła wyrenderować kolory
                                setTimeout(() => {{
                                    alert("Brawo! Rozwiązałeś krzyżówkę w czasie: " + finalTime);
                                }}, 100);
                            }}
                        }}

                        function clearValidation(input) {{
                            input.classList.remove("valid", "invalid");
                        }}

                        function updateTooltip(input) {{
                            document.querySelectorAll('.tooltip.force-visible').forEach(el => {{ el.classList.remove('force-visible'); }});
                            const parentAcross = input.getAttribute('data-parent-across');
                            const parentDown = input.getAttribute('data-parent-down');
                            let targetId = null;
                            if (parentAcross && !parentDown) targetId = parentAcross;
                            else if (!parentAcross && parentDown) targetId = parentDown;
                            else if (parentAcross && parentDown) targetId = (currentDirection === 'across') ? parentAcross : parentDown;

                            if (targetId) {{
                                const numberCell = document.getElementById(targetId);
                                if (numberCell) {{
                                    const tooltip = numberCell.querySelector('.tooltip');
                                    if (tooltip) tooltip.classList.add('force-visible');
                                }}
                            }}
                        }}

                        function checkAndJumpToNextWord() {{
                            if (!lastFocusedInput) {{
                                // Jeśli nie ma fokusu, zachowaj stare zachowanie (zacznij od początku)
                                currentIndex = -1;
                            }} else {{
                                // 1. Zidentyfikuj ID startowe bieżącego słowa (format: num-r-c)
                                const parentId = lastFocusedInput.getAttribute(
                                    currentDirection === 'across' ? 'data-parent-across' : 'data-parent-down'
                                );
                                
                                if (!parentId) {{
                                    currentIndex = -1;
                                }} else {{
                                    const parts = parentId.split('-');
                                    const curR = parseInt(parts[1]);
                                    const curC = parseInt(parts[2]);
                                    
                                    // Znajdź pozycję obecnego słowa w wordOrder
                                    currentIndex = wordOrder.findIndex(w => w.r === curR && w.c === curC && w.dir === currentDirection);
                                }}
                            }}
                        
                            // 2. Szukaj następnego słowa, zaczynając od (currentIndex + 1)
                            for (let i = 1; i <= wordOrder.length; i++) {{
                                // Używamy modulo %, aby po dojściu do końca listy wrócić na początek
                                let nextIndex = (currentIndex + i) % wordOrder.length;
                                let w = wordOrder[nextIndex];
                        
                                let dr = (w.dir === 'across') ? 0 : 1;
                                let dc = (w.dir === 'across') ? 1 : 0;
                                let isWordFull = true; 
                                let firstEmptyInput = null;
                                
                                // Zacznij sprawdzanie od pierwszej litery za numerkiem
                                let currR = w.r + dr; 
                                let currC = w.c + dc;
                        
                                while (true) {{
                                    let el = document.getElementById("input-" + currR + "-" + currC);
                                    if (!el) break;
                                    if (el.value.length === 0) {{
                                        isWordFull = false;
                                        if (!firstEmptyInput) firstEmptyInput = el;
                                    }}
                                    currR += dr; 
                                    currC += dc;
                                }}
                        
                                // Jeśli znaleźliśmy słowo z wolnym miejscem, przenieś tam fokus
                                if (!isWordFull && firstEmptyInput) {{
                                    currentDirection = w.dir;
                                    firstEmptyInput.focus();
                                    return;
                                }}
                            }}
                        }}

                        function moveFocus(e) {{
                            const input = e.target;
                            let r = parseInt(input.getAttribute('data-row'));
                            let c = parseInt(input.getAttribute('data-col'));
                        
                            // --- NOWOŚĆ: Obsługa spacji jako skoku do następnego słowa ---
                            if (e.key === ' ' || e.code === 'Space') {{
                                e.preventDefault(); // Blokujemy wpisanie znaku
                                let nextR = r;
                                let nextC = c;
                                
                                if (currentDirection === 'across') nextC++;
                                else nextR++;
                        
                                const target = document.getElementById("input-" + nextR + "-" + nextC);
                                
                                if (target) {{
                                    // Jeśli istnieje następna komórka w tym samym kierunku - idź do niej
                                    target.focus();
                                }} else {{
                                    // Jeśli to był koniec słowa - przeskocz do następnego słowa na liście
                                    checkAndJumpToNextWord();
                                }}
                                return;
                            }}
                        
                            // Obsługa Backspace
                            if (e.key === 'Backspace') {{
                                if (input.value.length === 0) {{
                                    if (currentDirection === 'across') c--;
                                    if (currentDirection === 'down') r--;
                                    const target = document.getElementById("input-" + r + "-" + c);
                                    if (target) {{ 
                                        e.preventDefault(); 
                                        target.focus(); 
                                    }}
                                }}
                                return;
                            }}
                        
                            // Obsługa Strzałek
                            if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) return;
                            
                            if (e.key === 'ArrowUp') {{ r--; currentDirection = 'down'; }}
                            if (e.key === 'ArrowDown') {{ r++; currentDirection = 'down'; }}
                            if (e.key === 'ArrowLeft') {{ c--; currentDirection = 'across'; }}
                            if (e.key === 'ArrowRight') {{ c++; currentDirection = 'across'; }}
                            
                            const target = document.getElementById("input-" + r + "-" + c);
                            if (target) {{ 
                                e.preventDefault(); 
                                target.focus(); 
                            }}
                            setTimeout(() => {{
                                if (document.activeElement.tagName === 'INPUT') {{
                                    highlightCurrentWord(document.activeElement);
                                }}
                            }}, 10);
                        }}

                        function handleInput(e) {{
                            const input = e.target;
                            clearValidation(input);
                            if (input.value.length === 1) {{
                                syncRealtimeScore()
                                let r = parseInt(input.getAttribute('data-row'));
                                let c = parseInt(input.getAttribute('data-col'));
                                let dr = (currentDirection === 'across') ? 0 : 1;
                                let dc = (currentDirection === 'across') ? 1 : 0;
                                let foundNextInWord = false;
                                let nextR = r; let nextC = c;
                                while(true) {{
                                    nextR += dr; nextC += dc;
                                    const nextTarget = document.getElementById("input-" + nextR + "-" + nextC);
                                    if (!nextTarget) break;
                                    if (nextTarget.value.length === 0) {{
                                        nextTarget.focus();
                                        foundNextInWord = true;
                                        break;
                                    }}
                                }}
                                if (!foundNextInWord) {{ checkAndJumpToNextWord(); }}
                            }}
                        }}

                        function handleFocus(input) {{
                            lastFocusedInput = input;
                            const pAcross = input.getAttribute('data-parent-across');
                            const pDown = input.getAttribute('data-parent-down');
                            if (pAcross && !pDown) currentDirection = 'across';
                            if (!pAcross && pDown) currentDirection = 'down';
                            updateTooltip(input);
                            highlightCurrentWord(input);
                        }}
                        
                        function clearWordHighlight() {{
                            document.querySelectorAll('.input-cell input').forEach(el => {{
                                el.classList.remove('highlight-word');
                            }});
                        }}
                        
                        function highlightCurrentWord(input) {{
                            clearWordHighlight();
                            if (!input) return;
                        
                            const parentId = currentDirection === 'across' 
                                ? input.getAttribute('data-parent-across') 
                                : input.getAttribute('data-parent-down');
                        
                            if (parentId) {{
                                const selector = currentDirection === 'across' 
                                    ? `input[data-parent-across="${{parentId}}"]` 
                                    : `input[data-parent-down="${{parentId}}"]`;
                                
                                document.querySelectorAll(selector).forEach(el => {{
                                    el.classList.add('highlight-word');
                                }});
                            }}
                        }}

                        const inputs = document.querySelectorAll('input');
                        inputs.forEach(input => {{
                            input.addEventListener('input', handleInput);
                            input.addEventListener('keydown', moveFocus);
                            input.addEventListener('focus', function() {{ handleFocus(this); }});
                        }});

                        document.body.addEventListener('click', function(e) {{
                            if (e.target.tagName !== 'INPUT' && !e.target.classList.contains('btn')) {{
                                 document.querySelectorAll('.tooltip.force-visible').forEach(el => {{ el.classList.remove('force-visible'); }});
                            }}
                        }});
                    </script>
                </body>
                </html>
                """
        iframe_height = (ROWS * 37) + 120
        components.html(full_html, height=iframe_height, scrolling=True)
        if not student_mode and 'crossword_data' in st.session_state:
            with col_export:
                with st.popover("Udostępnij Sesję (QR)", use_container_width=True):
                    st.subheader("Utwórz sesję w bazie danych")
                    new_session_name = st.text_input("Nazwa sesji:", placeholder="np. Lekcja 1")
                    if st.button("Generuj kod QR", type="primary"):
                        if not new_session_name:
                            st.error("Podaj nazwę!")
                        else:
                            raw_code = encode_crossword(st.session_state.crossword_data)
                            session_id = save_session_to_db(new_session_name, raw_code)
                            if session_id:
                                full_link = f"{APP_BASE_URL}/?session_id={session_id}"
                                st.image(generate_qr_image(full_link), use_container_width=True)
                                st.code(full_link)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("POZIOMO")
            if clues_across:
                for x in clues_across: st.text(x)
        with c2:
            st.subheader("PIONOWO")
            if clues_down:
                for x in clues_down: st.text(x)
