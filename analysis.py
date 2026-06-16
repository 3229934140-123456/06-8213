from text_breaking import (
    tokenize, GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter,
    compute_line_width, compute_break_penalty, generate_candidate_breakpoints,
    BreakPointType
)


def print_separator(char='=', length=90):
    print(char * length)


def run_detailed_comparison():
    print_separator()
    print("贪心断行 vs Knuth-Plass - 深度对比分析")
    print_separator()
    
    long_text = (
        "The Knuth-Plass line breaking algorithm is a dynamic programming approach to "
        "typography that was developed by Donald Knuth and Michael Plass in 1981. "
        "It is widely regarded as one of the best algorithms for determining where "
        "to break lines in a paragraph to produce the most visually pleasing result. "
        "Unlike greedy algorithms that make decisions one line at a time, Knuth-Plass "
        "considers the entire paragraph globally, optimizing the overall appearance "
        "by minimizing the sum of penalties associated with each possible line break. "
        "This approach significantly reduces the occurrence of rivers, which are "
        "unsightly gaps that appear to flow through a paragraph when spaces on "
        "successive lines align vertically. The algorithm also handles hyphenation "
        "intelligently, choosing appropriate break points within words when necessary."
    )
    
    target_width = 10.0
    words = tokenize(long_text)
    
    print(f"\n段落长度: {len(words)} 个词")
    print(f"目标行宽: {target_width} 单位 (约 {int(target_width / 0.4)} 字符)")
    print(f"原文预览: {long_text[:100]}...")
    print()
    
    greedy = GreedyLineBreaker(target_width)
    kp = KnuthPlassLineBreaker(target_width)
    typesetter = Typesetter(target_width, justify=True)
    
    greedy_layout = greedy.break_lines(words)
    kp_layout = kp.break_lines(words)
    
    greedy_text, greedy_analysis = typesetter.render_with_analysis(greedy_layout)
    kp_text, kp_analysis = typesetter.render_with_analysis(kp_layout)
    
    col_width = int(target_width / 0.4) + 25
    
    print(f"{' 贪心断行 ':=^{col_width}} | {' Knuth-Plass ':=^{col_width}}")
    print(f"{'  行数: ' + str(len(greedy_layout.lines)) + '  惩罚: ' + f'{greedy_layout.total_penalty:.1f}':<{col_width}} | {'  行数: ' + str(len(kp_layout.lines)) + '  惩罚: ' + f'{kp_layout.total_penalty:.1f}':<{col_width}}")
    print(f"{'-' * col_width} | {'-' * col_width}")
    
    greedy_lines = greedy_text.split('\n')
    kp_lines = kp_text.split('\n')
    
    max_lines = max(len(greedy_lines), len(kp_lines))
    
    loose_greedy = 0
    loose_kp = 0
    tight_greedy = 0
    tight_kp = 0
    normal_greedy = 0
    normal_kp = 0
    
    for i in range(max_lines):
        g_line = greedy_lines[i] if i < len(greedy_lines) else ''
        k_line = kp_lines[i] if i < len(kp_lines) else ''
        
        g_a = greedy_analysis[i] if i < len(greedy_analysis) else None
        k_a = kp_analysis[i] if i < len(kp_analysis) else None
        
        g_info = ''
        if g_a:
            mark = '⚠️ ' if g_a['tightness'] != 'normal' else '✓ '
            g_info = f" {mark}{g_a['tightness']:6s} r={g_a['adjustment_ratio']:5.2f}"
            if g_a['tightness'] == 'loose': loose_greedy += 1
            elif g_a['tightness'] == 'tight': tight_greedy += 1
            else: normal_greedy += 1
        
        k_info = ''
        if k_a:
            mark = '⚠️ ' if k_a['tightness'] != 'normal' else '✓ '
            k_info = f" {mark}{k_a['tightness']:6s} r={k_a['adjustment_ratio']:5.2f}"
            if k_a['tightness'] == 'loose': loose_kp += 1
            elif k_a['tightness'] == 'tight': tight_kp += 1
            else: normal_kp += 1
        
        g_display = g_line[:col_width - 25]
        k_display = k_line[:col_width - 25]
        
        print(f"{g_display:<{col_width - 25}}{g_info} | {k_display:<{col_width - 25}}{k_info}")
    
    print(f"{'=' * col_width} | {'=' * col_width}")
    
    penalty_improvement = greedy_layout.total_penalty - kp_layout.total_penalty
    print(f"{'KP 惩罚降低: ' + f'{penalty_improvement:.1f} ({(penalty_improvement/greedy_layout.total_penalty*100):.1f}%)':>{col_width * 2 + 3}}")
    
    print(f"\n{'':^{col_width}} | 质量统计:")
    print(f"{'  正常: ' + str(normal_greedy) + '/' + str(len(greedy_lines)):^{col_width}} | {'  正常: ' + str(normal_kp) + '/' + str(len(kp_lines)):^{col_width}}")
    print(f"{'  过松: ' + str(loose_greedy) + '/' + str(len(greedy_lines)):^{col_width}} | {'  过松: ' + str(loose_kp) + '/' + str(len(kp_lines)):^{col_width}}")
    print(f"{'  过紧: ' + str(tight_greedy) + '/' + str(len(greedy_lines)):^{col_width}} | {'  过紧: ' + str(tight_kp) + '/' + str(len(kp_lines)):^{col_width}}")
    
    print()
    show_dp_example(words, target_width)
    show_hyphenation_example(words)
    show_punctuation_analysis(words, target_width)


