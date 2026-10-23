# 每张牌的牌型参与概率: 10 个 4x13 矩阵(精确 DP, 无蒙特卡洛)
# 输入: 4x13 计数矩阵 M[suit][rank] (每格 0-n 张), k = ceil(1.8*m) (m = 手牌上限,
#       模型含义为"抽牌+弃牌"后的可见牌数), n = sum(M)
# 输出: 对每个牌型 T, 矩阵 M_T[s][r] = P(抽 k 张能打出包含 (s,r) 这张牌的 T 型手牌)
# T 的枚举: pair, two_pair, three, four, full_house, flush, straight,
#           straight_flush, flush_house, flush_five
# 关键点: 打出的是手牌的最优子集(最多 5 张), 所以"包含 x 的 T 型手牌"= 以 x 为必含牌的
# 构成问题; 对每格 (s,r) 单独做条件 DP(该格至少抽 1 张), 事件条件按 T 分:
#   pair/two_pair/three/four/full_house: 只看点数总量, 锚定牌所在点数额外拆分计数
#   flush: 只看花色总量, 锚定花色 >=5
#   straight: 锚定点数所在圆形连续段(顺时针+逆时针, 各封顶4)之和 >=4
#   straight_flush: 同上但连续段只看锚定花色那一行
#   flush_house: 锚定格 >=3 且同行其他点数 >=2, 或锚定格 >=2 且同行其他点数 >=3
#   flush_five: 锚定格 >=5
# 概率 = 事件方案数 / C(n,k), 全程精确整数/Fraction
import random
from fractions import Fraction
from math import comb
from itertools import combinations

# ---------- 基础 ----------


def rank_totals(M):
    return [sum(M[s][r] for s in range(4)) for r in range(13)]


def suit_totals(M):
    return [sum(M[s]) for s in range(4)]


# 10 种顺子窗口(下标 0=A, 1=2, ..., 12=K), 枚举校验用
STRAIGHT_WINDOWS = ((0, 1, 2, 3, 4), (1, 2, 3, 4, 5), (2, 3, 4, 5, 6), (3, 4, 5, 6, 7),
                    (4, 5, 6, 7, 8), (5, 6, 7, 8, 9), (6, 7, 8, 9, 10), (7, 8, 9, 10, 11),
                    (8, 9, 10, 11, 12), (9, 10, 11, 12, 0))

KINDS = ('pair', 'two_pair', 'three', 'four', 'full_house', 'flush',
         'straight', 'straight_flush', 'flush_house', 'flush_five')

RANK_LABEL = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K")


def _zeros():
    return [[Fraction(0)] * 13 for _ in range(4)]


# ---------- 1) 对子族: pair / two_pair / three / four / full_house ----------
# 状态: (t, rr, o2, o3). rr = 锚定点数的已抽张数(封顶4), o2/o3 = 其余 12 个点数中
# 是否存在 >=2 / >=3 张. 锚定格拆成 c(锚定) 与 ms[r0]-c(同点数其他牌)两部分, c 部分强制 >=1
_PAIR_ACCEPT = {
    'pair': lambda rr, o2, o3: rr >= 2,
    'two_pair': lambda rr, o2, o3: rr >= 2 and o2,
    'three': lambda rr, o2, o3: rr >= 3,
    'four': lambda rr, o2, o3: rr >= 4,
    'full_house': lambda rr, o2, o3: (rr >= 3 and o2) or (rr >= 2 and o3),
}


def _other_ranks_dp(other_ms, kmax):
    """其余点数的 DP: (q, o2, o3) -> 方案数"""
    dp = {(0, 0, 0): 1}
    for m in other_ms:
        ndp = {}
        for (q, o2, o3), w in dp.items():
            for take in range(0, min(m, kmax - q) + 1):
                key = (q + take, o2 or (take >= 2), o3 or (take >= 3))
                ndp[key] = ndp.get(key, 0) + w * comb(m, take)
        dp = ndp
    return dp


