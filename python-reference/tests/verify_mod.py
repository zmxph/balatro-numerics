"""Run the mod in the game's real LuaJIT DLL; compare to Python exact arithmetic."""
import ast
import ctypes
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import types

HERE = Path(__file__).resolve().parent
PYREF = HERE.parent
ROOT = PYREF.parent
sys.path.insert(0, str(PYREF))
os.chdir(ROOT)
DLL = Path(sys.argv[1]) if len(sys.argv) > 1 else None


from lua_runtime import Lua, lua_value


def reference_module():
    # The supplied hand_type_probs.py runs a long demo on import. Load its
    # unchanged function definitions and the three constants they use only.
    source = ast.parse((PYREF / 'hand_type_probs.py').read_text(encoding='utf-8'))
    keep = []
    for node in source.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            keep.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in {'EVENTS', 'STRAIGHT_SETS', 'SF_MASKS'} for t in node.targets
        ):
            keep.append(node)
    module = types.ModuleType('hand_type_probs')
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'hand_type_probs.py', 'exec'), module.__dict__)
    sys.modules['hand_type_probs'] = module
    sys.path.insert(0, str(PYREF))
    import card_type_probs
    return card_type_probs


lua = Lua(DLL)
lua.run('''
function encode(x)
    if type(x) == 'number' then return string.format('%.17g', x) end
    if type(x) == 'string' then return string.format('%q', x) end
    local parts = {}
    if #x > 0 then
        for i = 1, #x do parts[i] = encode(x[i]) end
        return '[' .. table.concat(parts, ',') .. ']'
    end
    for key, value in pairs(x) do parts[#parts+1] = encode(key) .. ':' .. encode(value) end
    return '{' .. table.concat(parts, ',') .. '}'
end
factory = assert(loadfile('HandProbabilities/probability.lua'))()
engine = factory()
-- Workers deserialize precisely this factory, in a new Lua state.
engine = assert(loadstring(string.dump(factory)))()
return 'engine loaded'
''')
ref = reference_module()
from card_type_expectations import compute_expectations, CAPS
from expectation_oracle import enum_expected


def check(deck, k, label, enumerate_small=False):
    start = time.perf_counter()
    actual = json.loads(lua.run(f'return encode(engine.compute({lua_value(deck)}, {k}))'))
    elapsed = time.perf_counter() - start
    n = sum(map(sum, deck))
    effective = min(n, max(0, math.ceil(k)))
    if effective:
        expected = ref.marginal_probs(deck, effective)
        matrices = ref.all_matrices(deck, effective)
        if enumerate_small:
            assert matrices == ref.enum_card_probs(deck, effective)
        for kind in ref.KINDS:
            assert math.isclose(actual['marginal'][kind], float(expected[kind]), abs_tol=2e-12), (label, kind)
            for s in range(4):
                for r in range(13):
                    assert math.isclose(actual['matrices'][kind][s][r], float(matrices[kind][s][r]), abs_tol=2e-12), (label, kind, s, r)
    else:
        assert all(p == 0 for p in actual['marginal'].values())
    for kind, p in actual['marginal'].items():
        assert 0 <= p <= 1
        assert all(0 <= v <= p + 2e-12 for row in actual['matrices'][kind] for v in row)
    expected_counts = compute_expectations(deck, effective, marginal=expected if effective else None)
    if enumerate_small:
        oracle = enum_expected(deck, effective)
        for field in ('expected_counts', 'unconditional_counts', 'marginal', 'suit_expected_counts', 'rank_expected_counts'):
            assert expected_counts[field] == oracle[field], (label, field)
    sizes = dict(pair=2, two_pair=4, three=3, four=4, five=5, full_house=5,
                 flush=5, straight=5, straight_flush=5, flush_house=5, flush_five=5, high_card=1)
    for kind, size in sizes.items():
        for field, length in [('suit_expected_counts', 4), ('rank_expected_counts', 13)]:
            assert len(actual[field][kind]) == length
            for i in range(length):
                value = actual[field][kind][i]
                assert math.isclose(value, float(expected_counts[field][kind][i]), abs_tol=2e-12), (label, field, kind, i, value, expected_counts[field][kind][i])
                assert -2e-12 <= value <= size + 2e-12
                cells = actual['expected_counts'][kind][i] if length == 4 else [row[i] for row in actual['expected_counts'][kind]]
                assert max(cells) <= value + 2e-12
                assert value <= sum(cells) + 2e-12
            if actual['marginal'][kind] > 0:
                assert sum(actual[field][kind]) >= size - 2e-12
    for kind, cap in CAPS.items():
        for s in range(4):
            for r in range(13):
                for field in ('expected_counts', 'unconditional_counts'):
                    assert math.isclose(actual[field][kind][s][r], float(expected_counts[field][kind][s][r]), abs_tol=2e-12), (label, field, kind, s, r)
                e = actual['expected_counts'][kind][s][r]
                u = actual['unconditional_counts'][kind][s][r]
                assert 0 <= e <= min(cap, deck[s][r]) + 2e-12
                assert math.isclose(u, e * actual['marginal'][kind], abs_tol=2e-12)
                assert actual['matrices'][kind][s][r] <= u + 2e-12
    assert actual['marginal']['high_card'] == (1 if effective else 0)
    print(f'PASS {label}: n={n}, k={effective}; Lua {elapsed:.3f}s', flush=True)
    return actual


