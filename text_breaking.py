from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import re
from enum import Enum


class BreakPointType(Enum):
    SPACE = "space"
    HYPHEN = "hyphen"
    FORCED = "forced"


@dataclass
class Word:
    text: str
    width: float
    is_punctuation: bool = False
    is_start_of_sentence: bool = False


@dataclass
class BreakPoint:
    word_index: int
    type: BreakPointType
    penalty: float = 0.0
    hyphenated_text: Optional[str] = None
    remaining_text: Optional[str] = None


@dataclass
class Glue:
    min_width: float
    ideal_width: float
    max_width: float
    stretchability: float = 0.0
    shrinkability: float = 0.0


@dataclass
class Line:
    words: List[Word]
    break_point: Optional[BreakPoint] = None
    glue: Glue = field(default_factory=lambda: Glue(0, 0, 0))
    actual_width: float = 0.0
    adjustment_ratio: float = 0.0


@dataclass
class LayoutResult:
    lines: List[Line]
    total_penalty: float
    algorithm: str


PUNCTUATION_SET = set('.,;:!?()[]{}"\'')
SENTENCE_END_PUNCTUATION = set('.!?')
CHAR_WIDTHS = {
    'i': 0.5, 'l': 0.5, 'j': 0.5, 't': 0.5, 'f': 0.5,
    'r': 0.6, 'c': 0.6, 's': 0.6, 'z': 0.6, 'e': 0.6,
    'a': 0.7, 'o': 0.7, 'n': 0.7, 'u': 0.7, 'v': 0.7, 'x': 0.7,
    'b': 0.75, 'd': 0.75, 'g': 0.75, 'h': 0.75, 'k': 0.75, 'p': 0.75, 'q': 0.75, 'y': 0.75,
    'm': 0.9, 'w': 0.9,
    ' ': 0.4,
    '-': 0.5,
    '.': 0.4, ',': 0.4, ';': 0.4, ':': 0.4, '!': 0.5, '?': 0.5,
    '(': 0.5, ')': 0.5, '[': 0.5, ']': 0.5, '{': 0.5, '}': 0.5,
    '"': 0.5, "'": 0.3,
}

DEFAULT_CHAR_WIDTH = 0.7


def measure_text(text: str) -> float:
    width = 0.0
    for ch in text:
        width += CHAR_WIDTHS.get(ch.lower(), DEFAULT_CHAR_WIDTH)
    return width


def is_punctuation(word: str) -> bool:
    return all(ch in PUNCTUATION_SET for ch in word)


def is_sentence_end(word: str) -> bool:
    return any(ch in SENTENCE_END_PUNCTUATION for ch in word)


def tokenize(text: str) -> List[Word]:
    tokens = re.findall(r'\w+|\S', text)
    words: List[Word] = []
    
    for i, token in enumerate(tokens):
        words.append(Word(
            text=token,
            width=measure_text(token),
            is_punctuation=is_punctuation(token),
            is_start_of_sentence=(i > 0 and is_sentence_end(tokens[i-1]))
        ))
    
    return words


def find_hyphenation_points(word: Word, hyphen_dict: Optional[dict] = None) -> List[Tuple[int, float]]:
    text = word.text
    lower_text = text.lower()
    
    if hyphen_dict and lower_text in hyphen_dict:
        dict_points = hyphen_dict[lower_text]
        if isinstance(dict_points, list):
            points = []
            for pos in dict_points:
                if isinstance(pos, int) and 2 <= pos <= len(text) - 2:
                    points.append((pos, 0.1))
            if points:
                return points
    
    points = []
    if len(text) < 5:
        return points
    
    vowels = set('aeiouAEIOU')
    
    for i in range(2, len(text) - 2):
        if text[i-1] not in vowels and text[i] in vowels:
            penalty = 1.0
        elif text[i-1] in vowels and text[i] not in vowels:
            penalty = 0.5
        else:
            penalty = 2.0
        
        if i < 3 or len(text) - i < 3:
            penalty += 1.0
        
        points.append((i, penalty))
    
    return points


