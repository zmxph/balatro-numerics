using System.Diagnostics;
using System.Text.Json;

// Counts of ranks with (held, remaining) copies. Suits do not affect these events.
sealed class RankSolver {
    static readonly int[] H={0,0,0,0,0,1,1,1,1,2,2,2,3,3,4};
    static readonly int[] R={0,1,2,3,4,0,1,2,3,0,1,2,0,1,0};
    static readonly int[,] Index=MakeIndex();
    static int[,] MakeIndex(){var a=new int[5,5];for(int i=0;i<15;i++)a[H[i],R[i]]=i;return a;}
    readonly int kind;
    readonly Dictionary<ulong,double> cache=new();
    readonly Dictionary<ulong,double> terminal=new();
    public int Count=>cache.Count;
    public RankSolver(int kind){this.kind=kind;}
    public double Conditional(int[] held,int[] remaining,int t){int[] g=new int[15];for(int i=0;i<13;i++)g[Index[held[i],remaining[i]]]++;return Success(g,t);}
    bool Hit(int c2,int c3,int c4)=>kind switch {0=>c2>=2,1=>c3>=1,2=>c3>=1&&c2>=2,3=>c4>=1,_=>false};
    bool Hit(int[] g){int c2=0,c3=0,c4=0;for(int i=9;i<15;i++){c2+=g[i];if(H[i]>=3)c3+=g[i];if(H[i]>=4)c4+=g[i];}return Hit(c2,c3,c4);}
    static ulong Key(int[] g,int t){ulong k=(uint)t;for(int i=0;i<15;i++)k=(k<<4)|(uint)g[i];return k;}
    static int Total(int[] g){int n=0;for(int i=0;i<15;i++)n+=g[i]*R[i];return n;}
    double Last(int[] g,int d){
        ulong key=Key(g,d);if(terminal.TryGetValue(key,out double found))return found;
        // DP over drawn cards and capped counts of ranks with 2+, 3+, 4+ cards.
        double[,,,] dp=new double[d+1,3,2,2];dp[0,0,0,0]=1;
        for(int i=0;i<15;i++)for(int a=0;a<g[i];a++){
            var next=new double[d+1,3,2,2];int h=H[i],r=R[i];
            for(int n=0;n<=d;n++)for(int p=0;p<3;p++)for(int t=0;t<2;t++)for(int f=0;f<2;f++){
                double w=dp[n,p,t,f];if(w==0)continue;
                for(int x=0;x<=Math.Min(r,d-n);x++)next[n+x,Math.Min(2,p+(h+x>=2?1:0)),Math.Max(t,h+x>=3?1:0),Math.Max(f,h+x>=4?1:0)]+=w*Combinatorics.C[r,x];
            }
            dp=next;
        }
        double sum=0;for(int p=0;p<3;p++)for(int t=0;t<2;t++)for(int f=0;f<2;f++)if(Hit(p,t,f))sum+=dp[d,p,t,f];
        double result=sum/Combinatorics.C[Total(g),d];terminal[key]=result;return result;
    }
    IEnumerable<(int[],int)> Actions(int[] g){
        // Enumerate all card-count discards per held rank; collapse rank permutations.
        var ranks=new List<(int h,int r)>();for(int i=5;i<15;i++)for(int a=0;a<g[i];a++)ranks.Add((H[i],R[i]));
        var work=(int[])g.Clone();var seen=new HashSet<ulong>();var results=new List<(int[],int)>();
        void Walk(int n,int d){
            if(n==ranks.Count){if(d>0){ulong key=Key(work,0);if(seen.Add(key))results.Add(((int[])work.Clone(),d));}return;}
            var(h,r)=ranks[n];int from=Index[h,r];
            for(int x=0;x<=Math.Min(h,5-d);x++){work[from]--;work[Index[h-x,r]]++;Walk(n+1,d+x);work[Index[h-x,r]]--;work[from]++;}
        }
        Walk(0,0);return results;
    }
    readonly record struct DrawOption(int Taken,double Weight,int[] Delta);
    readonly Dictionary<(int,int),List<DrawOption>> options=new();
    List<DrawOption> Options(int type,int count){
        if(options.TryGetValue((type,count),out var found))return found;
        var result=new List<DrawOption>();int h=H[type],r=R[type];int[] delta=new int[15];
        void Walk(int x,int left,int taken,double w){
            if(x>r){if(left==0)result.Add(new(taken,w,(int[])delta.Clone()));return;}
            for(int num=0;num<=left && taken+num*x<=5;num++){
                delta[Index[h+x,r-x]]+=num;
                Walk(x+1,left-num,taken+num*x,w*Combinatorics.C[left,num]*Math.Pow(Combinatorics.C[r,x],num));
                delta[Index[h+x,r-x]]-=num;
            }
        }
        Walk(0,count,0,1);options[(type,count)]=result;return result;
    }
    double Draw(int[] g,int d,int t){
        var groups=new List<List<DrawOption>>();for(int i=0;i<15;i++)if(g[i]>0)groups.Add(Options(i,g[i]));
        int[] next=new int[15];double sum=0;
        void Walk(int n,int left,double w){
            if(n==groups.Count){if(left==0)sum+=w*Success(next,t);return;}
            foreach(var opt in groups[n]){if(opt.Taken>left)continue;for(int i=0;i<15;i++)next[i]+=opt.Delta[i];Walk(n+1,left-opt.Taken,w*opt.Weight);for(int i=0;i<15;i++)next[i]-=opt.Delta[i];}
        }
        Walk(0,d,1);return sum/Combinatorics.C[Total(g),d];
    }
    double Success(int[] g,int t){
        if(Hit(g))return 1;if(t==0)return 0;ulong key=Key(g,t);if(cache.TryGetValue(key,out var hit))return hit;
        double best=0;
        foreach(var(action,d) in Actions(g)){
            if(d>Total(g))continue;
            double v=t==1?Last(action,d):Draw(action,d,t-1);best=Math.Max(best,v);
        }
        cache[key]=best;return best;
    }
    public double Initial(int m,int j){
        double sum=0;int[] g=new int[15];
        void Walk(int h,int leftRanks,int leftCards,double w){
            if(h==5){if(leftRanks==0&&leftCards==0)sum+=w*Success(g,j);return;}
            for(int a=0;a<=leftRanks&&h*a<=leftCards;a++){
                g[Index[h,4-h]]=a;Walk(h+1,leftRanks-a,leftCards-h*a,w*Combinatorics.C[leftRanks,a]*Math.Pow(Combinatorics.C[4,h],a));g[Index[h,4-h]]=0;
            }
        }
        Walk(0,13,m,1);return sum/Combinatorics.C[52,m];
    }
    public static void Run(string[] args){
        int kind=int.Parse(args[1]);string name=new[]{"two_pair","three","full_house","four"}[kind];int maxj=args.Length>2?int.Parse(args[2]):1;
        using var file=new StreamWriter($"discard_analysis/{name}-exact.jsonl",false){AutoFlush=true};
        for(int m=6;m<=10;m++){
            var solver=new RankSolver(kind);var sw=Stopwatch.StartNew();
            for(int j=1;j<=maxj;j++){
                double p=solver.Initial(m,j);var line=JsonSerializer.Serialize(new{kind=name,m,j,p,states=solver.Count,seconds=sw.Elapsed.TotalSeconds});Console.WriteLine(line);file.WriteLine(line);
            }
        }
    }
}