def pair_family_matrix(M, k, kind):
    ms = rank_totals(M)
    n = sum(ms)
    den = comb(n, k)
    if den == 0:
        return _zeros()
    acc = _PAIR_ACCEPT[kind]
    out = _zeros()
    for r0 in range(13):
        other = [ms[r] for r in range(13) if r != r0]
        od = _other_ranks_dp(other, k)
        by_q = {}
        for (q, o2, o3), w in od.items():
            d = by_q.setdefault(q, {})
            d[(o2, o3)] = d.get((o2, o3), 0) + w
        for s0 in range(4):
            c = M[s0][r0]
            if c == 0:
                continue
            rest = ms[r0] - c          # 同点数其他花色的牌
            num = 0
            for j in range(1, min(c, k) + 1):
                for a in range(0, min(rest, k - j) + 1):
                    rr = min(j + a, 4)
                    q = k - j - a
                    wj = comb(c, j) * comb(rest, a)
                    for (o2, o3), w in by_q.get(q, {}).items():
                        if acc(rr, o2, o3):
                            num += wj * w
            out[s0][r0] = Fraction(num, den)
    return out


# ---------- 2) flush: 只看花色总量 ----------


def flush_matrix(M, k):
    asums = suit_totals(M)
    n = sum(asums)
    den = comb(n, k)
    if den == 0:
        return _zeros()
    out = _zeros()
    for s0 in range(4):
        a = asums[s0]
        other_suits = n - a
        for r0 in range(13):
            c = M[s0][r0]
            if c == 0:
                continue
            rest_row = a - c
            num = 0
            for j in range(1, min(c, k) + 1):
                for b in range(0, min(rest_row, k - j) + 1):
                    if j + b < 5:
                        continue
                    q = k - j - b
                    num += comb(c, j) * comb(rest_row, b) * comb(other_suits, q)
            out[s0][r0] = Fraction(num, den)
    return out


# ---------- 3) straight / straight_flush: 合法窗口覆盖 ----------
# 条件: 存在覆盖 r0 的合法 5 连窗口 W(10 个标准窗口之一), 且 W 的全部点数在场.
# 实现: 每个锚定格维护"存活窗口"位掩码(只统计含 r0 的窗口),
#       某点数缺席则杀死所有含它的窗口; 收尾仍有存活窗口才接受.
# 注: 不能用"锚定点两侧圆形连续段长度和>=4"——那会把 {K,A,2,3,4}
#       这类非法跨段(K 与 2 夹住 A)误判为顺子(如 A,2,3,4,K 不成顺子).
def straight_matrix(M, k, flush_only=False):
    """flush_only=False: 任意花色的点数在场上即可(顺子);
    flush_only=True: 连续段只看锚定牌所在花色那一行(同花顺)"""
    ms = rank_totals(M)
    n = sum(ms)
    den = comb(n, k)
    if den == 0:
        return _zeros()
    # 每个点数缺席时杀死的窗口位
    kill = [0] * 13
    for i, W in enumerate(STRAIGHT_WINDOWS):
        for x in W:
            kill[x] |= 1 << i
    out = _zeros()
    for r0 in range(13):
        rel = 0                       # 覆盖 r0 的全部窗口位
        for i, W in enumerate(STRAIGHT_WINDOWS):
            if r0 in W:
                rel |= 1 << i
        for s0 in range(4):
            c = M[s0][r0]
            if c == 0:
                continue
            rest = ms[r0] - c          # 同点数其他花色: 只占额度, 不改变在场状态
            num = 0
            for j in range(1, min(c, k) + 1):
                for a in range(0, min(rest, k - j) + 1):
                    dp = {(j + a, rel): comb(c, j) * comb(rest, a)}
                    for r in range(13):
                        if r == r0:
                            continue
                        if not flush_only:
                            steps = ((ms[r], True),)
                        else:
                            cr = M[s0][r]      # 同花顺: 只看锚定牌所在花色这一行
                            steps = ((cr, True),)
                            if ms[r] - cr > 0:
                                steps = steps + ((ms[r] - cr, False),)
                        for tot, is_pres in steps:
                            # 注意 tot==0 时也必须走一遍(take 只能为 0), 否则该点数
                            # 无法杀死含它的窗口(牌组中不存在的点数恒缺席)
                            ndp = {}
                            for (t, mask), w in dp.items():
                                for take in range(0, min(tot, k - t) + 1):
                                    nm = mask & ~kill[r] if (is_pres and take == 0) else mask
                                    key = (t + take, nm)
                                    ndp[key] = ndp.get(key, 0) + w * comb(tot, take)
                            dp = ndp
                    for (t, mask), w in dp.items():
                        if t == k and mask:
                            num += w
            out[s0][r0] = Fraction(num, den)
    return out


