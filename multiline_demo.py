from text_breaking import (
    tokenize, GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter,
    compute_line_width, compute_break_penalty, generate_candidate_breakpoints,
    BreakPointType, Glue
)


def print_separator(char='=', length=95):
    print(char * length)


def run_multiline_demo():
    print_separator()
    print("文本断行与排版引擎 - 多行对比演示")
    print_separator()
    
    test_text = (
        "The Knuth-Plass algorithm is widely regarded as one of the best approaches "
        "to line breaking. Unlike greedy methods that process text line by line, "
        "Knuth-Plass considers the entire paragraph globally to find the optimal "
        "break points. This results in more evenly spaced lines and fewer unsightly "
        "gaps known as rivers. The algorithm uses dynamic programming to minimize "
        "the total penalty across all lines, taking into account factors like "
        "hyphenation preferences, spacing constraints, and typographic conventions."
    )
    
    words = tokenize(test_text)
    
    target_widths = [6.0, 7.0, 8.0]
    
    for width in target_widths:
        compare_at_width(test_text, words, width)
    
    print_detailed_explanation()


def compare_at_width(text, words, target_width):
    print_separator()
    print(f"目标行宽: {target_width} 单位 (约 {int(target_width / 0.4)} 字符)")
    print(f"段落总词数: {len(words)}")
    print_separator('-')
    
    greedy = GreedyLineBreaker(target_width)
    kp = KnuthPlassLineBreaker(target_width)
    typesetter = Typesetter(target_width, justify=True)
    
    greedy_layout = greedy.break_lines(words)
    kp_layout = kp.break_lines(words)
    
    greedy_text, greedy_analysis = typesetter.render_with_analysis(greedy_layout)
    kp_text, kp_analysis = typesetter.render_with_analysis(kp_layout)
    
    col_width = int(target_width / 0.4) + 25
    
    print(f"{' 贪心断行 ':=^{col_width}} | {' Knuth-Plass ':=^{col_width}}")
    g_stats = f"  行数: {len(greedy_layout.lines)}  惩罚: {greedy_layout.total_penalty:.0f}"
    k_stats = f"  行数: {len(kp_layout.lines)}  惩罚: {kp_layout.total_penalty:.0f}"
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
            g_info = f" {mark}{g_a['tightness']:6s} r={g_a['adjustment_ratio']:5.2f}"
            if g_a['tightness'] == 'loose': loose_g += 1
            elif g_a['tightness'] == 'tight': tight_g += 1
            else: normal_g += 1
        
        if k_a:
            mark = '⚠️ ' if k_a['tightness'] != 'normal' else '✓ '
            k_info = f" {mark}{k_a['tightness']:6s} r={k_a['adjustment_ratio']:5.2f}"
            if k_a['tightness'] == 'loose': loose_k += 1
            elif k_a['tightness'] == 'tight': tight_k += 1
            else: normal_k += 1
        
        g_display = g_line[:col_width - 25]
        k_display = k_line[:col_width - 25]
        
        print(f"{g_display:<{col_width - 25}}{g_info} | {k_display:<{col_width - 25}}{k_info}")
    
    print(f"{'=' * col_width} | {'=' * col_width}")
    
    penalty_improvement = greedy_layout.total_penalty - kp_layout.total_penalty
    if penalty_improvement > 0 and greedy_layout.total_penalty > 0:
        imp_text = f"KP 惩罚降低: {penalty_improvement:.0f} ({(penalty_improvement/greedy_layout.total_penalty*100):.1f}%)"
        print(f"{imp_text:>{col_width * 2 + 3}}")
    
    quality_text = f"正常行: {normal_g}→{normal_k} ({normal_k-normal_g:+d}) | 过松: {loose_g}→{loose_k} ({loose_k-loose_g:+d}) | 过紧: {tight_g}→{tight_k} ({tight_k-tight_g:+d})"
    print(f"{quality_text:>{col_width * 2 + 3}}")
    print()


