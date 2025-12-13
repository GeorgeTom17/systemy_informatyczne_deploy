import streamlit as st
import streamlit.components.v1 as components
import json
from utils.crossword_generator import CrosswordGenerator
from utils.data_manager import load_words, get_all_sets
from utils.export_code_manager import encode_crossword
from utils.qr_manager import generate_qr_image
from utils.session_manager import save_session
import urllib.parse
from utils.results_manager import save_result
from utils.ml_engine import ai_engine
from utils.db_manager import save_student_feedback

#NIE RUSZAĆ !!!!! JAK KTOŚ TEN LINK ZMIENI TO WIDZIMY SIĘ ZA GARAŻAMI
APP_BASE_URL = "https://systemyinformatycznedeploy-3crdjb98tkhzrmwgfuccaz.streamlit.app"

SPECIAL_CHARACTERS = {
    "Polski": "ĄĆĘŁŃÓŚŹŻ",
    "Niemiecki": "ÄÖÜß",
    "Francuski": "ÀÂÇÉÈÊËÎÏÔÛÙY",
    "Hiszpański": "ÑÁÉÍÓÚÜ",
    "Włoski": "ÀÈÉÌÒÓÙ",
    "Angielski": ""
}


def show_crossword_view(student_mode=False, session_name=None, student_name=None):
    if not student_mode:
        st.title("🧩 Generator Krzyżówek")
    else:
        display_name = session_name if session_name else "Zadanie"
        user_display = student_name if student_name else "Uczniu"
        st.title(f"{display_name}")
        st.caption(f"Powodzenia, **{user_display}**! Czas start!")

    # ==================================================
    # 1. LOGIKA ZARZĄDZANIA (TYLKO DLA NAUCZYCIELA)
    # ==================================================
    if not student_mode:
        available_sets = get_all_sets()
        is_imported = st.session_state.get('last_set') == "Imported"

        if not available_sets:
            st.error("Brak zestawów słów! Wróć do menu.")
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
                "Zestaw:",
                available_sets,
                index=default_index,
                key="set_selector"
            )
        st.session_state.active_set = selected_set

        col_gen, col_export, col_back = st.columns([3, 2, 1])
        with col_gen:
            target_count = st.slider("Liczba słów:", 3, 40, 10)
            generate_clicked = st.button("Generuj Nową", type="primary")
        with col_back:
            if st.button("Menu"):
                st.session_state.current_view = 'main_menu'
                st.rerun()

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
            all_words = load_words(selected_set)
            if len(all_words) < 2:
                st.warning(f"Zestaw '{selected_set}' ma za mało słów.")
                return

            with st.spinner(f'Układam krzyżówkę...'):
                import random
                real_count = min(target_count, len(all_words))
                selection = random.sample(all_words, real_count)
                generator = CrosswordGenerator(selection)
                grid, clues_across, clues_down = generator.generate()

                word_starts = {}
                rows, cols = grid.shape
                for r in range(rows):
                    for c in range(cols):
                        cell = grid[r, c]
                        if isinstance(cell, dict) and 'number' in cell:
                            word_starts[(r, c)] = cell['number']

                st.session_state.crossword_data = (grid, clues_across, clues_down, word_starts)
                st.session_state.last_set = selected_set

            current_lang_for_ml = st.session_state.get('crossword_language', 'Polski')

            difficulty_report = {"ŁATWE": 0, "ŚREDNIE": 0, "TRUDNE": 0}

            for item in selection:
                word = item['word']
                clue = item['clue']

                pred, _, _ = ai_engine.predict(word, clue, current_lang_for_ml)

                difficulty_report[pred] += 1

            st.session_state.difficulty_stats = difficulty_report

    else:
        if 'crossword_data' not in st.session_state:
            st.error("Brak danych krzyżówki. Zeskanuj kod ponownie.")
            return

    if student_mode:
        st.markdown("---")
        st.subheader("Rozwiązane?")

        is_submitted = st.session_state.get('result_submitted', False)
        is_feedback_sent = st.session_state.get('feedback_sent', False)

        if not is_submitted:
            st.info("Gdy krzyżówka wyświetli komunikat o wygranej, wpisz swój czas ze stopera:")

            with st.form("submit_result_form"):
                c_time, c_btn = st.columns([2, 1])
                with c_time:
                    final_time = st.text_input("Twój czas (mm:ss):", placeholder="np. 02:45")
                with c_btn:
                    st.write("")
                    st.write("")
                    submitted = st.form_submit_button("Wyślij do Nauczyciela", type="primary")

                if submitted:
                    if not final_time:
                        st.error("Wpisz czas!")
                    else:
                        save_result(session_name, student_name, final_time)
                        st.session_state.result_submitted = True
                        st.rerun()

        else:
            st.success("Twój wynik został wysłany do nauczyciela! Możesz zamknąć stronę.")

            if not is_feedback_sent:
                st.markdown("---")
                st.subheader("Pomóż nam ulepszyć grę!")
                st.write("Zaznacz słowa, które sprawiły Ci największą trudność:")

                words_in_puzzle = []
                if 'crossword_data' in st.session_state:
                    grid = st.session_state.crossword_data[0]
                    for item in selection:
                        words_in_puzzle.append(item['word'])

                with st.form("learning_feedback"):
                    hard_words = st.multiselect(
                        "Wybierz trudne słowa:",
                        options=words_in_puzzle
                    )

                    if st.form_submit_button("Wyślij opinię"):
                        feedback_data = []
                        current_lang = st.session_state.get('crossword_language', 'Polski')

                        for w in hard_words:
                            feedback_data.append((w, "User Feedback", current_lang, "TRUDNE"))

                        easy_words = set(words_in_puzzle) - set(hard_words)
                        for w in easy_words:
                            feedback_data.append((w, "User Feedback", current_lang, "ŁATWE"))

                        save_student_feedback(feedback_data)

                        st.session_state.feedback_sent = True
                        st.balloons()
                        st.rerun()

            else:
                st.info("Dziękujemy za przesłanie opinii! 🙏")

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
                    grid_html += f'<div class="cell input-cell"><input type="text" maxlength="1" id="input-{r}-{c}" data-row="{r}" data-col="{c}" data-correct="{correct_letter}" data-parent-across="{p_across}" data-parent-down="{p_down}"></div>'

        cell_size = (700 / ROWS) * 1.2
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <style>
            :root {{
                --cell-size: {cell_size}px;
                --font-size: 20px;
                --gap-size: 2px;
                --btn-color: #28a745;
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
                margin: 0;
                padding: 0;
                width: 100%;
                box-sizing: border-box;
                touch-action: manipulation;
            }}

            .controls-bar {{
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 15px;
                margin-bottom: 10px;
                padding: 5px;
            }}

            .timer-display {{
                font-size: 18px;
                font-weight: bold;
                color: #333;
                background: #f0f0f0;
                padding: 5px 10px;
                border-radius: 4px;
                min-width: 60px;
                text-align: center;
                border: 1px solid #ccc;
            }}

            .check-btn {{
                background-color: var(--btn-color);
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 16px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
                transition: background-color 0.2s;
            }}

            .check-btn:hover {{ background-color: #218838; }}
            .check-btn:active {{ transform: scale(0.98); }}

            .scroll-wrapper {{
                width: 100%;
                overflow-x: auto;
                display: flex;
                justify-content: safe center;
                padding-bottom: 20px;
            }}
            @supports not (justify-content: safe center) {{
                .scroll-wrapper {{ display: block; text-align: center; }}
            }}

            .main-container {{
                display: inline-block;
                padding: 0 10px;
            }}

            .crossword {{
                display: grid;
                grid-template-columns: repeat({COLS}, var(--cell-size));
                grid-template-rows: repeat({ROWS}, var(--cell-size));
                gap: var(--gap-size);
                background: #222;
                padding: 4px;
                border-radius: 4px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                margin: 0 auto;
            }}

            .cell {{ width: var(--cell-size); height: var(--cell-size); position: relative; box-sizing: border-box; }}
            .block {{ background: #000; }}

            .number-cell {{
                background-color: #FF8C00; color: white; font-weight: bold;
                display: flex; justify-content: center; align-items: center;
                font-size: calc(var(--cell-size) * 0.5);
                cursor: help; position: relative;
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
        </style>
        </head>
        <body>
            <div class="controls-bar">
                <div class="timer-display" id="timer">00:00</div>
                <button class="check-btn" onclick="checkAnswers()">Sprawdź</button>
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

                // --- STOPER ---
                let startTime = Date.now();
                let timerInterval;
                let isSolved = false;

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

                function checkAnswers() {{
                    if (isSolved) return;

                    const inputs = document.querySelectorAll('input');
                    let errors = 0;
                    let empty = 0;

                    inputs.forEach(input => {{
                        const val = input.value.toUpperCase();
                        const correct = input.getAttribute("data-correct");

                        input.classList.remove("valid", "invalid");

                        if (val.length === 0) {{
                            empty++;
                        }} else if (val === correct) {{
                            input.classList.add("valid");
                        }} else {{
                            input.classList.add("invalid");
                            errors++;
                        }}
                    }});

                    if (errors === 0 && empty === 0) {{
                        isSolved = true;
                        clearInterval(timerInterval);
                        const finalTime = document.getElementById("timer").innerText;

                        alert("Gratulacje! Rozwiązano w czasie: " + finalTime);

                        inputs.forEach(i => i.disabled = true);
                    }}
                }}

                function clearValidation(input) {{
                    input.classList.remove("valid", "invalid");
                }}

                function updateTooltip(input) {{
                    document.querySelectorAll('.tooltip.force-visible').forEach(el => {{
                        el.classList.remove('force-visible');
                    }});
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
                    for (let w of wordOrder) {{
                        let r = w.r; let c = w.c; let dir = w.dir;
                        let dr = (dir === 'across') ? 0 : 1;
                        let dc = (dir === 'across') ? 1 : 0;
                        let isWordFull = true; let firstEmptyInput = null;
                        let currR = r + dr; let currC = c + dc;

                        while (true) {{
                            let el = document.getElementById("input-" + currR + "-" + currC);
                            if (!el) break;
                            if (el.value.length === 0) {{
                                isWordFull = false;
                                if (!firstEmptyInput) firstEmptyInput = el;
                            }}
                            currR += dr; currC += dc;
                        }}

                        if (!isWordFull && firstEmptyInput) {{
                            currentDirection = dir;
                            firstEmptyInput.focus();
                            return;
                        }}
                    }}
                }}

                function moveFocus(e) {{
                    const input = e.target;
                    let r = parseInt(input.getAttribute('data-row'));
                    let c = parseInt(input.getAttribute('data-col'));

                    if (e.key === 'Backspace') {{
                        if (input.value.length === 0) {{
                            if (currentDirection === 'across') c--;
                            if (currentDirection === 'down') r--;
                            const target = document.getElementById("input-" + r + "-" + c);
                            if (target) {{ e.preventDefault(); target.focus(); }}
                        }}
                        return;
                    }}
                    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) return;

                    if (e.key === 'ArrowUp') {{ r--; currentDirection = 'down'; }}
                    if (e.key === 'ArrowDown') {{ r++; currentDirection = 'down'; }}
                    if (e.key === 'ArrowLeft') {{ c--; currentDirection = 'across'; }}
                    if (e.key === 'ArrowRight') {{ c++; currentDirection = 'across'; }}

                    const target = document.getElementById("input-" + r + "-" + c);
                    if (target) {{ e.preventDefault(); target.focus(); }}
                }}

                function handleInput(e) {{
                    const input = e.target;

                    clearValidation(input);

                    if (input.value.length === 1) {{
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
                    const pAcross = input.getAttribute('data-parent-across');
                    const pDown = input.getAttribute('data-parent-down');
                    if (pAcross && !pDown) currentDirection = 'across';
                    if (!pAcross && pDown) currentDirection = 'down';
                    updateTooltip(input);
                }}

                const inputs = document.querySelectorAll('input');
                inputs.forEach(input => {{
                    input.addEventListener('input', handleInput);
                    input.addEventListener('keydown', moveFocus);
                    input.addEventListener('focus', function() {{ handleFocus(this); }});
                }});

                document.body.addEventListener('click', function(e) {{
                    if (e.target.tagName !== 'INPUT' && e.target.className !== 'check-btn') {{
                         document.querySelectorAll('.tooltip.force-visible').forEach(el => {{ el.classList.remove('force-visible'); }});
                    }}
                }});
            </script>
        </body>
        </html>
        """

        iframe_height = (ROWS * 37) + 120
        components.html(full_html, height=iframe_height, scrolling=True)

        # ==================================================
        # 4. EKSPORT (TYLKO DLA NAUCZYCIELA)
        # ==================================================
        if not student_mode:
            with col_export:
                with st.popover("Udostępnij / Zapisz Sesję", use_container_width=True):
                    st.subheader("Utwórz sesję dla uczniów")

                    new_session_name = st.text_input("Nazwa sesji (np. Klasa 4B):", placeholder="Wpisz nazwę...")

                    if st.button("Zapisz Sesję i Pokaż QR", type="primary"):
                        if not new_session_name:
                            st.error("Podaj nazwę sesji!")
                        else:
                            raw_code = encode_crossword(st.session_state.crossword_data)

                            save_session(new_session_name, st.session_state.crossword_data, raw_code)
                            st.success(f"Zapisano sesję: {new_session_name}")

                            safe_name = urllib.parse.quote(new_session_name)
                            full_link = f"{APP_BASE_URL}/?data={raw_code}&name={safe_name}"

                            st.image(generate_qr_image(full_link), use_container_width=True)
                            st.caption("Link bezpośredni:")
                            st.code(full_link, language="text")

                if not student_mode and 'difficulty_stats' in st.session_state:
                    st.subheader("Analiza Trudności (wg Twojego AI)")
                    stats = st.session_state.difficulty_stats

                    k1, k2, k3 = st.columns(3)
                    k1.metric("Łatwe", stats["ŁATWE"])
                    k2.metric("Średnie", stats["ŚREDNIE"])
                    k3.metric("Trudne", stats["TRUDNE"])

                    if stats["TRUDNE"] > stats["ŁATWE"]:
                        st.warning("Uwaga! Twoje AI uważa, że ta krzyżówka może być trudna dla uczniów.")
                    else:
                        st.success("Poziom trudności wydaje się odpowiedni.")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("POZIOMO")
        if clues_across:
            for x in clues_across: st.text(x)
    with c2:
        st.subheader("PIONOWO")
        if clues_down:
            for x in clues_down: st.text(x)