# ---------- 4) flush_house / flush_five: 只看锚定花色那一行 ----------


def flush_house_matrix(M, k):
    """同花葫芦: 5 张同花色且为 3+2. 锚定格可属三条部分(>=3 且同行他点>=2)或对子部分(>=2 且同行他点>=3)"""
    ms = rank_totals(M)
    n = sum(ms)
    den = comb(n, k)
    if den == 0:
        return _zeros()
    out = _zeros()
    for s0 in range(4):
        row = M[s0]
        for r0 in range(13):
            c = row[r0]
            if c == 0:
                continue
            # 其余点数的两步走法: 本行格(影响 o2/o3) 与其他花色(只加 t)
            others = []
            if ms[r0] - c > 0:
                others.append((ms[r0] - c, False))   # 同点数其他花色: 只加 t
            for r in range(13):
                if r == r0:
                    continue
                others.append((row[r], True))
                if ms[r] - row[r] > 0:
                    others.append((ms[r] - row[r], False))
            num = 0
            for j in range(1, min(c, k) + 1):
                csr = min(j, 5)
                dp = {(j, 0, 0): comb(c, j)}  # (t, o2, o3)
                for tot, is_row in others:
                    ndp = {}
                    for (t, o2, o3), w in dp.items():
                        for take in range(0, min(tot, k - t) + 1):
                            key = (t + take, o2 or (is_row and take >= 2),
                                   o3 or (is_row and take >= 3))
                            ndp[key] = ndp.get(key, 0) + w * comb(tot, take)
                    dp = ndp
                for (t, o2, o3), w in dp.items():
                    if t != k:
                        continue
                    if (csr >= 3 and o2) or (csr >= 2 and o3):
                        num += w
            out[s0][r0] = Fraction(num, den)
    return out


def flush_five_matrix(M, k):
    """同花五条: 5 张同花色同点数, 即锚定格抽 >=5"""
    n = sum(sum(row) for row in M)
    den = comb(n, k)
    if den == 0:
        return _zeros()
    out = _zeros()
    for s in range(4):
        for r in range(13):
            c = M[s][r]
            if c == 0:
                continue
            num = sum(comb(c, j) * comb(n - c, k - j)
                      for j in range(5, min(c, k) + 1))
            out[s][r] = Fraction(num, den)
    return out


# ---------- 5) 边际概率: P(手牌能打出各牌型), contains 口径 ----------
# 对子族/顺子族边际复用 hand_type_probs.py 的已验证 DP; 此处补同花葫芦与
# 同花五条, 并统一聚合为 marginal_probs(M, k) -> {牌型: P}


def _row_house_dp(row, k):
    """单行 13 格 DP: 状态 (c, n3, n2) -> 方案数. c = 行内已抽张数,
    n3/n2 = 行内 >=3 / >=2 张的点数个数(封顶 2, n2 计数含 n3 的点)"""
    dp = {(0, 0, 0): 1}
    for m in row:
        ndp = {}
        for (c, n3, n2), w in dp.items():
            for take in range(0, min(m, k - c) + 1):
                key = (c + take, min(2, n3 + (take >= 3)), min(2, n2 + (take >= 2)))
                ndp[key] = ndp.get(key, 0) + w * comb(m, take)
        dp = ndp
    return dp


