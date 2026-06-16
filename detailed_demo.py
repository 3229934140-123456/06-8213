from text_breaking import (
    compare_algorithms, tokenize,
    GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter
)


def print_separator(char='=', length=90):
    print(char * length)


def demo_algorithm_difference():
    print_separator()
    print("贪心断行 vs Knuth-Plass 断行算法对比")
    print_separator()
    
    test_cases = [
        {
            "name": "经典 Knuth 段落",
            "text": "On the other hand, we may consider line breaking as an optimization problem. We wish to choose break points such that the resulting paragraphs are as visually pleasing as possible. This is exactly what the Knuth-Plass algorithm does.",
            "width": 14.0
        },
        {
            "name": "含长单词的段落",
            "text": "The implementation demonstrates hyphenation capabilities with extraordinarily long words like antidisestablishmentarianism. These words present interesting challenges.",
            "width": 15.0
        },
        {
            "name": "含标点符号的段落",
            "text": "When considering punctuation, we must avoid 'orphaned' punctuation at line breaks. For example: the period, comma, and other marks should stay with the preceding word.",
            "width": 13.0
        },
        {
            "name": "容易产生河流的段落",
            "text": "In typesetting, a river is a visually noticeable gap that runs through a paragraph, formed by spaces on successive lines aligning. The Knuth-Plass algorithm significantly reduces river formation.",
            "width": 14.5
        }
    ]
    
    for test in test_cases:
        print_comparison(test["name"], test["text"], test["width"])


def print_comparison(text_name: str, text: str, target_width: float):
    print_separator()
    print(f"测试: {text_name}")
    print(f"目标行宽: {target_width} 单位  |  字符宽度约: {int(target_width / 0.4)} 字符")
    print_separator('-')
    
    words = tokenize(text)
    print(f"原文 ({len(words)} 个词): {text}")
    print()
    
    result = compare_algorithms(text, target_width)
    greedy = result['greedy']
    kp = result['knuth_plass']
    
    col_width = int(target_width / 0.4) + 10
    
    print(f"{'贪心断行':^{col_width}} | {'Knuth-Plass':^{col_width}}")
    print(f"{'='*col_width} | {'='*col_width}")
    
    greedy_lines = greedy['text'].split('\n')
    kp_lines = kp['text'].split('\n')
    
    max_lines = max(len(greedy_lines), len(kp_lines))
    
    for i in range(max_lines):
        g_line = greedy_lines[i] if i < len(greedy_lines) else ''
        k_line = kp_lines[i] if i < len(kp_lines) else ''
        
        g_analysis = greedy['analysis'][i] if i < len(greedy['analysis']) else None
        k_analysis = kp['analysis'][i] if i < len(kp['analysis']) else None
        
        g_info = ''
        if g_analysis:
            g_info = f" [{g_analysis['tightness']:6s} r={g_analysis['adjustment_ratio']:5.2f}]"
        
        k_info = ''
        if k_analysis:
            k_info = f" [{k_analysis['tightness']:6s} r={k_analysis['adjustment_ratio']:5.2f}]"
        
        print(f"{g_line:<{col_width-20}}{g_info} | {k_line:<{col_width-20}}{k_info}")
    
    print(f"{'='*col_width} | {'='*col_width}")
    
    penalty_improvement = greedy['total_penalty'] - kp['total_penalty']
    print(f"行数: {greedy['num_lines']:2d} / 惩罚: {greedy['total_penalty']:12.2f} | 行数: {kp['num_lines']:2d} / 惩罚: {kp['total_penalty']:12.2f}")
    if penalty_improvement > 0:
        print(f"{'':<{col_width}} | KP 惩罚降低: {penalty_improvement:.2f} ({(penalty_improvement/greedy['total_penalty']*100):.1f}%)")
    print()


