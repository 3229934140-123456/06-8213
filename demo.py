from text_breaking import (
    compare_algorithms, tokenize,
    GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter
)


SAMPLE_TEXTS = {
    "simple": "The quick brown fox jumps over the lazy dog. This is a simple paragraph to test line breaking algorithms.",
    
    "classic_knuth": "On the other hand, we may consider line breaking as an optimization problem. We wish to choose break points such that the resulting paragraphs are as visually pleasing as possible. This is exactly what the Knuth-Plass algorithm does. It considers all possible ways to break the paragraph into lines, and chooses the one that minimizes a certain penalty function.",
    
    "with_long_words": "The implementation demonstrates hyphenation capabilities with extraordinarily long words like antidisestablishmentarianism and supercalifragilisticexpialidocious. These words present interesting challenges for line breaking algorithms.",
    
    "with_punctuation": "When considering punctuation, we must avoid 'orphaned' punctuation at line breaks. For example: the period, comma, and other marks should stay with the preceding word. This is particularly important for readability!",
    
    "dense_paragraph": "In typesetting, a river is a visually noticeable gap that runs through a paragraph, formed by spaces on successive lines aligning. The Knuth-Plass algorithm significantly reduces river formation by considering the global picture rather than making locally optimal decisions that may have negative consequences later."
}


def print_separator(char='=', length=80):
    print(char * length)


def print_comparison(text_name: str, text: str, target_width: float):
    print_separator()
    print(f"测试用例: {text_name}")
    print(f"目标行宽: {target_width} 单位")
    print_separator('-')
    
    result = compare_algorithms(text, target_width)
    
    print(f"\n总词数: {result['num_words']}")
    print()
    
    greedy = result['greedy']
    kp = result['knuth_plass']
    
    print(f"{'='*40} 贪心断行 {'='*40}")
    print(f"总行数: {greedy['num_lines']}  |  总惩罚: {greedy['total_penalty']:.2f}")
    print(f"正常行: {greedy['normal_lines']}  |  过松行: {greedy['loose_lines']}  |  过紧行: {greedy['tight_lines']}")
    print_separator('-')
    print(greedy['text'])
    print_separator('-')
    
    print(f"\n{'='*40} Knuth-Plass {'='*40}")
    print(f"总行数: {kp['num_lines']}  |  总惩罚: {kp['total_penalty']:.2f}")
    print(f"正常行: {kp['normal_lines']}  |  过松行: {kp['loose_lines']}  |  过紧行: {kp['tight_lines']}")
    penalty_improvement = greedy['total_penalty'] - kp['total_penalty']
    if penalty_improvement > 0:
        print(f"惩罚值降低: {penalty_improvement:.2f} ({(penalty_improvement/greedy['total_penalty']*100):.1f}%)")
    print_separator('-')
    print(kp['text'])
    print_separator('-')
    
    print("\n" + "=" * 80)
    print("逐行对比分析:")
    print("-" * 80)
    
    max_lines = max(len(greedy['analysis']), len(kp['analysis']))
    
    for i in range(max_lines):
        print(f"\n第 {i+1} 行:")
        
        if i < len(greedy['analysis']):
            ga = greedy['analysis'][i]
            print(f"  贪心:  词数={ga['num_words']:2d}  松紧度={ga['adjustment_ratio']:6.2f} ({ga['tightness']:6s})  断点={ga['break_type']:6s}  '{ga['words']}'")
        
        if i < len(kp['analysis']):
            ka = kp['analysis'][i]
            print(f"  KP:    词数={ka['num_words']:2d}  松紧度={ka['adjustment_ratio']:6.2f} ({ka['tightness']:6s})  断点={ka['break_type']:6s}  '{ka['words']}'")
    
    print()