def house_marginal(M, k):
    """P(能打出同花葫芦) = P(某行内存在 >=3 的点数与另一个 >=2 的点数).
    行间独立, 跨行只需合并 (总张数, 是否已有行满足)"""
    n = sum(sum(row) for row in M)
    den = comb(n, k)
    if den == 0:
        return Fraction(0)
    dp = {(0, 0): 1}
    for row in M:
        rd = _row_house_dp(row, k)
        ndp = {}
        for (t, sat), w in dp.items():
            for (c, n3, n2), w2 in rd.items():
                if t + c > k:
                    continue
                key = (t + c, sat or (n3 >= 1 and n2 >= 2))
                ndp[key] = ndp.get(key, 0) + w * w2
        dp = ndp
    return Fraction(dp.get((k, True), 0), den)


def flush_five_marginal(M, k):
    """P(能打出同花五条) = P(某格抽到 >=5 张)"""
    n = sum(sum(row) for row in M)
    den = comb(n, k)
    if den == 0:
        return Fraction(0)
    dp = {(0, 0): 1}                       # (t, 是否已有格 >=5)
    for row in M:
        for m in row:
            ndp = {}
            for (t, f), w in dp.items():
                for take in range(0, min(m, k - t) + 1):
                    key = (t + take, f or take >= 5)
                    ndp[key] = ndp.get(key, 0) + w * comb(m, take)
            dp = ndp
    return Fraction(dp.get((k, 1), 0), den)


def marginal_probs(M, k):
    """10 种牌型的 P(手牌能打出), contains 口径, 精确无重叠.
    对子族/flush/顺子/同花顺由 hand_type_probs 的 DP 给出,
    同花葫芦/同花五条为上面新增 DP"""
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        from hand_type_probs import (probs, flush_probs, straight_probs,
                                     straight_flush_probs)
    ms = rank_totals(M)
    P = probs(ms, k)[k]['contains']
    return {
        'pair': P['pair'],
        'two_pair': P['two_pair'],
        'three': P['three'],
        'four': P['four'],
        'full_house': P['full_house'],
        'flush': flush_probs(suit_totals(M), k)[k],
        'straight': straight_probs(ms, k)[k],
        'straight_flush': straight_flush_probs(M, k)[k],
        'flush_house': house_marginal(M, k),
        'flush_five': flush_five_marginal(M, k),
    }


def enum_house_five(M, k):
    """全枚举校验(与上面两个边际 DP 独立): 返回 (P(同花葫芦), P(同花五条))"""
    labels = [(s, r) for s in range(4) for r in range(13) for _ in range(M[s][r])]
    n = len(labels)
    den = comb(n, k)
    h = f5 = 0
    for hand in combinations(labels, k):
        cc = {}
        for s, r in hand:
            cc[(s, r)] = cc.get((s, r), 0) + 1
        for s in range(4):
            cnts = [cc.get((s, r), 0) for r in range(13)]
            n3 = sum(1 for v in cnts if v >= 3)
            n2 = sum(1 for v in cnts if v >= 2)
            if n3 >= 1 and n2 >= 2:
                h += 1
                break
        f5 += any(v >= 5 for v in cc.values())
    return Fraction(h, den), Fraction(f5, den)


# ---------- 6) 全枚举校验(确定性, 与 DP 独立) ----------


