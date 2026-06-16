from text_breaking import tokenize, KnuthPlassLineBreaker, Typesetter, GreedyLineBreaker

def test_hyphenation():
    print("=" * 70)
    print("测试连字符断词 - 文本完整性验证")
    print("=" * 70)
    
    test_cases = [
        ("The extraordinary programming challenges.", 5.0),
        ("Understanding antidisestablishmentarianism is difficult.", 6.0),
        ("The implementation demonstrates hyphenation capabilities.", 5.5),
    ]
    
    all_passed = True
    
    for text, width in test_cases:
        words = tokenize(text)
        print(f"\n原文: {text}")
        print(f"目标行宽: {width}")
        
        breaker = KnuthPlassLineBreaker(width)
        layout = breaker.break_lines(words)
        
        print("断行详情:")
        for i, line in enumerate(layout.lines):
            bp = line.break_point
            bp_type = bp.type.value if bp else 'none'
            word_texts = [w.text for w in line.words]
            print(f"  Line {i+1}: {word_texts} 断点={bp_type}")
            if bp and bp_type == 'hyphen':
                print(f"    hyphenated='{bp.hyphenated_text}', remaining='{bp.remaining_text}'")
        
        typesetter = Typesetter(width, justify=True)
        rendered = typesetter.render(layout)
        print("\n渲染后文本:")
        for line in rendered.split('\n'):
            print(f"  |{line}|")
        
        reconstructed = reconstruct_text(rendered)
        print(f"\n拼回去: '{reconstructed}'")
        print(f"原  文: '{text}'")
        
        if reconstructed == text:
            print("✅ 文本完整性验证通过!")
        else:
            print(f"❌ 文本不匹配!")
            all_passed = False
    
    return all_passed


def reconstruct_text(rendered: str) -> str:
    import re
    text = rendered.replace('\n', ' ')
    text = re.sub(r'-\s+', '', text)
    text = ' '.join(text.split())
    return text


if __name__ == "__main__":
    result = test_hyphenation()
    print("\n" + "=" * 70)
    if result:
        print("所有测试通过!")
    else:
        print("部分测试失败!")
