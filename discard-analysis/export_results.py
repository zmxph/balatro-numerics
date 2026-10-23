"""Create the user-facing table and a reproducible, full-precision data file."""
import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

root=Path(__file__).resolve().parent
baseline=json.loads((root/'baselines.json').read_text())
names={'pair':'一对','two_pair':'两对','three':'三条','straight':'顺子','flush':'同花','full_house':'葫芦','four':'四条','straight_flush':'同花顺'}

def inverse(kind,p,m):
    q=baseline[kind]
    if p<=q[m]:return float(m)
    for n in range(m,len(q)-1):
        if q[n+1]>=p:
            return n+(p-q[n])/(q[n+1]-q[n])
    raise ValueError((kind,p,m))

records=[]
for kind in names:
    exact=kind not in ('straight','straight_flush')
    if exact:paths=[root/f'{kind}-exact.jsonl']
    elif (root/f'{kind}-final.jsonl').exists():paths=[root/f'{kind}-final.jsonl']
    else:paths=sorted(root.glob(f'{kind}-final-m*.jsonl'))
    rows=[json.loads(line) for path in paths for line in path.read_text().splitlines()]
    assert len(rows)==20,(kind,len(rows))
    for row in rows:
        m,j,p=row['m'],row['j'],row['p'];se=row.get('se',0)
        assert baseline[kind][m]-1e-10<=p<=baseline[kind][m+5*j]+1e-10,(kind,m,j,p)
        k=inverse(kind,p,m)
        rec={'kind':kind,'name':names[kind],'m':m,'j':j,'p':p,'k':k,
             'optimal_strategy':exact or j==1,'exact_probability':exact,
             'method':'exact_dynamic_programming' if exact else ('sampled_initial_hands_exact_optimal_one_discard' if j==1 else 'independent_evaluation_of_selected_lookahead_policy'),
             'sampling_se_p':se,'sampling_ci95_p':[max(0,p-1.96*se),min(1,p+1.96*se)],
             'sampling_ci95_k':[inverse(kind,max(0,p-1.96*se),m),inverse(kind,min(1,p+1.96*se),m)],
             'strategy_optimality_gap':'zero' if exact or j==1 else 'unknown; the evaluated feasible policy may underperform the optimum'}
        for field in ('n','seed','reserve','failure'):
            if field in row:rec[field]=row[field]
        records.append(rec)

for kind in names:
    by={(r['m'],r['j']):r['p'] for r in records if r['kind']==kind}
    assert all(by[m,j]>=by[m,j-1] for m in range(6,11) for j in range(2,5))
    assert all(by[m,j]>=by[m-1,j] for m in range(7,11) for j in range(1,5))

metadata={
 'deck':'standard 52-card deck without replacement; discards never return',
 'hand_sizes':[6,7,8,9,10],'discard_rounds':[1,2,3,4],'discard_limit':5,
 'success':'contains a target core; targets overlap; straight flush includes royal flush',
 'k_definition':'piecewise-linear inverse of exact direct-draw success probabilities',
 'sampling_intervals':'individual approximate 95% normal intervals for a bounded conditional-success mean; exclude policy suboptimality and rounding',
 'policy':'At each non-final step, maximize conditional probability of containing the target after a hypothetical future draw of d + round((t-1)*min(5,m-reserve)) cards. The held cards plus future drawn cards are used as a lookahead surrogate, not as actual accumulated inventory. Choose reserve on separate pilot samples. On the final step, maximize exact one-discard success probability over every legal action. Straight flush lookahead sums suit-wise union probabilities; at the final step the possible two-suit intersection for m=10 is subtracted exactly.',
 'validation':'Exact no-discard DP vs independent integer combinatorial baseline; all 8 last-step optimizers vs physical-card enumeration on 15 reduced decks; multi-step rank/suit recursion vs independent physical-card enumeration on 4 reduced decks.'}
(root/'results.json').write_text(json.dumps({'metadata':metadata,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
lookup={(r['kind'],r['m'],r['j']):r for r in records}
lines=['# 最优弃牌与等效抓牌张数','',
'标准 52 张牌，无放回；弃牌不回牌堆；每次可弃 0–5 张并补齐手牌。针对每个目标牌型分别优化，能选出目标核心组合即成功；同花顺包含皇家同花顺。',
'', '**计算性质：** 一对、两对、三条、同花、葫芦、四条的 120 项是精确最优动态规划（双精度数值运算，无抽样误差）。顺子和同花顺每项用 20 万个独立样本评估：j=1 的策略严格最优，j=2–4 为经过策略比较后的可行近似策略，未证明全局最优。后一类真实策略表现不超过最优表现；点估计另有抽样误差。',
'', 'k 在相邻整数抽牌数之间按成功率线性插值，不是累计见过的牌数。以下显示两位小数；四舍五入接近概率饱和点不代表必定成功。', '',
'| m | j | '+' | '.join(v+('†' if k in ('straight','straight_flush') else '') for k,v in names.items())+' |',
'|'+'---|'*10]
for m in range(6,11):
    for j in range(1,5):lines.append(f'| {m} | {j} | '+' | '.join(f"{lookup[k,m,j]['k']:.2f}" for k in names)+' |')
errs=[max(r['k']-r['sampling_ci95_k'][0],r['sampling_ci95_k'][1]-r['k']) for r in records if not r['exact_probability']]
lines+=['',f'† 这些数值含抽样误差。各项 95% 抽样区间的半宽约为 {min(errs):.3f}–{max(errs):.3f} 张，详见下表；该区间不包含未知的策略次优误差。', '', '## 实际成牌概率（%）','', '| m | j | '+' | '.join(names.values())+' |','|'+'---|'*10]
for m in range(6,11):
    for j in range(1,5):lines.append(f'| {m} | {j} | '+' | '.join(f"{100*lookup[k,m,j]['p']:.6f}" for k in names)+' |')
lines+=['','## 顺子与同花顺的抽样区间','','| 牌型 | m | j | k | 95% 抽样区间 | 最优性 |','|---|---|---|---|---|---|']
for r in records:
    if not r['exact_probability']:
        low,high=r['sampling_ci95_k'];lines.append(f"| {r['name']} | {r['m']} | {r['j']} | {r['k']:.4f} | [{low:.4f}, {high:.4f}] | {'单次策略严格最优' if r['j']==1 else '多步策略未证明最优'} |")
lines+=['','## 方法与复现','','1. 基准曲线：复用项目的整数计数组合动态规划，计算直接抓 0–30 张牌时的各牌型包含概率。','2. 精确弃牌：对子、对子族、同花分别按剩余点数副本和花色计数压缩状态，枚举所有合法弃法与补牌计数；动态规划最大化剩余全部弃牌机会的最终成功率。','3. 顺子类：容斥计算每次弃法的直接补牌成功率；比较不同前瞻长度与只优化下一次的策略。初步比较和最终评估使用不同种子；最后一轮补牌被解析积分掉，减少方差。策略详情、每项样本数、种子和前瞻参数保存在 results.json。','4. 精确递推与独立实体牌枚举对照，覆盖两轮弃牌及弃牌不放回。','', '执行顺序：baselines.py → 编译 DiscardAnalysis.csproj → pair 4 / flush 4 / rank 0..3 4 → simulate straight 或 straight_flush 的 pilot、pilot_extra、final → validate → export_results.py。完整入口及参数见源码。','', '本计算未修改游戏 Mod 或其中原有的 1.5m 近似。']
(root/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:30]))
print('Max 95% sampling half-width in k:',max(errs))
print('Saved 160 records to results.json and report.md')
