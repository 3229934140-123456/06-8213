from text_breaking import (
    tokenize, GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter,
    compute_break_penalty, generate_candidate_breakpoints,
    BreakPointType
)


def print_separator(char='=', length=100):
    print(char * length)


def run_true_multiline_demo():
    print_separator()
    print("文本断行与排版引擎 - 真实多行对比")
    print_separator()
    
    very_long_text = (
        "The Knuth-Plass line breaking algorithm is one of the most important contributions "
        "to digital typography. Developed by Donald Knuth and Michael Plass in 1981, this "
        "algorithm revolutionized how computers handle paragraph layout. Unlike the simple "
        "greedy approach that most word processors use, Knuth-Plass takes a global view of "
        "the entire paragraph. It considers every possible way to break the text into lines "
        "and selects the combination that produces the most aesthetically pleasing result. "
        "The algorithm uses dynamic programming to efficiently find the optimal solution "
        "among exponentially many possibilities. It balances factors such as even spacing, "
        "minimal hyphenation, and avoiding awkward line breaks. The result is paragraphs "
        "that have a uniform gray color when viewed from a distance, without the distracting "
        "rivers of white space that often plague greedily formatted text. Professional "
        "typesetting systems like TeX and LaTeX have used this algorithm for decades to "
        "produce publication-quality documents."
    )
    
    words = tokenize(very_long_text)
    print(f"\n段落长度: {len(words)} 个词")
    print(f"总字符数: {len(very_long_text)}")
    print()
    
    target_width = 5.5
    
    print(f"使用行宽: {target_width} 单位 (约 {int(target_width / 0.4)} 字符)")
    print_separator('-')
    
    greedy = GreedyLineBreaker(target_width)
    kp = KnuthPlassLineBreaker(target_width)
    typesetter = Typesetter(target_width, justify=True)
    
    greedy_layout = greedy.break_lines(words)
    kp_layout = kp.break_lines(words)
    
    greedy_text, greedy_analysis = typesetter.render_with_analysis(greedy_layout)
    kp_text, kp_analysis = typesetter.render_with_analysis(kp_layout)
    
    col_width = int(target_width / 0.4) + 30
    
    print(f"{' 贪心断行 ':=^{col_width}} | {' Knuth-Plass ':=^{col_width}}")
    g_stats = f"行数: {len(greedy_layout.lines)}  总惩罚: {greedy_layout.total_penalty:.0f}"
    k_stats = f"行数: {len(kp_layout.lines)}  总惩罚: {kp_layout.total_penalty:.0f}"
    print(f"{g_stats:<{col_width}} | {k_stats:<{col_width}}")
    print(f"{'-' * col_width} | {'-' * col_width}")
    
    greedy_lines = greedy_text.split('\n')
    kp_lines = kp_text.split('\n')
    
    max_lines = max(len(greedy_lines), len(kp_lines))
    
    loose_g = tight_g = normal_g = 0
    loose_k = tight_k = normal_k = 0
    
    for i in range(max_lines):
        g_line = greedy_lines[i] if i < len(greedy_lines) else ''
        k_line = kp_lines[i] if i < len(kp_lines) else ''
        
        g_a = greedy_analysis[i] if i < len(greedy_analysis) else None
        k_a = kp_analysis[i] if i < len(kp_analysis) else None
        
        g_info = k_info = ''
        
        if g_a:
            mark = '⚠️ ' if g_a['tightness'] != 'normal' else '✓ '
            g_info = f" {mark}{g_a['tightness']:6s} r={g_a['adjustment_ratio']:5.2f} n={g_a['num_words']:2d}"
            if g_a['tightness'] == 'loose': loose_g += 1
            elif g_a['tightness'] == 'tight': tight_g += 1
            else: normal_g += 1
        
        if k_a:
            mark = '⚠️ ' if k_a['tightness'] != 'normal' else '✓ '
            k_info = f" {mark}{k_a['tightness']:6s} r={k_a['adjustment_ratio']:5.2f} n={k_a['num_words']:2d}"
            if k_a['tightness'] == 'loose': loose_k += 1
            elif k_a['tightness'] == 'tight': tight_k += 1
            else: normal_k += 1
        
        g_display = g_line[:col_width - 35]
        k_display = k_line[:col_width - 35]
        
        print(f"{g_display:<{col_width - 35}}{g_info} | {k_display:<{col_width - 35}}{k_info}")
    
    print(f"{'=' * col_width} | {'=' * col_width}")
    
    penalty_improvement = greedy_layout.total_penalty - kp_layout.total_penalty
    if penalty_improvement > 0 and greedy_layout.total_penalty > 0:
        imp_text = f"KP 惩罚降低: {penalty_improvement:.0f} ({(penalty_improvement/greedy_layout.total_penalty*100):.1f}%)"
        print(f"{imp_text:>{col_width * 2 + 3}}")
    
    quality_text = f"正常行: {normal_g}→{normal_k} ({normal_k-normal_g:+d}) | 过松: {loose_g}→{loose_k} ({loose_k-loose_g:+d}) | 过紧: {tight_g}→{tight_k} ({tight_k-tight_g:+d})"
    print(f"{quality_text:>{col_width * 2 + 3}}")
    
    print()
    print_river_analysis(greedy_lines, kp_lines, col_width)
    print_hyphenation_detection(words, target_width)
    print_punctuation_analysis()


