"""Integer geometry producer, using a caller-supplied source record and SG table."""
from fractions import Fraction as Q
from math import lcm
from itertools import product
from collections import deque
import algorithm as base
def need(ok,msg):
    if not ok:raise ValueError(msg)

def build(rec,expressions):
    ops=[base.parse(x) for x in expressions]
    allcoords=[list(map(Q,v['coordinate'])) for v in rec['vertices']+rec['edge_centers']]
    D=lcm(*(q.denominator for p in allcoords for q in p),*(q.denominator for _,t in ops for q in t))
    intops=[(m,tuple(int(x*D) for x in t)) for m,t in ops]
    def orbit(point):
        p=tuple(int(x*D) for x in point)
        return sorted({tuple((sum(m[i][j]*p[j] for j in range(3))+t[i])%D for i in range(3)) for m,t in intops})
    points=[];labels=[];degrees=[];roots={}
    for index,v in enumerate(rec['vertices']):
        ps=orbit(allcoords[index]);need(len(ps)==v['multiplicity'],f"vertex orbit size {v['label']}: {len(ps)} != {v['multiplicity']}")
        roots[v['label']]=len(points)+ps.index(tuple(int(x*D)%D for x in allcoords[index]));points+=ps;labels += [v['label']]*len(ps);degrees += [v['degree']]*len(ps)
    need(len(set(points))==len(points),'coincident source vertices')
    n=len(points);need(n<=1200,'quotient size cap 1200')
    gram,lo=base.gram(rec['cell']);scale=lcm(*(Q(x).denominator for row in gram for x in row));m=[[int(x*scale) for x in row] for row in gram];low=int(lo*scale)*D*D
    shifts=list(product(range(-1,2),repeat=3))
    def scores(center,exclude=None):
        out=[]
        for j,q in enumerate(points):
            for s in shifts:
                if exclude==j and s==(0,0,0):continue
                x,y,z=(q[k]+D*s[k]-center[k] for k in range(3));value=m[0][0]*x*x+m[1][1]*y*y+m[2][2]*z*z+2*m[0][1]*x*y
                out.append((value,j,s))
        out.sort();return out
    adj=[set() for p in points];audit=[];mode='nearest-valence' if rec['embed_type'].startswith('1') else 'edge-centers'
    if mode=='nearest-valence':
        for i,p in enumerate(points):
            sc=scores(p,i);k=degrees[i];need(sc[k-1][0]<sc[k][0] and sc[k-1][0]<=low,'nearest-valence gap or box bound')
            adj[i]={(j,s) for _,j,s in sc[:k]}
    # For all records retain explicit endpoint witnesses for the checker.
    from_centers=[set() for p in points]
    rowbound=max(sum(abs(x) for x in row) for mat,_ in intops for row in mat)
    for k,e in enumerate(rec['edge_centers']):
        centers=orbit(allcoords[len(rec['vertices'])+k]);need(len(centers)==e['multiplicity'],f"edge orbit size {e['label']}")
        for center in centers:
            sc=scores(center);a,b,c=sc[:3];need(b[0]<c[0] and b[0]<=low,'edge-center nearest gap or box bound')
            _,i,s=a;_,j,t=b;res=[points[i][q]+D*s[q]+points[j][q]+D*t[q]-2*center[q] for q in range(3)]
            need(all(abs(x)*10000<=2*rowbound*D for x in res),'rounded midpoint residual')
            delta=tuple(t[q]-s[q] for q in range(3));from_centers[i].add((j,delta));from_centers[j].add((i,tuple(-x for x in delta)))
            audit.append([e['label'],list(center),[i,list(s)],[j,list(t)]])
    if mode=='nearest-valence':need(adj==from_centers,'nearest-valence and edge-centers disagree')
    else:adj=from_centers
    for i,row in enumerate(adj):
        need(len(row)==degrees[i],f'degree mismatch {i}')
        for j,s in row:need((i,tuple(-x for x in s)) in adj[j],'asymmetric edge')
    for v in rec['vertices']:
        start=(roots[v['label']],0,0,0);ds={start:0};queue=deque([start]);counts=[0]*10
        while queue:
            u=queue.popleft();r=ds[u]
            if r==10:continue
            for j,s in adj[u[0]]:
                w=(j,*(u[q+1]+s[q] for q in range(3)))
                if w not in ds:
                    ds[w]=r+1;counts[r]+=1;queue.append(w)
                    need(len(ds)<=50000,'CS10 vertex cap')
        need(counts==v['cs10'],f"CS10 mismatch {v['label']}: {counts}")
    return {'schema':'R019-periodic-graph-v1','net':rec['name'],'record_id':rec['record_id'],
        'vertices':[{'coordinate':[str(Q(x,D)) for x in p],'source_orbit':labels[i],'degree':degrees[i]} for i,p in enumerate(points)],
        'adjacency':[[[j,list(s)] for j,s in sorted(row)] for row in adj],'source_roots':roots,'source_mode':mode,
        'grid_denominator':D,'integer_gram':m,'metric_scale':scale,'source_edge_witnesses':audit,'rounding_row_bound':rowbound}
