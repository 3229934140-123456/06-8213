import sys
import io
import json
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from text_breaking import (
    tokenize,
    GreedyLineBreaker,
    KnuthPlassLineBreaker,
    Typesetter,
    compare_algorithms,
    LayoutResult,
    find_hyphenation_points,
    BreakPoint,
    BreakPointType,
    generate_candidate_breakpoints,
)


def render_layout(typesetter, layout):
    return typesetter.render(layout)


def compute_stats(layout, typesetter):
    _, analysis = typesetter.render_with_analysis(layout)
    loose = sum(1 for a in analysis if a['tightness'] == 'loose')
    tight = sum(1 for a in analysis if a['tightness'] == 'tight')
    normal = sum(1 for a in analysis if a['tightness'] == 'normal')
    return {
        'num_lines': len(layout.lines),
        'total_penalty': layout.total_penalty,
        'loose': loose,
        'tight': tight,
        'normal': normal,
    }


def make_greedy_breaker(width, hyphen_dict):
    return GreedyLineBreaker(width, hyphen_dict=hyphen_dict)


def make_kp_breaker(width, hyphen_dict):
    return KnuthPlassLineBreaker(width, hyphen_dict=hyphen_dict)


def run_single(text, width, algorithm, justify, hyphen_dict):
    words = tokenize(text)
    typesetter = Typesetter(width, justify=justify)

    if algorithm == 'both':
        greedy_breaker = make_greedy_breaker(width, hyphen_dict)
        kp_breaker = make_kp_breaker(width, hyphen_dict)
        greedy_layout = greedy_breaker.break_lines(words)
        kp_layout = kp_breaker.break_lines(words)

        greedy_text = render_layout(typesetter, greedy_layout)
        kp_text = render_layout(typesetter, kp_layout)
        greedy_stats = compute_stats(greedy_layout, typesetter)
        kp_stats = compute_stats(kp_layout, typesetter)

        return {
            'greedy': {
                'text': greedy_text,
                'stats': greedy_stats,
            },
            'knuth_plass': {
                'text': kp_text,
                'stats': kp_stats,
            },
        }
    elif algorithm == 'greedy':
        breaker = make_greedy_breaker(width, hyphen_dict)
        layout = breaker.break_lines(words)
        rendered = render_layout(typesetter, layout)
        stats = compute_stats(layout, typesetter)
        return {
            'greedy': {
                'text': rendered,
                'stats': stats,
            },
        }
    else:
        breaker = make_kp_breaker(width, hyphen_dict)
        layout = breaker.break_lines(words)
        rendered = render_layout(typesetter, layout)
        stats = compute_stats(layout, typesetter)
        return {
            'knuth_plass': {
                'text': rendered,
                'stats': stats,
            },
        }


def run_compare(text, widths, hyphen_dict):
    results = []
    for width in widths:
        words = tokenize(text)
        greedy_breaker = make_greedy_breaker(width, hyphen_dict)
        kp_breaker = make_kp_breaker(width, hyphen_dict)
        typesetter = Typesetter(width, justify=True)

        greedy_layout = greedy_breaker.break_lines(words)
        kp_layout = kp_breaker.break_lines(words)

        greedy_stats = compute_stats(greedy_layout, typesetter)
        kp_stats = compute_stats(kp_layout, typesetter)

        if greedy_stats['total_penalty'] > 0:
            reduction = (1 - kp_stats['total_penalty'] / greedy_stats['total_penalty']) * 100
        else:
            reduction = 0.0

        results.append({
            'width': width,
            'greedy': greedy_stats,
            'knuth_plass': kp_stats,
            'penalty_reduction': round(reduction, 1),
        })
    return results


def format_single_text(results):
    lines = []
    for algo_name, data in results.items():
        label = 'Greedy' if algo_name == 'greedy' else 'Knuth-Plass'
        lines.append(f'--- {label} ---')
        lines.append(data['text'])
        lines.append('')
        stats = data['stats']
        lines.append(f'Lines: {stats["num_lines"]}  Penalty: {stats["total_penalty"]:.1f}  Loose: {stats["loose"]}  Tight: {stats["tight"]}  Normal: {stats["normal"]}')
        lines.append('')
    return '\n'.join(lines)


