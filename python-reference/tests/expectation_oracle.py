"""Independent oracle: enumerate actual draws and every legal core subset."""
from collections import Counter
from fractions import Fraction
from itertools import combinations

KINDS = ('pair', 'two_pair', 'three', 'four', 'five', 'full_house', 'flush',
         'straight', 'straight_flush', 'flush_house', 'flush_five', 'high_card')


def enum_expected(deck, k, queries=None):
    cards = [(s, r) for s, row in enumerate(deck) for r, count in enumerate(row) for _ in range(count)]
    k = min(len(cards), k)
    windows = [set(range(start, start + 5)) for start in range(9)] + [{9, 10, 11, 12, 0}]
    totals = {kind: Counter() for kind in KINDS}
    suit_totals = {kind: Counter() for kind in KINDS}
    rank_totals = {kind: Counter() for kind in KINDS}
    possible = Counter()
    histograms = {name: {kind: Counter() for kind in KINDS} for name in (queries or {})}
    events = {name: Counter() for name in ('flower_pot','seeing_double')}
    joints = Counter()
    draws = 0
    for draw in combinations(cards, k):
        draws += 1
        maxima = {kind: Counter() for kind in KINDS}
        suit_maxima = {kind: Counter() for kind in KINDS}
        rank_maxima = {kind: Counter() for kind in KINDS}
        present = set()
        query_max = {name: Counter() for name in (queries or {})}
        event_present = {name: set() for name in events}
        joint_present = set()
        for size in range(1, min(5, k) + 1):
            for core in combinations(draw, size):
                rc = Counter(r for s, r in core)
                counts = sorted(rc.values())
                same_suit = len(set(s for s, r in core)) == 1
                straight = size == 5 and set(rc) in windows
                kinds = []
                for kind, shape in [('high_card', [1]), ('pair', [2]), ('two_pair', [2, 2]),
                                    ('three', [3]), ('four', [4]), ('five', [5]), ('full_house', [2, 3])]:
                    if counts == shape:
                        kinds.append(kind)
                if size == 5 and same_suit:
                    kinds.append('flush')
                    if counts == [2, 3]: kinds.append('flush_house')
                    if counts == [5]: kinds.append('flush_five')
                    if straight: kinds.append('straight_flush')
                if straight:
                    kinds.append('straight')
                cc = Counter(core)
                sc = Counter(s for s, r in core)
                triggers = []
                if any(v >= 2 for v in rc.values()): triggers.append('pair')
                if any(v >= 3 for v in rc.values()): triggers.append('three')
                if any(v >= 4 for v in rc.values()): triggers.append('four')
                if sum(v >= 2 for v in rc.values()) >= 2: triggers.append('two_pair')
                if straight: triggers.append('straight')
                if size == 5 and same_suit: triggers.append('flush')
                for kind in kinds:
                    present.add(kind)
                    for cell, value in cc.items():
                        maxima[kind][cell] = max(maxima[kind][cell], value)
                    for suit, value in sc.items():
                        suit_maxima[kind][suit] = max(suit_maxima[kind][suit], value)
                    for rank, value in rc.items():
                        rank_maxima[kind][rank] = max(rank_maxima[kind][rank], value)
                    for name, target in (queries or {}).items():
                        score = sum(v for (s,r),v in cc.items() if target[s][r])
                        query_max[name][kind] = max(query_max[name][kind], score)
                    if len(sc) == 4: event_present['flower_pot'].add(kind)
                    if sc[2] > 0 and sum(v for s,v in sc.items() if s != 2) > 0: event_present['seeing_double'].add(kind)
                    for trigger in triggers: joint_present.add((kind,trigger))
        for kind in present:
            possible[kind] += 1
            totals[kind].update(maxima[kind])
            suit_totals[kind].update(suit_maxima[kind])
            rank_totals[kind].update(rank_maxima[kind])
            for name in histograms: histograms[name][kind][query_max[name][kind]] += 1
        for name, kinds in event_present.items():
            events[name].update(kinds)
        joints.update(joint_present)
    conditional = {kind: [[Fraction(totals[kind][s, r], possible[kind]) if possible[kind] else Fraction(0)
                          for r in range(13)] for s in range(4)] for kind in KINDS}
    uncond = {kind: [[Fraction(totals[kind][s, r], draws) for r in range(13)] for s in range(4)] for kind in KINDS}
    suits = {kind: [Fraction(suit_totals[kind][s], possible[kind]) if possible[kind] else Fraction(0)
                    for s in range(4)] for kind in KINDS}
    ranks = {kind: [Fraction(rank_totals[kind][r], possible[kind]) if possible[kind] else Fraction(0)
                    for r in range(13)] for kind in KINDS}
    return dict(expected_counts=conditional, unconditional_counts=uncond,
                suit_expected_counts=suits, rank_expected_counts=ranks,
                target_distributions={name:{kind:[Fraction(counts[j],draws) for j in range(6)] for kind,counts in data.items()} for name,data in histograms.items()},
                joker_events={name:{kind:Fraction(counts[kind],draws) for kind in KINDS} for name,counts in events.items()},
                type_joints={kind:{trigger:Fraction(joints[kind,trigger],draws) for trigger in ('pair','two_pair','three','four','straight','flush')} for kind in KINDS},
                marginal={kind: Fraction(possible[kind], draws) for kind in KINDS})