def demo_how_greedy_works():
    print_separator()
    print("贪心断行算法工作原理演示")
    print_separator()
    
    text = "The quick brown fox jumps over the lazy dog near the riverbank."
    target_width = 12.0
    
    words = tokenize(text)
    print(f"\n原文: {text}")
    print(f"目标行宽: {target_width} 单位")
    print(f"单词列表: {[w.text for w in words]}")
    print()
    
    print("逐词填充过程:")
    print("-" * 70)
    print(f"{'步骤':<4} {'单词':<15} {'累计宽度':<10} {'决策':<40}")
    print("-" * 70)
    
    current_width = 0.0
    current_line = []
    line_num = 1
    
    for i, word in enumerate(words):
        space_needed = 0 if len(current_line) == 0 else 0.4
        projected = current_width + space_needed + word.width
        
        if len(current_line) == 0 or projected <= target_width:
            current_width = projected
            current_line.append(word.text)
            decision = f"加入第 {line_num} 行"
        else:
            decision = f"换行！第 {line_num} 行完成: {' '.join(current_line)}"
            line_num += 1
            current_line = [word.text]
            current_width = word.width
        
        print(f"{i+1:<4} {word.text:<15} {projected:<10.2f} {decision:<40}")
    
    print(f"      {'':<15} {'':<10} 最后一行: {' '.join(current_line)}")
    print()
    
    print("贪心算法的问题:")
    print("  - 第 1 行可能因为一个长单词而过早换行")
    print("  - 导致后续行出现过松或过紧的情况")
    print("  - 无法预见未来的单词分布")
    print()


def demo_how_kp_works():
    print_separator()
    print("Knuth-Plass 动态规划求解演示")
    print_separator()
    
    text = "A B C D E"
    target_width = 6.0
    
    words = tokenize(text)
    print(f"\n原文: {text}")
    print(f"目标行宽: {target_width} 单位")
    print()
    
    print("候选断点 (所有可能的换行位置):")
    print("-" * 60)
    print(f"{'断点位置':<10} {'断词后文本':<20} {'类型':<12} {'惩罚':<8}")
    print("-" * 60)
    
    from text_breaking import generate_candidate_breakpoints, BreakPointType
    breakpoints = generate_candidate_breakpoints(words)
    
    for bp in breakpoints:
        btype = bp.type.value
        text_display = words[bp.word_index].text
        if bp.type == BreakPointType.HYPHEN:
            text_display = bp.hyphenated_text
        print(f"{bp.word_index:<10} {text_display:<20} {btype:<12} {bp.penalty:<8.2f}")
    
    print()
    print("动态规划状态转移:")
    print("-" * 60)
    print("dp[i] = 排版前 i 个词的最小总惩罚")
    print("dp[i] = min(dp[j] + penalty(j, i)) 对所有 j < i")
    print()
    
    print("假设我们有以下状态:")
    print("  dp[0] = 0 (初始状态)")
    print("  dp[1] = dp[0] + penalty(0, 1) = 排版 'A' 的惩罚")
    print("  dp[2] = min( dp[0]+penalty(0,2), dp[1]+penalty(1,2) )")
    print("  ...")
    print()
    print("通过回溯 prev 数组，我们可以得到最优的断行方案")
    print()


