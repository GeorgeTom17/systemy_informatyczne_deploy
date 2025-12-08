import base64
import zlib
import numpy as np

# Separatory
SEP_MAIN = "|"
SEP_ITEM = ";"
SEP_VAL = ":"


def encode_crossword(grid_data):
    """
    Eksportuje krzyżówkę do formatu V2:
    HEADER | METADATA (zawierająca słowa)
    """
    grid, clues_across, clues_down, word_starts = grid_data
    rows, cols = grid.shape

    metadata = []

    for r in range(rows):
        for c in range(cols):
            cell = grid[r, c]

            if isinstance(cell, dict) and 'number' in cell:
                number = cell['number']
                direction = cell['direction']  # 'across' lub 'down'
                dir_short = 'a' if direction == 'across' else 'd'

                word_str = ""
                curr_r, curr_c = r, c

                if direction == 'across':
                    curr_c += 1
                else:
                    curr_r += 1

                while 0 <= curr_r < rows and 0 <= curr_c < cols:
                    val = grid[curr_r, curr_c]
                    if isinstance(val, str):
                        word_str += val
                        if direction == 'across':
                            curr_c += 1
                        else:
                            curr_r += 1
                    else:
                        break

                safe_clue = str(cell['clue']).replace(SEP_MAIN, "").replace(SEP_ITEM, "").replace(SEP_VAL, "")

                entry = f"{r}{SEP_VAL}{c}{SEP_VAL}{number}{SEP_VAL}{dir_short}{SEP_VAL}{word_str}{SEP_VAL}{safe_clue}"
                metadata.append(entry)

    header = f"{rows}{SEP_VAL}{cols}"

    meta_str = SEP_ITEM.join(metadata)

    raw_data = f"{header}{SEP_MAIN}{meta_str}"

    compressed_data = zlib.compress(raw_data.encode('utf-8'), level=9)
    encoded_bytes = base64.urlsafe_b64encode(compressed_data)

    return encoded_bytes.decode('utf-8')


def decode_crossword(encoded_string):
    """
    Odtwarza krzyżówkę z formatu V2 (ze słowami w metadanych).
    """
    try:
        if not encoded_string:
            return None

        compressed_data = base64.urlsafe_b64decode(encoded_string.encode('utf-8'))
        raw_data = zlib.decompress(compressed_data).decode('utf-8')

        sections = raw_data.split(SEP_MAIN)


        if len(sections) == 2:
            header, meta_str = sections
        elif len(sections) == 3:
            return None
        else:
            return None

        rows, cols = map(int, header.split(SEP_VAL))
        grid = np.full((rows, cols), None, dtype=object)

        clues_across = []
        clues_down = []
        word_starts = {}

        if meta_str:
            for item in meta_str.split(SEP_ITEM):
                if not item: continue

                parts = item.split(SEP_VAL)

                if len(parts) >= 6:
                    r = int(parts[0])
                    c = int(parts[1])
                    num = int(parts[2])
                    dir_short = parts[3]
                    word_str = parts[4]
                    clue = parts[5]

                    direction = 'across' if dir_short == 'a' else 'down'

                    grid[r, c] = {
                        'number': num,
                        'clue': clue,
                        'direction': direction
                    }
                    word_starts[(r, c)] = num

                    curr_r, curr_c = r, c
                    if direction == 'across':
                        curr_c += 1
                    else:
                        curr_r += 1

                    for char in word_str:
                        grid[curr_r, curr_c] = char

                        if direction == 'across':
                            curr_c += 1
                        else:
                            curr_r += 1

                    clue_txt = f"{num}. {clue} ({len(word_str)})"
                    if direction == 'across':
                        clues_across.append(clue_txt)
                    else:
                        clues_down.append(clue_txt)

        clues_across.sort(key=lambda x: int(x.split('.')[0]))
        clues_down.sort(key=lambda x: int(x.split('.')[0]))

        return grid, clues_across, clues_down, word_starts

    except Exception as e:
        import streamlit as st
        st.error(f"Błąd importu kodu QR: {e}")
        return None