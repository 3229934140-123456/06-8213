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


def split_paragraphs(text):
    paragraphs = []
    current = []
    for line in text.split('\n'):
        if line.strip() == '':
            if current:
                paragraphs.append(' '.join(current))
                current = []
        else:
            current.append(line.strip())
    if current:
        paragraphs.append(' '.join(current))
    return paragraphs


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


def run_multi_paragraph(text, width, algorithm, justify, hyphen_dict):
    paragraphs = split_paragraphs(text)
    if len(paragraphs) <= 1:
        return run_single(text, width, algorithm, justify, hyphen_dict), []

    all_results = []
    for para in paragraphs:
        result = run_single(para, width, algorithm, justify, hyphen_dict)
        all_results.append(result)

    merged = {}
    algo_keys = list(all_results[0].keys())
    for key in algo_keys:
        merged_texts = []
        merged_stats = {'num_lines': 0, 'total_penalty': 0.0, 'loose': 0, 'tight': 0, 'normal': 0}
        for r in all_results:
            merged_texts.append(r[key]['text'])
            s = r[key]['stats']
            merged_stats['num_lines'] += s['num_lines']
            merged_stats['total_penalty'] += s['total_penalty']
            merged_stats['loose'] += s['loose']
            merged_stats['tight'] += s['tight']
            merged_stats['normal'] += s['normal']
        merged[key] = {
            'text': '\n\n'.join(merged_texts),
            'stats': merged_stats,
            'paragraphs': [r[key] for r in all_results],
        }

    return merged, paragraphs


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


def run_recommend(text, width_min, width_max, step, hyphen_dict):
    widths = []
    w = width_min
    while w <= width_max + 0.001:
        widths.append(round(w, 2))
        w += step

    all_results = []
    for width in widths:
        words = tokenize(text)
        kp_breaker = make_kp_breaker(width, hyphen_dict)
        greedy_breaker = make_greedy_breaker(width, hyphen_dict)
        typesetter = Typesetter(width, justify=True)

        kp_layout = kp_breaker.break_lines(words)
        greedy_layout = greedy_breaker.break_lines(words)
        kp_stats = compute_stats(kp_layout, typesetter)
        greedy_stats = compute_stats(greedy_layout, typesetter)

        all_results.append({
            'width': width,
            'kp_penalty': kp_stats['total_penalty'],
            'kp_lines': kp_stats['num_lines'],
            'kp_loose': kp_stats['loose'],
            'kp_tight': kp_stats['tight'],
            'kp_normal': kp_stats['normal'],
            'greedy_penalty': greedy_stats['total_penalty'],
            'greedy_lines': greedy_stats['num_lines'],
            'greedy_loose': greedy_stats['loose'],
            'greedy_tight': greedy_stats['tight'],
            'greedy_normal': greedy_stats['normal'],
        })

    if len(all_results) < 2:
        return all_results, all_results

    penalties = [r['kp_penalty'] for r in all_results if r['kp_penalty'] > 0]
    if not penalties:
        return all_results, all_results[:3]

    min_pen = min(penalties)
    max_pen = max(penalties)
    pen_range = max_pen - min_pen if max_pen > min_pen else 1.0

    scored = []
    for r in all_results:
        pen_score = 1.0 - (r['kp_penalty'] - min_pen) / pen_range if r['kp_penalty'] > 0 else 1.0
        tight_ratio = r['kp_tight'] / r['kp_lines'] if r['kp_lines'] > 0 else 0
        loose_ratio = r['kp_loose'] / r['kp_lines'] if r['kp_lines'] > 0 else 0
        stability_score = 1.0 - (tight_ratio + loose_ratio)
        score = pen_score * 0.6 + stability_score * 0.4
        scored.append((score, r))

    scored.sort(key=lambda x: -x[0])
    top_n = min(3, len(scored))
    recommended = [r for _, r in scored[:top_n]]
    recommended.sort(key=lambda r: r['width'])

    return all_results, recommended


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
        entry = {
            'rendered_text': data['text'],
            'num_lines': stats['num_lines'],
            'total_penalty': round(stats['total_penalty'], 1),
            'loose': stats['loose'],
            'tight': stats['tight'],
            'normal': stats['normal'],
        }
        if 'paragraphs' in data:
            entry['paragraphs'] = []
            for p in data['paragraphs']:
                entry['paragraphs'].append({
                    'rendered_text': p['text'],
                    'num_lines': p['stats']['num_lines'],
                    'total_penalty': round(p['stats']['total_penalty'], 1),
                    'loose': p['stats']['loose'],
                    'tight': p['stats']['tight'],
                    'normal': p['stats']['normal'],
                })
        output[algo_name] = entry
    return json.dumps(output, indent=2, ensure_ascii=False)


def format_multi_paragraph_text(results, paragraphs):
    lines = []
    lines.append(f'Total paragraphs: {len(paragraphs)}')
    lines.append('')

    for algo_name, data in results.items():
        label = 'Greedy' if algo_name == 'greedy' else 'Knuth-Plass'
        stats = data['stats']
        lines.append(f'--- {label} (merged) ---')
        lines.append(data['text'])
        lines.append('')
        lines.append(f'Total Lines: {stats["num_lines"]}  Penalty: {stats["total_penalty"]:.1f}  Loose: {stats["loose"]}  Tight: {stats["tight"]}  Normal: {stats["normal"]}')
        lines.append('')

        if 'paragraphs' in data:
            lines.append(f'  Per-paragraph breakdown:')
            for pi, p in enumerate(data['paragraphs']):
                ps = p['stats']
                lines.append(f'    Para {pi+1}: {ps["num_lines"]} lines, penalty={ps["total_penalty"]:.1f}, loose={ps["loose"]}, tight={ps["tight"]}')
            lines.append('')

    return '\n'.join(lines)


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


