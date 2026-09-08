"""Persistent surface identities: validate data/visual/surface-registry.json
and resolve its wall/floor/ceiling entries against the current house.json
shape. Pure Python; shared by check-study-surfaces.py, the refresh/interior
preflight checks, and (for now) nothing else -- see
docs/tasks/W03-C-surface-identities.md for what this deliberately does not do
yet (no UE mesh/material connection; that is W04).

Design: wall numbering/mesh names are not persistent (they shift with array
order and opening splits), so registry entries carry a manually-assigned ASCII
id and, for walls, the room polygon edge's endpoints (source coordinates,
metres) at the time the id was assigned. Resolution re-finds that edge in the
CURRENT polygon by endpoint coordinates (either order), never by nearest-edge
or partial overlap; floor/ceiling entries just track the room by roomId and
always resolve to its current polygon. Nothing here writes back to the
registry or invents a replacement wall -- ambiguous or missing matches are
reported as issues for a human to resolve by editing the registry.
"""
import html
import json
from pathlib import Path

SCHEMA='1.0.0'
ROOT=Path(__file__).resolve().parents[1]
EDGE_TOLERANCE=1e-6
REGISTRY_PATH='data/visual/surface-registry.json'
KINDS=('wall','floor','ceiling')


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def _point_close(a,b,tol=EDGE_TOLERANCE):
    return abs(a[0]-b[0])<=tol and abs(a[1]-b[1])<=tol


def _edge_close(a,b,tol=EDGE_TOLERANCE):
    """a,b: ((x0,z0),(x1,z1)). Endpoint order does not matter."""
    return (_point_close(a[0],b[0],tol) and _point_close(a[1],b[1],tol)) or \
           (_point_close(a[0],b[1],tol) and _point_close(a[1],b[0],tol))


def _room_edges(polygon):
    n=len(polygon)
    return [(tuple(polygon[i]),tuple(polygon[(i+1)%n])) for i in range(n)]


def validate_registry(registry):
    """Structural + duplicate checks only (no house.json cross-reference here
    -- that is resolve()'s job). Raises ValueError with a specific reason.
    Returns the surfaces list."""
    if not isinstance(registry,dict) or registry.get('schemaVersion')!=SCHEMA:
        raise ValueError('data/visual/surface-registry.json: unsupported or missing schemaVersion')
    surfaces=registry.get('surfaces')
    if not isinstance(surfaces,list):
        raise ValueError('data/visual/surface-registry.json: missing "surfaces" array')
    seen_ids=set(); wall_edges_by_room={}; floor_by_room={}; ceiling_by_room={}
    for s in surfaces:
        if not isinstance(s,dict): raise ValueError('surface-registry.json: entry is not an object')
        sid=s.get('id')
        if not isinstance(sid,str) or not sid or not sid.isascii():
            raise ValueError(f'surface-registry.json: invalid id {sid!r} (must be a non-empty ASCII string)')
        if sid in seen_ids: raise ValueError(f'surface-registry.json: duplicate id "{sid}"')
        seen_ids.add(sid)
        room_id=s.get('roomId')
        if not isinstance(room_id,str) or not room_id:
            raise ValueError(f'{sid}: missing roomId')
        kind=s.get('kind')
        if kind not in KINDS:
            raise ValueError(f'{sid}: kind must be one of {KINDS}, got {kind!r}')
        if kind=='wall':
            edge=s.get('edge')
            if not (isinstance(edge,list) and len(edge)==2 and all(
                    isinstance(p,list) and len(p)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in p)
                    for p in edge)):
                raise ValueError(f'{sid}: edge must be [[x0,z0],[x1,z1]]')
            edge_t=(tuple(edge[0]),tuple(edge[1]))
            claimed=wall_edges_by_room.setdefault(room_id,[])
            for other_id,other_edge in claimed:
                if _edge_close(edge_t,other_edge):
                    raise ValueError(f'{sid}: duplicate wall edge registration in room "{room_id}" (already registered as "{other_id}")')
            claimed.append((sid,edge_t))
        elif kind=='floor':
            if room_id in floor_by_room:
                raise ValueError(f'{sid}: duplicate floor registration in room "{room_id}" (already registered as "{floor_by_room[room_id]}")')
            floor_by_room[room_id]=sid
        else:
            if room_id in ceiling_by_room:
                raise ValueError(f'{sid}: duplicate ceiling registration in room "{room_id}" (already registered as "{ceiling_by_room[room_id]}")')
            ceiling_by_room[room_id]=sid
    return surfaces


