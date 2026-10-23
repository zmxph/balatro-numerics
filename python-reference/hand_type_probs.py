# 牌型概率直接计算(无蒙特卡洛): 对子 / 两对 / 三条 / 四条 / 葫芦 / 同花 / 顺子 / 同花顺
# 输入: 4x13 计数矩阵 M[suit][rank] in {0,1,2} (每格 0-2 张, 允许同名牌副本或缺牌)
#       点数维度: m_r = sum_s M[s][r] (对子族与顺子都用点数总量)
#       花色维度: a_s = sum_r M[s][r] (同花只用花色总量; 单花色 >=5 即同花)
#       注: 同花与对子族/顺子是点数-花色两个维度的单事件, 各自边际 DP 即可;
#           同花顺是联合事件, 由 straight_flush_probs 做 花色x点数 联合 DP
# 顺子: 覆盖事件(而非计数事件), 只看点数总量 mᵣ. 扫描序 A,2,...,K 逐点 DP,
#       状态 (t, run, st, ace): run=以当前点数结尾的连续"在场"长度(封顶5),
#       st=已出现 5 连(覆盖 A2345,2-6,...,9-K 共 9 种), ace=A 在场.
#       第 10 种 TJQKA 跨首尾, 收尾特判 st=0 且 run_K>=4 且 ace=1
# 同花顺: 也是覆盖事件, 但 5 连必须落在同一花色内, 故扫描序为 suit-major:
#       每花色内部按 A,2,...,K 走一遍顺子 run DP; 一个花色扫完只剩 1 bit 有用
#       (该花色 K 端 run>=4 且 A 在场 -> 该花色的 TJQKA), 其余状态可弃;
#       任一花色 run 到 5 则整手立即判活, 其余花色细节全部塌缩,
#       状态数控制在 O(k * 2^花色数 * run上限)
# 模型: 从牌组无放回抽 k 张 (k = ceil(1.8*m), 抽牌+弃牌的简化模拟)
# 记号: c2/c3/c4 = k 张中张数 >=2/>=3/>=4 的点数个数
# 两套口径(均由同一 DP 的状态 (t, c2, c3, c4) 直接读出):
#   含(能构成): 对子 c2>=1 | 两对 c2>=2 | 三条 c3>=1 | 四条 c4>=1 | 葫芦 c3>=1 且 c2>=2
#   恰好(互斥): 按 四条 > 葫芦 > 三条 > 两对 > 对子 的优先级分解, 各抽法唯一归类, 五类加高牌和为 1
# 同花: 含 = 至少一个花色 >=5 (逐花色 DP, 状态 (t, max_suit_capped5));
#       另附单花色 marginal P(花色 s >=5) (超几何分布), 供 abcd 占比视角
# 算法: 逐点数/逐花色无放回 DP, 状态 -> 权重 = 方案数, 全程精确整数/Fraction
#       概率 = 事件权重和 / C(n, k)
from fractions import Fraction
from math import comb
from itertools import combinations
import random

EVENTS = ('pair', 'two_pair', 'three', 'four', 'full_house')


def rank_totals(matrix):
    return [sum(matrix[s][r] for s in range(4)) for r in range(13)]