def show_dp_example(words, target_width):
    print_separator()
    print("动态规划求解过程示例")
    print_separator()
    
    sample_words = words[:8]
    print(f"\n示例词序列: {[w.text for w in sample_words]}")
    print(f"目标行宽: {target_width} 单位")
    print()
    
    from text_breaking import Glue
    space_glue = Glue(0.3, 0.4, 0.6, 0.2, 0.1)
    
    breakpoints = generate_candidate_breakpoints(sample_words)
    print(f"候选断点数量: {len(breakpoints)}")
    for bp in breakpoints[:6]:
        btype = bp.type.value
        text = sample_words[bp.word_index].text
        if bp.type == BreakPointType.HYPHEN:
            text = bp.hyphenated_text
        print(f"  位置 {bp.word_index} ({text}): {btype}, 惩罚={bp.penalty:.2f}")
    print("  ...")
    print()
    
    print("dp 状态转移示意:")
    print("-" * 70)
    print(f"{'i':<3} {'词':<15} {'可能的 j':<20} {'dp[i]':<10} {'最优断点':<20}")
    print("-" * 70)
    
    n = len(sample_words)
    dp = [float('inf')] * (n + 1)
    dp[0] = 0
    prev = [-1] * (n + 1)
    
    for i in range(1, n + 1):
        options = []
        for j in range(0, i):
            line_words = sample_words[j:i]
            bp = None
            for b in breakpoints:
                if b.word_index == i - 1:
                    bp = b
                    break
            
            if bp is None:
                continue
            
            num_spaces = 0
            for k in range(len(line_words) - 1):
                if not line_words[k + 1].is_punctuation:
                    num_spaces += 1
            
            line_width = compute_line_width(line_words, 0, len(line_words) - 1, bp, space_glue)
            
            penalty = compute_break_penalty(
                sample_words, j, i - 1, bp,
                line_width, target_width, space_glue, num_spaces
            )
            
            if dp[j] + penalty < dp[i]:
                dp[i] = dp[j] + penalty
                prev[i] = j
            
            options.append(f"{j}(p={penalty:.0f})")
        
        word_text = sample_words[i - 1].text if i <= n else ''
        best_j = prev[i]
        best_bp = f"在 {best_j} 后换行" if best_j != -1 else "N/A"
        options_str = ', '.join(options[:3])
        if len(options) > 3:
            options_str += "..."
        
        print(f"{i:<3} {word_text:<15} {options_str:<20} {dp[i]:<10.1f} {best_bp:<20}")
    
    print()
    print("回溯最优解:")
    current = n
    line_num = 1
    while current > 0:
        prev_idx = prev[current]
        line = sample_words[prev_idx:current]
        words_str = ' '.join(w.text for w in line)
        print(f"  行 {line_num}: [{words_str}]")
        current = prev_idx
        line_num += 1
    print()