def enum_card_probs(M, k):
    labels = [(s, r) for s in range(4) for r in range(13) for _ in range(M[s][r])]
    n = len(labels)
    den = comb(n, k)
    acc = {kd: [[0] * 13 for _ in range(4)] for kd in KINDS}
    for hand in combinations(labels, k):
        rc, sc, cc = [0] * 13, [0] * 4, {}
        for s, r in hand:
            rc[r] += 1
            sc[s] += 1
            cc[(s, r)] = cc.get((s, r), 0) + 1
        for s, r in set(hand):
            o2 = any(rc[r2] >= 2 for r2 in range(13) if r2 != r)
            o3 = any(rc[r2] >= 3 for r2 in range(13) if r2 != r)
            ro2 = any(cc.get((s, r2), 0) >= 2 for r2 in range(13) if r2 != r)
            ro3 = any(cc.get((s, r2), 0) >= 3 for r2 in range(13) if r2 != r)
            acc['pair'][s][r] += rc[r] >= 2
            acc['three'][s][r] += rc[r] >= 3
            acc['four'][s][r] += rc[r] >= 4
            acc['two_pair'][s][r] += rc[r] >= 2 and o2
            acc['full_house'][s][r] += (rc[r] >= 3 and o2) or (rc[r] >= 2 and o3)
            acc['flush'][s][r] += sc[s] >= 5
            acc['straight'][s][r] += any(all(rc[x] >= 1 for x in W)
                                          for W in STRAIGHT_WINDOWS if r in W)
            acc['straight_flush'][s][r] += any(all(cc.get((s, x), 0) >= 1 for x in W)
                                                for W in STRAIGHT_WINDOWS if r in W)
            acc['flush_house'][s][r] += (cc.get((s, r), 0) >= 3 and ro2) or \
                                         (cc.get((s, r), 0) >= 2 and ro3)
            acc['flush_five'][s][r] += cc.get((s, r), 0) >= 5
    return {kd: [[Fraction(v, den) for v in row] for row in acc[kd]] for kd in KINDS}


# ---------- 6) 计算全部 10 个矩阵 ----------


def all_matrices(M, k):
    return {
        'pair': pair_family_matrix(M, k, 'pair'),
        'two_pair': pair_family_matrix(M, k, 'two_pair'),
        'three': pair_family_matrix(M, k, 'three'),
        'four': pair_family_matrix(M, k, 'four'),
        'full_house': pair_family_matrix(M, k, 'full_house'),
        'flush': flush_matrix(M, k),
        'straight': straight_matrix(M, k),
        'straight_flush': straight_matrix(M, k, flush_only=True),
        'flush_house': flush_house_matrix(M, k),
        'flush_five': flush_five_matrix(M, k),
    }


def show(Mt, title, k):
    print(f"== {title} (k={k}) ==")
    print("        " + "".join(f"{RANK_LABEL[r]:>9}" for r in range(13)))
    for s in range(4):
        print(f"suit {s} " + "".join(f"{float(v):>9.6f}" for v in Mt[s]))
    print()


