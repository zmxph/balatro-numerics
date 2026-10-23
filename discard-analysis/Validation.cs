using System.Numerics;
using System.Text.Json;

static class Validation {
    static bool[] Events(int[] cards){
        int[] ranks=new int[13],suits=new int[4];foreach(int c in cards){ranks[c%13]++;suits[c/13]++;}
        int pairs=ranks.Count(n=>n>=2),triples=ranks.Count(n=>n>=3),fours=ranks.Count(n=>n>=4);
        return new[]{pairs>0,pairs>=2,triples>0,triples>0&&pairs>=2,fours>0,suits.Max()>=5,new SequencePolicy(false).Hit(cards,cards.Length),new SequencePolicy(true).Hit(cards,cards.Length)};
    }
    static void Close(double a,double b,string label){if(Math.Abs(a-b)>1e-10)throw new Exception($"{label}: {a} != {b}");}
    public static void Run(){
        var baseline=JsonDocument.Parse(File.ReadAllText("discard_analysis/baselines.json")).RootElement;
        for(int m=6;m<=10;m++){
            Close(1-new PairSolver().InitialFailure(m,0),baseline.GetProperty("pair")[m].GetDouble(),"pair baseline");
            Close(new FlushSolver().InitialSuccess(m,0),baseline.GetProperty("flush")[m].GetDouble(),"flush baseline");
            for(int k=0;k<4;k++)Close(new RankSolver(k).Initial(m,0),baseline.GetProperty(new[]{"two_pair","three","full_house","four"}[k])[m].GetDouble(),"rank baseline");
        }
        var rng=new Random(719827);
        for(int trial=0;trial<15;trial++){
            int m=6+trial%5;
            // Suited sequences, low-rank multiplicities, and unrestricted cases.
            int[] pool=trial<5?Enumerable.Range(0,26).ToArray():trial<10?Enumerable.Range(0,52).Where(c=>c%13<6).ToArray():Enumerable.Range(0,52).ToArray();
            rng.Shuffle(pool);int[] hand=pool.Take(m).ToArray(),rest=pool.Skip(m).Take(6).ToArray();ulong rem=0;foreach(int c in rest)rem|=1UL<<c;
            double[] best=Events(hand).Select(b=>b?1.0:0).ToArray();
            for(int kept=0;kept<(1<<m);kept++){
                int d=m-BitOperations.PopCount((uint)kept);if(d<1||d>5)continue;
                double[] hits=new double[8];int n=0;
                for(int drawn=0;drawn<(1<<rest.Length);drawn++){
                    if(BitOperations.PopCount((uint)drawn)!=d)continue;
                    int[] after=new int[m];int pos=0;for(int i=0;i<m;i++)if((kept&(1<<i))!=0)after[pos++]=hand[i];for(int i=0;i<rest.Length;i++)if((drawn&(1<<i))!=0)after[pos++]=rest[i];
                    bool[] e=Events(after);for(int k=0;k<8;k++)if(e[k])hits[k]++;n++;
                }
                for(int k=0;k<8;k++)best[k]=Math.Max(best[k],hits[k]/n);
            }
            int[] rh=new int[13],rr=new int[13],sh=new int[4],sr=new int[4];foreach(int c in hand){rh[c%13]++;sh[c/13]++;}foreach(int c in rest){rr[c%13]++;sr[c/13]++;}
            if(rh.Max()<=1){int[] h=new int[4],u=new int[5];for(int r=0;r<13;r++)if(rh[r]>0)h[rr[r]]++;else u[rr[r]]++;Close(1-new PairSolver().Failure(h,u,1),best[0],"pair conditional");}
            for(int k=0;k<4;k++)Close(new RankSolver(k).Conditional(rh,rr,1),best[k+1],"rank conditional");
            Close(new FlushSolver().Success(sh,sr,1),best[5],"flush conditional");
            foreach(bool sf in new[]{false,true}){
                var policy=new SequencePolicy(sf);double p=policy.Hit(hand,m)?1:policy.Decide(hand,m,rem,1,4).Score;
                Close(p,best[sf?7:6],$"sequence conditional {trial} {sf}");
            }
        }
        for(int trial=0;trial<4;trial++){
            int[] pool=trial<2?Enumerable.Range(0,52).Where(c=>c%13<5).ToArray():Enumerable.Range(0,26).ToArray();rng.Shuffle(pool);int[] cards=pool.Take(10).ToArray();
            var memo=new Dictionary<(int,int,int),double[]>();
            double[] Brute(int h,int r,int t){
                if(memo.TryGetValue((h,r,t),out var old))return old;
                var actual=Enumerable.Range(0,10).Where(i=>(h&(1<<i))!=0).Select(i=>cards[i]).ToArray();double[] best=Events(actual).Select(b=>b?1.0:0).ToArray();
                if(t==0||r==0)return best;
                for(int disc=h;disc>0;disc=(disc-1)&h){int d=BitOperations.PopCount((uint)disc);if(d>5||d>BitOperations.PopCount((uint)r))continue;double[] sum=new double[8];int n=0;
                    for(int draw=r;draw>0;draw=(draw-1)&r)if(BitOperations.PopCount((uint)draw)==d){var v=Brute((h^disc)|draw,r^draw,t-1);for(int k=0;k<8;k++)sum[k]+=v[k];n++;}
                    for(int k=0;k<8;k++)best[k]=Math.Max(best[k],sum[k]/n);
                }
                memo[(h,r,t)]=best;return best;
            }
            var expect=Brute(63,960,2);int[] rh=new int[13],rr=new int[13],sh=new int[4],sr=new int[4];for(int i=0;i<6;i++){rh[cards[i]%13]++;sh[cards[i]/13]++;}for(int i=6;i<10;i++){rr[cards[i]%13]++;sr[cards[i]/13]++;}
            for(int k=0;k<4;k++)Close(new RankSolver(k).Conditional(rh,rr,2),expect[k+1],"two-round rank recursion");
            Close(new FlushSolver().Success(sh,sr,2),expect[5],"two-round flush recursion");
            if(rh.Max()<=1){int[] h=new int[4],u=new int[5];for(int r=0;r<13;r++)if(rh[r]>0)h[rr[r]]++;else u[rr[r]]++;Close(1-new PairSolver().Failure(h,u,2),expect[0],"two-round pair recursion");}
        }
        Console.WriteLine("PASS: 30 exact baseline checks; all eight one-discard optimizers match physical-card enumeration on 15 reduced decks; two-round recursions match independent enumeration on four reduced decks.");
    }
}