def show_hyphenation_example(words):
    print_separator()
    print("连字符断词点分析")
    print_separator()
    
    from text_breaking import Word, find_hyphenation_points, measure_text
    
    test_long_words = ["extraordinary", "programming", "algorithm", "development"]
    
    for word_text in test_long_words:
        word = Word(text=word_text, width=measure_text(word_text))
        points = find_hyphenation_points(word)
        
        print(f"\n单词: {word_text}")
        if points:
            print(f"  可能的断词点 (按质量排序):")
            sorted_points = sorted(points, key=lambda x: x[1])
            for pos, penalty in sorted_points:
                quality = "优" if penalty < 1.0 else "中" if penalty < 2.0 else "差"
                print(f"    {word_text[:pos]}-{word_text[pos:]} (惩罚: {penalty:.2f}, 质量: {quality})")
        else:
            print(f"  无可断词点")
    print()


def show_punctuation_analysis(words, target_width):
    print_separator()
    print("行尾标点孤立处理分析")
    print_separator()
    
    sample_text = "This is a test, to show how punctuation stays with words. It should not be alone!"
    sample_words = tokenize(sample_text)
    
    print(f"\n示例文本: {sample_text}")
    print(f"分词结果: {[w.text + '(标点)' if w.is_punctuation else w.text for w in sample_words]}")
    print()
    
    print("断点惩罚分析:")
    print("-" * 80)
    print(f"{'断点位置':<10} {'断后文本':<20} {'下一个词':<15} {'惩罚':<10} {'原因':<25}")
    print("-" * 80)
    
    from text_breaking import Glue, compute_break_penalty, BreakPoint, BreakPointType
    space_glue = Glue(0.3, 0.4, 0.6, 0.2, 0.1)
    
    for i in range(len(sample_words) - 1):
        bp = BreakPoint(word_index=i, type=BreakPointType.SPACE, penalty=0)
        
        line_words = sample_words[:i + 1]
        num_spaces = 0
        for k in range(len(line_words) - 1):
            if not line_words[k + 1].is_punctuation:
                num_spaces += 1
        
        line_width = compute_line_width(line_words, 0, len(line_words) - 1, bp, space_glue)
        penalty = compute_break_penalty(
            sample_words, 0, i, bp, line_width, target_width, space_glue, num_spaces
        )
        
        next_word = sample_words[i + 1].text
        reason = []
        if sample_words[i + 1].is_punctuation:
            reason.append("下一个是标点(+200)")
        if sample_words[i].is_punctuation:
            reason.append("行尾是标点(-10)")
        
        reason_str = ', '.join(reason) if reason else "无特殊惩罚"
        
        print(f"{i:<10} {sample_words[i].text:<20} {next_word:<15} {penalty:<10.1f} {reason_str:<25}")
    
    print()
    print("惩罚机制说明:")
    print("  • 如果下一个词是标点符号，断点惩罚 +200")
    print("    → 强烈阻止在标点前换行，避免行首出现孤立标点")
    print("  • 如果行尾是标点符号，断点惩罚 -10")
    print("    → 鼓励将标点留在行尾")
    print("  • 松紧度惩罚 = 100 * |ratio|³")
    print("    → 行宽偏离目标越多，惩罚越大（立方增长）")
    print()


if __name__ == "__main__":
    run_detailed_comparison()