def run_checks(m=8):
    """小样本与结构校验(全枚举/闭式计数/结构性质, 独立于 DP 实现), 耗时较长.
    日常出数时注释掉 __main__ 里的 run_checks(...) 调用即可."""
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        from hand_type_probs import (probs, flush_probs, straight_probs,
                                     straight_flush_probs)

    k = -(-m * 9 // 5)
    STD = [[1] * 13] * 4        # 正常 52 牌组, 每格 1 张
    print(f"校验: 正常 52 牌组(每格 1 张), m={m}, k=ceil(1.8*m)={k}\n")

    # ===== check-1: 小牌组 10 类 DP == 全枚举(独立实现) =====
    decks = (
        # A2345 双花色(基础 + 与对子/同花重合)
        ([[1] * 5 + [0] * 8, [1] * 5 + [0] * 8, [0] * 13, [0] * 13], 6),
        # TJQKA 回环(回环窗口 + 同花顺回环)
        ([[1] + [0] * 8 + [1] * 4, [1] + [0] * 8 + [1] * 4, [0] * 13, [0] * 13], 5),
        # 同格 5 副本与 3 副本(同花五条/同花葫芦/葫芦/四条可达)
        ([[5, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
          [3, 3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          [0] * 13, [0] * 13], 6),
        # 0-2 副本混合(一般副本结构)
        ([[2, 1, 1, 0, 1, 1, 2, 0, 1, 1, 0, 0, 0],
          [1, 2, 0, 1, 1, 0, 2, 1, 1, 0, 0, 0, 0],
          [0] * 13, [0] * 13], 6),
    )
    for D, kk in decks:
        dp, en = all_matrices(D, kk), enum_card_probs(D, kk)
        for kd in KINDS:
            for s in range(4):
                for r in range(13):
                    assert dp[kd][s][r] == en[kd][s][r], (kd, s, r)
    print("[check-1] 4 个小牌组(同格 5/3 副本, 0-2 副本, TJQKA 回环) 10 类 DP == 全枚举  OK\n")

    # ===== check-2: 标准牌组 k=5 闭式计数 =====
    A5 = all_matrices(STD, 5)
    C5 = comb(52, 5)
    win_cnt = [sum(1 for W in STRAIGHT_WINDOWS if r in W) for r in range(13)]
    closed = {
        # 手牌含该牌(1 张) + 同点数再抽 a 张 + 其余牌补齐 5 张
        'pair': Fraction(sum(comb(3, a) * comb(48, 4 - a) for a in range(1, 4)), C5),
        # 锚定点成一对 + 另一点数成一对(其余 4 张里非同点且互异)
        'two_pair': Fraction(9864, C5),
        'three': Fraction(comb(3, 2) * comb(48, 2) + comb(3, 3) * comb(48, 1), C5),
        'four': Fraction(comb(3, 3) * comb(48, 1), C5),
        'full_house': Fraction(comb(3, 2) * comb(12, 1) * comb(4, 2)
                               + comb(3, 1) * comb(12, 1) * comb(4, 3), C5),
        'flush': Fraction(comb(12, 4), C5),
        'flush_house': Fraction(0),   # 每格 1 张, 结构性不可能
        'flush_five': Fraction(0),
    }
    for kd, e in closed.items():
        for s in range(4):
            for r in range(13):
                assert A5[kd][s][r] == e, (kd, s, r, float(A5[kd][s][r]))
    for s in range(4):
        for r in range(13):
            # 顺子: 覆盖该点数的窗口数 x 每窗 4^4 种抽法; 同花顺: 窗口数 x 1
            assert A5['straight'][s][r] == Fraction(win_cnt[r] * 4 ** 4, C5)
            assert A5['straight_flush'][s][r] == Fraction(win_cnt[r], C5)
    assert sum(A5['straight_flush'][s][r] for s in range(4) for r in range(13)) \
        == Fraction(5 * 40, C5)      # 5 张牌 x 40 种同花顺 = 每张牌的参与概率之和
    print("[check-2] 标准牌组 k=5, 10 类逐一等于闭式计数(顺子每格=覆盖窗口数x4^4),"
          "且 sum(M_SF)=5*40/C(52,5)  OK\n")

    # ===== check-3: 标准牌组 k=12 结构性质 =====
    A8 = all_matrices(STD, k)
    for kd in ('pair', 'two_pair', 'three', 'four', 'full_house', 'straight',
               'straight_flush'):
        for r in range(13):
            assert len({A8[kd][s][r] for s in range(4)}) == 1, (kd, r)  # 花色对称
    for s in range(4):
        assert len({A8['flush'][s][r] for r in range(13)}) == 1, s      # 点数对称
    for kd in ('flush_house', 'flush_five'):
        assert all(A8[kd][s][r] == 0 for s in range(4) for r in range(13)), kd
    Pp = probs([4] * 13, k)[k]['contains']
    bounds = {'pair': Pp['pair'], 'two_pair': Pp['two_pair'], 'three': Pp['three'],
              'four': Pp['four'], 'full_house': Pp['full_house'],
              'flush': flush_probs([13] * 4, k)[k],
              'straight': straight_probs([4] * 13, k)[k],
              'straight_flush': straight_flush_probs(STD, k)[k],
              'flush_house': Fraction(0), 'flush_five': Fraction(0)}
    for kd, P in bounds.items():
        for s in range(4):
            for r in range(13):
                assert A8[kd][s][r] <= P, (kd, s, r)   # 参与概率 <= 牌型边际概率
    for s in range(4):
        for r in range(13):
            assert A8['straight_flush'][s][r] <= A8['straight'][s][r]
            assert A8['straight_flush'][s][r] <= A8['flush'][s][r]
            assert A8['flush_house'][s][r] <= A8['full_house'][s][r]
            assert A8['flush_five'][s][r] <= A8['four'][s][r]
    print("[check-3] k=12: 对子族/顺子/同花顺各列花色对称, 同花各行点数对称,"
          "同花葫芦与同花五条全零,")
    print("         每格不超过对应牌型边际概率, 且 SF<=顺子, SF<=同花,"
          "同花葫芦<=葫芦, 同花五条<=四条  OK\n")

    # ===== check-4: 同花葫芦/同花五条 边际 DP == 全枚举 =====
    for D, kk in decks:
        ph, pf5 = house_marginal(D, kk), flush_five_marginal(D, kk)
        eh, ef5 = enum_house_five(D, kk)
        assert ph == eh, (float(ph), float(eh))
        assert pf5 == ef5, (float(pf5), float(ef5))
    print("[check-4] 同花葫芦/同花五条 边际 DP == 全枚举(含 5 副本可达同花五条)  OK\n")


def random_deck(max_copy=3, seed=0, m=8):
    """自定义随机牌组: 每格独立均匀取 0..max_copy 副本, 保证总牌数 >= k"""
    k = -(-m * 9 // 5)
    rng = random.Random(seed)
    while True:
        M = [[rng.randint(0, max_copy) for _ in range(13)] for _ in range(4)]
        if sum(map(sum, M)) >= k:
            return M


if __name__ == '__main__':
    # ===== 选择牌组(改这里) =====
    DECK_MODE = 'random'       # 'std' = 标准 52 张(每格 1 张); 'random' = 每格随机 0-3 副本
    RANDOM_SEED = 20260924     # random 模式的种子, 换数字换一副牌
    # ===========================
    m = 8                      # 手牌上限(未开局默认 8), k = ceil(1.8*m)
    k = -(-m * 9 // 5)

    # ----- 小样本/结构校验: 耗时较长, 不需要时注释掉这一行 -----
    # run_checks(m)

    if DECK_MODE == 'random':
        M = random_deck(max_copy=3, seed=RANDOM_SEED, m=m)
        tag = f"随机牌组(每格 0-3 副本, seed={RANDOM_SEED})"
    else:
        M = [[1] * 13] * 4
        tag = "标准 52 牌组(每格 1 张)"
    n = sum(map(sum, M))
    print(f"{tag}, m={m}, k=ceil(1.8*m)={k}, 总牌数 n={n}")
    print("        " + "".join(f"{RANK_LABEL[r]:>4}" for r in range(13)))
    for s in range(4):
        print(f"suit {s} " + "".join(f"{M[s][r]:>4}" for r in range(13)))
    print()

    # ----- 10 种牌型 P(手牌能打出), contains 口径, 精确 -----
    P = marginal_probs(M, k)
    print("P(手牌能打出各牌型):")
    for kd in KINDS:
        print(f"  {kd:<15}{float(P[kd]):.6f}")
    print()

    # ----- 10 个参与矩阵: M_T[s][r] = P(能打出包含 (s,r) 的该牌型) -----
    A = all_matrices(M, k)
    for kd in KINDS:
        show(A[kd], kd, k)
