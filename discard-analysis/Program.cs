using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

static class Combinatorics {
    public static readonly double[,] C = Build();
    static double[,] Build() { var a=new double[53,53]; for(int n=0;n<=52;n++){a[n,0]=1;for(int k=1;k<=n;k++)a[n,k]=k==n?1:a[n-1,k-1]+a[n-1,k];}return a; }
    public static double Choose(int n,int k) => n<0 || k<0 || k>n ? 0 : C[n,k];
    public static List<int[]> Comps(int n,int groups){var list=new List<int[]>();var a=new int[groups]; void Walk(int i,int left){if(i==groups-1){a[i]=left;list.Add((int[])a.Clone());return;}for(int v=0;v<=left;v++){a[i]=v;Walk(i+1,left-v);}}Walk(0,n);return list;}
    public static readonly List<int[]>[] Four = Enumerable.Range(0,6).Select(n=>Comps(n,4)).ToArray();
}

// On all failure paths, held ranks are distinct. H[r] counts held ranks
// with r undrawn copies; U[r] counts unheld ranks with r undrawn copies.
sealed class PairSolver {
    readonly Dictionary<ulong,double> cache=new();
    public int Count=>cache.Count;
    ulong Key(int[] h,int[] u,int t){ulong k=(uint)t;for(int i=0;i<4;i++)k=(k<<4)|(uint)h[i];for(int i=0;i<5;i++)k=(k<<4)|(uint)u[i];return k;}
    public double Failure(int[] h,int[] u,int t){
        if(t==0)return 1;
        ulong key=Key(h,u,t);if(cache.TryGetValue(key,out double cached))return cached;
        int remaining=0;for(int r=0;r<4;r++)remaining+=r*h[r];for(int r=0;r<5;r++)remaining+=r*u[r];
        if(remaining==0)return 1;
        double best=1;
        for(int d=1;d<=Math.Min(5,remaining);d++)foreach(var disc in Combinatorics.Four[d]){
            bool legal=true;for(int r=0;r<4;r++)if(disc[r]>h[r]){legal=false;break;}if(!legal)continue;
            int[] nh=new int[4],nu=(int[])u.Clone();for(int r=0;r<4;r++){nh[r]=h[r]-disc[r];nu[r]+=disc[r];}
            double sum=0;
            foreach(var take in Combinatorics.Four[d]){
                double w=1;for(int r=1;r<=4;r++){int e=take[r-1];if(e>nu[r]){w=0;break;}w*=Combinatorics.C[nu[r],e]*Math.Pow(r,e);}if(w==0)continue;
                if(t==1){sum+=w;continue;}
                int[] hh=(int[])nh.Clone(),uu=(int[])nu.Clone();for(int r=1;r<=4;r++){hh[r-1]+=take[r-1];uu[r]-=take[r-1];}
                sum+=w*Failure(hh,uu,t-1);
            }
            best=Math.Min(best,sum/Combinatorics.C[remaining,d]);
        }
        cache[key]=best;return best;
    }
    public double InitialFailure(int m,int j)=>Combinatorics.C[13,m]*Math.Pow(4,m)/Combinatorics.C[52,m]*Failure(new[]{0,0,0,m},new[]{0,0,0,0,13-m},j);
}

sealed class FlushSolver {
    readonly Dictionary<ulong,double> cache=new();
    public int Count=>cache.Count;
    static ulong Key(int[] h,int[] r,int t){Span<int>a=stackalloc int[4];for(int i=0;i<4;i++)a[i]=(h[i]<<4)|r[i];a.Sort();ulong k=(uint)t;for(int i=0;i<4;i++)k=(k<<7)|(uint)a[i];return k;}
    double Last(int[] kept,int[] r,int d,int total){
        double result=0;
        for(int i=0;i<4;i++)for(int x=5-kept[i];x<=d;x++)result+=Combinatorics.Choose(r[i],x)*Combinatorics.Choose(total-r[i],d-x);
        // A 10-card hand can contain two disjoint flushes; subtract overlaps.
        for(int i=0;i<4;i++)for(int l=i+1;l<4;l++)for(int x=5-kept[i];x<=d;x++)for(int y=5-kept[l];x+y<=d;y++)result-=Combinatorics.Choose(r[i],x)*Combinatorics.Choose(r[l],y)*Combinatorics.Choose(total-r[i]-r[l],d-x-y);
        return result/Combinatorics.C[total,d];
    }
    public double Success(int[] h,int[] r,int t){
        if(h.Any(x=>x>=5))return 1;if(t==0)return 0;
        ulong key=Key(h,r,t);if(cache.TryGetValue(key,out double cached))return cached;
        int total=r.Sum();double best=0;
        for(int d=1;d<=Math.Min(5,total);d++)foreach(var disc in Combinatorics.Four[d]){
            bool legal=true;for(int i=0;i<4;i++)if(disc[i]>h[i]){legal=false;break;}if(!legal)continue;
            int[] kept=new int[4];for(int i=0;i<4;i++)kept[i]=h[i]-disc[i];
            double val;
            if(t==1)val=Last(kept,r,d,total);
            else {
                double sum=0;
                foreach(var draw in Combinatorics.Four[d]){
                    double w=1;bool hit=false;for(int i=0;i<4;i++){if(draw[i]>r[i]){w=0;break;}w*=Combinatorics.C[r[i],draw[i]];if(kept[i]+draw[i]>=5)hit=true;}
                    if(w==0)continue;if(hit){sum+=w;continue;}
                    int[] hh=new int[4],rr=new int[4];for(int i=0;i<4;i++){hh[i]=kept[i]+draw[i];rr[i]=r[i]-draw[i];}
                    sum+=w*Success(hh,rr,t-1);
                }
                val=sum/Combinatorics.C[total,d];
            }
            best=Math.Max(best,val);
        }
        cache[key]=best;return best;
    }
    public double InitialSuccess(int m,int j){double sum=0;foreach(var h in Combinatorics.Comps(m,4)){double w=1;for(int i=0;i<4;i++)w*=Combinatorics.C[13,h[i]];sum+=w*Success(h,h.Select(x=>13-x).ToArray(),j);}return sum/Combinatorics.C[52,m];}
}

class Program {
    static void Main(string[] args){
        CultureInfo.CurrentCulture=CultureInfo.InvariantCulture;
        string mode=args.Length>0?args[0]:"pair";
        if(mode=="rank"){RankSolver.Run(args);return;}
        if(mode=="simulate"){Simulation.Run(args);return;}
        if(mode=="validate"){Validation.Run();return;}
        int maxj=args.Length>1?int.Parse(args[1]):4;
        string output=$"discard_analysis/{mode}-exact.jsonl";
        using var file=new StreamWriter(output,false){AutoFlush=true};
        for(int m=6;m<=10;m++){
            var pair=new PairSolver();var flush=new FlushSolver();var watch=Stopwatch.StartNew();
            for(int j=1;j<=maxj;j++){
                double f=mode=="pair"?pair.InitialFailure(m,j):1-flush.InitialSuccess(m,j);
                string line=JsonSerializer.Serialize(new{kind=mode,m,j,p=1-f,failure=f,states=mode=="pair"?pair.Count:flush.Count,seconds=watch.Elapsed.TotalSeconds});
                file.WriteLine(line);Console.WriteLine(line);
            }
        }
    }
}