def generate_candidate_breakpoints(words: List[Word], hyphen_dict: Optional[dict] = None) -> List[BreakPoint]:
    breakpoints: List[BreakPoint] = []
    
    for i, word in enumerate(words):
        if i < len(words) - 1:
            if word.is_punctuation:
                breakpoints.append(BreakPoint(
                    word_index=i,
                    type=BreakPointType.SPACE,
                    penalty=3.0
                ))
            else:
                breakpoints.append(BreakPoint(
                    word_index=i,
                    type=BreakPointType.SPACE,
                    penalty=0.0
                ))
        
        if not word.is_punctuation and len(word.text) >= 5:
            hyphen_points = find_hyphenation_points(word, hyphen_dict)
            for pos, penalty in hyphen_points:
                breakpoints.append(BreakPoint(
                    word_index=i,
                    type=BreakPointType.HYPHEN,
                    penalty=penalty,
                    hyphenated_text=word.text[:pos] + '-',
                    remaining_text=word.text[pos:]
                ))
    
    return breakpoints


def compute_line_width(
    words: List[Word],
    start: int,
    end: int,
    break_point: Optional[BreakPoint],
    space_glue: Glue
) -> float:
    width = 0.0
    for i in range(start, end + 1):
        width += words[i].width
        if i < end and not words[i + 1].is_punctuation:
            width += space_glue.ideal_width
    
    if break_point and break_point.type == BreakPointType.HYPHEN:
        width -= words[end].width
        width += measure_text(break_point.hyphenated_text)
    
    return width


def compute_break_penalty(
    words: List[Word],
    start: int,
    end: int,
    break_point: BreakPoint,
    line_width: float,
    target_width: float,
    space_glue: Glue,
    num_spaces: int
) -> float:
    if num_spaces > 0:
        adjustment = line_width - target_width
        if adjustment > 0:
            ratio = adjustment / (num_spaces * space_glue.shrinkability) if space_glue.shrinkability > 0 else float('inf')
        else:
            ratio = -adjustment / (num_spaces * space_glue.stretchability) if space_glue.stretchability > 0 else float('inf')
    else:
        ratio = abs(line_width - target_width)
    
    if ratio > 1:
        badness = 100 * (ratio ** 3)
    else:
        badness = 100 * (abs(ratio) ** 3)
    
    if break_point.type == BreakPointType.HYPHEN:
        break_penalty = 50 + break_point.penalty * 20
    else:
        break_penalty = break_point.penalty * 20
    
    if end < len(words) - 1 and words[end + 1].is_punctuation:
        break_penalty += 200
    
    if words[end].is_punctuation:
        break_penalty -= 10
    
    if words[end].is_start_of_sentence and end > start:
        break_penalty += 50
    
    return badness + break_penalty


