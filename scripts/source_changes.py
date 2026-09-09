"""Compare a previously generated package's frozen inputs (SourcePackage/) against
the current source, and check the current source's cross-file references --
before any Blender/Unreal generation starts. Pure Python; shared by the
standalone CLI (check-study-changes.py) and refresh-visual-study.py.

Scope is deliberately narrow (see docs/tasks/W03-B-source-changes.md): rooms,
furniture placements, and the furniture catalog for change tracking; a fixed
list of cross-file references for the current source. This is not a general
change-detection or reference-graph system.
"""
import hashlib
import html
import json
from pathlib import Path

SCHEMA='1.0.0'
ROOT=Path(__file__).resolve().parents[1]

SCOPE_NOTE=('この比較はrooms/furniture/furniture-catalogの追加・削除・変更と、'
    '下記の限定した参照先の有無だけを対象にしています。屋根・階段・設備・開口全体の変更検出は含みません。')

# (relative path, extractor(doc)->list[dict], key field, field->category groups, label field)
ROOM_GROUPS=[('形状・階・天井',{'polygon','level','ceiling'}),('名称・注記',{'label','note','status'})]
FURNITURE_GROUPS=[('配置',{'x','z','rotation','elevation','room','level'}),('型・寸法',{'type'}),('名称・注記',{'label','note','status'})]
CATALOG_GROUPS=[('型・寸法',{'width','depth','height','shape','category','rotationConvention','clearance'}),('名称・注記',{'label','note'})]
# W06-v1 review R4: track data/visual/lighting-settings.json's profiles/groups
# too (the settings an operator actually edits), same shallow keyed-diff
# treatment as the targets above -- NOT data/electrical.json's full fixture
# placement list (145 items; reviewer confirmed that detailed a diff is not
# required: "電気設備全項目の詳細な差分UIは不要").
LIGHTING_PROFILE_GROUPS=[('光学値',{'source','lumens','temperatureK','spotAngleDeg','directionLocal'}),('状態・注記',{'status','note'})]
LIGHTING_GROUP_GROUPS=[('構成',{'fixtureIds'}),('名称',{'label'})]

TARGETS={
    'rooms':            ('data/house.json',                    lambda d:d.get('rooms',[]),   'id',   ROOM_GROUPS,             'label'),
    'furniture':        ('data/furniture.json',                 lambda d:d.get('items',[]),   'id',   FURNITURE_GROUPS,        'label'),
    'catalog':          ('data/furniture-catalog.json',         lambda d:d.get('types',[]),   'type', CATALOG_GROUPS,          'label'),
    'lightingProfiles': ('data/visual/lighting-settings.json',  lambda d:[dict(type=k,**v) for k,v in d.get('profiles',{}).items()], 'type', LIGHTING_PROFILE_GROUPS, 'type'),
    'lightingGroups':   ('data/visual/lighting-settings.json',  lambda d:d.get('groups',[]),  'id',   LIGHTING_GROUP_GROUPS,   'label'),
}


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def content_sha(path): return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def classify(field,groups):
    for name,fields in groups:
        if field in fields: return name
    return 'その他'


def _index(records,key,which):
    result={}
    for record in records:
        k=record.get(key)
        if k in result:
            raise ValueError(f'{which} data has duplicate {key} "{k}"')
        result[k]=record
    return result


def diff_keyed(before_list,after_list,key,groups,label_field):
    """Added/removed/modified by key; raises ValueError on a duplicate key on
    either side rather than silently overwriting it (dict-indexing would)."""
    before=_index(before_list,key,'Previous')
    after=_index(after_list,key,'Current')
    added=[dict(id=k,label=after[k].get(label_field),record=after[k]) for k in sorted(set(after)-set(before))]
    removed=[dict(id=k,label=before[k].get(label_field),record=before[k]) for k in sorted(set(before)-set(after))]
    modified=[]
    for k in sorted(set(before)&set(after)):
        b,a=before[k],after[k]
        if b==a: continue
        fields=[]
        for field in sorted(set(b)|set(a)):
            bp=field in b; ap=field in a
            if bp and ap and b[field]==a[field]: continue
            fields.append(dict(field=field,category=classify(field,groups),
                beforePresent=bp,afterPresent=ap,
                before=b.get(field) if bp else None,after=a.get(field) if ap else None))
        if fields: modified.append(dict(id=k,label=a.get(label_field,b.get(label_field)),fields=fields))
    return dict(added=added,removed=removed,modified=modified)