def demo_glue_system():
    print_separator()
    print("伸缩空白 (Glue) 模型演示")
    print_separator()
    
    print("""
Glue 模型参数:
  min_width   = 0.3  (空白可压缩到的最小宽度)
  ideal_width = 0.4  (空白的理想宽度)
  max_width   = 0.6  (空白可拉伸到的最大宽度)
  
  stretchability = max_width - ideal_width = 0.2
  shrinkability  = ideal_width - min_width = 0.1

adjustment_ratio (调整比例):
  r = (target_width - natural_width) / (num_spaces * flexibility)
  
  r = 0   → 所有空白都是理想宽度
  r > 0   → 空白被拉伸 (r=1 时拉伸到 max_width)
  r < 0   → 空白被压缩 (r=-1 时压缩到 min_width)
  |r| > 1 → 超出伸缩极限，排版质量差
""")
    
    examples = [
        ("r = 0.0", "理想排版", "word1 word2 word3", 0.4),
        ("r = 0.5", "轻微拉伸", "word1  word2  word3", 0.5),
        ("r = 1.0", "最大拉伸", "word1   word2   word3", 0.6),
        ("r = -0.5", "轻微压缩", "word1 word2 word3", 0.35),
        ("r = -1.0", "最大压缩", "word1word2word3", 0.3),
    ]
    
    print("示例:")
    print("-" * 70)
    for r, desc, example, space_width in examples:
        print(f"{r:<10} {desc:<15} 空白宽度={space_width:.2f}  '{example}'")
    print()


def demo_hyphenation():
    print_separator()
    print("连字符断词点识别演示")
    print_separator()
    
    from text_breaking import Word, find_hyphenation_points, measure_text
    
    test_words = ["extraordinary", "antidisestablishmentarianism", "hello", "programming"]
    
    for word_text in test_words:
        word = Word(text=word_text, width=measure_text(word_text))
        points = find_hyphenation_points(word)
        
        print(f"\n单词: {word_text} (长度: {len(word_text)})")
        if points:
            print(f"  可能的断词点:")
            for pos, penalty in points:
                print(f"    位置 {pos}: {word_text[:pos]}-{word_text[pos:]} (惩罚: {penalty:.2f})")
        else:
            print(f"  无可断词点（单词过短）")
    print()


def demo_punctuation_handling():
    print_separator()
    print("行尾标点孤立处理演示")
    print_separator()
    
    text = "This is a test, to show how punctuation stays with words. It should not be alone!"
    target_width = 10.0
    
    print(f"\n原文: {text}")
    print(f"目标行宽: {target_width} 单位")
    print()
    
    result = compare_algorithms(text, target_width)
    
    print("贪心断行结果:")
    print("-" * 50)
    for i, line in enumerate(result['greedy']['analysis']):
        words_str = ', '.join(f"'{w}'" for w in line['words'])
        print(f"  行 {i+1}: [{words_str}]")
    print()
    
    print("Knuth-Plass 断行结果:")
    print("-" * 50)
    for i, line in enumerate(result['knuth_plass']['analysis']):
        words_str = ', '.join(f"'{w}'" for w in line['words'])
        print(f"  行 {i+1}: [{words_str}]")
    print()
    
    print("惩罚机制:")
    print("  - 行首是标点: +200 惩罚（强烈不推荐）")
    print("  - 行尾是标点: -10 奖励（推荐）")
    print("  - 连字符断行: +50 基础惩罚（谨慎使用）")
    print()


def main():
    demo_how_greedy_works()
    demo_how_kp_works()
    demo_glue_system()
    demo_hyphenation()
    demo_punctuation_handling()
    demo_algorithm_difference()
    
    print_separator()
    print("总结")
    print_separator()
    print("""
贪心断行:
  ✅ 简单快速 O(n)
  ❌ 局部最优，可能产生过松/过紧行
  ❌ 容易产生"河流"现象
  ✅ 适合实时编辑场景

Knuth-Plass 最优断行:
  ✅ 全局最优，整体松紧度最均匀
  ✅ 显著减少河流现象
  ✅ 智能利用连字符断词点
  ✅ 自动处理行尾标点问题
  ❌ 复杂度较高 O(n²)
  ✅ 适合专业排版、出版场景

关键技术:
  • Glue 伸缩空白模型: 控制空白的弹性
  • 动态规划: 寻找全局最优断行方案
  • 惩罚函数: badness + 断行类型惩罚 + 上下文惩罚
  • 连字符识别: 基于元音-辅音模式的断词点
  • 标点处理: 避免行首出现孤立标点
""")
    print_separator()


if __name__ == "__main__":
    main()
