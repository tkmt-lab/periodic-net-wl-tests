"""Complete IR proof producer. Input graphs are generated at runtime."""

def isomorphism_or_refutation(a,da,b,db,refine):
    if len(a)!=len(b):return None,{'leaf':'size'},1
    A=list(map(set,a));B=list(map(set,b));mapping={0:0};used={0};nodes=0
    def search():
        nonlocal nodes
        nodes+=1
        if nodes>100000:raise TimeoutError("IR node cap 100000")
        ca,cb,it,_,_=refine(a,da,b,db,mapping)
        if it is not None:return None,{'leaf':'colour-histogram'}
        if len(mapping)==len(a):return [mapping[i] for i in range(len(a))],None
        options=[]
        for u in range(len(a)):
            if u in mapping:continue
            candidates=[v for v in range(len(b)) if v not in used and ca[u]==cb[v] and all((x in A[u])==(y in B[v]) for x,y in mapping.items())]
            if not candidates:return None,{'leaf':'no-candidates','vertex':u}
            options.append((len(candidates),-sum(x in A[u] for x in mapping),u,candidates))
        _,_,u,candidates=min(options);children=[]
        for v in candidates:
            mapping[u]=v;used.add(v);found,proof=search()
            if found is not None:return found,None
            children.append([v,proof]);del mapping[u];used.remove(v)
        return None,{'vertex':u,'children':children}
    mapping_out,proof=search();return mapping_out,proof,nodes
