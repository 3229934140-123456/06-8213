from text_breaking import (
    compare_algorithms, tokenize,
    GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter
)


def print_separator(char='=', length=100):
    print(char * length)


def run_final_demo():
    print_separator()
    print("文本断行与排版引擎 - 最终对比演示")
    print_separator()
    
    test_cases = [
        {
            "name": "经典排版问题 (行宽 8.5)",
            "text": "On the other hand, we may consider line breaking as an optimization problem. We wish to choose break points such that the resulting paragraphs are as visually pleasing as possible.",
            "width": 8.5
        },
        {
            "name": "含长单词 (行宽 9.0)",
            "text": "The implementation demonstrates hyphenation capabilities with extraordinarily long words. These words present interesting challenges for line breaking algorithms.",
            "width": 9.0
        },
        {
            "name": "标点符号处理 (行宽 7.5)",
            "text": "When considering punctuation, we must avoid 'orphaned' punctuation at line breaks. For example: the period, comma, and other marks should stay with the preceding word.",
            "width": 7.5
        },
        {
            "name": "河流现象对比 (行宽 8.0)",
            "text": "In typesetting, a river is a visually noticeable gap that runs through a paragraph, formed by spaces on successive lines aligning. The Knuth-Plass algorithm significantly reduces river formation by considering the global picture.",
            "width": 8.0
        },
        {
            "name": "连字符断词 (行宽 7.0)",
            "text": "The extraordinary programming demonstration shows antidisestablishmentarianism challenges. Understanding these concepts is fundamentally important for computer scientists.",
            "width": 7.0
        }
    ]
    
    for test in test_cases:
        print_side_by_side(test["name"], test["text"], test["width"])
    
    print_summary()


def print_side_by_side(text_name: str, text: str, target_width: float):
    print_separator()
    print(f"测试: {text_name}")
    print(f"目标行宽: {target_width} 单位  |  约 {int(target_width / 0.4)} 字符")
    print(f"原文: {text}")
    print_separator('-')
    
    result = compare_algorithms(text, target_width)
    greedy = result['greedy']
    kp = result['knuth_plass']
    
    col_width = int(target_width / 0.4) + 25
    
    print(f"{' 贪心断行 ':=^{col_width}} | {' Knuth-Plass ':=^{col_width}}")
    print(f"{'  行数: ' + str(greedy['num_lines']) + '  惩罚: ' + f'{greedy['total_penalty']:.1f}':<{col_width}} | {'  行数: ' + str(kp['num_lines']) + '  惩罚: ' + f'{kp['total_penalty']:.1f}':<{col_width}}")
    print(f"{'-' * col_width} | {'-' * col_width}")
    
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
            mark = '⚠️ ' if g_analysis['tightness'] != 'normal' else '✓ '
            g_info = f" {mark}{g_analysis['tightness']:6s} r={g_analysis['adjustment_ratio']:5.2f}"
        
        k_info = ''
        if k_analysis:
            mark = '⚠️ ' if k_analysis['tightness'] != 'normal' else '✓ '
            k_info = f" {mark}{k_analysis['tightness']:6s} r={k_analysis['adjustment_ratio']:5.2f}"
        
        g_display = g_line[:col_width - 25]
        k_display = k_line[:col_width - 25]
        
        print(f"{g_display:<{col_width - 25}}{g_info} | {k_display:<{col_width - 25}}{k_info}")
    
    print(f"{'=' * col_width} | {'=' * col_width}")
    
    penalty_improvement = greedy['total_penalty'] - kp['total_penalty']
    if penalty_improvement > 0 and greedy['total_penalty'] > 0:
        print(f"{'KP 惩罚降低: ' + f'{penalty_improvement:.1f} ({(penalty_improvement/greedy['total_penalty']*100):.1f}%)':>{col_width * 2 + 3}}")
    
    loose_diff = greedy['loose_lines'] - kp['loose_lines']
    tight_diff = greedy['tight_lines'] - kp['tight_lines']
    normal_diff = kp['normal_lines'] - greedy['normal_lines']
    
    quality_msg = f"正常行: +{normal_diff}  |  过松行: -{loose_diff}  |  过紧行: -{tight_diff}"
    print(f"{quality_msg:>{col_width * 2 + 3}}")
    print()


