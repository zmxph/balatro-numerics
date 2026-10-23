using System.Diagnostics;
using System.Numerics;
using System.Text.Json;

// Straight and straight flush: exact one-discard action values, and a
// direct-draw lookahead surrogate for earlier decisions. The last draw is
// integrated out (Rao-Blackwellization), not sampled.
sealed class SequencePolicy {
    public static readonly int[] Windows=Enumerable.Range(0,9).Select(i=>31<<i).Append(7681).ToArray(); // A2345 ... 9TJQK, TJQKA
    static readonly (int Mask,int Coeff)[] IE=BuildIE();
    static (int,int)[] BuildIE(){var dict=new Dictionary<int,int>();foreach(int w in Windows){var add=new Dictionary<int,int>{{w,1}};foreach(var(k,v) in dict){int u=k|w;add[u]=add.GetValueOrDefault(u)-v;}foreach(var(k,v) in add){dict[k]=dict.GetValueOrDefault(k)+v;if(dict[k]==0)dict.Remove(k);}}return dict.Select(p=>(p.Key,p.Value)).ToArray();}
    readonly bool sf;
    readonly Dictionary<(int,int),double[]> completion=new();
    public SequencePolicy(bool sf){this.sf=sf;}
    static int PC(int x)=>BitOperations.PopCount((uint)x);
    static int PC(ulong x)=>BitOperations.PopCount(x);
    double Complete(int total,int draws,int code){
        if(code==0)return 1;
        if(!completion.TryGetValue((total,draws),out var arr)){arr=new double[65536];Array.Fill(arr,-1);arr[0]=1;completion[(total,draws)]=arr;}
        double cached=arr[code];if(cached>=0)return cached;
        int a=code&15,b=(code>>4)&15,c=(code>>8)&15,e=(code>>12)&15;
        if(a+b+c+e>draws)return arr[code]=0;
        double sum=0;
        for(int i=0;i<=a;i++)for(int j=0;j<=b;j++)for(int k=0;k<=c;k++)for(int l=0;l<=e;l++){
            double w=Combinatorics.C[a,i]*Combinatorics.C[b,j]*Combinatorics.C[c,k]*Combinatorics.C[e,l]*Combinatorics.Choose(total-i-2*j-3*k-4*l,draws);
            sum+=((i+j+k+l)&1)==0?w:-w;
        }
        return arr[code]=Math.Clamp(sum/Combinatorics.C[total,draws],0,1);
    }
    static double Required(int total,int draws,int need)=>need>draws?0:Combinatorics.Choose(total-need,draws-need)/Combinatorics.C[total,draws];
    public bool Hit(int[] hand,int m){
        if(sf){Span<int> masks=stackalloc int[4];for(int i=0;i<m;i++)masks[hand[i]/13]|=1<<(hand[i]%13);for(int s=0;s<4;s++)foreach(int w in Windows)if((masks[s]&w)==w)return true;}
        else{int mask=0;for(int i=0;i<m;i++)mask|=1<<(hand[i]%13);foreach(int w in Windows)if((mask&w)==w)return true;}
        return false;
    }
    public (int Keep,double Score) Decide(int[] hand,int m,ulong remaining,int turns,double reserve){
        return sf?DecideSF(hand,m,remaining,turns,reserve):DecideStraight(hand,m,remaining,turns,reserve);
    }
    (int,double) DecideStraight(int[] hand,int m,ulong remaining,int turns,double reserve){
        int total=PC(remaining),present=0;Span<int> counts=stackalloc int[13];Span<int> first=stackalloc int[13];
        for(int i=0;i<m;i++){int r=hand[i]%13;counts[r]++;present|=1<<r;first[r]=i;}
        Span<int> rmask=stackalloc int[5];for(int r=0;r<13;r++){int n=0;for(int s=0;s<4;s++)if((remaining&(1UL<<(13*s+r)))!=0)n++;rmask[n]|=1<<r;}
        double best=-1;int chosen=0;
        int future=(int)Math.Round((turns-1)*Math.Min(5,m-reserve),MidpointRounding.AwayFromZero);
        for(int kept=present;kept>0;kept=(kept-1)&present){
            int n=PC(kept),keepCount=Math.Max(m-5,n),d=m-keepCount;if(d==0)continue;
            int available=0;for(int x=kept;x>0;x&=x-1)available+=counts[BitOperations.TrailingZeroCount((uint)x)];if(available<keepCount)continue;
            int draws=Math.Min(total,d+future);double value=0;
            foreach(var(w,c) in IE){
                int missing=w&~kept;if((missing&rmask[0])!=0||PC(missing)>draws)continue;
                int code=PC(missing&rmask[1])|(PC(missing&rmask[2])<<4)|(PC(missing&rmask[3])<<8)|(PC(missing&rmask[4])<<12);
                value+=c*Complete(total,draws,code);
            }
            if(value>best+1e-14){
                int mask=0;for(int x=kept;x>0;x&=x-1)mask|=1<<first[BitOperations.TrailingZeroCount((uint)x)];
                for(int i=0;i<m&&PC(mask)<keepCount;i++)if((kept&(1<<(hand[i]%13)))!=0)mask|=1<<i;
                best=value;chosen=mask;
            }
        }
        return(chosen,Math.Clamp(best,0,1));
    }
    (int,double) DecideSF(int[] hand,int m,ulong remaining,int turns,double reserve){
        int total=PC(remaining),size=1<<m;ulong held=0;for(int i=0;i<m;i++)held|=1UL<<hand[i];ulong accessible=held|remaining;
        var events=new List<(int Need,int Held,int Coeff)>();
        for(int s=0;s<4;s++)foreach(var(w,c) in IE){
            ulong cards=(ulong)w<<(13*s);if((cards&~accessible)!=0)continue;
            int h=0;for(int i=0;i<m;i++)if((cards&(1UL<<hand[i]))!=0)h|=1<<i;
            events.Add((PC(cards&remaining),h,c));
        }
        // For m=10 at the final draw, subtract the possibility of two SFs.
        int[]? cross=null;
        if(m==10&&turns==1){
            var singles=new List<(int Held,int Suit)>();for(int s=0;s<4;s++)foreach(int w in Windows){ulong cards=(ulong)w<<(13*s);if((cards&~accessible)!=0)continue;int h=0;for(int i=0;i<m;i++)if((cards&(1UL<<hand[i]))!=0)h|=1<<i;singles.Add((h,s));}
            cross=new int[size];for(int i=0;i<singles.Count;i++)for(int q=i+1;q<singles.Count;q++)if(singles[i].Suit!=singles[q].Suit)cross[singles[i].Held|singles[q].Held]++;
        }
        double best=-1;int chosen=0;var scores=new double[size];
        int future=(int)Math.Round((turns-1)*Math.Min(5,m-reserve),MidpointRounding.AwayFromZero);
        for(int d=1;d<=5;d++){
            int draws=Math.Min(total,d+future);Array.Clear(scores);
            foreach(var e in events)if(e.Need<=draws)scores[e.Held]+=e.Coeff*Required(total,draws,e.Need);
            for(int b=1;b<size;b<<=1)for(int mask=0;mask<size;mask++)if((mask&b)!=0)scores[mask]+=scores[mask^b];
            for(int mask=0;mask<size;mask++){
                if(PC(mask)!=m-d)continue;double value=scores[mask];
                if(cross!=null){
                    // Two disjoint 5-card windows must cover the entire final hand.
                    value-=cross[mask]/Combinatorics.C[total,d];
                }
                if(value>best+1e-14){best=value;chosen=mask;}
            }
        }
        return(chosen,Math.Clamp(best,0,1));
    }
}

