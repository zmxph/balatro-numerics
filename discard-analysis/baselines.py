"""Exact direct-draw reference curves; uses the existing integer-count DPs."""
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from hand_type_probs import probs,flush_probs,straight_probs,straight_flush_probs

root=Path(__file__).resolve().parent
rank=probs([4]*13,30)
out={kind:[0.0]+[float(rank[k]['contains'][kind]) for k in range(1,31)] for kind in ('pair','two_pair','three','four','full_house')}
for name,result in [('flush',flush_probs([13]*4,30)),('straight',straight_probs([4]*13,30)),('straight_flush',straight_flush_probs([[1]*13]*4,30))]:
    out[name]=[0.0]+[float(result[k]) for k in range(1,31)]
(root/'baselines.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Wrote exact baseline probabilities for k=0..30')
