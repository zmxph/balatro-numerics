"""每种牌型的逐格最大参与张数条件期望，精确整数 DP / Fraction。

expected_counts[T][s][r] = E[max_{合法 T 核心组合} 目标格张数 | 可组成 T]。
只计算组成牌型的牌，不计算顺带打出的牌；沿用 contains 的重叠事件口径。
可组成 T 但目标牌无法参与时记 0。P(T)=0 时条件期望未定义，API 约定输出 0。
同一矩阵的不同格独立优化，未必对应同一次出牌。花色行沿用 Lua 顺序：
黑桃、红桃、梅花、方块；列 A,2,...,K。游戏中 k=min(n,ceil(1.8*m))。
"""
from fractions import Fraction
from math import ceil, comb

import card_type_probs as old
from grouped_expectations import grouped_expectations

KINDS = (*old.KINDS, 'five', 'high_card')
CAPS = dict(pair=2, two_pair=2, three=3, four=4, five=5,
            full_house=3, flush=5, straight=1, straight_flush=1,
            flush_house=3, flush_five=5, high_card=1)


def _choose(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def _zeros():
    return [[Fraction(0) for _ in range(13)] for _ in range(4)]


def compute_expectations(M, k, *, marginal=None, queries=None):
    """k 为实际抽取张数；按手牌上限调用请用 for_hand_limit(M,m)。

    返回 marginal、expected_counts（条件）、unconditional_counts（失败记零），
    以及 suit_expected_counts（4 项）、rank_expected_counts（13 项）。
    后两者按整组目标重新优化核心，不是把逐格矩阵相加。
    marginal 可传入已计算的精确 Fraction 字典，以复用现有计算。
    """
    if len(M) != 4 or any(len(row) != 13 for row in M):
        raise ValueError('M must have four rows and thirteen columns')
    if any(not isinstance(c, int) or isinstance(c, bool) or c < 0 for row in M for c in row):
        raise ValueError('Deck counts must be nonnegative integers')
    n = sum(map(sum, M))
    k = min(n, max(0, ceil(k)))
    den = comb(n, k)
    ranks, suits = old.rank_totals(M), old.suit_totals(M)
    if not k:
        p = {kind: Fraction(0) for kind in KINDS}
    else:
        p = dict(old.marginal_probs(M, k) if marginal is None else marginal)
        # Group by rank, so "some cell >=5" becomes "some rank >=5".
        p['five'] = old.flush_five_marginal([ranks] + [[0] * 13 for _ in range(3)], k)
        p['high_card'] = Fraction(1)
    uncond = {kind: _zeros() for kind in KINDS}
    for r in range(13):
        od = old._other_ranks_dp([ranks[rr] for rr in range(13) if rr != r], k)
        for s in range(4):
            c = M[s][r]
            if not c:
                continue
            nums = {kind: 0 for kind in ('pair', 'two_pair', 'three', 'four', 'five', 'full_house')}
            # Separate j target copies from a same-rank cards of other suits.
            for j in range(1, min(c, k) + 1):
                for a in range(min(ranks[r] - c, k - j) + 1):
                    count = j + a
                    weight = comb(c, j) * comb(ranks[r] - c, a)
                    for (q, o2, o3), ways in od.items():
                        if q != k - count:
                            continue
                        hits = dict(pair=count >= 2, two_pair=count >= 2 and o2,
                                    three=count >= 3, four=count >= 4, five=count >= 5,
                                    full_house=(count >= 3 and o2) or (count >= 2 and o3))
                        for kind, hit in hits.items():
                            if hit:
                                cap = (3 if count >= 3 and o2 else 2) if kind == 'full_house' else CAPS[kind]
                                nums[kind] += weight * ways * min(j, cap)
            for kind, num in nums.items():
                uncond[kind][s][r] = Fraction(num, den)

            row_dp = old._other_ranks_dp([M[s][rr] for rr in range(13) if rr != r], k)
            flush = house = five = seen = 0
            for j in range(1, min(c, k) + 1):
                weight = comb(c, j)
                all_others = weight * _choose(n - c, k - j)
                seen += all_others
                if j >= 5:
                    five += 5 * all_others
                for b in range(max(0, 5 - j), min(suits[s] - c, k - j) + 1):
                    flush += min(j, 5) * weight * comb(suits[s] - c, b) * _choose(n - suits[s], k - j - b)
                for (q, o2, o3), ways in row_dp.items():
                    cap = 3 if j >= 3 and o2 else 2 if j >= 2 and o3 else 0
                    if cap:
                        house += min(j, cap) * weight * ways * _choose(n - suits[s], k - j - q)
            for kind, num in [('flush', flush), ('flush_house', house), ('flush_five', five), ('high_card', seen)]:
                uncond[kind][s][r] = Fraction(num, den)
    # These cores can contain at most one target copy, so E[max] = P(max>=1).
    uncond['straight'] = old.straight_matrix(M, k)
    uncond['straight_flush'] = old.straight_matrix(M, k, flush_only=True)
    expected = {kind: [[v / p[kind] if p[kind] else Fraction(0) for v in row]
                       for row in uncond[kind]] for kind in KINDS}
    return dict(marginal=p, expected_counts=expected, unconditional_counts=uncond, n=n, k=k,
                **grouped_expectations(M, k, p, queries))


def for_hand_limit(M, m):
    result = compute_expectations(M, ceil(1.8 * max(0, m)))
    result['m'] = m
    return result


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deck', type=Path, help='4x13 integer matrix as JSON; default: standard 52 cards')
    parser.add_argument('--hand-limit', type=float, default=8)
    args = parser.parse_args()
    deck = json.loads(args.deck.read_text(encoding='utf-8-sig')) if args.deck else [[1] * 13 for _ in range(4)]
    output = for_hand_limit(deck, args.hand_limit)
    print(json.dumps(output, default=float, ensure_ascii=False, indent=2))