def print_summary():
    print_separator()
    print("算法原理详解")
    print_separator()
    
    print("\n" + "=" * 45 + " 贪心断行算法 " + "=" * 45)
    print("""
工作原理:
  1. 逐词填充当前行，计算累计宽度（考虑标点前无空格）
  2. 每次加入新词后判断是否超过目标宽度
  3. 如果放不下，就在上一个词后换行，新词作为下一行的开头
  4. 重复直到所有词处理完毕

为什么会导致整体不美观:
  • 局部最优而非全局最优：每一行的断行决策只考虑当前行
  • 可能导致某些行异常宽松（行尾留有大量空白，adjustment_ratio >> 0）
  • 可能产生"河流"现象（连续几行的空白对齐形成可见的白色通道）
  • 可能导致后续行异常拥挤（adjustment_ratio << 0）
  • 无法有效利用连字符断词点来改善整体效果

示例场景:
  假设行宽刚好能容纳 "A very long sentence here"，
  但贪心算法可能在 "sentence" 前换行，导致前一行过松，
  而如果在 "long" 后连字符断词，整体效果会更好。

时间复杂度: O(n)
""")
    
    print("\n" + "=" * 40 + " Knuth-Plass 最优断行算法 " + "=" * 40)
    print("""
核心思想:
  将断行问题转化为全局优化问题，在所有可能的断点组合中，
  寻找使各行"松紧度"惩罚总和最小的解。

动态规划求解:
  定义 dp[i] = 将前 i 个词排版好的最小总惩罚
  对于每个 i，考虑所有可能的 j < i，尝试在第 j 到 i-1 个词后换行
  dp[i] = min(dp[j] + penalty(j, i)) 对所有 j < i
  penalty(j, i) = 将第 j 到 i-1 个词作为一行的惩罚值
  
  通过回溯 prev 数组，可以得到最优的断行方案

惩罚函数构成:
  1. 松紧度惩罚 (badness): 基于行实际宽度与目标宽度的偏差
     badness = 100 * |ratio|^3，其中 ratio = 偏差 / 可伸缩总量
  2. 断行类型惩罚:
     • 空格断行: 基础惩罚 0
     • 连字符断行: 基础惩罚 50 + 断词位置惩罚（位置越差惩罚越高）
     • 强制换行: 惩罚 0（最后一行）
  3. 附加惩罚:
     • 行首标点: +200（避免标点孤立，强烈不推荐）
     • 行尾标点: -10（鼓励标点留在行尾）
     • 句首词在非行首: +50（鼓励句子开头另起行）

候选断点:
  1. 空格断点: 每个词后可以换行
  2. 连字符断点: 根据元音-辅音模式识别可能的断词点
     • 优先在"辅音+元音"处断词（惩罚 0.5）
     • 其次在"元音+辅音"处断词（惩罚 1.0）
     • 词首词尾 3 个字符内不允许断词
     • 过短词（<5字符）不进行断词

时间复杂度: O(n^2)，n 为词数
""")

    print("\n" + "=" * 45 + " 伸缩空白 (Glue) " + "=" * 45)
    print("""
Glue 模型参数:
  • min_width: 空白的最小宽度（可压缩到的极限）= 0.3
  • ideal_width: 空白的理想宽度（正常排版时的宽度）= 0.4
  • max_width: 空白的最大宽度（可拉伸到的极限）= 0.6
  • stretchability = max_width - ideal_width = 0.2（可拉伸量）
  • shrinkability = ideal_width - min_width = 0.1（可压缩量）

adjustment_ratio 含义:
  r = (target_width - natural_width) / (num_spaces * flexibility)
  
  r = 0   → 理想状态，所有空白都是理想宽度
  r > 0   → 空白被拉伸，值越大越松（r=1 时达到 max_width）
  r < 0   → 空白被压缩，值越小越紧（r=-1 时达到 min_width）
  |r| > 1 → 超出伸缩极限，排版质量差

两端对齐时的空白分配:
  1. 计算行内自然宽度（所有词宽 + 标准间距，标点前无空格）
  2. 计算与目标宽度的差值 deficit
  3. 每个词间空白的调整量 = deficit / 实际空白数（排除标点前的位置）
  4. 实际空白宽度 = 理想宽度 + 调整量
  5. 受限于 glue 的 min_width 和 max_width 约束
""")

    print("\n" + "=" * 43 + " 行尾标点孤立处理 " + "=" * 43)
    print("""
问题:
  标点符号出现在行首（如行首是逗号、句号等）
  违反排版惯例，影响可读性。

解决方案:
  1. 在惩罚函数中对"下一个词是标点"的断点给予 +200 惩罚
     这强烈阻止算法在标点前换行
  2. 对"行尾是标点"的断点给予 -10 奖励
     鼓励算法将标点与前面的词放在同一行
  3. 在宽度计算和渲染时，标点前不计算空格
     确保标点紧跟前面的单词
  4. 连字符断词时自动将连字符放在行尾
""")

    print("\n" + "=" * 48 + " 对比总结 " + "=" * 47)
    print("""
指标              | 贪心算法                      | Knuth-Plass 算法
------------------|-------------------------------|-------------------------------
决策方式          | 局部最优，逐行决策             | 全局最优，整体规划
时间复杂度        | O(n)                          | O(n²)
解的质量          | 可能产生过松/过紧行           | 整体松紧度最均匀
河流现象          | 容易产生                      | 显著减少
连字符利用        | 不支持（本实现扩展支持）       | 优化使用
行尾标点处理      | 需特殊处理                    | 惩罚函数自动处理
正常行比例        | 较低                          | 较高
适用场景          | 实时编辑、简单排版             | 专业排版、最终出版
""")
    print_separator()
    
    print("\n核心代码文件:")
    print("  • text_breaking.py - 核心算法实现")
    print("    - Word, BreakPoint, Glue, Line 数据结构")
    print("    - GreedyLineBreaker - 贪心断行算法")
    print("    - KnuthPlassLineBreaker - 最优断行算法")
    print("    - Typesetter - 排版渲染层")
    print("  • demo.py - 基础对比演示")
    print("  • detailed_demo.py - 详细原理演示")
    print("  • final_demo.py - 本演示程序")
    print()
    print_separator()


if __name__ == "__main__":
    run_final_demo()
