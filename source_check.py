"""Source witness checker; no geometry producer import."""
from fractions import Fraction as Q
from collections import Counter
from itertools import product
import ast
import core_check as helper

def need(x,msg):
    if not x:raise ValueError(msg)

def seq(adj,root):
    seen={(root,0,0,0)};counts=[]
    for r in range(10):
        expanded=seen|{(j,x+u,y+v,z+w) for i,x,y,z in seen for j,u,v,w in adj[i]}
        need(len(expanded)<=50000,'source-check CS vertex cap');counts.append(len(expanded)-len(seen));seen=expanded
    return counts

def verify(g,rec,groups,excerpts):
    adj=[{(j,*s) for j,s in row} for row in g['adjacency']]
    for i,row in enumerate(adj):
        need(len(row)==len(g['adjacency'][i]) and (i,0,0,0) not in row,'simple lift')
        for j,x,y,z in row:need((i,-x,-y,-z) in adj[j],'reverse edge')
    if g['source_mode'].startswith('ARC'):
        key=excerpts[rec['name']];need(key==g['arc_key'] and key[0]==3,'ARC source excerpt')
        expected=[set() for _ in adj]
        for k in range(1,len(key),5):
            a,b,x,y,z=key[k:k+5];expected[a-1].add((b-1,x,y,z));expected[b-1].add((a-1,-x,-y,-z))
        need(expected==adj,'ARC explicit graph differs')
        sequences=[seq(adj,i) for i in range(len(adj))];need(sequences==g['arc_all_vertex_cs10'],'ARC CS independently computed')
        actual=Counter(map(tuple,sequences));wanted=Counter()
        for v in rec['vertices']:wanted[tuple(v['cs10'])]+=v['multiplicity']
        need(set(actual)==set(wanted),'ARC CS set')
        need(all(actual[s]*rec['estimated_quotient_vertices']==wanted[s]*len(adj) for s in actual),'ARC weighted CS proportions')
        for v in rec['vertices']:
            if v['label'] in g['source_roots']:
                need(sum(w['cs10']==v['cs10'] for w in rec['vertices'])==1,'ARC source root ambiguous')
                need(sequences[g['source_roots'][v['label']]]==v['cs10'],'ARC root descriptor')
        return {'mode':g['source_mode'],'vertices':len(adj),'source_root_count':len(g['source_roots'])}
    D=g['grid_denominator'];need(type(D) is int and D>0,'grid')
    def scaled(xs):
        values=[Q(x)*D for x in xs];need(all(x.denominator==1 for x in values),'source grid exactness');return tuple(int(x) for x in values)
    ops=[]
    for op in groups[rec['spacegroup_table_key']]:
        trees=[ast.parse(c,mode='eval').body for c in op.split(',')]
        def act(p):return scaled([helper.numeric(t,dict(zip('xyz',[Q(x,D) for x in p]))) for t in trees])
        origin=act((0,0,0));cols=[tuple((act(tuple(D if j==k else 0 for j in range(3)))[i]-origin[i])//D for i in range(3)) for k in range(3)]
        ops.append((list(map(list,zip(*cols))),origin))
    def action(op,p):
        m,t=op;return tuple(sum(m[i][j]*p[j] for j in range(3))+t[i] for i in range(3))
    def orbit(xs):
        p=scaled(xs);return {tuple(x%D for x in action(op,p)) for op in ops}
    points=[scaled(v['coordinate']) for v in g['vertices']];lookup={p:i for i,p in enumerate(points)};need(len(lookup)==len(points),'duplicate point')
    for v in rec['vertices']:
        ps=orbit(v['coordinate']);need(len(ps)==v['multiplicity'],'vertex orbit size')
        need(ps=={p for p,w in zip(points,g['vertices']) if w['source_orbit']==v['label']},'vertex orbit set')
        root=g['source_roots'][v['label']];need(points[root]==tuple(x%D for x in scaled(v['coordinate'])),'source root point')
        need(len(adj[root])==v['degree'],'root degree')
        need(seq(adj,root)==v['cs10'],'CS source comparison')
    a,b,c,alpha,beta,gamma=map(Q,rec['cell']);need(alpha==beta==90 and gamma in [90,120],'metric angles')
    gram=[[a*a,-a*b/2 if gamma==120 else Q(0),Q(0)],[-a*b/2 if gamma==120 else Q(0),b*b,Q(0)],[Q(0),Q(0),c*c]]
    matrix=g['integer_gram'];scale=g['metric_scale'];need(all(Q(matrix[i][j],scale)==gram[i][j] for i in range(3) for j in range(3)),'metric from source')
    low=min(matrix[i][i]-sum(abs(matrix[i][j]) for j in range(3) if j!=i) for i in range(3))*D*D;need(low>0,'positive distance bound')
    nonzero=[(i,j,matrix[i][j]) for i in range(3) for j in range(3) if matrix[i][j]]
    def dist(p,q):
        delta=[p[k]-q[k] for k in range(3)];return sum(v*delta[i]*delta[j] for i,j,v in nonzero)
    expected_centers={(e['label'],p) for e in rec['edge_centers'] for p in orbit(e['coordinate'])}
    need(len(expected_centers)==sum(e['multiplicity'] for e in rec['edge_centers']),'center orbit sizes')
    seen_centers=set();derived=[set() for _ in adj];shifts=list(product([-1,0,1],repeat=3))
    rowbound=max(sum(abs(v) for v in row) for m,t in ops for row in m)
    for label,p,left,right in g['source_edge_witnesses']:
        p=tuple(p);need((label,p) in expected_centers and (label,p) not in seen_centers,'center witness coverage');seen_centers.add((label,p))
        i,s=left;j,t=right;need(tuple(s) in shifts and tuple(t) in shifts,'endpoint outside finite box')
        endpoints=[tuple(points[k][z]+D*shift[z] for z in range(3)) for k,shift in [(i,s),(j,t)]]
        threshold=max(dist(p,q) for q in endpoints);need(threshold<=low,'outside-box global bound')
        selected={(i,tuple(s)),(j,tuple(t))};need(len(selected)==2,'same endpoint twice')
        for k,q in enumerate(points):
            for shift in shifts:
                if (k,shift) not in selected:
                    need(dist(p,tuple(q[z]+D*shift[z] for z in range(3)))>threshold,'unselected point not strictly farther')
        need(all(abs(endpoints[0][z]+endpoints[1][z]-2*p[z])*10000<=2*rowbound*D for z in range(3)),'midpoint rounding bound')
        delta=tuple(t[k]-s[k] for k in range(3));derived[i].add((j,*delta));derived[j].add((i,*(-x for x in delta)))
    need(seen_centers==expected_centers and derived==adj,'edge witness graph and coverage')
    # Every listed source operation must preserve the full infinite edge relation.
    for op in ops:
        images=[]
        for p in points:
            q=action(op,p);part=tuple(x%D for x in q);images.append((lookup[part],tuple((q[k]-part[k])//D for k in range(3))))
        for i,row in enumerate(adj):
            ii,si=images[i]
            for j,x,y,z in row:
                jj,sj=images[j];m,_=op;delta=tuple(sj[k]-si[k]+sum(m[k][l]*(x,y,z)[l] for l in range(3)) for k in range(3))
                need((jj,*delta) in adj[ii],'source SG operation does not preserve lifted edges')
    return {'mode':g['source_mode'],'vertices':len(adj),'centers_checked':len(seen_centers),'source_root_count':len(g['source_roots'])}