static class Simulation {
    static (double mean,double se,double seconds) Evaluate(bool sf,int m,int j,double reserve,int trials,int seed){
        var rng=new Random(seed);var policy=new SequencePolicy(sf);var sw=Stopwatch.StartNew();double sum=0,sum2=0;
        int[] deck=new int[52],hand=new int[m];
        for(int trial=0;trial<trials;trial++){
            for(int i=0;i<52;i++)deck[i]=i;int pos=0;ulong remaining=(1UL<<52)-1;
            int Draw(){int index=rng.Next(pos,52);(deck[pos],deck[index])=(deck[index],deck[pos]);int c=deck[pos++];remaining&=~(1UL<<c);return c;}
            for(int i=0;i<m;i++)hand[i]=Draw();double score=0;
            for(int t=j;t>=1;t--){
                if(policy.Hit(hand,m)){score=1;break;}
                var(keep,value)=policy.Decide(hand,m,remaining,t,reserve);
                if(t==1){score=value;break;}
                for(int i=0;i<m;i++)if((keep&(1<<i))==0)hand[i]=Draw();
            }
            sum+=score;sum2+=score*score;
        }
        double mean=sum/trials,se=Math.Sqrt(Math.Max(0,(sum2-sum*sum/trials)/(trials-1))/trials);return(mean,se,sw.Elapsed.TotalSeconds);
    }
    public static void Run(string[] args){
        bool sf=args[1]=="straight_flush";int trials=int.Parse(args[2]);string phase=args.Length>3?args[3]:"pilot";
        int onlyM=args.Length>4?int.Parse(args[4]):0;
        string path=$"discard_analysis/{args[1]}-{phase}"+(onlyM>0?$"-m{onlyM}":"")+".jsonl";
        var reusable=new Dictionary<(int,int,double),string>();
        if(phase=="final")foreach(string f in Directory.GetFiles("discard_analysis",onlyM>0?$"{args[1]}-final-m{onlyM}.jsonl":$"{args[1]}-final*.jsonl"))foreach(string line in File.ReadLines(f)){
            var doc=JsonDocument.Parse(line).RootElement;if(doc.GetProperty("n").GetInt32()==trials)reusable[(doc.GetProperty("m").GetInt32(),doc.GetProperty("j").GetInt32(),doc.GetProperty("reserve").GetDouble())]=line;
        }
        using var file=new StreamWriter(path,false){AutoFlush=true};
        Dictionary<(int,int),double> selected=new();
        if(phase=="final"){
            foreach(string f in Directory.GetFiles("discard_analysis",$"{args[1]}-pilot*.jsonl"))foreach(string line in File.ReadLines(f)){
                var doc=JsonDocument.Parse(line).RootElement;int m=doc.GetProperty("m").GetInt32(),j=doc.GetProperty("j").GetInt32();double p=doc.GetProperty("p").GetDouble();
                // Pilot entries are ordered by descending preference only on exact ties.
                double old=selected.GetValueOrDefault((m,-j),-1);if(p>old){selected[(m,-j)]=p;selected[(m,j)]=doc.GetProperty("reserve").GetDouble();}
            }
        }
        for(int m=6;m<=10;m++)if(onlyM==0||m==onlyM)for(int j=1;j<=4;j++){
            if(phase=="pilot_extra"&&j==1)continue;
            double[] reserves=phase=="final"?new[]{selected[(m,j)]}:phase=="pilot_extra"?(m==6?new[]{(double)m}:new[]{(double)m,(double)m-1}):j==1||m==10?new[]{4.0}:new[]{3.0,4.0,5.0};
            foreach(double reserve in reserves){
                if(phase=="final"&&reusable.TryGetValue((m,j,reserve),out var saved)){file.WriteLine(saved);Console.WriteLine($"Reused {args[1]} m={m} j={j}");continue;}
                int seed=20260926+(sf?1000000:0)+m*1000+j*10+(phase=="final"?2000000:0);
                var(p,se,seconds)=Evaluate(sf,m,j,reserve,trials,seed);
                string line=JsonSerializer.Serialize(new{kind=args[1],m,j,reserve,n=trials,p,se,seconds,phase,seed,optimal_strategy=j==1});file.WriteLine(line);Console.WriteLine(line);
            }
        }
    }
}