class GreedyLineBreaker:
    def __init__(self, target_width: float, space_glue: Optional[Glue] = None, hyphen_dict: Optional[dict] = None):
        self.target_width = target_width
        self.space_glue = space_glue or Glue(
            min_width=0.3,
            ideal_width=0.4,
            max_width=0.6,
            stretchability=0.2,
            shrinkability=0.1
        )
        self.hyphen_dict = hyphen_dict
    
    def break_lines(self, words: List[Word]) -> LayoutResult:
        lines: List[Line] = []
        total_penalty = 0.0
        
        if not words:
            return LayoutResult(lines=[], total_penalty=0.0, algorithm="greedy")
        
        current_start = 0
        current_width = 0.0
        word_count = 0
        
        i = 0
        while i < len(words):
            word = words[i]
            is_first_in_line = (word_count == 0)
            
            additional_width = word.width
            if not is_first_in_line and not word.is_punctuation:
                additional_width += self.space_glue.ideal_width
            
            projected_width = current_width + additional_width
            
            if is_first_in_line or projected_width <= self.target_width:
                current_width = projected_width
                word_count += 1
                i += 1
                continue
            
            if i < len(words) and words[i].is_punctuation and word_count > 0:
                current_width += additional_width
                word_count += 1
                i += 1
                continue
            
            hyphen_bp = self._try_hyphenate_current_line(words, i, current_width)
            
            if hyphen_bp:
                line_words = words[current_start:i + 1]
                num_spaces = 0
                for j in range(len(line_words) - 1):
                    if not line_words[j + 1].is_punctuation:
                        num_spaces += 1
                
                line = self._make_line(line_words, hyphen_bp, num_spaces)
                lines.append(line)
                total_penalty += self._compute_line_penalty(words, current_start, i, hyphen_bp, line.actual_width, num_spaces)
                
                current_start = i + 1
                current_width = 0.0
                word_count = 0
            else:
                end_idx = i - 1
                
                if end_idx >= current_start and i < len(words) and words[i].is_punctuation and end_idx + 1 < len(words):
                    end_idx = i
                    i += 1
                
                line_words = words[current_start:end_idx + 1]
                num_spaces = 0
                for j in range(len(line_words) - 1):
                    if not line_words[j + 1].is_punctuation:
                        num_spaces += 1
                
                break_point = BreakPoint(
                    word_index=end_idx,
                    type=BreakPointType.SPACE
                )
                
                line = self._make_line(line_words, break_point, num_spaces)
                lines.append(line)
                total_penalty += self._compute_line_penalty(words, current_start, end_idx, break_point, line.actual_width, num_spaces)
                
                current_start = i
                current_width = 0.0
                word_count = 0
        
        if word_count > 0:
            end_idx = len(words) - 1
            line_words = words[current_start:end_idx + 1]
            num_spaces = 0
            for j in range(len(line_words) - 1):
                if not line_words[j + 1].is_punctuation:
                    num_spaces += 1
            
            break_point = BreakPoint(
                word_index=end_idx,
                type=BreakPointType.FORCED,
                penalty=-1000
            )
            
            line = self._make_line(line_words, break_point, num_spaces, is_last=True)
            lines.append(line)
        
        lines = self._fix_punctuation_orphans(lines, words)
        
        return LayoutResult(lines=lines, total_penalty=total_penalty, algorithm="greedy")
    
    def _try_hyphenate_current_line(self, words, word_idx, current_width):
        if word_idx <= 0 or word_idx >= len(words):
            return None
        
        word = words[word_idx]
        if word.is_punctuation or len(word.text) < 5:
            return None
        
        hyphen_points = find_hyphenation_points(word, self.hyphen_dict)
        if not hyphen_points:
            return None
        
        available = self.target_width - current_width - self.space_glue.ideal_width
        if available <= 0:
            return None
        
        best_bp = None
        best_fill = -1
        
        for pos, penalty in hyphen_points:
            hyp_text = word.text[:pos] + '-'
            hyp_width = measure_text(hyp_text)
            if hyp_width <= available:
                fill = hyp_width / available
                if fill > best_fill:
                    best_fill = fill
                    best_bp = BreakPoint(
                        word_index=word_idx - 1,
                        type=BreakPointType.HYPHEN,
                        penalty=penalty,
                        hyphenated_text=hyp_text,
                        remaining_text=word.text[pos:]
                    )
        
        return best_bp
    
    def _fix_punctuation_orphans(self, lines: List[Line], all_words: List[Word]) -> List[Line]:
        if len(lines) < 2:
            return lines
        
        changed = True
        while changed:
            changed = False
            new_lines = []
            i = 0
            while i < len(lines):
                current_line = lines[i]
                is_last = (i == len(lines) - 1)
                need_merge = False
                
                if current_line.words and current_line.words[0].is_punctuation and i > 0:
                    if not is_last:
                        need_merge = True
                    elif is_last and all(w.is_punctuation for w in current_line.words):
                        need_merge = True
                    elif is_last and current_line.words[0].is_punctuation:
                        need_merge = True
                
                if need_merge:
                    prev_line = new_lines[-1] if new_lines else lines[i - 1]
                    merge_words = []
                    
                    if is_last and all(w.is_punctuation for w in current_line.words):
                        merge_words = current_line.words
                    elif current_line.words[0].is_punctuation:
                        merge_words = [current_line.words[0]]
                    
                    if merge_words:
                        merged_words = prev_line.words + merge_words
                        merged_num_spaces = 0
                        for j in range(len(merged_words) - 1):
                            if not merged_words[j + 1].is_punctuation:
                                merged_num_spaces += 1
                        
                        remaining_words = current_line.words[len(merge_words):]
                        is_really_last = is_last and len(remaining_words) == 0
                        
                        if is_really_last:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words) if prev_line.break_point else 0,
                                type=BreakPointType.FORCED,
                                penalty=-1000
                            )
                        elif prev_line.break_point and prev_line.break_point.type == BreakPointType.HYPHEN:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words),
                                type=BreakPointType.HYPHEN,
                                penalty=prev_line.break_point.penalty,
                                hyphenated_text=prev_line.break_point.hyphenated_text,
                                remaining_text=prev_line.break_point.remaining_text
                            )
                        else:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words) if prev_line.break_point else 0,
                                type=BreakPointType.FORCED,
                                penalty=-1000
                            )
                        
                        merged_line = self._make_line(merged_words, merged_bp, merged_num_spaces, is_last=True)
                        
                        if new_lines:
                            new_lines[-1] = merged_line
                        else:
                            new_lines.append(merged_line)
                        
                        remaining_words = current_line.words[len(merge_words):]
                        if remaining_words:
                            rem_num_spaces = 0
                            for j in range(len(remaining_words) - 1):
                                if not remaining_words[j + 1].is_punctuation:
                                    rem_num_spaces += 1
                            rem_line = self._make_line(remaining_words, current_line.break_point, rem_num_spaces, is_last=is_last)
                            new_lines.append(rem_line)
                        
                        changed = True
                    else:
                        new_lines.append(current_line)
                else:
                    new_lines.append(current_line)
                
                i += 1
            
            lines = new_lines
        
        return lines
    
    def _make_line(self, words: List[Word], break_point: BreakPoint, num_spaces: int, is_last: bool = False) -> Line:
        line_width = compute_line_width(words, 0, len(words) - 1, break_point, self.space_glue)
        
        if is_last:
            adjustment_ratio = 0.0
        elif num_spaces > 0:
            diff = self.target_width - line_width
            if diff >= 0:
                adjustment_ratio = diff / (num_spaces * self.space_glue.stretchability) if self.space_glue.stretchability > 0 else 0
            else:
                adjustment_ratio = diff / (num_spaces * self.space_glue.shrinkability) if self.space_glue.shrinkability > 0 else 0
        else:
            adjustment_ratio = 0.0
        
        return Line(
            words=words,
            break_point=break_point,
            glue=self.space_glue,
            actual_width=line_width,
            adjustment_ratio=adjustment_ratio
        )
    
    def _compute_line_penalty(self, words: List[Word], start: int, end: int, break_point: BreakPoint, line_width: float, num_spaces: int) -> float:
        return compute_break_penalty(
            words, start, end,
            break_point, line_width, self.target_width,
            self.space_glue, num_spaces
        )


