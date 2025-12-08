import numpy as np


GRID_SIZE = 20


class CrosswordGenerator:
    def __init__(self, data, size=GRID_SIZE):
        self.size = size
        self.data = sorted(data, key=lambda x: len(x['word']), reverse=True)

        # Grid roboczy
        self.grid = np.full((self.size, self.size), None, dtype=object)

        # Listy wynikowe
        self.clues_across = []
        self.clues_down = []

    def generate(self):
        """Główna metoda uruchamiająca proces generowania."""
        self.grid = np.full((self.size, self.size), None, dtype=object)

        success = self._backtrack(self.data)

        if np.any(self.grid != None):
            return self._finalize_grid()
        else:
            return self.grid, [], []

    def _backtrack(self, words_to_place):
        """
        Rekurencyjna funkcja (serce algorytmu).
        Próbuje ułożyć słowa jedno po drugim. Jeśli utknie, cofa się.
        """
        if not words_to_place:
            return True

        current_word_data = words_to_place[0]
        word = current_word_data['word'].upper()

        is_first_word = np.all(self.grid == None)

        possible_moves = self._find_all_moves(word)

        if is_first_word:
            mid = self.size // 2
            start_col = max(1, mid - len(word) // 2)
            possible_moves = [
                (mid, start_col, 'across', 0),
                (start_col, mid, 'down', 0)
            ]
        else:
            possible_moves = [m for m in possible_moves if m[3] > 0]
            possible_moves.sort(key=lambda x: x[3], reverse=True)

        if not possible_moves:
            return self._backtrack(words_to_place[1:])

        for move in possible_moves:
            r, c, direction, score = move

            grid_backup = self.grid.copy()

            self._place_word_temp(word, current_word_data, r, c, direction)

            if self._backtrack(words_to_place[1:]):
                return True

            self.grid = grid_backup

        return self._backtrack(words_to_place[1:])

    def _find_all_moves(self, word):
        """Skanuje planszę w poszukiwaniu miejsc na słowo."""
        moves = []
        for r in range(1, self.size - 1):
            for c in range(1, self.size - 1):
                if self._can_place(word, r, c, 'across'):
                    score = self._calculate_score(word, r, c, 'across')
                    moves.append((r, c, 'across', score))

                if self._can_place(word, r, c, 'down'):
                    score = self._calculate_score(word, r, c, 'down')
                    moves.append((r, c, 'down', score))
        return moves

    def _calculate_score(self, word, r, c, direction):
        """Liczy ile liter się pokrywa (intersections)."""
        score = 0
        for i, char in enumerate(word):
            rr, cc = (r, c + 1 + i) if direction == 'across' else (r + 1 + i, c)
            cell = self.grid[rr, cc]
            if isinstance(cell, str) and cell == char:
                score += 1
        return score

    def _can_place(self, word, r_num, c_num, direction):
        """Sprawdza kolizje i zasady sąsiedztwa."""
        length = len(word)

        if self.grid[r_num, c_num] is not None:
            return False

        r_start, c_start = (r_num, c_num + 1) if direction == 'across' else (r_num + 1, c_num)

        if direction == 'across':
            if c_start + length >= self.size: return False
        else:
            if r_start + length >= self.size: return False

        for i in range(length):
            rr = r_start + (0 if direction == 'across' else i)
            cc = c_start + (i if direction == 'across' else 0)

            cell = self.grid[rr, cc]
            char = word[i]

            if cell is None:
                if not self._check_neighbors_empty(rr, cc, direction):
                    return False
            elif isinstance(cell, str):
                if cell != char:
                    return False
            else:
                return False

        r_prev, c_prev = (r_num, c_num - 1) if direction == 'across' else (r_num - 1, c_num)
        if 0 <= r_prev < self.size and 0 <= c_prev < self.size:
            if self.grid[r_prev, c_prev] is not None: return False

        r_after = r_start + (0 if direction == 'across' else length)
        c_after = c_start + (length if direction == 'across' else 0)
        if 0 <= r_after < self.size and 0 <= c_after < self.size:
            if self.grid[r_after, c_after] is not None: return False

        return True

    def _check_neighbors_empty(self, r, c, direction):
        """Sprawdza sąsiadów prostopadłych, aby zachować odstęp między równoległymi słowami."""
        if direction == 'across':
            neighbors = [(r - 1, c), (r + 1, c)]
        else:
            neighbors = [(r, c - 1), (r, c + 1)]

        for nr, nc in neighbors:
            if 0 <= nr < self.size and 0 <= nc < self.size:
                if self.grid[nr, nc] is not None:
                    return False
        return True

    def _place_word_temp(self, word, word_data, r, c, direction):
        """Wstawia słowo jako placeholder (bez finalnego numeru)."""
        self.grid[r, c] = {
            'type': 'number_placeholder',
            'clue': word_data['clue'],
            'direction': direction,
            'word_len': len(word)
        }
        for i, char in enumerate(word):
            rr = r + (0 if direction == 'across' else 1 + i)
            cc = c + (1 + i if direction == 'across' else 0)
            self.grid[rr, cc] = char

    def _finalize_grid(self):
        """Konwertuje placeholdery na finalne numery (1, 2, 3...) czytając od góry."""
        self.clues_across = []
        self.clues_down = []
        current_num = 1

        for r in range(self.size):
            for c in range(self.size):
                cell = self.grid[r, c]
                if isinstance(cell, dict) and cell.get('type') == 'number_placeholder':
                    final_cell = {
                        'number': current_num,
                        'clue': cell['clue'],
                        'direction': cell['direction']
                    }
                    self.grid[r, c] = final_cell

                    clue_text = f"{current_num}. {cell['clue']} ({cell['word_len']})"
                    if cell['direction'] == 'across':
                        self.clues_across.append(clue_text)
                    else:
                        self.clues_down.append(clue_text)

                    current_num += 1

        return self.grid, self.clues_across, self.clues_down