std = [[1] * 13 for _ in range(4)]
standard = check(std, 12, 'standard 52 / legacy explicit k=12')
check(std, 5, 'standard 52 / closed-form 5-card draw')
print('Standard k=12:', standard['marginal'], flush=True)
check([[1] * 5 + [0] * 8] * 2 + [[0] * 13] * 2, 6, 'wheel', True)
check([[1] + [0] * 8 + [1] * 4] * 2 + [[0] * 13] * 2, 5, 'royal straight', True)
bad_wrap = [[1, 1, 1, 1] + [0] * 8 + [1]] + [[0] * 13] * 3
assert check(bad_wrap, 5, 'K A 2 3 4 is not straight', True)['marginal']['straight'] == 0
copies = [[5, 3, 2] + [0] * 10, [2, 1] + [0] * 11] + [[0] * 13] * 2
check(copies, 6, 'duplicate cells / flush house / flush five', True)
full = check(copies, 30, 'draw capped at deck size')
assert full['marginal']['five'] == 1 and full['matrices']['five'][0][0] == 1
check([[0] * 13] * 4, 12, 'empty deck')
check(std, 0, 'zero hand limit')
rng = random.Random(937)
for i in range(3):
    deck = [[0] * 13 for _ in range(4)]
    for _ in range(10):
        deck[rng.randrange(4)][rng.randrange(13)] += 1
    check(deck, 6, f'irregular small deck {i}', True)
check([[rng.randrange(4) for _ in range(13)] for _ in range(4)], 14, '0-3 copies / k=14')
# User example: choose H2,H2 even though D2 is also available.
example = [[0]*13 for _ in range(4)]
example[1][1], example[3][1] = 2, 1
ex = check(example, 3, 'two H2 + one D2: independent greedy maxima', True)
assert ex['expected_counts']['pair'][1][1] == 2
assert ex['expected_counts']['pair'][3][1] == 1
ex = check(example, 2, 'same example / only draw two', True)
assert math.isclose(ex['expected_counts']['pair'][1][1], 4/3)
# T is possible without the target. Such successful draws remain in denominator.
example[3][1] = 0
example[0][2] = 2
ex = check(example, 2, 'condition on any pair, not target presence', True)
assert math.isclose(ex['marginal']['pair'], 1/3)
assert ex['expected_counts']['pair'][1][1] == 1
assert math.isclose(ex['unconditional_counts']['pair'][1][1], 1/3)
house = [[0]*13 for _ in range(4)]
house[1][1], house[1][2] = 3, 3
ex = check(house, 6, 'both full-house roles available: prefer target triplet', True)
assert ex['expected_counts']['full_house'][1][1] == 3
assert ex['expected_counts']['flush_house'][1][1] == 3
house[1][2] = 2
house[3][2] = 1
ex = check(house, 6, 'flush-house role differs from ordinary house', True)
assert ex['expected_counts']['full_house'][1][2] == 2
assert ex['expected_counts']['flush_house'][1][2] == 2
print('PASS all 12 conditional count matrices / Fraction DP / independent legal-core enumeration', flush=True)
assert all(v <= 1 for v in standard['suit_expected_counts']['pair'])
# Same rank split among suits: summing independent cell maxima overcounts.
ex = check(example := [[0]*13 for _ in range(4)], 0, 'empty grouped arrays', True)
example[1][1], example[3][1] = 2, 1
ex = check(example, 3, 'rank greedy maximum is two, not sum of cell maxima three', True)
assert ex['rank_expected_counts']['pair'][1] == 2
assert sum(ex['expected_counts']['pair'][s][1] for s in range(4)) == 3
# Three possible all-heart pairs; a two-pair play uses only two of them.
example = [[0]*13 for _ in range(4)]
example[1][:3] = [2, 2, 2]
ex = check(example, 6, 'suit greedy maxima: choose pairs jointly', True)
assert ex['suit_expected_counts']['pair'][1] == 2
assert ex['suit_expected_counts']['two_pair'][1] == 4
assert sum(ex['expected_counts']['two_pair'][1]) == 6
# Three hearts plus two diamonds vs two hearts plus three diamonds.
example = [[0]*13 for _ in range(4)]
example[1][1:3], example[3][1:3] = [2, 3], [1, 1]
ex = check(example, 7, 'house optimizes suit across both roles', True)
assert ex['suit_expected_counts']['full_house'][1] == 5
# Two complete flushes: pick one suit, do not combine target-rank copies.
example = [[0]*13 for _ in range(4)]
example[1][1:4], example[3][1:4] = [2, 2, 1], [3, 1, 1]
ex = check(example, 10, 'rank flush maximum across competing suits', True)
assert ex['rank_expected_counts']['flush'][1] == 3
assert sum(ex['expected_counts']['flush'][s][1] for s in range(4)) == 5
# Royal and wheel can use different counts of the target suit.
example = [[0]*13 for _ in range(4)]
for r in (0, 9, 10, 11, 12): example[1][r] = 1
for r in (1, 2, 3, 4): example[3][r] = 1
ex = check(example, 9, 'straight chooses target-suit-rich royal window', True)
assert ex['suit_expected_counts']['straight'][1] == 5
print('PASS independent suit/rank greedy arrays for all 12 hands', flush=True)
print(lua.run("return assert(loadfile('tests/ui_contract.lua'))()"), flush=True)
lua.close()