def print_detailed_explanation():
    print_separator()
    print("算法原理详解")
    print_separator()
    
    print("\n" + "━" * 45 + " 贪心断行算法 " + "━" * 45)
    print("""
工作原理:
  逐词填充当前行，直到无法容纳下一个词为止，然后换行。
  这是一种"所见即所得"的局部最优策略。

算法步骤:
  1. 初始化当前行宽度为 0，当前行词列表为空
  2. 对于每个词 w：
     a. 计算加入 w 后的预期宽度（考虑标点前无空格）
     b. 如果预期宽度 ≤ 目标宽度或当前行为空：
        - 加入 w，更新当前宽度
     c. 否则：
        - 在当前行最后一个词后换行
        - 开始新行，w 作为第一个词
  3. 处理完所有词后，将剩余词作为最后一行

为什么会导致整体不美观:
  1. 目光短浅：只考虑当前行，不考虑后续内容
  2. 过松行：某行刚好差一点点放不下下一个词，导致大量空白
  3. 过紧行：后续行可能因为前面的"浪费"而被迫拥挤
  4. 河流现象：连续几行的空白位置对齐，形成可见的白色通道
  5. 无法利用连字符：不会考虑通过断词来改善整体效果

时间复杂度: O(n)，n 为词数
适用场景: 实时编辑器、简单文本显示、性能要求极高的场景
""")
    
    print("\n" + "━" * 40 + " Knuth-Plass 最优断行算法 " + "━" * 40)
    print("""
核心思想:
  将断行问题建模为全局优化问题。通过考虑所有可能的断点组合，
  找到使"各行松紧度惩罚总和最小"的解。

动态规划建模:
  状态定义:
    dp[i] = 将前 i 个词排版好的最小总惩罚
  
  状态转移:
    dp[i] = min{ dp[j] + penalty(j, i) | 0 ≤ j < i }
    其中 penalty(j, i) 是将第 j 到 i-1 个词作为一行的惩罚
  
  边界条件:
    dp[0] = 0（0 个词的惩罚为 0）
  
  最优解回溯:
    维护 prev 数组记录每个状态的最优前驱，最后从 dp[n] 回溯得到断行方案

惩罚函数 penalty(j, i) 的构成:
  1. 松紧度惩罚 (badness):
     ratio = |实际宽度 - 目标宽度| / (空白数 × 可伸缩量)
     badness = 100 × ratio³  (ratio > 1 时惩罚急剧上升)
  
  2. 断行类型惩罚:
     • 空格断行: 0
     • 连字符断行: 50 + 位置惩罚 × 20 (不鼓励断词)
     • 强制换行(最后一行): 0
  
  3. 上下文惩罚:
     • 行首标点: +200 (强烈不推荐)
     • 行尾标点: -10 (推荐)
     • 句首词在非行首: +50 (鼓励另起行)

候选断点生成:
  1. 空格断点: 每个词后都可以换行
  2. 连字符断点:
     • 词长 < 5: 不断词
     • 词首尾 3 字符内: 不断词
     • 辅音+元音交界处: 优先断词 (惩罚 0.5)
     • 元音+辅音交界处: 可断词 (惩罚 1.0)
     • 其他位置: 尽量不断 (惩罚 2.0+)

时间复杂度: O(n²)，n 为词数
适用场景: 专业排版、出版印刷、高质量文档生成
""")
    
    print("\n" + "━" * 45 + " 伸缩空白 (Glue) 模型 " + "━" * 45)
    print("""
为什么需要 Glue?
  单词间的空白不是固定宽度，而是有弹性的。
  这使得两端对齐成为可能。

Glue 参数:
  min_width   = 0.3  ──┐
  ideal_width = 0.4  ──┤ 空白可以在 [0.3, 0.6] 范围内伸缩
  max_width   = 0.6  ──┘
  
  stretchability = max - ideal = 0.2  (可拉伸量)
  shrinkability  = ideal - min = 0.1  (可压缩量)

adjustment_ratio (r):
  r = (目标宽度 - 自然宽度) / (空白数 × 可伸缩量)
  
  r = 0   → 完美，所有空白都是理想宽度 0.4
  0 < r ≤ 1 → 空白被拉伸，r=1 时达到 max_width 0.6
  -1 ≤ r < 0 → 空白被压缩，r=-1 时达到 min_width 0.3
  |r| > 1 → 超出弹性极限，排版质量差

两端对齐时的空白分配:
  例: 行内有 4 个词，3 个空白，自然宽度 = 8，目标宽度 = 10
      deficit = 10 - 8 = 2
      每个空白需要增加 = 2 / 3 ≈ 0.67
      但受限于 max_width = 0.6，实际只能增加 0.2
      此时 r = 2 / (3 × 0.2) ≈ 3.33 > 1，说明过于宽松
""")
    
    print("\n" + "━" * 43 + " 行尾标点孤立处理 " + "━" * 43)
    print("""
问题描述:
  错误: "Hello , how are you ?"
        "Hello"
        ", how are you"
        "?"
  
  正确: "Hello, how are you?"
        "Hello, how are"
        "you?"

实现机制:
  1. 词法分析阶段识别标点符号
  2. 宽度计算时，标点前不计算空格
  3. 渲染阶段，标点前不输出空格
  4. 惩罚函数中:
     - 在标点前换行: +200 惩罚（强烈阻止）
     - 在标点后换行: -10 奖励（鼓励）
""")
    
    print("\n" + "━" * 47 + " 对比总结 " + "━" * 47)
    print("""
┌─────────────┬─────────────────────────┬─────────────────────────┐
│    指标     │       贪心算法          │    Knuth-Plass 算法     │
├─────────────┼─────────────────────────┼─────────────────────────┤
│ 决策方式    │ 局部最优，逐行决策       │ 全局最优，整体规划       │
│ 时间复杂度  │ O(n)                    │ O(n²)                   │
│ 解的质量    │ 可能过松或过紧          │ 整体松紧度最均匀        │
│ 河流现象    │ 容易产生                │ 显著减少                │
│ 连字符利用  │ 不支持                  │ 智能优化使用            │
│ 标点处理    │ 需额外处理              │ 惩罚函数自动处理        │
│ 正常行比例  │ 约 30-50%               │ 约 70-90%               │
│ 适用场景    │ 实时编辑、简单显示       │ 专业排版、出版印刷       │
└─────────────┴─────────────────────────┴─────────────────────────┘

核心文件:
  • [text_breaking.py](file:///d:/trae-bz/TraeProjects/8213/text_breaking.py) - 核心算法
  • [demo.py](file:///d:/trae-bz/TraeProjects/8213/demo.py) - 基础演示
  • [detailed_demo.py](file:///d:/trae-bz/TraeProjects/8213/detailed_demo.py) - 原理演示
  • [final_demo.py](file:///d:/trae-bz/TraeProjects/8213/final_demo.py) - 最终对比
  • [analysis.py](file:///d:/trae-bz/TraeProjects/8213/analysis.py) - 深度分析
  • [multiline_demo.py](file:///d:/trae-bz/TraeProjects/8213/multiline_demo.py) - 本程序
""")
    print_separator()


if __name__ == "__main__":
    run_multiline_demo()