class KnuthPlassLineBreaker:
    def __init__(self, target_width: float, space_glue: Optional[Glue] = None, hyphen_dict: Optional[dict] = None):
        self.target_width = target_width
        self.space_glue = space_glue or Glue(
            min_width=0.3,
            ideal_width=0.4,
            max_width=0.6,
            stretchability=0.2,
            shrinkability=0.1
        )
        self.hyphen_dict = hyphen_dict
    
    def break_lines(self, words: List[Word]) -> LayoutResult:
        if not words:
            return LayoutResult(lines=[], total_penalty=0.0, algorithm="knuth-plass")
        
        breakpoints = generate_candidate_breakpoints(words, self.hyphen_dict)
        breakpoints.append(BreakPoint(
            word_index=len(words) - 1,
            type=BreakPointType.FORCED,
            penalty=-1000
        ))
        
        n = len(words)
        dp = [float('inf')] * (n + 1)
        dp[0] = 0.0
        prev = [-1] * (n + 1)
        selected_break = [None] * (n + 1)
        
        for i in range(1, n + 1):
            for bp in breakpoints:
                if bp.word_index != i - 1:
                    continue
                
                if i == n and bp.type != BreakPointType.FORCED:
                    continue
                
                for j in range(0, i):
                    if dp[j] == float('inf'):
                        continue
                    
                    line_words = words[j:i]
                    num_spaces = 0
                    for k in range(len(line_words) - 1):
                        if not line_words[k + 1].is_punctuation:
                            num_spaces += 1
                    line_width = compute_line_width(line_words, 0, len(line_words) - 1, bp, self.space_glue)
                    
                    if line_width > self.target_width * 2.5:
                        if bp.type != BreakPointType.FORCED or line_width > self.target_width * 3.5:
                            continue
                    
                    penalty = compute_break_penalty(
                        words, j, i - 1, bp,
                        line_width, self.target_width,
                        self.space_glue, num_spaces
                    )
                    
                    if bp.type == BreakPointType.FORCED:
                        if line_width <= self.target_width:
                            penalty = 0
                        else:
                            overflow = line_width - self.target_width
                            ratio = overflow / self.target_width
                            penalty = 100 * (overflow ** 2) * (1 + ratio)
                    
                    total = dp[j] + penalty
                    if total < dp[i]:
                        dp[i] = total
                        prev[i] = j
                        selected_break[i] = bp
        
        lines: List[Line] = []
        current = n
        while current > 0:
            prev_idx = prev[current]
            if prev_idx == -1:
                break
            
            line_words = words[prev_idx:current]
            bp = selected_break[current]
            num_spaces = 0
            for k in range(len(line_words) - 1):
                if not line_words[k + 1].is_punctuation:
                    num_spaces += 1
            
            is_last = (current == n)
            line = self._make_line(line_words, bp, num_spaces, is_last)
            lines.append(line)
            
            current = prev_idx
        
        lines.reverse()
        total_penalty = dp[n] if dp[n] != float('inf') else 0.0
        
        lines = self._fix_punctuation_orphans(lines, words)
        
        return LayoutResult(lines=lines, total_penalty=total_penalty, algorithm="knuth-plass")
    
    def _fix_punctuation_orphans(self, lines: List[Line], all_words: List[Word]) -> List[Line]:
        if len(lines) < 2:
            return lines
        
        changed = True
        while changed:
            changed = False
            new_lines = []
            i = 0
            while i < len(lines):
                current_line = lines[i]
                is_last = (i == len(lines) - 1)
                need_merge = False
                
                if current_line.words and current_line.words[0].is_punctuation and i > 0:
                    if not is_last:
                        need_merge = True
                    elif is_last and all(w.is_punctuation for w in current_line.words):
                        need_merge = True
                    elif is_last and current_line.words[0].is_punctuation:
                        need_merge = True
                
                if need_merge:
                    prev_line = new_lines[-1] if new_lines else lines[i - 1]
                    merge_words = []
                    
                    if is_last and all(w.is_punctuation for w in current_line.words):
                        merge_words = current_line.words
                    elif current_line.words[0].is_punctuation:
                        merge_words = [current_line.words[0]]
                    
                    if merge_words:
                        merged_words = prev_line.words + merge_words
                        merged_num_spaces = 0
                        for j in range(len(merged_words) - 1):
                            if not merged_words[j + 1].is_punctuation:
                                merged_num_spaces += 1
                        
                        remaining_words = current_line.words[len(merge_words):]
                        is_really_last = is_last and len(remaining_words) == 0
                        
                        if is_really_last:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words) if prev_line.break_point else 0,
                                type=BreakPointType.FORCED,
                                penalty=-1000
                            )
                        elif prev_line.break_point and prev_line.break_point.type == BreakPointType.HYPHEN:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words),
                                type=BreakPointType.HYPHEN,
                                penalty=prev_line.break_point.penalty,
                                hyphenated_text=prev_line.break_point.hyphenated_text,
                                remaining_text=prev_line.break_point.remaining_text
                            )
                        else:
                            merged_bp = BreakPoint(
                                word_index=prev_line.break_point.word_index + len(merge_words) if prev_line.break_point else 0,
                                type=BreakPointType.FORCED,
                                penalty=-1000
                            )
                        
                        merged_line = self._make_line(merged_words, merged_bp, merged_num_spaces, is_last=True)
                        
                        if new_lines:
                            new_lines[-1] = merged_line
                        else:
                            new_lines.append(merged_line)
                        
                        remaining_words = current_line.words[len(merge_words):]
                        if remaining_words:
                            rem_num_spaces = 0
                            for j in range(len(remaining_words) - 1):
                                if not remaining_words[j + 1].is_punctuation:
                                    rem_num_spaces += 1
                            rem_line = self._make_line(remaining_words, current_line.break_point, rem_num_spaces, is_last=is_last)
                            new_lines.append(rem_line)
                        
                        changed = True
                    else:
                        new_lines.append(current_line)
                else:
                    new_lines.append(current_line)
                
                i += 1
            
            lines = new_lines
        
        return lines
    
    def _make_line(self, words: List[Word], break_point: BreakPoint, num_spaces: int, is_last: bool = False) -> Line:
        line_width = compute_line_width(words, 0, len(words) - 1, break_point, self.space_glue)
        
        if is_last:
            adjustment_ratio = 0.0
        elif num_spaces > 0:
            diff = self.target_width - line_width
            if diff >= 0:
                adjustment_ratio = diff / (num_spaces * self.space_glue.stretchability) if self.space_glue.stretchability > 0 else 0
            else:
                adjustment_ratio = diff / (num_spaces * self.space_glue.shrinkability) if self.space_glue.shrinkability > 0 else 0
        else:
            adjustment_ratio = 0.0
        
        return Line(
            words=words,
            break_point=break_point,
            glue=self.space_glue,
            actual_width=line_width,
            adjustment_ratio=adjustment_ratio
        )


