"""Closed styling meshes in furniture-local x/z/y metres; no simulation cache.

Dimensions are provisional. Fabric folds are deterministic, not cloth physics.
"""
import math
from furniture_assets import check_dimensions


def rounded_cushion(cx, cz, bottom, width=.37, depth=.15, height=.37):
    n, rings = 48, 24
    def power(x): return math.copysign(abs(x)**.5,x)
    vertices=[(cx,cz,bottom)]
    for row in range(1,rings):
        lat=-math.pi/2+math.pi*row/rings
        for col in range(n):
            lon=2*math.pi*col/n
            vertices.append((cx+width/2*power(math.cos(lat))*power(math.cos(lon)),
                             cz+depth/2*power(math.cos(lat))*power(math.sin(lon)),
                             bottom+height/2*(1+power(math.sin(lat)))))
    vertices.append((cx,cz,bottom+height)); top=len(vertices)-1
    faces=[(0,1+(j+1)%n,1+j) for j in range(n)]
    for row in range(rings-2):
        a=1+row*n; b=a+n
        faces += [(a+j,a+(j+1)%n,b+(j+1)%n,b+j) for j in range(n)]
    faces += [(top,1+(rings-2)*n+j,1+(rings-2)*n+(j+1)%n) for j in range(n)]
    return dict(vertices=vertices,faces=faces,role='fabric',smooth=True)


def throw_mesh(w,d,h,seat):
    # Runs over the back cushion, down to the seat, then over its front edge.
    path=[(-d/2+.06,h+.012),(-d/2+.19,h+.012),(-d/2+.215,h-.035),
          (-d/2+.23,seat+.10),(-d/2+.29,seat+.012),(d/2-.05,seat+.012),
          (d/2+.025,seat-.015),(d/2+.035,.21)]
    columns=24; rows=len(path); vertices=[]
    for skin in (0,1):
        for row,(z,y) in enumerate(path):
            for j in range(columns+1):
                u=j/columns
                fold=.009*(1+math.sin(u*8*math.pi+.25*row))
                vertices.append((w*.27+(u-.5)*.36,z,y+fold-skin*.003))
    count=rows*(columns+1); faces=[]
    for row in range(rows-1):
        for j in range(columns):
            a=row*(columns+1)+j; b=a+columns+1
            face=(a,a+1,b+1,b); faces.append(face)
            faces.append(tuple(i+count for i in reversed(face)))
    boundary=list(range(columns+1))
    boundary += [row*(columns+1)+columns for row in range(1,rows)]
    boundary += list(range(count-2,count-columns-2,-1))
    boundary += [row*(columns+1) for row in range(rows-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]): faces.append((a,b,b+count,a+count))
    return dict(name='throw',vertices=vertices,faces=faces,role='fabric',smooth=True)


def box(name,x,z,y,w,d,h,role):
    vertices=[(x+sx*w/2,z+sz*d/2,y+sy*h) for sy in (0,1) for sx,sz in ((-1,-1),(1,-1),(1,1),(-1,1))]
    return dict(name=name,vertices=vertices,faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role=role)


def vase(x,z,y):
    # Continuous outer wall, rim and inner cavity, sealed at the base.
    profile=[(0,0),(.035,0),(.055,.02),(.065,.065),(.055,.105),(.027,.14),(.027,.18),
             (.021,.18),(.021,.14),(.049,.102),(.059,.065),(.049,.023),(.03,.007),(0,.007)]
    n=64; vertices=[(x,z,y)]; loops=[]
    for radius,height in profile[1:-1]:
        loops.append(len(vertices))
        vertices += [(x+radius*math.cos(j*2*math.pi/n),z+radius*math.sin(j*2*math.pi/n),y+height) for j in range(n)]
    end=len(vertices); vertices.append((x,z,y+.007))
    faces=[(0,loops[0]+(j+1)%n,loops[0]+j) for j in range(n)]
    for a,b in zip(loops,loops[1:]): faces += [(a+j,a+(j+1)%n,b+(j+1)%n,b+j) for j in range(n)]
    faces += [(end,loops[-1]+j,loops[-1]+(j+1)%n) for j in range(n)]
    return dict(name='ceramic-vase',vertices=vertices,faces=faces,role='stone',smooth=True)


def styling_parts(kind,w,d,h):
    if kind=='sofa-textiles':
        check_dimensions((w,d,h),((1.2,2.4),(.7,1.05),(.65,1)))
        seat=min(.44,h*.58)
        return [dict(rounded_cushion(w*offset,-d/2+.29,seat),name=f'pillow-{j}')
                for j,offset in enumerate((-.27,-.015))]+[throw_mesh(w,d,h,seat)]
    if kind!='tabletop': raise ValueError('Unknown styling kind')
    check_dimensions((w,d,h),((.65,1.4),(.32,.8),(.25,.65)))
    parts=[]
    for j in range(2):
        y=h+.001+j*.024; x=-w*.23+j*.015
        parts += [box(f'book-{j}-bottom',x,0,y,.22,.14,.002,'wood'),
                  box(f'book-{j}-pages',x,0,y+.002,.213,.134,.019,'fabric'),
                  box(f'book-{j}-cover',x,0,y+.021,.22,.14,.002,'wood')]
    return parts+[vase(w*.25,0,h+.001)]
