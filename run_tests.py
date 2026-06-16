import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from text_breaking import (
    tokenize, GreedyLineBreaker, KnuthPlassLineBreaker, Typesetter,
    measure_text
)


def run_tests():
    print("=" * 80)
    print("文本断行与排版引擎 - 综合测试")
    print("=" * 80)
    
    all_passed = True
    
    all_passed &= test_final_demo_launch()
    all_passed &= test_hyphenation_text_integrity()
    all_passed &= test_punctuation_not_orphaned()
    all_passed &= test_greedy_punctuation_handling()
    all_passed &= test_end_punctuation_not_alone()
    all_passed &= test_narrow_width_hyphenation_integrity()
    
    print("\n" + "=" * 80)
    if all_passed:
        print("[OK] 所有测试通过!")
    else:
        print("[FAIL] 部分测试失败!")
    print("=" * 80)
    
    return 0 if all_passed else 1


def test_final_demo_launch():
    print("\n" + "-" * 80)
    print("测试 1: final_demo.py 能正常启动并输出")
    print("-" * 80)
    
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, 'final_demo.py'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        if result.returncode == 0:
            print("[OK] final_demo.py 执行成功，退出码 0")
            
            output = result.stdout
            checks = [
                ("包含'贪心断行'", "贪心断行" in output),
                ("包含'Knuth-Plass'", "Knuth-Plass" in output),
                ("包含'算法原理详解'", "算法原理详解" in output),
                ("至少输出 50 行", len(output.split('\n')) >= 50),
            ]
            
            all_ok = True
            for desc, ok in checks:
                status = "[OK]" if ok else "[FAIL]"
                print(f"  {status} {desc}")
                if not ok:
                    all_ok = False
            
            if all_ok:
                return True
            else:
                print("[FAIL] 部分检查未通过")
                if len(output) > 500:
                    print(f"  (输出已截断，共 {len(output)} 字符)")
                return False
        else:
            print(f"[FAIL] final_demo.py 执行失败，退出码 {result.returncode}")
            print(f"  stderr: {result.stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 执行异常: {e}")
        return False


def reconstruct_text(rendered: str) -> str:
    text = rendered.replace('\n', ' ')
    text = re.sub(r'-\s+', '', text)
    text = ' '.join(text.split())
    return text


def test_hyphenation_text_integrity():
    print("\n" + "-" * 80)
    print("测试 2: 连字符断词后文本完整性验证")
    print("-" * 80)
    
    test_cases = [
        ("The extraordinary programming challenges.", 5.0),
        ("Understanding antidisestablishmentarianism is difficult.", 6.0),
        ("The implementation demonstrates hyphenation capabilities.", 5.5),
        ("A simple short text without hyphenation.", 4.0),
        ("The extraordinary programming challenges.", 3.0),
        ("Consider extraordinary implementation.", 3.5),
        ("Programming is extraordinary.", 3.0),
    ]
    
    all_passed = True
    
    for text, width in test_cases:
        for breaker_name, breaker_class in [("Greedy", GreedyLineBreaker), ("KP", KnuthPlassLineBreaker)]:
            words = tokenize(text)
            breaker = breaker_class(width)
            layout = breaker.break_lines(words)
            typesetter = Typesetter(width, justify=True)
            rendered = typesetter.render(layout)
            
            reconstructed = reconstruct_text(rendered)
            
            status = "[OK]" if reconstructed == text else "[FAIL]"
            if reconstructed != text:
                all_passed = False
            
            has_hyphen = any(line.rstrip().endswith('-') for line in rendered.split('\n')[:-1])
            hyphen_note = " (含连字符断词)" if has_hyphen else " (无连字符断词)"
            
            print(f"  {status} {breaker_name} 行宽={width}{hyphen_note}")
            if reconstructed != text:
                print(f"     原文:     '{text}'")
                print(f"     还原后:   '{reconstructed}'")
                for i, line in enumerate(rendered.split('\n')):
                    print(f"     渲染行{i+1}: |{line}|")
    
    return all_passed


def test_punctuation_not_orphaned():
    print("\n" + "-" * 80)
    print("测试 3: 标点符号不出现在行首（避免标点孤立）")
    print("-" * 80)
    
    test_cases = [
        ("Hello, world! This is a test. Note how punctuation stays with words.", 4.0),
        ("When considering punctuation, we must avoid 'orphaned' punctuation at line breaks.", 4.5),
        ("A, B, C, D, E, F, G. These letters should not have commas alone on lines.", 3.0),
        ("Is this a question? Yes! It certainly is.", 3.5),
        ("Hello world.", 2.0),
        ("Is this ok?", 2.5),
        ("It works.", 2.0),
        ("Stop. Go? Wait!", 2.0),
    ]
    
    all_passed = True
    punctuation_marks = set('.,;:!?)]}\'"')
    
    for text, width in test_cases:
        words = tokenize(text)
        
        for breaker_name, breaker_class in [("贪心", GreedyLineBreaker), ("KP", KnuthPlassLineBreaker)]:
            breaker = breaker_class(width)
            layout = breaker.break_lines(words)
            typesetter = Typesetter(width, justify=True)
            rendered = typesetter.render(layout)
            
            lines = rendered.split('\n')
            has_orphan = False
            orphan_lines = []
            
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped and stripped[0] in punctuation_marks:
                    has_orphan = True
                    orphan_lines.append((i + 1, stripped[:20]))
            
            status = "[FAIL]" if has_orphan else "[OK]"
            if has_orphan:
                all_passed = False
            
            print(f"  {status} {breaker_name}算法 行宽={width}")
            if has_orphan:
                for ln, content in orphan_lines:
                    print(f"     [WARN] 第 {ln} 行行首出现标点: '{content}'")
                print(f"     原文:   '{text}'")
                for i, line in enumerate(lines):
                    print(f"     渲染行{i+1}: |{line}|")
    
    return all_passed