class Typesetter:
    def __init__(self, target_width: float, justify: bool = True):
        self.target_width = target_width
        self.justify = justify
    
    def render(self, layout: LayoutResult) -> str:
        rendered_lines = []
        pending_remaining = None
        
        for line in layout.lines:
            rendered_lines.append(self._render_line(line, pending_remaining))
            if line.break_point and line.break_point.type == BreakPointType.HYPHEN:
                pending_remaining = line.break_point.remaining_text
            else:
                pending_remaining = None
        
        return '\n'.join(rendered_lines)
    
    def _render_line(self, line: Line, pending_remaining: Optional[str] = None) -> str:
        words = line.words
        if not words:
            if pending_remaining:
                return pending_remaining
            return ''
        
        is_last_line = line.break_point and line.break_point.type == BreakPointType.FORCED
        num_spaces = len(words) - 1
        
        if self.justify and not is_last_line and num_spaces > 0:
            return self._render_justified(line, words, num_spaces, pending_remaining)
        else:
            return self._render_flush_left(line, words, pending_remaining)
    
    def _render_justified(self, line: Line, words: List[Word], num_spaces: int, pending_remaining: Optional[str] = None) -> str:
        natural_width = sum(w.width for w in words) + num_spaces * line.glue.ideal_width
        deficit = self.target_width - natural_width
        
        actual_spaces = 0
        for i in range(len(words) - 1):
            if not words[i + 1].is_punctuation:
                actual_spaces += 1
        
        base_space_width = line.glue.ideal_width
        extra_per_space = deficit / actual_spaces if actual_spaces > 0 else 0
        
        result = []
        for i, word in enumerate(words):
            text_to_add = ''
            
            if i == len(words) - 1 and line.break_point and line.break_point.type == BreakPointType.HYPHEN:
                text_to_add = line.break_point.hyphenated_text
            else:
                text_to_add = word.text
            
            if i == 0 and pending_remaining:
                result.append(pending_remaining)
                if not word.is_punctuation:
                    result.append(' ')
            
            result.append(text_to_add)
            
            if i < len(words) - 1:
                if words[i + 1].is_punctuation:
                    continue
                space_count = int(round((base_space_width + extra_per_space) / 0.4))
                space_count = max(1, space_count)
                result.append(' ' * space_count)
        
        rendered = ''.join(result)
        
        current_length = len(rendered)
        target_chars = int(self.target_width / 0.4)
        if current_length < target_chars:
            rendered += ' ' * (target_chars - current_length)
        elif current_length > target_chars:
            rendered = rendered[:target_chars]
        
        return rendered
    
    def _render_flush_left(self, line: Line, words: List[Word], pending_remaining: Optional[str] = None) -> str:
        result = []
        for i, word in enumerate(words):
            text_to_add = ''
            
            if i == len(words) - 1 and line.break_point and line.break_point.type == BreakPointType.HYPHEN:
                text_to_add = line.break_point.hyphenated_text
            else:
                text_to_add = word.text
            
            if i == 0 and pending_remaining:
                result.append(pending_remaining)
                if not word.is_punctuation:
                    result.append(' ')
            
            result.append(text_to_add)
            
            if i < len(words) - 1:
                if not words[i + 1].is_punctuation:
                    result.append(' ')
        
        return ''.join(result)
    
    def render_with_analysis(self, layout: LayoutResult) -> Tuple[str, List[dict]]:
        rendered_lines = []
        analysis = []
        pending_remaining = None
        
        for line_idx, line in enumerate(layout.lines):
            current_pending = pending_remaining
            rendered = self._render_line(line, current_pending)
            rendered_lines.append(rendered)
            
            if line.break_point and line.break_point.type == BreakPointType.HYPHEN:
                pending_remaining = line.break_point.remaining_text
            else:
                pending_remaining = None
            
            num_spaces = len(line.words) - 1
            tightness = "tight" if line.adjustment_ratio < -0.5 else \
                       "loose" if line.adjustment_ratio > 0.5 else "normal"
            
            words_text = []
            for i, w in enumerate(line.words):
                display_text = w.text
                if i == len(line.words) - 1 and line.break_point and line.break_point.type == BreakPointType.HYPHEN:
                    display_text = line.break_point.hyphenated_text
                
                if i == 0 and current_pending:
                    words_text.append(current_pending)
                    words_text.append(display_text)
                else:
                    words_text.append(display_text)
            
            analysis.append({
                'line_number': line_idx + 1,
                'words': words_text,
                'num_words': len(line.words),
                'num_spaces': num_spaces,
                'natural_width': round(line.actual_width, 2),
                'target_width': round(self.target_width, 2),
                'adjustment_ratio': round(line.adjustment_ratio, 2),
                'tightness': tightness,
                'break_type': line.break_point.type.value if line.break_point else 'none',
                'rendered_length': len(rendered)
            })
        
        return '\n'.join(rendered_lines), analysis


