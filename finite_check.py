"""Separate set-partition and exhaustive-proof verifier, no solver import."""
from collections import Counter,defaultdict

def need(ok,msg):
    if not ok:raise ValueError(msg)

def wl(a,b):
    n=len(a[0]);adj=list(a[2])+[{n+j for j in e} for e in b[2]];blocks=defaultdict(set)
    for i,(d,e) in enumerate(zip(a[1]+b[1],adj)):blocks[d,len(e)].add(i)
    partition=list(blocks.values());iteration=0
    while True:
        if any(sum(i<n for i in p)!=sum(i>=n for i in p) for p in partition):return iteration
        classes={v:k for k,p in enumerate(partition) for v in p};new=[]
        for p in partition:
            pieces=defaultdict(set)
            for v in p:pieces[tuple(sorted(Counter(classes[w] for w in adj[v]).items()))].add(v)
            new.extend(pieces.values())
        if len(new)==len(partition):return None
        partition=new;iteration+=1

def check_witness(w,a,b):
    n=len(a[0]);edges=list(a[2])+[{n+j for j in row} for row in b[2]]
    initial=[(d,len(e)) for data in [a,b] for d,e in zip(data[1],data[2])];prev=None
    for it,step in enumerate(w):
        need(len(step[0])==len(a[0]) and len(step[1])==len(b[0]),'colour vector lengths');colors=step[0]+step[1]
        keys=initial if prev is None else [(prev[i],tuple(sorted(prev[j] for j in row))) for i,row in enumerate(edges)]
        f={};g={}
        for key,color in zip(keys,colors):
            need(type(color) is int and color>=0,'colour id');need(key not in f or f[key]==color,'split equal signature');need(color not in g or g[color]==key,'merge different signatures');f[key]=color;g[color]=key
        need((Counter(step[0])!=Counter(step[1]))==(it==len(w)-1),'WL final histogram difference');prev=colors

def check_refutation(tree,a,b):
    n=len(a[0]);m=len(b[0]);A=list(a[2]);B=list(b[2]);calls=0
    def partition(mapping):
        ma={u:k for k,(u,v) in enumerate(mapping.items(),1)};mb={v:k for k,(u,v) in enumerate(mapping.items(),1)}
        labels=[(a[1][i],len(e),ma.get(i,0)) for i,e in enumerate(A)]+[(b[1][i],len(e),mb.get(i,0)) for i,e in enumerate(B)]
        adj=A+[{n+j for j in e} for e in B];blocks=defaultdict(set)
        for i,label in enumerate(labels):blocks[label].add(i)
        ps=list(blocks.values())
        while True:
            if any(sum(i<n for i in p)!=sum(i>=n for i in p) for p in ps):return None
            which={v:k for k,p in enumerate(ps) for v in p};new=[]
            for p in ps:
                pieces=defaultdict(set)
                for v in p:pieces[tuple(sorted(Counter(which[w] for w in adj[v]).items()))].add(v)
                new.extend(pieces.values())
            if len(new)==len(ps):return [which[i] for i in range(n)],[which[n+i] for i in range(m)]
            ps=new
    def visit(node,mapping):
        nonlocal calls
        calls+=1
        if node.get('leaf')=='size':need(n!=m,'size leaf false');return
        need(n==m,'unexpected size mismatch')
        refined=partition(mapping)
        if refined is None:need(node=={'leaf':'colour-histogram'},'missing colour refutation leaf');return
        if 'forced' in node:
            ca,cb=refined;ac=Counter(ca);bc=Counter(cb);used=set(mapping.values());pairs=node['forced'];need(bool(pairs),'empty forced node')
            need(len({u for u,v in pairs})==len(pairs)==len({v for u,v in pairs}),'duplicate forced assignments')
            for u,v in pairs:
                need(type(u) is int and type(v) is int and 0<=u<n and 0<=v<m,'forced vertex bounds')
                need(u not in mapping and v not in used and ca[u]==cb[v] and ac[ca[u]]==bc[cb[v]]==1,'assignment not forced by singleton colour')
            for u,v in pairs:mapping[u]=v
            visit(node['next'],mapping)
            for u,v in pairs:del mapping[u]
            return
        need('vertex' in node and len(mapping)<n,'refutation reached a full mapping or absent branch')
        u=node['vertex'];need(type(u) is int and 0<=u<n and u not in mapping,'branch vertex')
        ca,cb=refined;used=set(mapping.values())
        candidates=[v for v in range(m) if v not in used and ca[u]==cb[v] and all((x in A[u])==(y in B[v]) for x,y in mapping.items())]
        if node.get('leaf')=='no-candidates':need(not candidates,'no-candidate leaf false');return
        children=node['children'];need(sorted(v for v,kid in children)==candidates,'refutation did not cover all candidate images')
        for v,kid in children:
            mapping[u]=v;visit(kid,mapping);del mapping[u]
    visit(tree,{0:0});return calls
