"""Canonical straight/arc stair treads. Source metres; no inferred dimensions."""
import math


def layout(stair, levels):
    segments=[]; total=0
    for s in stair['segments']:
        length=math.hypot(s['x1']-s['x0'],s['z1']-s['z0']) if s['type']=='straight' else abs(math.radians(s['endAngleDeg']-s['startAngleDeg']))*s['radius']
        segments.append((s,total,total+length)); total+=length
    count=stair['totalSteps']; half=stair['width']/2
    if count<=0 or total<=0: raise ValueError('Invalid canonical stair')
    low=levels[f"fl{stair['levelFrom']}"]; high=levels[f"fl{stair['levelTo']}"]
    steps=[]
    for k in range(count):
        polygons=[]
        for seg,start,end in segments:
            a,b=max(k*total/count,start),min((k+1)*total/count,end)
            if b-a<1e-8: continue
            t0,t1=(a-start)/(end-start),(b-start)/(end-start)
            if seg['type']=='straight':
                dx,dz=seg['x1']-seg['x0'],seg['z1']-seg['z0']; length=math.hypot(dx,dz)
                ax,az=seg['x0']+dx*t0,seg['z0']+dz*t0
                bx,bz=seg['x0']+dx*t1,seg['z0']+dz*t1
                nx,nz=-dz/length*half,dx/length*half
                poly=[(ax+nx,az+nz),(bx+nx,bz+nz),(bx-nx,bz-nz),(ax-nx,az-nz)]
            else:
                a0=math.radians(seg['startAngleDeg']+(seg['endAngleDeg']-seg['startAngleDeg'])*t0)
                a1=math.radians(seg['startAngleDeg']+(seg['endAngleDeg']-seg['startAngleDeg'])*t1)
                n=max(1,math.ceil(abs(a1-a0)/(math.pi/32)))
                angles=[a0+(a1-a0)*i/n for i in range(n+1)]
                def arc(radius,angles): return [(seg['pivotX']+radius*math.cos(a),seg['pivotZ']+radius*math.sin(a)) for a in angles]
                inner=max(0,seg['radius']-half)
                poly=arc(seg['radius']+half,angles)+(arc(inner,list(reversed(angles))) if inner>1e-8 else [(seg['pivotX'],seg['pivotZ'])])
            polygons.append(poly)
        steps.append(dict(polygons=polygons,bottom=low+k*(high-low)/count,top=low+(k+1)*(high-low)/count))
    return dict(id=stair['id'],levelFrom=stair['levelFrom'],levelTo=stair['levelTo'],steps=steps,status=stair.get('status'),note=stair.get('note'))


def walking_ramps(stair,levels):
    """Closed smooth support along tread nosings; visible treads stay separate.

    A radial grid avoids a single twisted quad creating a near-vertical
    collision triangle on the inside of the 180-degree turn.
    """
    lengths=[math.hypot(s['x1']-s['x0'],s['z1']-s['z0']) if s['type']=='straight' else abs(math.radians(s['endAngleDeg']-s['startAngleDeg']))*s['radius'] for s in stair['segments']]
    total=sum(lengths);start=0;low=levels[f"fl{stair['levelFrom']}"];rise=levels[f"fl{stair['levelTo']}"]-low
    for seg,length in zip(stair['segments'],lengths):
        rows=16 if seg['type']=='straight' else 64
        cols=1 if seg['type']=='straight' else 16
        top=[]
        for i in range(rows+1):
            t=i/rows;y=low+min(1,(start+length*t)/total+1/stair['totalSteps'])*rise
            for j in range(cols+1):
                if seg['type']=='straight':
                    dx,dz=seg['x1']-seg['x0'],seg['z1']-seg['z0'];offset=(j/cols-.5)*stair['width']
                    x=seg['x0']+t*dx-dz/length*offset;z=seg['z0']+t*dz+dx/length*offset
                else:
                    a=math.radians(seg['startAngleDeg']+(seg['endAngleDeg']-seg['startAngleDeg'])*t)
                    inner=max(.015,seg['radius']-stair['width']/2);outer=seg['radius']+stair['width']/2
                    r=outer+(inner-outer)*j/cols
                    x=seg['pivotX']+r*math.cos(a);z=seg['pivotZ']+r*math.sin(a)
                top.append((x,z,y))
        n=len(top);vertices=top+[(x,z,y-.08) for x,z,y in top];faces=[]
        for i in range(rows):
            for j in range(cols):
                a=i*(cols+1)+j;b=a+1;c=b+cols+1;d=a+cols+1
                faces.extend([(a,b,c,d),(d+n,c+n,b+n,a+n)])
        boundary=list(range(cols+1))+[i*(cols+1)+cols for i in range(1,rows+1)]+[rows*(cols+1)+j for j in range(cols-1,-1,-1)]+[i*(cols+1) for i in range(rows-1,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,a+n,b+n,b))
        yield vertices,faces
        start+=length


def wall_clearances(wall,data):
    """Cut only internal walls actually crossed by a canonical tread.

    For example the pantry's north partition ends at the underside of the
    overhead flight; it must not continue through that flight. Side walls
    touched by a tread edge (rather than crossed) remain intact.
    """
    if wall.get('id','').startswith('wall-ext-') or 'guardHeight' in wall:return []
    horizontal=wall['orientation']=='H';at=wall['z0'] if horizontal else wall['x0']
    lo,hi=(wall['x0'],wall['x1']) if horizontal else (wall['z0'],wall['z1'])
    normal=1 if horizontal else 0;along=1-normal;cuts=[]
    for stair in data.get('stairs',[]):
        if stair['levelFrom']!=wall['level']:continue
        for i,step in enumerate(layout(stair,data['levels'])['steps']):
            points=[p for poly in step['polygons'] for p in poly]
            if not min(p[normal] for p in points)<at-1e-6<at+1e-6<max(p[normal] for p in points):continue
            intersections=[]
            for poly in step['polygons']:
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    if abs(a[normal]-at)<1e-7:intersections.append(a[along])
                    if (a[normal]-at)*(b[normal]-at)<0:
                        t=(at-a[normal])/(b[normal]-a[normal]);intersections.append(a[along]+t*(b[along]-a[along]))
            if len(intersections)<2:continue
            start,end=max(lo,min(intersections)),min(hi,max(intersections))
            if end-start<1e-6:continue
            cuts.append(dict(id=f"clearance-{stair['id']}-{i}",start=start,end=end,bottom=step['bottom'],
                top=data['levels'][f"fl{stair['levelTo']}"]+data['defaults']['ceilingHeight'],
                operation='open',exterior=False,status=stair.get('status'),note=stair.get('note'),derivedFrom=stair['id']))
    return cuts