def print_river_analysis(greedy_lines, kp_lines, col_width):
    print_separator()
    print("河流现象分析")
    print_separator()
    
    print("\n河流是指连续几行的空白位置对齐，形成可见的白色通道。")
    print("贪心算法由于只考虑局部最优，容易产生这种现象。")
    print()
    
    def detect_rivers(lines):
        if len(lines) < 3:
            return 0
        
        rivers = 0
        max_len = max(len(line) for line in lines)
        
        for col in range(max_len):
            consecutive = 0
            for line in lines:
                if col < len(line) and line[col] == ' ':
                    consecutive += 1
                else:
                    if consecutive >= 3:
                        rivers += consecutive - 2
                    consecutive = 0
            if consecutive >= 3:
                rivers += consecutive - 2
        
        return rivers
    
    greedy_rivers = detect_rivers(greedy_lines)
    kp_rivers = detect_rivers(kp_lines)
    
    print(f"贪心算法检测到的河流数量: {greedy_rivers}")
    print(f"Knuth-Plass 检测到的河流数量: {kp_rivers}")
    if greedy_rivers > 0:
        print(f"河流减少: {greedy_rivers - kp_rivers} ({((greedy_rivers - kp_rivers)/greedy_rivers*100):.0f}% 减少)")
    print()


def print_hyphenation_detection(words, target_width):
    print_separator()
    print("连字符断词点检测")
    print_separator()
    
    from text_breaking import find_hyphenation_points, Word, measure_text
    
    test_words = [w for w in words if len(w.text) >= 8 and not w.is_punctuation][:5]
    
    for word in test_words:
        hyphen_word = Word(text=word.text, width=measure_text(word.text))
        points = find_hyphenation_points(hyphen_word)
        
        print(f"\n单词: {word.text} (宽度: {word.width:.2f}, 行宽: {target_width})")
        if points:
            print(f"  可行断词点:")
            for pos, penalty in sorted(points, key=lambda x: x[1])[:3]:
                hyphenated = word.text[:pos] + '-'
                remaining = word.text[pos:]
                hyphen_width = measure_text(hyphenated)
                quality = "优" if penalty < 1.0 else "中" if penalty < 2.0 else "差"
                fits = "✓ 可容纳" if hyphen_width <= target_width else "✗ 超出"
                print(f"    {hyphenated:<20} 剩余: {remaining:<15} 宽度: {hyphen_width:.2f}  惩罚: {penalty:.2f} ({quality}) {fits}")
        else:
            print(f"  无可断词点")
    print()