def format_recommend_text(all_results, recommended):
    lines = []
    lines.append('Width Recommendation')
    lines.append('=' * 80)
    lines.append('')

    header = (
        f'{"Width":>5} | {"KP Lines":>8} | {"KP Penalty":>10} | '
        f'{"Greedy Lines":>12} | {"Greedy Penalty":>14} | '
        f'{"L/T":>5} | {"Note":>12}'
    )
    separator = (
        f'{"-" * 5}-+-{"-" * 8}-+-{"-" * 10}-+-'
        f'{"-" * 12}-+-{"-" * 14}-+-'
        f'{"-" * 5}-+-{"-" * 12}'
    )
    lines.append(header)
    lines.append(separator)

    rec_widths = set(r['width'] for r in recommended)

    for r in all_results:
        note = '<< recommended' if r['width'] in rec_widths else ''
        lt = f'{r["kp_loose"]}/{r["kp_tight"]}'
        row = (
            f'{r["width"]:5.1f} | {r["kp_lines"]:8d} | {r["kp_penalty"]:10.1f} | '
            f'{r["greedy_lines"]:12d} | {r["greedy_penalty"]:14.1f} | '
            f'{lt:>5} | {note:>12}'
        )
        lines.append(row)

    lines.append('')
    lines.append('Recommended widths:')
    for r in recommended:
        lines.append(f'  w={r["width"]:.1f}: KP penalty={r["kp_penalty"]:.1f}, lines={r["kp_lines"]}, loose/tight={r["kp_loose"]}/{r["kp_tight"]}')

    return '\n'.join(lines)


def format_recommend_json(all_results, recommended):
    output = {
        'all_widths': [],
        'recommended': [],
    }
    for r in all_results:
        output['all_widths'].append({
            'width': r['width'],
            'kp_lines': r['kp_lines'],
            'kp_penalty': round(r['kp_penalty'], 1),
            'kp_loose': r['kp_loose'],
            'kp_tight': r['kp_tight'],
            'greedy_lines': r['greedy_lines'],
            'greedy_penalty': round(r['greedy_penalty'], 1),
        })
    for r in recommended:
        output['recommended'].append({
            'width': r['width'],
            'kp_lines': r['kp_lines'],
            'kp_penalty': round(r['kp_penalty'], 1),
            'kp_loose': r['kp_loose'],
            'kp_tight': r['kp_tight'],
            'greedy_lines': r['greedy_lines'],
            'greedy_penalty': round(r['greedy_penalty'], 1),
        })
    return json.dumps(output, indent=2, ensure_ascii=False)


def load_hyphen_dict(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_input(args):
    sources = []
    if args.text:
        sources.append('text')
    if args.file:
        sources.append('file')
    if not sys.stdin.isatty():
        sources.append('stdin')

    if len(sources) > 1:
        print(f'Error: multiple input sources specified ({", ".join(sources)}). Use only one: text argument, -f/--file, or stdin.', file=sys.stderr)
        sys.exit(1)

    if args.text:
        return args.text
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            return f.read()
    elif not sys.stdin.isatty():
        return sys.stdin.read()
    else:
        print('Error: no input provided. Use text argument, -f/--file, or pipe via stdin.', file=sys.stderr)
        sys.exit(1)


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
    parser.add_argument('--recommend', type=float, nargs=3, default=None, metavar=('MIN', 'MAX', 'STEP'),
                        help='Width recommendation: min max step (e.g. --recommend 4.0 10.0 0.5)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--dict', type=str, default=None, dest='dict_path',
                        help='Path to custom hyphenation dictionary (JSON)')

    args = parser.parse_args()

    raw_text = read_input(args)
    text = raw_text.strip()
    if not text:
        print('Error: input text is empty.', file=sys.stderr)
        sys.exit(1)

    hyphen_dict = None
    if args.dict_path:
        hyphen_dict = load_hyphen_dict(args.dict_path)

    if args.compare:
        results = run_compare(text, args.compare, hyphen_dict)
        if args.format == 'json':
            print(format_compare_json(results))
        else:
            print(format_compare_text(results))
    elif args.recommend:
        width_min, width_max, step = args.recommend
        all_results, recommended = run_recommend(text, width_min, width_max, step, hyphen_dict)
        if args.format == 'json':
            print(format_recommend_json(all_results, recommended))
        else:
            print(format_recommend_text(all_results, recommended))
    else:
        paragraphs = split_paragraphs(text)
        is_multi = len(paragraphs) > 1

        if is_multi:
            merged, para_list = run_multi_paragraph(text, args.width, args.algorithm, args.justify, hyphen_dict)
            if args.format == 'json':
                print(format_single_json(merged))
            else:
                print(format_multi_paragraph_text(merged, para_list))
        else:
            results = run_single(text, args.width, args.algorithm, args.justify, hyphen_dict)
            if args.format == 'json':
                print(format_single_json(results))
            else:
                print(format_single_text(results))


if __name__ == "__main__":
    main()