def format_single_json(results):
    output = {}
    for algo_name, data in results.items():
        stats = data['stats']
        output[algo_name] = {
            'rendered_text': data['text'],
            'num_lines': stats['num_lines'],
            'total_penalty': round(stats['total_penalty'], 1),
            'loose': stats['loose'],
            'tight': stats['tight'],
            'normal': stats['normal'],
        }
    return json.dumps(output, indent=2, ensure_ascii=False)


def format_compare_text(results):
    header = (
        f'{"Width":>5} | {"Greedy Lines":>12} | {"KP Lines":>8} | '
        f'{"Greedy Penalty":>14} | {"KP Penalty":>10} | '
        f'{"Greedy L/T":>10} | {"KP L/T":>6} | {"Reduction":>9}'
    )
    separator = (
        f'{"-" * 5}-+-{"-" * 12}-+-{"-" * 8}-+-'
        f'{"-" * 14}-+-{"-" * 10}-+-'
        f'{"-" * 10}-+-{"-" * 6}-+-{"-" * 9}'
    )
    lines = [header, separator]

    for r in results:
        g = r['greedy']
        k = r['knuth_plass']
        row = (
            f'{r["width"]:5.1f} | {g["num_lines"]:12d} | {k["num_lines"]:8d} | '
            f'{g["total_penalty"]:14.1f} | {k["total_penalty"]:10.1f} | '
            f'{g["loose"]:>4}/{g["tight"]:<4} | {k["loose"]:>2}/{k["tight"]:<2} | '
            f'{r["penalty_reduction"]:8.1f}%'
        )
        lines.append(row)

    return '\n'.join(lines)


def format_compare_json(results):
    output = []
    for r in results:
        g = r['greedy']
        k = r['knuth_plass']
        output.append({
            'width': r['width'],
            'greedy': {
                'num_lines': g['num_lines'],
                'total_penalty': round(g['total_penalty'], 1),
                'loose': g['loose'],
                'tight': g['tight'],
                'normal': g['normal'],
            },
            'knuth_plass': {
                'num_lines': k['num_lines'],
                'total_penalty': round(k['total_penalty'], 1),
                'loose': k['loose'],
                'tight': k['tight'],
                'normal': k['normal'],
            },
            'penalty_reduction': r['penalty_reduction'],
        })
    return json.dumps(output, indent=2, ensure_ascii=False)


def load_hyphen_dict(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Text breaking engine CLI')
    parser.add_argument('text', nargs='?', default=None, help='Text to typeset')
    parser.add_argument('-f', '--file', type=str, default=None, help='Path to text file to read')
    parser.add_argument('-w', '--width', type=float, default=8.0, help='Line width (default: 8.0)')
    parser.add_argument('-a', '--algorithm', choices=['greedy', 'kp', 'both'], default='both',
                        help='Algorithm choice (default: both)')
    parser.add_argument('-j', '--justify', action='store_true', default=True,
                        help='Justify text (default: True)')
    parser.add_argument('--no-justify', dest='justify', action='store_false',
                        help='Disable text justification')
    parser.add_argument('--compare', type=float, nargs='+', default=None,
                        help='Batch compare mode with multiple widths')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--dict', type=str, default=None, dest='dict_path',
                        help='Path to custom hyphenation dictionary (JSON)')

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.error('Either provide text as a positional argument or use -f/--file')

    text = text.strip()

    hyphen_dict = None
    if args.dict_path:
        hyphen_dict = load_hyphen_dict(args.dict_path)

    if args.compare:
        results = run_compare(text, args.compare, hyphen_dict)
        if args.format == 'json':
            print(format_compare_json(results))
        else:
            print(format_compare_text(results))
    else:
        results = run_single(text, args.width, args.algorithm, args.justify, hyphen_dict)
        if args.format == 'json':
            print(format_single_json(results))
        else:
            print(format_single_text(results))


if __name__ == "__main__":
    main()