def print_punctuation_analysis():
    print_separator()
    print("行尾标点孤立处理机制")
    print_separator()
    
    test_text = "Hello, world! This is a test. Note how punctuation stays with words."
    words = tokenize(test_text)
    
    print(f"\n测试文本: {test_text}")
    print(f"分词结果: {[w.text + '(标)' if w.is_punctuation else w.text for w in words]}")
    print()
    
    from text_breaking import Glue, BreakPoint, BreakPointType
    space_glue = Glue(0.3, 0.4, 0.6, 0.2, 0.1)
    target_width = 6.0
    
    print("断点惩罚对比:")
    print("-" * 90)
    print(f"{'断点位置':<10} {'行尾词':<15} {'下一个词':<15} {'惩罚值':<12} {'惩罚原因':<30}")
    print("-" * 90)
    
    for i in range(len(words) - 1):
        bp = BreakPoint(word_index=i, type=BreakPointType.SPACE, penalty=0)
        
        line_words = words[:i + 1]
        num_spaces = sum(1 for k in range(len(line_words) - 1) if not line_words[k + 1].is_punctuation)
        
        from text_breaking import compute_line_width
        line_width = compute_line_width(line_words, 0, len(line_words) - 1, bp, space_glue)
        penalty = compute_break_penalty(
            words, 0, i, bp, line_width, target_width, space_glue, num_spaces
        )
        
        reasons = []
        if words[i + 1].is_punctuation:
            reasons.append("下一个是标点(+200)")
        if words[i].is_punctuation:
            reasons.append("行尾是标点(-10)")
        if not reasons:
            reasons.append("无特殊惩罚")
        
        reason_str = ', '.join(reasons)
        
        print(f"{i:<10} {words[i].text:<15} {words[i+1].text:<15} {penalty:<12.0f} {reason_str:<30}")
    
    print()
    print("惩罚机制效果:")
    print("  • 位置 4（'Hello' 后，下一个是 ','）: 惩罚增加 200，阻止在标点前换行")
    print("  • 位置 5（',' 后）: 惩罚减少 10，鼓励在标点后换行")
    print("  • 这样确保标点符号紧跟前面的单词，不会孤立出现在行首")
    print()


def print_final_summary():
    print_separator()
    print("完整实现总结")
    print_separator()
    
    print("""
核心数据结构:
  • Word: 表示一个词或标点，包含文本、宽度、是否为标点等属性
  • BreakPoint: 表示一个可能的断行点，包含位置、类型、惩罚等
  • Glue: 表示词间的伸缩空白，包含最小/理想/最大宽度
  • Line: 表示一行，包含词列表、断行点、调整比例等

贪心断行算法 (GreedyLineBreaker):
  • 位置: [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L220-L324)
  • 核心方法: break_lines() - 逐词填充，放不下就换行
  • 时间复杂度: O(n)
  • 特点: 简单快速，但只考虑局部最优

Knuth-Plass 最优断行算法 (KnuthPlassLineBreaker):
  • 位置: [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L327-L422)
  • 核心方法: break_lines() - 动态规划求解全局最优
  • 时间复杂度: O(n²)
  • 特点: 全局最优，整体效果更好，但计算量更大

排版渲染层 (Typesetter):
  • 位置: [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L425-L524)
  • 核心方法: render() - 将布局结果渲染为文本
  • 支持两端对齐，自动调整空白宽度
  • 正确处理标点符号前无空格的情况

关键技术:
  1. 伸缩空白模型 (Glue): 控制词间空白的弹性
  2. 动态规划: 寻找全局最优断行方案
  3. 惩罚函数: badness + 断行类型 + 上下文惩罚
  4. 连字符识别: 基于元音-辅音模式的断词点
  5. 标点处理: 避免行首出现孤立标点

核心函数:
  • tokenize(): [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L97-L116) - 文本分词
  • find_hyphenation_points(): [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L119-L145) - 连字符检测
  • generate_candidate_breakpoints(): [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L148-L157) - 生成候选断点
  • compute_break_penalty(): [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py#L179-L217) - 计算断点惩罚
""")
    print_separator()


if __name__ == "__main__":
    run_true_multiline_demo()
    print_final_summary()