def attach_catalog_usage(catalog_diff,current_furniture_items):
    """For each changed/removed catalog type, list current furniture IDs that
    reference it -- 'candidate impact', not a recomputed/confirmed dimension
    change (per-item overrides are not analysed)."""
    by_type={}
    for item in current_furniture_items:
        by_type.setdefault(item.get('type'),[]).append(item.get('id'))
    for entry in catalog_diff['modified']+catalog_diff['removed']:
        entry['affectedFurnitureIds']=sorted(by_type.get(entry['id'],[]))
    return catalog_diff


def check_references(root):
    """Reference checks against the CURRENT source only (root/data/...). Lets
    exceptions from unreadable/malformed required current files propagate --
    those are hard stops, not something to report as a soft issue."""
    house=read(root/'data/house.json')
    furniture=read(root/'data/furniture.json')
    catalog=read(root/'data/furniture-catalog.json')
    study=read(root/'data/visual/guest-ldk-study.json')
    bindings=read(root/'data/visual/asset-bindings.json')
    decor=read(root/'data/visual/guest-decor.json')
    openings=read(root/'data/openings.json')

    issues=[]
    def dup(records,key,source_file):
        seen=set()
        for r in records:
            k=r.get(key)
            if k in seen:
                issues.append(dict(code='duplicate-id',sourceFile=source_file,sourceId=k,field=key,targetId=None,
                    message=f'{source_file}に{key} "{k}" が複数あります。'))
            seen.add(k)
        return seen

    room_ids=dup(house.get('rooms',[]),'id','data/house.json')
    furniture_ids=dup(furniture.get('items',[]),'id','data/furniture.json')
    catalog_types=dup(catalog.get('types',[]),'type','data/furniture-catalog.json')

    def missing(source_file,source_id,field,target,target_ids,message):
        if target is not None and target not in target_ids:
            issues.append(dict(code='missing-reference',sourceFile=source_file,sourceId=source_id,field=field,targetId=target,message=message))

    for item in furniture.get('items',[]):
        fid=item.get('id')
        missing('data/furniture.json',fid,'room',item.get('room'),room_ids,
            f'家具{fid}が参照する部屋{item.get("room")}がありません。furniture.jsonの配置を確認してください。')
        missing('data/furniture.json',fid,'type',item.get('type'),catalog_types,
            f'家具{fid}が参照する型{item.get("type")}がありません。furniture-catalog.jsonを確認してください。')

    missing('data/visual/guest-ldk-study.json',None,'roomId',study.get('roomId'),room_ids,
        f'guest-ldk-study.jsonが参照する部屋{study.get("roomId")}がありません。')

    for b in bindings.get('bindings',[]):
        missing('data/visual/asset-bindings.json',b.get('assetId'),'furnitureId',b.get('furnitureId'),furniture_ids,
            f'asset-bindings.jsonの{b.get("assetId")}が参照する家具{b.get("furnitureId")}がありません。asset-bindings.jsonの設定を確認してください。')

    missing('data/visual/guest-decor.json',None,'roomId',decor.get('roomId'),room_ids,
        f'guest-decor.jsonが参照する部屋{decor.get("roomId")}がありません。')
    opening_ids={o.get('id') for o in openings.get('items',[])}
    for it in decor.get('items',[]):
        did=it.get('id')
        if 'furnitureId' in it:
            missing('data/visual/guest-decor.json',did,'furnitureId',it.get('furnitureId'),furniture_ids,
                f'{did}が参照する家具{it.get("furnitureId")}がありません。guest-decor.jsonの設定を確認してください。')
        if 'openingId' in it:
            missing('data/visual/guest-decor.json',did,'openingId',it.get('openingId'),opening_ids,
                f'{did}が参照する開口{it.get("openingId")}がありません。guest-decor.jsonの設定を確認してください。')
    return issues