def probs(ms, kmax):
    """ms: 13 个点数总量. 返回 {k: {'contains': {...}, 'exact': {...}}}"""
    n = sum(ms)
    dp = {(0, 0, 0, 0): 1}
    for m in ms:
        ndp = {}
        for (t, c2, c3, c4), w in dp.items():
            # take 取真实张数(不做合并), t 始终是真实已抽牌数
            for take in range(0, min(m, kmax - t) + 1):
                k2 = (t + take, c2 + (take >= 2), c3 + (take >= 3), c4 + (take >= 4))
                ndp[k2] = ndp.get(k2, 0) + w * comb(m, take)
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        cont = {e: 0 for e in EVENTS}
        exa = {e: 0 for e in EVENTS}
        exa['high_card'] = 0
        for (t, c2, c3, c4), w in dp.items():
            if t != k:
                continue
            if c2 >= 1:
                cont['pair'] += w
            if c2 >= 2:
                cont['two_pair'] += w
            if c3 >= 1:
                cont['three'] += w
            if c4 >= 1:
                cont['four'] += w
            if c3 >= 1 and c2 >= 2:
                cont['full_house'] += w
            if c4 >= 1:
                exa['four'] += w
            elif c3 >= 1 and c2 >= 2:
                exa['full_house'] += w
            elif c3 >= 1:
                exa['three'] += w
            elif c2 >= 2:
                exa['two_pair'] += w
            elif c2 >= 1:
                exa['pair'] += w
            else:
                exa['high_card'] += w
        out[k] = {
            'contains': {e: Fraction(v, den) for e, v in cont.items()},
            'exact': {e: Fraction(v, den) for e, v in exa.items()},
        }
    return out


def enum_probs(ms, kmax):
    """全枚举校验(确定性, 非模拟): 对每张具体牌枚举 C(n,k) 个子集"""
    labels = []
    for r, m in enumerate(ms):
        labels += [r] * m
    n = len(labels)
    out = {}
    for k in range(1, min(kmax, n) + 1):
        den = comb(n, k)
        cont = {e: 0 for e in EVENTS}
        exa = {e: 0 for e in EVENTS}
        exa['high_card'] = 0
        for sub in combinations(labels, k):
            cnt = {}
            for x in sub:
                cnt[x] = cnt.get(x, 0) + 1
            c2 = sum(1 for v in cnt.values() if v >= 2)
            c3 = sum(1 for v in cnt.values() if v >= 3)
            c4 = sum(1 for v in cnt.values() if v >= 4)
            if c2 >= 1:
                cont['pair'] += 1
            if c2 >= 2:
                cont['two_pair'] += 1
            if c3 >= 1:
                cont['three'] += 1
            if c4 >= 1:
                cont['four'] += 1
            if c3 >= 1 and c2 >= 2:
                cont['full_house'] += 1
            if c4 >= 1:
                exa['four'] += 1
            elif c3 >= 1 and c2 >= 2:
                exa['full_house'] += 1
            elif c3 >= 1:
                exa['three'] += 1
            elif c2 >= 2:
                exa['two_pair'] += 1
            elif c2 >= 1:
                exa['pair'] += 1
            else:
                exa['high_card'] += 1
        out[k] = {
            'contains': {e: Fraction(v, den) for e, v in cont.items()},
            'exact': {e: Fraction(v, den) for e, v in exa.items()},
        }
    return out


def fmt(x):
    return f"{float(x):.6f}"


def suit_totals(matrix):
    return [sum(matrix[s]) for s in range(4)]


def flush_probs(suit_ms, kmax):
    """suit_ms: 4 个花色的牌数. 返回 {k: P(至少一个花色 >=5 张)}"""
    n = sum(suit_ms)
    dp = {(0, 0): 1}  # (t, 已遍历花色的最大张数, 封顶 5)
    for a in suit_ms:
        ndp = {}
        for (t, mx), w in dp.items():
            for take in range(0, min(a, kmax - t) + 1):
                nmx = max(mx, min(take, 5))
                key = (t + take, nmx)
                ndp[key] = ndp.get(key, 0) + w * comb(a, take)
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        num = sum(w for (t, mx), w in dp.items() if t == k and mx >= 5)
        out[k] = Fraction(num, den)
    return out


def per_suit_probs(suit_ms, kmax):
    """单花色 marginal: P(花色 s 有 >=5 张), s 按输入顺序. 超几何分布闭式"""
    n = sum(suit_ms)
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        row = []
        for a in suit_ms:
            num = sum(comb(a, j) * comb(n - a, k - j) for j in range(5, min(a, k) + 1))
            row.append(Fraction(num, den))
        out[k] = row
    return out