def test_greedy_punctuation_handling():
    print("\n" + "-" * 80)
    print("测试 4: 贪心算法在窄行宽下的标点处理")
    print("-" * 80)
    
    test_cases = [
        ("Test, very narrow width.", 2.5),
        ("Hello, how are you?", 3.0),
        ("Word1, word2, word3!", 2.8),
    ]
    
    all_passed = True
    punctuation_marks = set('.,;:!?)]}\'"')
    
    for text, width in test_cases:
        words = tokenize(text)
        breaker = GreedyLineBreaker(width)
        layout = breaker.break_lines(words)
        typesetter = Typesetter(width, justify=True)
        rendered = typesetter.render(layout)
        
        lines = rendered.split('\n')
        
        has_orphan = False
        orphan_lines = []
        punctuation_with_prev = 0
        total_punctuation = 0
        
        for w in words:
            if w.is_punctuation:
                total_punctuation += 1
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped and stripped[0] in punctuation_marks:
                has_orphan = True
                orphan_lines.append((i + 1, stripped[:20]))
        
        status = "[FAIL]" if has_orphan else "[OK]"
        if has_orphan:
            all_passed = False
        
        print(f"  {status} 行宽={width} 文本='{text}'")
        for j, line in enumerate(lines):
            print(f"     行{j+1}: |{line.rstrip()}|")
        
        if has_orphan:
            for ln, content in orphan_lines:
                print(f"     [WARN] 第 {ln} 行行首出现孤立标点")
    
    return all_passed


def test_end_punctuation_not_alone():
    print("\n" + "-" * 80)
    print("测试 5: 段尾标点不单独成行")
    print("-" * 80)
    
    test_cases = [
        ("Hello world.", 2.0),
        ("Hello world.", 1.5),
        ("Is this ok?", 2.0),
        ("It works.", 2.0),
        ("The extraordinary programming challenges.", 5.0),
        ("The extraordinary programming challenges.", 3.0),
        ("Understanding antidisestablishmentarianism.", 5.0),
        ("The implementation demonstrates.", 4.0),
        ("A, B, C, D.", 2.0),
    ]
    
    all_passed = True
    
    for text, width in test_cases:
        for breaker_name, breaker_class in [("Greedy", GreedyLineBreaker), ("KP", KnuthPlassLineBreaker)]:
            words = tokenize(text)
            breaker = breaker_class(width)
            layout = breaker.break_lines(words)
            typesetter = Typesetter(width, justify=True)
            rendered = typesetter.render(layout)
            
            lines = rendered.split('\n')
            last_line = lines[-1].strip()
            
            last_line_words = layout.lines[-1].words
            all_punct = all(w.is_punctuation for w in last_line_words)
            
            status = "[OK]" if not all_punct else "[FAIL]"
            if all_punct:
                all_passed = False
            
            print(f"  {status} {breaker_name} 行宽={width} 末行='|{last_line}|'")
            if all_punct:
                print(f"     原文: '{text}'")
                for i, line in enumerate(lines):
                    print(f"     渲染行{i+1}: |{line}|")
    
    return all_passed


def test_narrow_width_hyphenation_integrity():
    print("\n" + "-" * 80)
    print("测试 6: 极窄宽度下连字符断词+文本完整性")
    print("-" * 80)
    
    test_cases = [
        ("The extraordinary programming challenges.", 3.0),
        ("Hello world.", 1.5),
        ("Understanding antidisestablishmentarianism.", 4.0),
        ("Consider extraordinary implementation.", 3.5),
        ("Programming is extraordinary.", 3.0),
        ("The implementation demonstrates.", 3.0),
    ]
    
    all_passed = True
    
    for text, width in test_cases:
        for breaker_name, breaker_class in [("Greedy", GreedyLineBreaker), ("KP", KnuthPlassLineBreaker)]:
            words = tokenize(text)
            breaker = breaker_class(width)
            layout = breaker.break_lines(words)
            typesetter = Typesetter(width, justify=True)
            rendered = typesetter.render(layout)
            
            reconstructed = reconstruct_text(rendered)
            match = (reconstructed == text)
            
            if not match:
                all_passed = False
            
            status = "[OK]" if match else "[FAIL]"
            print(f"  {status} {breaker_name} 行宽={width}")
            if not match:
                print(f"     原文:   '{text}'")
                print(f"     还原:   '{reconstructed}'")
                for i, line in enumerate(rendered.split('\n')):
                    print(f"     渲染行{i+1}: |{line}|")
    
    return all_passed


if __name__ == "__main__":
    sys.exit(run_tests())