def compare(previous, root=None):
    """previous: Path to a previously generated UE project directory (has
    SourcePackage/). root: current repo root (defaults to this worktree's
    ROOT; refresh-visual-study.py always uses the real one -- --current-data
    overrides are for the standalone CLI's own testing only)."""
    root=root or ROOT
    result=dict(schemaVersion=SCHEMA,comparisonBasis='previous-package-to-current-source',
        baselineStatus='available',comparedFiles={})
    manifest_path=previous/'SourcePackage/manifest.json'
    source_hashes={}
    try:
        manifest=read(manifest_path)
        source_hashes=manifest.get('sourceHashes',{})
        for name,(relpath,extract,key,groups,label_field) in TARGETS.items():
            snapshot=previous/'SourcePackage/inputs'/relpath
            expected=source_hashes.get(relpath)
            if not snapshot.is_file() or expected is None:
                raise ValueError(f'Previous package has no usable snapshot of {relpath}')
            if content_sha(snapshot)!=expected:
                raise ValueError(f'Previous snapshot of {relpath} does not match its recorded hash')
    except Exception as error:
        result['baselineStatus']='unavailable'
        result['baselineReason']=str(error)

    warnings=[SCOPE_NOTE]
    if result['baselineStatus']=='available':
        for name,(relpath,extract,key,groups,label_field) in TARGETS.items():
            before_path=previous/'SourcePackage/inputs'/relpath
            after_path=root/relpath
            result['comparedFiles'][relpath]=dict(previousSHA256=content_sha(before_path),currentSHA256=content_sha(after_path))
            try:
                diff=diff_keyed(extract(read(before_path)),extract(read(after_path)),key,groups,label_field)
            except ValueError as error:
                result[name]=None
                warnings.append(f'{relpath}: {error}; この対象の差分は算出していません。')
                continue
            if name=='catalog': diff=attach_catalog_usage(diff,read(root/'data/furniture.json').get('items',[]))
            result[name]=diff
    else:
        for name in TARGETS: result[name]=None
        warnings.append(result['baselineReason']+'（詳細比較できません。現在の全件を追加扱いにはしていません。）')

    result['issues']=check_references(root)
    result['warnings']=warnings
    return result


def summarize(changes):
    def counts(diff):
        if diff is None: return None
        return dict(added=len(diff['added']),removed=len(diff['removed']),modified=len(diff['modified']))
    return dict(rooms=counts(changes.get('rooms')),furniture=counts(changes.get('furniture')),
        catalog=counts(changes.get('catalog')),lightingProfiles=counts(changes.get('lightingProfiles')),
        lightingGroups=counts(changes.get('lightingGroups')),issueCount=len(changes['issues']))


def render_html(changes):
    esc=lambda s:html.escape(str(s),quote=True)
    def field_row(f):
        before='(なし)' if not f['beforePresent'] else esc(f['before'])
        after='(なし)' if not f['afterPresent'] else esc(f['after'])
        return f'<li><b>{esc(f["field"])}</b>（{esc(f["category"])}）：{before} → {after}</li>'
    def entity_section(title,diff):
        if diff is None: return f'<h3>{esc(title)}</h3><p>比較元データがないため詳細比較できません。</p>'
        parts=[f'<h3>{esc(title)}（追加{len(diff["added"])}・削除{len(diff["removed"])}・変更{len(diff["modified"])}）</h3>']
        if diff['added']:
            parts.append('<p>追加：</p><ul>'+''.join(f'<li>{esc(a["id"])}（{esc(a.get("label") or "")}）</li>' for a in diff['added'])+'</ul>')
        if diff['removed']:
            parts.append('<p>削除：</p><ul>'+''.join(f'<li>{esc(r["id"])}（{esc(r.get("label") or "")}）</li>' for r in diff['removed'])+'</ul>')
        for m in diff['modified']:
            parts.append(f'<details><summary>変更：{esc(m["id"])}（{esc(m.get("label") or "")}）</summary><ul>'
                +''.join(field_row(f) for f in m['fields'])+'</ul></details>')
        for entry in diff.get('modified',[])+diff.get('removed',[]):
            if entry.get('affectedFurnitureIds'):
                parts.append(f'<p>{esc(entry["id"])}を参照する家具：{esc(", ".join(entry["affectedFurnitureIds"]))}（影響候補、個別上書きは未解析）</p>')
        return ''.join(parts)
    issues_html=''
    if changes['issues']:
        issues_html='<h2>参照切れ・重複（要修正）</h2><ul>'+''.join(f'<li>{esc(i["message"])}</li>' for i in changes['issues'])+'</ul>'
    else:
        issues_html='<h2>参照切れ・重複</h2><p>現在のところありません。</p>'
    baseline_html=''
    if changes['baselineStatus']!='available':
        baseline_html=f'<p><b>前回モデルとの詳細比較：</b>{esc(changes.get("baselineReason",""))}</p>'
    warnings_html='<ul>'+''.join(f'<li>{esc(w)}</li>' for w in changes['warnings'])+'</ul>'
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>前回モデルからの変更</title><style>body{font:16px/1.8 system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#f5f3ef;color:#292722}'
        'details{margin:6px 0}summary{cursor:pointer}</style>'
        '<h1>前回モデルからの変更</h1>'+baseline_html+issues_html
        +entity_section('部屋',changes.get('rooms'))+entity_section('家具',changes.get('furniture'))+entity_section('家具カタログ',changes.get('catalog'))
        +entity_section('照明プロファイル',changes.get('lightingProfiles'))+entity_section('照明グループ',changes.get('lightingGroups'))
        +'<h2>注意</h2>'+warnings_html+'</html>')