def print_algo_explanation():
    print_separator()
    print("算法原理详解")
    print_separator()
    
    print("\n" + "=" * 40 + " 贪心断行算法 " + "=" * 40)
    print("""
工作原理:
  1. 逐词填充当前行，计算累计宽度
  2. 每次加入新词后判断是否超过目标宽度
  3. 如果放不下，就在上一个词后换行，新词作为下一行的开头
  4. 重复直到所有词处理完毕

为什么会导致整体不美观:
  - 局部最优而非全局最优：每一行的断行决策只考虑当前行
  - 可能导致某些行异常宽松（行尾留有大量空白）
  - 可能产生"河流"现象（连续几行的空白对齐形成可见的白色通道）
  - 可能导致后续行异常拥挤
  - 无法有效利用连字符断词点来改善整体效果

示例场景:
  假设行宽刚好能容纳 "A very long sentence here"，
  但贪心算法可能在 "sentence" 前换行，导致前一行过松，
  而如果在 "long" 后连字符断词，整体效果会更好。
""")
    
    print("\n" + "=" * 35 + " Knuth-Plass 最优断行 " + "=" * 35)
    print("""
核心思想:
  将断行问题转化为全局优化问题，在所有可能的断点组合中，
  寻找使各行"松紧度"惩罚总和最小的解。

动态规划求解:
  1. 定义 dp[i] = 将前 i 个词排版好的最小总惩罚
  2. 对于每个 i，考虑所有可能的 j < i，尝试在第 j 到 i-1 个词后换行
  3. dp[i] = min(dp[j] + penalty(j, i)) 对所有 j < i
  4. penalty(j, i) = 将第 j 到 i-1 个词作为一行的惩罚值

惩罚函数构成:
  - 松紧度惩罚 (badness): 基于行实际宽度与目标宽度的偏差
    badness = 100 * |ratio|^3，其中 ratio = 偏差 / 可伸缩总量
  - 断行类型惩罚:
    * 空格断行: 基础惩罚 0
    * 连字符断行: 基础惩罚 50 + 断词位置惩罚
    * 强制换行: 惩罚 -1000（最后一行）
  - 附加惩罚:
    * 行首标点: +200（避免标点孤立）
    * 行尾标点: -10（鼓励标点留在行尾）
    * 句首词在非行首: +50（鼓励句子开头另起行）

候选断点:
  1. 空格断点: 每个词后可以换行
  2. 连字符断点: 根据元音-辅音模式识别可能的断词点
     - 优先在"辅音+元音"处断词（惩罚 0.5）
     - 其次在"元音+辅音"处断词（惩罚 1.0）
     - 词首词尾 3 个字符内不允许断词
     - 过短词（<5字符）不进行断词

两端对齐时的空白分配:
  1. 计算行内自然宽度（所有词宽 + 标准间距）
  2. 计算与目标宽度的差值 deficit
  3. 每个词间空白的调整量 = deficit / (词数 - 1)
  4. 实际空白宽度 = 理想宽度 + 调整量
  5. 受限于 glue 的 min_width 和 max_width 约束
""")

    print("\n" + "=" * 40 + " 伸缩空白 (Glue) " + "=" * 40)
    print("""
Glue 模型参数:
  - min_width: 空白的最小宽度（可压缩到的极限）
  - ideal_width: 空白的理想宽度（正常排版时的宽度）
  - max_width: 空白的最大宽度（可拉伸到的极限）
  - stretchability = max_width - ideal_width （可拉伸量）
  - shrinkability = ideal_width - min_width （可压缩量）

adjustment_ratio 含义:
  - 0: 理想状态，所有空白都是理想宽度
  - >0: 空白被拉伸，值越大越松
  - <0: 空白被压缩，值越小越紧
  - 绝对值 > 1: 超出伸缩极限，排版质量差
""")

    print("\n" + "=" * 38 + " 行尾标点孤立处理 " + "=" * 38)
    print("""
问题:
  标点符号出现在行首（如行首是逗号、句号等）
  违反排版惯例，影响可读性。

解决方案:
  1. 在惩罚函数中对"下一个词是标点"的断点给予 +200 惩罚
  2. 鼓励算法将标点与前面的词放在同一行
  3. 对"行尾是标点"的断点给予 -10 奖励
  4. 连字符断词时自动将连字符放在行尾
""")


def main():
    print_separator()
    print("文本断行与排版引擎 - 贪心 vs Knuth-Plass 对比演示")
    print_separator()
    
    print_algo_explanation()
    
    print("\n" + "#" * 80)
    print("#" + " " * 78 + "#")
    print("#" + " " * 25 + "排版效果对比演示" + " " * 35 + "#")
    print("#" + " " * 78 + "#")
    print("#" * 80)
    
    target_widths = [12.0, 16.0, 20.0]
    
    for width in target_widths:
        for text_name, text in SAMPLE_TEXTS.items():
            print_comparison(text_name, text, width)
    
    print("\n" + "=" * 80)
    print("总结对比:")
    print("-" * 80)
    print("""
指标              | 贪心算法                | Knuth-Plass 算法
------------------|-------------------------|----------------------------
决策方式          | 局部最优，逐行决策       | 全局最优，整体规划
时间复杂度        | O(n)                    | O(n^2)
解的质量          | 可能产生过松/过紧行       | 整体松紧度最均匀
河流现象          | 容易产生                | 显著减少
连字符利用        | 不支持（本实现扩展支持） | 优化使用
行尾标点处理      | 需特殊处理              | 惩罚函数自动处理
适用场景          | 实时编辑、简单排版       | 专业排版、最终出版
""")
    print("=" * 80)


if __name__ == "__main__":
    main()