def enum_flush(suit_ms, kmax):
    """全枚举校验(确定性, 非模拟): 每张具体牌按花色计数"""
    labels = []
    for s, a in enumerate(suit_ms):
        labels += [s] * a
    n = len(labels)
    out = {}
    for k in range(1, min(kmax, n) + 1):
        den = comb(n, k)
        cnt = 0
        for sub in combinations(labels, k):
            c = {}
            for x in sub:
                c[x] = c.get(x, 0) + 1
            if c and max(c.values()) >= 5:
                cnt += 1
        out[k] = Fraction(cnt, den)
    return out


# 10 种顺子的点数下标集合(下标 0=A, 1=2, ..., 12=K)
STRAIGHT_SETS = ((0, 1, 2, 3, 4), (1, 2, 3, 4, 5), (2, 3, 4, 5, 6), (3, 4, 5, 6, 7),
                 (4, 5, 6, 7, 8), (5, 6, 7, 8, 9), (6, 7, 8, 9, 10), (7, 8, 9, 10, 11),
                 (8, 9, 10, 11, 12), (9, 10, 11, 12, 0))

# 同花色判顺用的位掩码(枚举校验用)
SF_MASKS = tuple(sum(1 << r for r in st) for st in STRAIGHT_SETS)


def straight_probs(ms, kmax):
    """ms: 13 个点数总量, 顺序 [A,2,...,K]. 返回 {k: P(能构成顺子)}.
    事件 = k 张中存在 5 个连续点数各 >=1 张(含同花顺情形, 即"能打出顺子").
    DP 状态 (t, run, st, ace):
      t   已抽牌数
      run 以扫描序当前点数结尾的连续在场长度, 封顶 5
      st  是否已出现 5 连(A2345 / 2-6 / ... / 9-K 共 9 种)
      ace A 是否在场(TJQKA 回环特判用)
    收尾: P = P(st=1) + P(st=0 且 run>=4 且 ace=1), 两项互斥
    """
    n = sum(ms)
    dp = {(0, 0, 0, 0): 1}
    for idx, m in enumerate(ms):
        is_ace = (idx == 0)
        ndp = {}
        for (t, run, st, ace), w in dp.items():
            for take in range(0, min(m, kmax - t) + 1):
                present = take >= 1
                nrun = min(run + 1, 5) if present else 0
                nst = 1 if (st or nrun == 5) else 0
                nace = 1 if (ace or (is_ace and present)) else 0
                key = (t + take, nrun, nst, nace)
                ndp[key] = ndp.get(key, 0) + w * comb(m, take)
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        num = sum(w for (t, run, st, ace), w in dp.items()
                  if t == k and (st == 1 or (run >= 4 and ace == 1)))
        out[k] = Fraction(num, den)
    return out


def enum_straight(ms, kmax):
    """全枚举校验(确定性, 非模拟): 用 10 个顺子 pattern 直接判定(与 run DP 独立实现)"""
    labels = []
    for r, m in enumerate(ms):
        labels += [r] * m
    n = len(labels)
    out = {}
    for k in range(1, min(kmax, n) + 1):
        den = comb(n, k)
        cnt = 0
        for sub in combinations(labels, k):
            ranks = set(sub)
            if any(all(r in ranks for r in s) for s in STRAIGHT_SETS):
                cnt += 1
        out[k] = Fraction(cnt, den)
    return out


# ---------- 同花顺: 花色x点数联合 DP ----------
def _adv(c, take, is_ace):
    """单花色 comp 转移: c=-1 表示该花色已出现线性 5 连(判活), 否则 c = run*2+ace, run 0..4.
    take = 该花色在此点数抽到的张数. run 到 5 立即置 -1."""
    if c == -1:
        return -1
    if take == 0:
        return c % 2          # run 归零, ace 保留(A 在场是事实, 与当前连续段无关)
    run, ace = divmod(c, 2)
    if run == 4:
        return -1             # run 到 5 -> 该花色成线性顺(9 种之一)
    return (run + 1) * 2 + (ace or is_ace)