def resolve(registry, rooms):
    """rooms: house.json's 'rooms' list (current shape). Never raises for a
    per-surface resolution failure -- those become issues; validate_registry's
    structural/duplicate errors still propagate (a malformed registry is not
    a per-surface issue, it is a hard stop)."""
    surfaces=validate_registry(registry)
    rooms_by_id={r['id']:r for r in rooms}
    resolved=[]; issues=[]
    for s in surfaces:
        sid=s['id']; room_id=s['roomId']; kind=s['kind']
        entry=dict(id=sid,roomId=room_id,kind=kind,label=s.get('label'),note=s.get('note'),status='unresolved')
        room=rooms_by_id.get(room_id)
        if room is None:
            issues.append(dict(id=sid,file=REGISTRY_PATH,
                reason=f'部屋{room_id}が現在のhouse.jsonにありません。',
                guidance=f'{sid}のroomIdを現在のIDへ更新するか、部屋が無くなった場合は登録を削除してください。'))
            if kind=='wall': entry['edge']=s['edge']
            resolved.append(entry); continue
        entry['roomStatus']=room.get('status'); entry['roomNote']=room.get('note')
        if kind=='wall':
            target=(tuple(s['edge'][0]),tuple(s['edge'][1]))
            matches=[e for e in _room_edges(room['polygon']) if _edge_close(target,e)]
            entry['edge']=s['edge']
            if not matches:
                issues.append(dict(id=sid,file=REGISTRY_PATH,
                    reason=f'登録された辺が部屋{room_id}の現在の形状に見つかりません（壁が移動または分割/結合された可能性があります）。',
                    guidance=f'{sid}のedgeを現在の辺の座標へ明示的に更新してください。同じ面として維持するならIDはそのまま、別の面になった場合は新しいIDを登録してください。'))
                resolved.append(entry); continue
            if len(matches)>1:
                issues.append(dict(id=sid,file=REGISTRY_PATH,
                    reason=f'登録された辺が部屋{room_id}の複数の現在の辺と一致し、曖昧です。',
                    guidance='house.jsonのpolygonに重複する辺がないか確認してください。'))
                resolved.append(entry); continue
            entry['status']='resolved'; entry['edge']=[list(matches[0][0]),list(matches[0][1])]
        else:
            entry['status']='resolved'; entry['polygon']=[list(p) for p in room['polygon']]
            if kind=='ceiling': entry['ceiling']=room.get('ceiling','flat')
        resolved.append(entry)
    return dict(schemaVersion=SCHEMA,surfaces=resolved,issues=issues)


def resolve_from(root):
    """root: a repo root (this worktree's ROOT for production use; a fixture
    root for tests). Raises ValueError if the registry is missing or
    malformed -- never returns an empty 'success' result for that."""
    registry_path=root/REGISTRY_PATH
    if not registry_path.is_file():
        raise ValueError(f'{REGISTRY_PATH} is missing')
    house_path=root/'data/house.json'
    if not house_path.is_file():
        raise ValueError('data/house.json is missing')
    return resolve(read(registry_path),read(house_path).get('rooms',[]))


def render_html(result):
    esc=lambda s:html.escape(str(s),quote=True) if s is not None else ''
    walls_by_room={}; floors=[]; ceilings=[]
    for s in result['surfaces']:
        if s['kind']=='wall': walls_by_room.setdefault(s['roomId'],[]).append(s)
        elif s['kind']=='floor': floors.append(s)
        else: ceilings.append(s)

    def plan_svg(room_id,walls):
        pad=0.3; scale=180
        xs=[p[0] for w in walls for p in w['edge']]; zs=[p[1] for w in walls for p in w['edge']]
        minx,maxx,minz,maxz=min(xs),max(xs),min(zs),max(zs)
        w=(maxx-minx+2*pad)*scale; h=(maxz-minz+2*pad)*scale
        sx=lambda x:(x-minx+pad)*scale; sz=lambda z:(z-minz+pad)*scale
        parts=[f'<svg width="{w:.0f}" height="{h:.0f}" style="background:#fff;border:1px solid #ccc">']
        for wsurf in walls:
            (x0,z0),(x1,z1)=wsurf['edge']
            color='#365d70' if wsurf['status']=='resolved' else '#c0392b'
            dash='' if wsurf['status']=='resolved' else ' stroke-dasharray="4 3"'
            parts.append(f'<line x1="{sx(x0):.1f}" y1="{sz(z0):.1f}" x2="{sx(x1):.1f}" y2="{sz(z1):.1f}" stroke="{color}" stroke-width="4"{dash}/>')
            mx,mz=sx((x0+x1)/2),sz((z0+z1)/2)
            parts.append(f'<text x="{mx:.1f}" y="{mz:.1f}" font-size="10" fill="{color}">{esc(wsurf["id"])}</text>')
        parts.append('</svg>')
        return f'<h3>{esc(room_id)}</h3>'+''.join(parts)

    def entity_row(s):
        status='resolved' if s['status']=='resolved' else '未解決'
        return f'<li>{esc(s["id"])}（{esc(s.get("label") or "")}）：{esc(status)}</li>'

    issues_html='<p>現在のところありません。</p>'
    if result['issues']:
        issues_html='<ul>'+''.join(f'<li>{esc(i["reason"])} {esc(i["guidance"])}</li>' for i in result['issues'])+'</ul>'

    svgs=''.join(plan_svg(rid,walls) for rid,walls in walls_by_room.items())
    floors_html='<ul>'+''.join(entity_row(f) for f in floors)+'</ul>' if floors else '<p>登録なし</p>'
    ceilings_html='<ul>'+''.join(entity_row(c) for c in ceilings)+'</ul>' if ceilings else '<p>登録なし</p>'

    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>面の永続ID</title><style>body{font:16px/1.8 system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#f5f3ef;color:#292722}'
        'svg{display:block;margin:8px 0}</style>'
        '<h1>面の永続ID</h1><p>W04が仕上げ設定の対象として参照するための識別・検証結果です。実メッシュへの接続・材質適用はまだ行っていません。</p>'
        '<h2>未解決・要修正</h2>'+issues_html
        +'<h2>壁（部屋境界面）</h2>'+svgs
        +'<h2>床</h2>'+floors_html+'<h2>天井</h2>'+ceilings_html+'</html>')
