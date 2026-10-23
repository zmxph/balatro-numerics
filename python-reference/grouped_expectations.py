"""Exact greedy expectations for a whole suit/rank, not sums of cell maxima."""
from fractions import Fraction
from math import comb

SHAPES = {'pair': (2,), 'two_pair': (2, 2), 'three': (3,), 'four': (4,),
          'five': (5,), 'full_house': (2, 3)}


def grouped_expectations(M, k, marginal, queries=None):
    n = sum(map(sum, M))
    den = comb(n, k)
    ranks = [sum(row[r] for row in M) for r in range(13)]
    suits = list(map(sum, M))

    def C(n, k):
        return comb(n, k) if 0 <= k <= n else 0

    def impossible(count):
        return {t: {-1: C(count, t)} for t in range(min(count, k) + 1)}

    cache = {}

    def pattern(counts, targets, shape):
        # A max-plus selection DP: each rank may fill at most one shape slot.
        key = (tuple(sorted(zip(counts, targets))), shape)
        if key in cache:
            return cache[key]
        can = any(c >= shape[0] for c in counts) if len(shape) == 1 else any(
            i != j and a >= shape[0] and b >= shape[1]
            for i, a in enumerate(counts) for j, b in enumerate(counts))
        if not can or sum(shape) > k:
            return impossible(sum(counts))
        initial = (-1,) if len(shape) == 1 else (-1, -1, -1)
        dp = {(0, initial): 1}
        for count, target in zip(counts, targets):
            if not count:
                continue
            options = {}
            for j in range(min(target, k) + 1):
                for a in range(min(count - target, k - j) + 1):
                    token = (j + a, min(j, 5))
                    options[token] = options.get(token, 0) + C(target, j) * C(count - target, a)
            ndp = {}
            for (t, state), ways in dp.items():
                for (take, j), weight in options.items():
                    if t + take > k:
                        continue
                    a = min(j, shape[0]) if take >= shape[0] else -1
                    if len(shape) == 1:
                        new = (max(state[0], a),)
                    else:
                        b = min(j, shape[1]) if take >= shape[1] else -1
                        both = max(state[2], state[0] + b if state[0] >= 0 and b >= 0 else -1,
                                   state[1] + a if state[1] >= 0 and a >= 0 else -1)
                        new = (max(state[0], a), max(state[1], b), both)
                    dest = (t + take, new)
                    ndp[dest] = ndp.get(dest, 0) + ways * weight
            dp = ndp
        out = {}
        for (t, state), ways in dp.items():
            row = out.setdefault(t, {})
            row[state[-1]] = row.get(state[-1], 0) + ways
        cache[key] = out
        return out

    def straight(counts, targets):
        # Retain the last four ranks, the ace, and the best completed window.
        # Tokens: absent=0, other cards only=1, at least one target card=2.
        dp = {(0, (0, 0, 0, 0), 0, -1): 1}
        for r, (count, target) in enumerate(zip(counts, targets)):
            ndp = {}
            options = [(0, 0, 1)]
            for take in range(1, min(count, k) + 1):
                without = C(count - target, take)
                options.extend([(take, 1, without), (take, 2, C(count, take) - without)])
            for (t, history, ace, best), ways in dp.items():
                for take, token, weight in options:
                    if not weight or t + take > k:
                        continue
                    newbest = max(best, sum(x == 2 for x in history) + (token == 2)) if token and all(history) else best
                    state = (t + take, history[1:] + (token,), token if r == 0 else ace, newbest)
                    ndp[state] = ndp.get(state, 0) + ways * weight
            dp = ndp
        out = {}
        for (t, history, ace, best), ways in dp.items():
            if ace and all(history):
                best = max(best, sum(x == 2 for x in history) + (ace == 2))
            row = out.setdefault(t, {})
            row[best] = row.get(best, 0) + ways
        return out

    def flush_target(s, target):
        out = {}
        for t in range(min(suits[s], k) + 1):
            row = out.setdefault(t, {})
            for j in range(min(target, t) + 1):
                ways = C(target, j) * C(suits[s] - target, t - j)
                score = min(j, 5) if t >= 5 else -1
                row[score] = row.get(score, 0) + ways
        return out

    def weighted(dp, outside=0, event=False):
        return Fraction(sum((int(score >= 0) if event else max(0, score)) * ways * C(outside, k - t)
                            for t, states in dp.items() for score, ways in states.items()), den)

    def best_suit(rows, raw=False):
        dp = {0: {-1: 1}}
        for row in rows:
            ndp = {}
            for t, states in dp.items():
                for take, row_states in row.items():
                    if take + t > k:
                        continue
                    dest = ndp.setdefault(t + take, {})
                    for score, ways in states.items():
                        for other, weight in row_states.items():
                            best = max(score, other)
                            dest[best] = dest.get(best, 0) + ways * weight
            dp = ndp
        return dp if raw else weighted(dp)

    suit_values = {kind: [Fraction(0)] * 4 for kind in marginal}
    rank_values = {kind: [Fraction(0)] * 13 for kind in marginal}
    zero_targets = [0] * 13
    for s in range(4):
        for kind, shape in SHAPES.items():
            suit_values[kind][s] = weighted(pattern(ranks, M[s], shape))
        suit_values['straight'][s] = weighted(straight(ranks, M[s]))
        suit_values['flush'][s] = Fraction(5 * sum(C(suits[s], t) * C(n - suits[s], k - t)
                                                  for t in range(5, min(suits[s], k) + 1)), den)
        for kind, row in [('straight_flush', straight(M[s], zero_targets)),
                          ('flush_house', pattern(M[s], zero_targets, (2, 3))),
                          ('flush_five', pattern(M[s], zero_targets, (5,)))]:
            suit_values[kind][s] = 5 * weighted(row, n - suits[s], event=True)
        suit_values['high_card'][s] = Fraction(den - C(n - suits[s], k), den)

    for r in range(13):
        target = [0] * 13
        target[r] = ranks[r]
        for kind, shape in SHAPES.items():
            rank_values[kind][r] = weighted(pattern(ranks, target, shape))
        rank_values['straight'][r] = weighted(straight(ranks, target))
        rank_values['high_card'][r] = Fraction(den - C(n - ranks[r], k), den)
        rank_values['flush'][r] = best_suit([flush_target(s, M[s][r]) for s in range(4)])
        row_straights, row_houses, row_fives = [], [], []
        for s in range(4):
            target = [0] * 13
            target[r] = M[s][r]
            row_straights.append(straight(M[s], target))
            row_houses.append(pattern(M[s], target, (2, 3)))
            row_fives.append(pattern(M[s], target, (5,)))
        rank_values['straight_flush'][r] = best_suit(row_straights)
        rank_values['flush_house'][r] = best_suit(row_houses)
        rank_values['flush_five'][r] = best_suit(row_fives)

    for kind, p in marginal.items():
        suit_values[kind] = [v / p if p else Fraction(0) for v in suit_values[kind]]
        rank_values[kind] = [v / p if p else Fraction(0) for v in rank_values[kind]]
    output = dict(suit_expected_counts=suit_values, rank_expected_counts=rank_values)
    if queries is not None:
        def histogram(dp):
            return [Fraction(dp.get(k, {}).get(j, 0), den) for j in range(6)]

        output['target_distributions'] = {}
        for name, target in queries.items():
            if len(target) != 4 or any(len(row) != 13 for row in target) or any(
                    not 0 <= target[s][r] <= M[s][r] for s in range(4) for r in range(13)):
                raise ValueError('Invalid target matrix')
            totals = [sum(row[r] for row in target) for r in range(13)]
            hist = {kind: histogram(pattern(ranks, totals, shape)) for kind, shape in SHAPES.items()}
            hist['straight'] = histogram(straight(ranks, totals))
            hist['high_card'] = [Fraction(0)] * 6
            if k:
                hist['high_card'][0] = Fraction(C(n - sum(totals), k), den)
                hist['high_card'][1] = 1 - hist['high_card'][0]
            for kind, rows in [
                    ('flush', [flush_target(s, sum(target[s])) for s in range(4)]),
                    ('straight_flush', [straight(M[s], target[s]) for s in range(4)]),
                    ('flush_house', [pattern(M[s], target[s], (2, 3)) for s in range(4)]),
                    ('flush_five', [pattern(M[s], target[s], (5,)) for s in range(4)])]:
                hist[kind] = histogram(best_suit(rows, raw=True))
            output['target_distributions'][name] = hist
        # A Flush core has exactly five cards, even when its trigger is a pair.
        output['flush_contains'] = {}
        for kind in ('pair', 'two_pair', 'three', 'four'):
            rows = []
            for s in range(4):
                dp = pattern(M[s], zero_targets, SHAPES[kind])
                row = {}
                for t, states in dp.items():
                    row[t] = {0: 0, 1: 0}
                    for score, ways in states.items():
                        row[t][int(t >= 5 and score >= 0)] += ways
                rows.append(row)
            output['flush_contains'][kind] = best_suit(rows)
    return output