def _sf_ok(c):
    """comp 是否表示"该花色已含顺子": 线性 5 连, 或 K 端 run>=4 且 A 在场(即该花色 TJQKA)"""
    return c == -1 or (c // 2 >= 4 and c % 2 == 1)


def straight_flush_probs(matrix, kmax):
    """matrix: 4x13 计数矩阵. 返回 {k: P(同花顺)} = P(某花色含 5 连点数).
    suit-major 扫描: 花色 s 内部按 A,2,...,K 逐点转移(与 straight_probs 同构),
    花色结束时压缩成 1 bit; 任一花色 run 到 5 整手判活, 其余花色状态塌缩.
    收尾: done=1 或任一位 bit=1, 两项互斥."""
    n = sum(sum(row) for row in matrix)
    dp = {(0, 0, (), 0, 0): 1}  # (t, done, q_bits, run, ace); done=1 时后三项无意义
    for s in range(4):
        for idx in range(13):
            m = matrix[s][idx]
            is_ace = (idx == 0)
            ndp = {}
            for (t, done, qs, run, ace), w in dp.items():
                for take in range(0, min(m, kmax - t) + 1):
                    if done:
                        key = (t + take, 1, (), 0, 0)
                    elif take == 0:
                        key = (t, 0, qs, 0, ace)
                    else:
                        nrun = run + 1
                        nace = 1 if (ace or is_ace) else 0
                        key = ((t + take, 1, (), 0, 0) if nrun == 5
                               else (t + take, 0, qs, nrun, nace))
                    ndp[key] = ndp.get(key, 0) + w * comb(m, take)
            dp = ndp
        # 花色 s 收尾: 折叠为 1 bit(K 端 run>=4 且 ace), 活性状态复位
        ndp = {}
        for (t, done, qs, run, ace), w in dp.items():
            if done:
                key = (t, 1, (), 0, 0)
            else:
                key = (t, 0, qs + (1 if (run >= 4 and ace) else 0,), 0, 0)
            ndp[key] = ndp.get(key, 0) + w
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        num = sum(w for (t, done, qs, run, ace), w in dp.items()
                  if t == k and (done or any(qs)))
        out[k] = Fraction(num, den)
    return out


def enum_straight_flush(matrix, kmax):
    """全枚举校验(确定性, 非模拟): 每张牌标签 (suit, rank), 按花色位掩码判 5 连"""
    labels = []
    for s in range(4):
        for r in range(13):
            labels += [(s, r)] * matrix[s][r]
    n = len(labels)
    out = {}
    for k in range(1, min(kmax, n) + 1):
        den = comb(n, k)
        cnt = 0
        for sub in combinations(labels, k):
            acc = [0, 0, 0, 0]
            for s, r in sub:
                acc[s] |= 1 << r
            if any(m & sf == sf for m in acc for sf in SF_MASKS):
                cnt += 1
        out[k] = Fraction(cnt, den)
    return out


def _sf_suit_prob(matrix, s, kmax):
    """P(E_s): 花色 s 单独成顺. 其余花色按点数合并成一组(自身不可能成顺), 只影响 t"""
    others = [sum(matrix[o][r] for o in range(4) if o != s) for r in range(13)]
    n = sum(matrix[s]) + sum(others)
    dp = {(0, 0): 1}  # (t, comp)
    for idx in range(13):
        is_ace = (idx == 0)
        m = matrix[s][idx]
        ndp = {}
        for (t, c), w in dp.items():
            for take in range(0, min(m, kmax - t) + 1):
                key = (t + take, _adv(c, take, is_ace))
                ndp[key] = ndp.get(key, 0) + w * comb(m, take)
        dp = ndp
        o = others[idx]
        ndp = {}
        for (t, c), w in dp.items():
            for take in range(0, min(o, kmax - t) + 1):
                key = (t + take, c)
                ndp[key] = ndp.get(key, 0) + w * comb(o, take)
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        num = sum(w for (t, c), w in dp.items() if t == k and _sf_ok(c))
        out[k] = Fraction(num, den)
    return out


def _sf_pair_intersect(matrix, s1, s2, kmax):
    """P(E_s1 且 E_s2): 两个花色同时成顺(容斥的交集项). 其余花色按点数合并"""
    others = [sum(matrix[o][r] for o in range(4) if o not in (s1, s2)) for r in range(13)]
    n = sum(matrix[s1]) + sum(matrix[s2]) + sum(others)
    dp = {(0, 0, 0): 1}  # (t, comp1, comp2)
    for idx in range(13):
        is_ace = (idx == 0)
        for tgt in (0, 1):
            m = matrix[s1][idx] if tgt == 0 else matrix[s2][idx]
            ndp = {}
            for (t, c1, c2), w in dp.items():
                c = c1 if tgt == 0 else c2
                for take in range(0, min(m, kmax - t) + 1):
                    nc = _adv(c, take, is_ace)
                    key = (t + take, nc, c2) if tgt == 0 else (t + take, c1, nc)
                    ndp[key] = ndp.get(key, 0) + w * comb(m, take)
            dp = ndp
        o = others[idx]
        ndp = {}
        for (t, c1, c2), w in dp.items():
            for take in range(0, min(o, kmax - t) + 1):
                ndp[(t + take, c1, c2)] = ndp.get((t + take, c1, c2), 0) + w * comb(o, take)
        dp = ndp
    out = {}
    for k in range(1, kmax + 1):
        den = comb(n, k)
        if den == 0:
            continue
        num = sum(w for (t, c1, c2), w in dp.items()
                  if t == k and _sf_ok(c1) and _sf_ok(c2))
        out[k] = Fraction(num, den)
    return out


def show(title, P, ks):
    print(title)
    for mode, mname in (('contains', '含(能构成)'), ('exact', '恰好(互斥)')):
        print(f"[{mname}]")
        hdr = (f"{'k':>3} {'对子':>12} {'两对':>12} {'三条':>12} {'四条':>12} {'葫芦':>12}"
               + ("  高牌" if mode == 'exact' else ""))
        print(hdr)
        for k in ks:
            p = P[k][mode]
            row = f"{k:>3} " + " ".join(f"{fmt(p[e]):>12}" for e in EVENTS)
            if mode == 'exact':
                row += f"  {fmt(p['high_card']):>12}"
            print(row)
        print()


def show_flush(title, fp, ps, suit_ms, ks):
    print(title)
    hdr = f"{'k':>3} {'同花':>12} " + " ".join(f"{'s%d(a=%d)' % (i, a):>12}"
                                                for i, a in enumerate(suit_ms))
    print(hdr)
    for k in ks:
        if k not in fp:
            continue
        row = f"{k:>3} {fmt(fp[k]):>12} " + " ".join(f"{fmt(ps[k][i]):>12}"
                                                    for i in range(len(suit_ms)))
        print(row)
    print()


def show_straight(title, sp, sfp, ks):
    print(title)
    print(f"{'k':>3} {'顺子':>12} {'同花顺':>12}")
    for k in ks:
        if k not in sp:
            continue
        print(f"{k:>3} {fmt(sp[k]):>12} {fmt(sfp[k]):>12}")
    print()


def pattern_prob(ms, s, k):
    """P(下标集合 s 的 5 个点数全部在场): 5 个秩各取 j>=1 张, 精确组合求和"""
    from itertools import product
    n = sum(ms)
    den = comb(n, k)
    if den == 0:
        return Fraction(0)
    total = 0
    for js in product(*[range(1, ms[r] + 1) for r in s]):
        sj = sum(js)
        if sj > k:
            continue
        term = comb(n - 5, k - sj)
        for r, j in zip(s, js):
            term *= comb(ms[r], j)
        total += term
    return Fraction(total, den)


def run_demo():
    # ---------- 1) 标准 52 牌组, k=5: 对照扑克经典值 ----------
    # 恰好: 对子 0.422569, 两对 0.047539, 三条 0.021128, 四条 0.000240, 葫芦 0.001441
    # 含:   对子 0.492917, 两对 0.048980, 三条 0.022809, 四条 0.000240, 葫芦 0.001441
    p5 = probs([4] * 13, 5)[5]
    check = {'exact': {'pair': 0.422569, 'two_pair': 0.047539, 'three': 0.021128,
                       'four': 0.000240, 'full_house': 0.001441},
             'contains': {'pair': 0.492917, 'two_pair': 0.048980, 'three': 0.022809,
                          'four': 0.000240, 'full_house': 0.001441}}
    print("[check-1] standard deck, k=5 vs known 5-card poker:")
    for mode, exp in check.items():
        for e, v in exp.items():
            got = float(p5[mode][e])
            ok = abs(got - v) < 1e-6
            print(f"  {mode:<8} {e:<10} got={got:.6f}  expect={v:.6f}  {'OK' if ok else 'FAIL'}")
            assert ok
    print()

    # ---------- 2) 小牌组全枚举交叉校验(含 0-2 副本结构) ----------
    small = [3, 3, 2, 2]
    edp, een = probs(small, 7), enum_probs(small, 7)
    print("[check-2] exhaustive enumeration cross-check (rank totals 3,3,2,2), k=1..7:")
    for k in range(1, 8):
        for mode in ('contains', 'exact'):
            for e in list(EVENTS) + (['high_card'] if mode == 'exact' else []):
                assert edp[k][mode][e] == een[k][mode][e], (k, mode, e)
    # 恰好口径五类加高牌必须为 1
    for k in range(1, 8):
        assert sum(edp[k]['exact'].values()) == 1
    print("  DP == enumeration; exact classes sum to 1  OK\n")

    # ---------- 3) 同花: 已知值 + 全枚举 + 边界 ----------
    # 标准牌组 k=5: 同花 = 4*C(13,5)/C(52,5) = 0.001980792; 单花色 = C(13,5)/C(52,5) = 0.000495198
    sfp5 = flush_probs([13] * 4, 5)[5]
    sps5 = per_suit_probs([13] * 4, 5)[5]
    print("[check-3] flush:")
    print(f"  k=5 P(flush)={float(sfp5):.9f}  expect=0.001980792  "
          f"{'OK' if abs(float(sfp5) - 0.0019807923) < 1e-9 else 'FAIL'}")
    assert abs(float(sfp5) - 0.0019807923) < 1e-9
    for i, p in enumerate(sps5):
        assert abs(float(p) - 0.0004951981) < 1e-9, i
    print(f"  k=5 per-suit = {[float(p) for p in sps5]}  expect all 0.000495198  OK")
    # 全枚举: 花色 6,5,4,3 (n=18), k=1..7
    esuits = [6, 5, 4, 3]
    edp_f, een_f = flush_probs(esuits, 7), enum_flush(esuits, 7)
    for k in range(1, 8):
        assert edp_f[k] == een_f[k], (k, edp_f[k], een_f[k])
    print("  DP == enumeration (suits 6,5,4,3), k=1..7  OK")
    # 边界: max per-suit <= flush <= sum per-suit; 且 P(flush) 随 k 单调不减
    for sm, tag in (([13] * 4, 'std'), ([9, 13, 18, 14], 'rand')):
        fp, ps = flush_probs(sm, 14), per_suit_probs(sm, 14)
        prev = Fraction(0)
        for k in range(2, 15):
            f = fp[k]
            assert f >= max(ps[k]) and f <= sum(ps[k]), (tag, k)
            assert f >= prev, (tag, k)  # 单调不减
            prev = f
    print("  bounds (max-suit <= P(flush) <= sum-suit) and monotonicity hold  OK\n")

    # ---------- 4) 顺子: 已知值 + 全枚举 + 边界 ----------
    # 标准牌组 k=5: 顺子(含同花顺) = 10*4^5/C(52,5) = 10240/2598960 = 0.0039400380
    # (扑克经典表 0.0039246468 是不含同花顺的 10200 种; 本事件"能构成"含同花顺)
    sp5 = straight_probs([4] * 13, 5)[5]
    print("[check-4] straight:")
    print(f"  k=5 P(straight)={float(sp5):.9f}  expect=0.003940038  "
          f"{'OK' if abs(float(sp5) - 0.0039400380) < 1e-9 else 'FAIL'}")
    assert abs(float(sp5) - 0.0039400380) < 1e-9
    # 边界小例: [A,2,3,4,5] 各 1 张(n=5), k=5 唯一子集即 A2345 -> P=1; k=4 -> 0
    assert straight_probs([1] * 5 + [0] * 8, 5)[5] == 1
    assert straight_probs([1] * 4 + [0] * 9, 4)[4] == 0
    # [A..6] 各 1 张(n=6), k=5: 6 个子集中仅 {A,2,3,4,5} 和 {2,3,4,5,6} 成顺 -> 2/6
    assert straight_probs([1] * 6 + [0] * 7, 5)[5] == Fraction(2, 6)
    # 全枚举交叉校验(pattern 判定 vs run DP, 独立实现):
    #   6 连续点数各 1 张(n=12); 每点 2 张的 13 点满牌组(n=26, 覆盖 k=5..7)
    for ms_, ks_ in (([1, 1, 1, 1, 1, 1] + [0] * 7, range(1, 7)),
                     ([3, 2, 2, 2, 2, 2, 2] + [0] * 6, range(1, 8)),
                     ([2] * 13, range(5, 8))):
        edp_s, een_s = straight_probs(ms_, 7), enum_straight(ms_, 7)
        for k in ks_:
            assert edp_s[k] == een_s[k], (ms_, k, edp_s[k], een_s[k])
    # 单调不减 + Boole 并集上界(顺子 <= sum_s P(pattern s 全部在场), pattern 概率精确计算)


    for ms_ in ([4] * 13, [4, 4, 4, 2, 5, 7, 5, 2, 5, 3, 3, 5, 5]):
        sp = straight_probs(ms_, 14)
        prev = Fraction(0)
        for k in range(5, 15):
            ub = sum(pattern_prob(ms_, s, k) for s in STRAIGHT_SETS)
            assert sp[k] <= ub, (k, float(sp[k]), float(ub))
            assert sp[k] >= prev, k
            prev = sp[k]
    print("  k=5 known value OK; 3 decks DP == enumeration; monotone; union bound hold  OK\n")

    # ---------- 5) 随机 4x13 矩阵(每格 0-2), k = 2..14 ----------
    rng = random.Random(20260923)
    M = [[rng.randint(0, 2) for _ in range(13)] for _ in range(4)]
    ms, as_ = rank_totals(M), suit_totals(M)
    print("[random deck] 4x13 matrix, each cell in {0,1,2}")
    for s in range(4):
        print("  suit", s, M[s])
    print("rank totals m_r:", ms, " n =", sum(ms))
    print("suit totals a_s:", as_)
    print("此历史演示按显式 k=11,12,14 测试；当前游戏采用 k=ceil(1.8*m)\n")

    # ---------- 6) 同花顺: 已知值 + 全枚举 + 容斥独立校验 + 边界 ----------
    # 标准牌组 k 张手牌含同花顺的精确计数(每花色内部点数组合推导):
    #   k=5: 4 * 10 = 40                        (10 个顺子 pattern, 每花色每 pattern 恰 1 种)
    #   k=6: 4 * (10*C(39,1) + 71) = 1844       (71 = 6 个点数内可成顺的子集数)
    #   k=7: 4 * (10*C(39,2) + 71*39 + 217) = 41584  (7 张扑克经典同花顺频率)
    sfp_std = straight_flush_probs([[1] * 13] * 4, 14)
    print("[check-5] straight flush:")
    for k, num in ((5, 40), (6, 1844), (7, 41584)):
        expect = Fraction(num, comb(52, k))
        got = sfp_std[k]
        ok = (got == expect)
        print(f"  k={k} P(SF)={float(got):.9f}  expect={float(expect):.9f}  {'OK' if ok else 'FAIL'}")
        assert ok
    # 全枚举交叉校验(与联合 DP 独立实现, 确定性非模拟)
    sf_decks = (
        ([[1] * 5 + [0] * 8, [1] * 5 + [0] * 8, [0] * 13, [0] * 13], 6),   # A2345 双花色
        ([[1] + [0] * 8 + [1] * 4, [1] + [0] * 8 + [1] * 4, [0] * 13, [0] * 13], 5),  # TJQKA 回环
        ([[2, 1, 1, 1, 0, 1, 1, 2, 0, 0, 0, 0, 0], [1, 2, 0, 1, 1, 0, 2, 1, 1, 0, 0, 0, 0],
          [0] * 13, [0] * 13], 7),                                          # 含 0-2 副本
        ([M[0], M[1], [0] * 13, [0] * 13], 7),                              # 随机牌组前两花色
    )
    for M_, kx in sf_decks:
        edp, een = straight_flush_probs(M_, kx), enum_straight_flush(M_, kx)
        for k in range(1, kx + 1):
            assert edp[k] == een[k], (k, float(edp[k]), float(een[k]))
    print("  DP == enumeration on 4 small decks (含 TJQKA 回环与 0-2 副本)  OK")
    # 容斥独立校验: k<=14 时三花色同时成顺需 >=15 张, 不可能, 故精确有
    #   P(SF) = sum_s P(E_s) - sum_{s<t} P(E_s 且 E_t)   (与联合 DP 完全不同的实现路径)
    for M_, tag in (([[1] * 13] * 4, 'std'), (M, 'rand')):
        jdp = straight_flush_probs(M_, 14)
        for k in range(5, 15):
            ie = (sum(_sf_suit_prob(M_, s, 14)[k] for s in range(4))
                  - sum(_sf_pair_intersect(M_, a, b, 14)[k]
                        for a in range(3) for b in range(a + 1, 4)))
            assert jdp[k] == ie, (tag, k, float(jdp[k]), float(ie))
    print("  k=5..14 联合 DP == 容斥(单花色-双花色交集), std/rand 两牌组  OK")
    # 边界 + 单调: max_s P(E_s) <= P(SF) <= min(P(顺子), P(同花), sum_s P(E_s))
    for M_, tag in (([[1] * 13] * 4, 'std'), (M, 'rand')):
        jdp = straight_flush_probs(M_, 14)
        sp, fp = straight_probs(rank_totals(M_), 14), flush_probs(suit_totals(M_), 14)
        prev = Fraction(0)
        for k in range(5, 15):
            es = [_sf_suit_prob(M_, s, 14)[k] for s in range(4)]
            assert max(es) <= jdp[k] <= min(sp[k], fp[k], sum(es)), (tag, k)
            assert jdp[k] >= prev, (tag, k)
            prev = jdp[k]
    print("  边界(夹在 P(顺子), P(同花), 单花色并集界之间)与单调性  OK\n")

    # ---------- 7) 两个牌组的完整概率表 ----------
    show("[random deck] pair family, rank totals m_r:", probs(ms, 14), range(2, 15))
    show_flush("[random deck] flush:", flush_probs(as_, 14), per_suit_probs(as_, 14), as_, range(2, 15))
    show_straight("[random deck] straight:", straight_probs(ms, 14),
                  straight_flush_probs(M, 14), range(2, 15))
    show("[standard deck] 52 cards, rank totals all 4, k = 2..14:",
         probs([4] * 13, 14), range(2, 15))
    show_flush("[standard deck] flush:", flush_probs([13] * 4, 14), per_suit_probs([13] * 4, 14),
               [13] * 4, range(2, 15))
    show_straight("[standard deck] straight:", straight_probs([4] * 13, 14),
                  straight_flush_probs([[1] * 13] * 4, 14), range(2, 15))


if __name__ == '__main__':
    run_demo()