def compare_algorithms(text: str, target_width: float) -> dict:
    words = tokenize(text)
    
    greedy_breaker = GreedyLineBreaker(target_width)
    kp_breaker = KnuthPlassLineBreaker(target_width)
    typesetter = Typesetter(target_width, justify=True)
    
    greedy_layout = greedy_breaker.break_lines(words)
    kp_layout = kp_breaker.break_lines(words)
    
    greedy_text, greedy_analysis = typesetter.render_with_analysis(greedy_layout)
    kp_text, kp_analysis = typesetter.render_with_analysis(kp_layout)
    
    return {
        'target_width': target_width,
        'num_words': len(words),
        'greedy': {
            'text': greedy_text,
            'analysis': greedy_analysis,
            'total_penalty': greedy_layout.total_penalty,
            'num_lines': len(greedy_layout.lines),
            'tight_lines': sum(1 for a in greedy_analysis if a['tightness'] == 'tight'),
            'loose_lines': sum(1 for a in greedy_analysis if a['tightness'] == 'loose'),
            'normal_lines': sum(1 for a in greedy_analysis if a['tightness'] == 'normal'),
        },
        'knuth_plass': {
            'text': kp_text,
            'analysis': kp_analysis,
            'total_penalty': kp_layout.total_penalty,
            'num_lines': len(kp_layout.lines),
            'tight_lines': sum(1 for a in kp_analysis if a['tightness'] == 'tight'),
            'loose_lines': sum(1 for a in kp_analysis if a['tightness'] == 'loose'),
            'normal_lines': sum(1 for a in kp_analysis if a['tightness'] == 'normal'),
        }
    }
