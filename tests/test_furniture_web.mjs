// Exercise the viewer's real furniture functions with its bundled Three.js.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root = new URL('../', import.meta.url);
const html = fs.readFileSync(new URL('interior-white-model.html', root), 'utf8');
const source = (a,b) => html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const nodes = new Map();
let downloaded;
const furnitureStorage=new Map();
function fakeElement(tag='DIV'){
  return {tagName:tag.toUpperCase(),style:{},children:[],_value:'',
    appendChild(child){this.children.push(child);return child;},
    replaceChildren(...children){this.children=[...children];this._value='';},
    get options(){return this.children.flatMap(child=>child.tagName==='OPTGROUP'?child.children:[child]);},
    get value(){return this._value||this.options[0]?.value||'';},set value(value){this._value=value;},
    click(){},remove(){}};
}
const ctx = vm.createContext({console, Number, Math, Blob:class {constructor(parts){downloaded=JSON.parse(parts[0]);}},
  URL:{createObjectURL:()=>'',revokeObjectURL(){}},
  localStorage:{getItem:k=>furnitureStorage.get(k)||null,setItem(k,v){furnitureStorage.set(k,v);}},
  document:{getElementById(id){if(!nodes.has(id))nodes.set(id,fakeElement(id==='fbAddType'||id==='fbDeleted'?'SELECT':'DIV'));return nodes.get(id);},
    createElement:tag=>fakeElement(tag),body:{appendChild(){},removeChild(){}}}});
const run = code=>vm.runInContext(code,ctx);
run(fs.readFileSync(new URL('vendor/three.min.js',root),'utf8'));
run(fs.readFileSync(new URL('generated/house-data.js',root),'utf8'));
run(`const labels=[]; const groups={furniture1:new THREE.Group(),furniture2:new THREE.Group()};
  const toScene=(x,z)=>[x,z];
  function makeLabel(label,x,y,z){return {pos:new THREE.Vector3(x,y,z),div:{remove(){}}};}
  let editMode=true,selectedFurnitureId='fur-045';
  function setSelectedFurniture(id){selectedFurnitureId=id;updateFurniturePanel();}`);
run(source('const FURNITURE_BOX','// ---- 家具編集パネル'));
run(source('function pointInPolygon(', 'const ROOM_PROBE_OFFSET'));
run(source('function updateFurniturePanel()',"document.getElementById('fpClose')"));
run(source('const furnitureSegmentsByLevel','const PLAYER_RADIUS'));
for (const rotation of [0,90,180,270]) {
  run(`furnitureEdits['fur-045']={rotation:${rotation},elevation:1.2};rebuildFurnitureItem('fur-045');`);
  const actual=run(`(()=>{const holder=furnitureMeshes.get('fur-045').holder;
    holder.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(holder);
    return [box.min.y,box.max.y,box.getSize(new THREE.Vector3()).x,
      new THREE.Vector3(0,0,1).applyQuaternion(holder.quaternion).x];})()`);
  const expected=[1.907,2.557,rotation%180 ? .06:1.12,Math.sin(rotation*Math.PI/180)];
  actual.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<1e-6,`${rotation}: ${actual}`));
}
run(`applySizeEdit('elevation','0');exportFurnitureJSON();`);
assert.equal(downloaded.items.find(i=>i.id==='fur-045').elevation,undefined);
run(`applySizeEdit('elevation','1.25');exportFurnitureJSON();`);
const tv=downloaded.items.find(i=>i.id==='fur-045');
assert.equal(tv.elevation,1.25);
assert.equal(tv.status,'estimated');assert.ok(tv.note);
for (const input of ['-1','Infinity','NaN']) {
  run(`applySizeEdit('elevation',${JSON.stringify(input)});exportFurnitureJSON();`);
  assert.equal(downloaded.items.find(i=>i.id==='fur-045').elevation,1.25);
}
run(`resetSelected();exportFurnitureJSON();rebuildFurnitureSegments();`);
assert.equal(downloaded.items.find(i=>i.id==='fur-045').elevation,1);
const original=JSON.parse(fs.readFileSync(new URL('data/furniture.json',root),'utf8'));
assert.deepEqual(downloaded.items,original.items);
const before=run('furnitureSegmentsByLevel[1].length');
run(`furnitureEdits['fur-045']={elevation:2};rebuildFurnitureSegments();`);
assert.equal(run('furnitureSegmentsByLevel[1].length'),before-4);
run(`furnitureEdits['fur-045']={elevation:1,x:4};rebuildFurnitureSegments();`);
assert.ok(run('furnitureSegmentsByLevel[1].some(s=>Math.abs(s.from-3.97)<1e-8)'));
console.log('Furniture: bounds, four rotations, edit/export/reset, provenance, invalid inputs and collision refresh passed.');
for (const rotation of [0,90,180,270]) {
  run(`furnitureEdits['fur-011']={rotation:${rotation},width:2.1,depth:.9,height:.85,elevation:.2};rebuildFurnitureItem('fur-011');`);
  const actual=run(`(()=>{const holder=furnitureMeshes.get('fur-011').holder;
    holder.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(holder);
    return [box.min.y,box.max.y,box.getSize(new THREE.Vector3()).x,
      new THREE.Vector3(0,0,1).applyQuaternion(holder.quaternion).x];})()`);
  const expected=[.907,1.757,rotation%180 ? .9:2.1,Math.sin(rotation*Math.PI/180)];
  actual.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<1e-6,`sofa ${rotation}: ${actual}`));
}
console.log('Sofa: edited size, elevation and canonical front agree across four rotations.');
for(const [id,w,d,h] of [['fur-008',1.2,.8,.75],['fur-009',.6,.6,.95]]){
  for(const rotation of [0,90,180,270]){
    run(`furnitureEdits['${id}']={rotation:${rotation},width:${w},depth:${d},height:${h},elevation:.2};rebuildFurnitureItem('${id}');`);
    const actual=run(`(()=>{const holder=furnitureMeshes.get('${id}').holder;holder.updateMatrixWorld(true);
      const b=new THREE.Box3().setFromObject(holder);return [b.min.y,b.max.y,b.getSize(new THREE.Vector3()).x];})()`);
    const expected=[.907,.907+h,rotation%180?d:w];
    actual.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<1e-6,`${id} ${rotation}: ${actual}`));
  }
}
console.log('Dining: resized circular/elliptical table and chairs agree across four rotations.');
for(const [id,w,d,h] of [['fur-047',.6,.5,.6],['fur-048',.1,.18,.3],['fur-049',.8,.25,.3]]){
  for(const rotation of [0,90,180,270]){
    run(`furnitureEdits['${id}']={rotation:${rotation},width:${w},depth:${d},height:${h},elevation:1};rebuildFurnitureItem('${id}');`);
    const actual=run(`(()=>{const holder=furnitureMeshes.get('${id}').holder;holder.updateMatrixWorld(true);
      const b=new THREE.Box3().setFromObject(holder);return [b.min.y,b.max.y,b.getSize(new THREE.Vector3()).x];})()`);
    [1.707,1.707+h,rotation%180?d:w].forEach((v,i)=>assert.ok(Math.abs(v-actual[i])<1e-6,`${id}: ${actual}`));
  }
}
for(const id of ['fur-006','fur-007']){
  assert.equal(run(`FURNITURE_ITEMS.find(i=>i.id==='${id}').rotation`),270);
  assert.ok(run(`new THREE.Vector3(0,0,1).applyQuaternion(furnitureMeshes.get('${id}').holder.quaternion).x < -.99`));
}
console.log('Fixtures: height/bounds in four rotations; guest kitchen and refrigerator face west.');

for (const shape of ['raisedPlatform','mattress','sofaWorkTable']) {
  for (const [w,d,h] of [[1.8,1.8,.3],[.97,1.95,.2],[.8,.45,.65]]) {
    const actual=run(`(()=>{const g=new THREE.Group();FURNITURE_SHAPES['${shape}'](g,${w},${d},${h});
      const b=new THREE.Box3().setFromObject(g);return [b.min.y,b.max.y,b.getSize(new THREE.Vector3()).x,b.getSize(new THREE.Vector3()).z];})()`);
    [0,h,w,d].forEach((v,i)=>assert.ok(Math.abs(v-actual[i])<1e-6,`${shape}: ${actual}`));
  }
}
console.log('New platform, mattress and work table: editable outer dimensions and floor origin passed.');

for (const type of ['raised-platform','mattress','sofa-work-table']) {
  const id=run(`addCatalogFurniture('${type}','room-2f-04')`);
  assert.ok(id);
  run(`applySizeEdit('elevation','.3');exportFurnitureJSON();`);
  const item=downloaded.items.find(i=>i.id===id);
  assert.equal(item.type,type);assert.equal(item.room,'room-2f-04');assert.equal(item.elevation,.3);
  assert.equal(item.status,'estimated');assert.ok(item.note);
  assert.ok(JSON.parse(furnitureStorage.get('ryuka-furniture-added-v1')).some(i=>i.id===id));
  run(`furnitureEdits['${id}']={x:-100,z:-100};`);
  assert.throws(()=>run('exportFurnitureJSON()'),/部屋の外/);
  assert.ok(run(`removeAddedFurniture('${id}')`));
  run('exportFurnitureJSON()');assert.ok(!downloaded.items.some(i=>i.id===id));
}
console.log('New furniture: add in concave room, elevation, export/provenance, persistence, invalid placement and removal passed.');

const catalog=JSON.parse(fs.readFileSync(new URL('data/furniture-catalog.json',root),'utf8'));
run('populateFurnitureTypeOptions()');
const picker=nodes.get('fbAddType');
assert.deepEqual([...picker.options.map(option=>option.value)].sort(),catalog.types.map(type=>type.type).sort());
for(const group of picker.children){
  assert.equal(group.tagName,'OPTGROUP');
  const category=catalog.types.find(type=>type.type===group.children[0].value).category;
  assert.equal(group.label,catalog.categories[category].split('（')[0]);
  assert.ok(group.children.every(option=>catalog.types.find(type=>type.type===option.value).category===category));
}
run("populateFurnitureTypeOptions('sofa-work-table')");
assert.deepEqual(picker.options.map(option=>option.value),['sofa-work-table']);
run("populateFurnitureTypeOptions('見つからない家具')");
assert.equal(nodes.get('fbAdd').disabled,true);
run('populateFurnitureTypeOptions()');
assert.equal(nodes.get('fbAdd').disabled,false);
console.log('Catalog picker: every type once, category groups, search and empty results passed.');

run("setSelectedFurniture('fur-045');rebuildFurnitureSegments()");
const segmentsBefore=run('furnitureSegmentsByLevel[1].length');
assert.equal(run('deleteSelectedFurniture()'),true);
assert.equal(run("furnitureMeshes.has('fur-045')"),false);
assert.ok(JSON.parse(furnitureStorage.get('ryuka-furniture-deleted-v1')).includes('fur-045'));
run('exportFurnitureJSON();rebuildFurnitureSegments()');
assert.equal(downloaded.items.some(item=>item.id==='fur-045'),false);
assert.equal(run('furnitureSegmentsByLevel[1].length'),segmentsBefore-4);
assert.equal(nodes.get('fbDeleted').value,'fur-045');
assert.equal(run("restoreDeletedFurniture('fur-045')"),true);
run('exportFurnitureJSON()');
assert.equal(downloaded.items.some(item=>item.id==='fur-045'),true);
assert.equal(run('furnitureSegmentsByLevel[1].length'),segmentsBefore);

const addedId=run("addCatalogFurniture('chair-timber','room-2f-04')");
assert.ok(addedId);
assert.equal(run('deleteSelectedFurniture()'),true);
run('exportFurnitureJSON()');
assert.equal(downloaded.items.some(item=>item.id===addedId),false);
console.log('Deletion: source and added furniture, export, collision, persistence and restore passed.');

// New closet types must also work when added later, without per-ID asset bindings.
for(const type of ['closet-single','closet-double','closet-box-shelf','closet-drawers','closet-mirror','storage-box']){
  const cat=catalog.types.find(t=>t.type===type);
  for(const rotation of [0,90,180,270]){
    const actual=run(`(()=>{const g=new THREE.Group();FURNITURE_SHAPES[${JSON.stringify(cat.shape)}](g,${cat.width},${cat.depth},${cat.height});
      g.rotation.y=${rotation}*Math.PI/180;g.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(g);return [b.getSize(new THREE.Vector3()).x,b.getSize(new THREE.Vector3()).y,b.getSize(new THREE.Vector3()).z];})()`);
    const expected=[rotation%180?cat.depth:cat.width,cat.height,rotation%180?cat.width:cat.depth];
    actual.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<.004,`${type} ${rotation}: ${actual}`));
  }
}
run(`setSelectedFurniture('fur-cloak-03');`);
nodes.get('fpRails').value='0.9, 1.8';nodes.get('fpContents').checked=false;
run('applyStorageEdit();exportFurnitureJSON()');
assert.deepEqual(downloaded.items.find(i=>i.id==='fur-cloak-03').storage,{railHeights:[.9,1.8],contents:false});
nodes.get('fpRails').value='1.8, 0.9';run('applyStorageEdit();exportFurnitureJSON()');
assert.deepEqual(downloaded.items.find(i=>i.id==='fur-cloak-03').storage.railHeights,[.9,1.8]);
assert.ok(nodes.get('fpStorageError').textContent);
run('resetSelected();exportFurnitureJSON()');
assert.deepEqual(downloaded.items.find(i=>i.id==='fur-cloak-03').storage.railHeights,[.85,1.65]);

// Compare actual part recipes from both renderers (including edited rail/shelf heights).
const {spawnSync}=await import('node:child_process');
const cases=catalog.types.filter(t=>run('STORAGE_SHAPES').includes(t.shape)).map(t=>[t.shape,t.width,t.depth,t.height,{}]);
cases.push(['closetDouble',1,.6,2.2,{railHeights:[.9,1.8],contents:false}],['closetShelves',1.1,.45,2.2,{shelfHeights:[.1,.49,.88,1.27,1.66,2.05],contents:true}]);
const py=spawnSync('python',['-c',`import sys,json;sys.path.insert(0,'blender');from storage_assets import storage_parts;print(json.dumps([storage_parts(*a) for a in json.load(sys.stdin)]))`],{cwd:new URL('..',import.meta.url),input:JSON.stringify(cases),encoding:'utf8'});
assert.equal(py.status,0,py.stderr);
const pythonParts=JSON.parse(py.stdout);
cases.forEach((args,i)=>{
  const actual=run(`storageParts(...${JSON.stringify(args)})`);
  assert.equal(actual.length,pythonParts[i].length);
  actual.forEach((part,j)=>{
    assert.equal(part.name,pythonParts[i][j].name);assert.equal(part.kind,pythonParts[i][j].kind);
    part.bounds.forEach((v,k)=>assert.ok(Math.abs(v-pythonParts[i][j].bounds[k])<1e-9));
  });
});
console.log('Closet: six types/four rotations, configuration edit/export/reset/rejection, JS-Python part parity passed.');

// 2026-09-17 脱衣室の造作（カウンター・壁付け棚・物干しバー）も、収納家具と同じく
// ブラウザとBlenderの部品レシピが一致することを機械確認する。寸法範囲外は両者とも拒否する。
const laundryCases=catalog.types.filter(t=>run('LAUNDRY_SHAPES').includes(t.shape)).map(t=>[t.shape,t.width,t.depth,t.height]);
assert.equal(laundryCases.length,4,'catalog should carry all four laundry fittings');
const pyLaundry=spawnSync('python',['-c',`import sys,json;sys.path.insert(0,'blender');from laundry_assets import laundry_parts;print(json.dumps([laundry_parts(*a) for a in json.load(sys.stdin)]))`],{cwd:new URL('..',import.meta.url),input:JSON.stringify(laundryCases),encoding:'utf8'});
assert.equal(pyLaundry.status,0,pyLaundry.stderr);
const laundryPython=JSON.parse(pyLaundry.stdout);
laundryCases.forEach((args,i)=>{
  const actual=run(`laundryParts(...${JSON.stringify(args)})`);
  assert.equal(actual.length,laundryPython[i].length);
  actual.forEach((part,j)=>{
    assert.equal(part.name,laundryPython[i][j].name);
    assert.equal(part.material,laundryPython[i][j].material);
    part.bounds.forEach((v,k)=>assert.ok(Math.abs(v-laundryPython[i][j].bounds[k])<1e-9,`${part.name} bound ${k}`));
  });
});
assert.throws(()=>run(`laundryParts('laundryCounter',3,.55,.85)`),/対応範囲外/);
assert.throws(()=>run(`laundryParts('laundryRack',1.2,.35,.5)`),/対応範囲外/);
console.log('Laundry fittings: catalog dimensions render and match the Blender part recipe; out-of-range rejected.');

// 2026-09-17 玄関・土間の造作（ウォールハンガー・壁付け板棚の靴棚）も同じ方式で検証する。
const entryCases=catalog.types.filter(t=>run('ENTRY_SHAPES').includes(t.shape)).map(t=>[t.shape,t.width,t.depth,t.height]);
assert.equal(entryCases.length,2,'catalog should carry the wall hook rail and the wall plank shelf');
const pyEntry=spawnSync('python',['-c',`import sys,json;sys.path.insert(0,'blender');from entry_assets import entry_parts;print(json.dumps([entry_parts(*a) for a in json.load(sys.stdin)]))`],{cwd:new URL('..',import.meta.url),input:JSON.stringify(entryCases),encoding:'utf8'});
assert.equal(pyEntry.status,0,pyEntry.stderr);
const entryPython=JSON.parse(pyEntry.stdout);
entryCases.forEach((args,i)=>{
  const actual=run(`entryParts(...${JSON.stringify(args)})`);
  assert.equal(actual.length,entryPython[i].length);
  actual.forEach((part,j)=>{
    assert.equal(part.name,entryPython[i][j].name);
    assert.equal(part.material,entryPython[i][j].material);
    part.bounds.forEach((v,k)=>assert.ok(Math.abs(v-entryPython[i][j].bounds[k])<1e-9,`${part.name} bound ${k}`));
  });
});
assert.equal(run(`entryPegCount(.6)`),5);assert.equal(run(`entryPegCount(1.5)`),8);
assert.throws(()=>run(`entryParts('wallHookRail',2,.1,.12)`),/対応範囲外/);
// フック先端が腕より上にあること（上向き＝J形。下向きに戻る回帰を防ぐ）。
{
  const parts=run(`entryParts('wallHookRail',.6,.1,.12)`);
  const arm=parts.find(p=>p.name==='peg-0-arm'), tip=parts.find(p=>p.name==='peg-0-tip');
  assert.ok(tip.bounds[4]>=arm.bounds[5]-1e-9, 'hook tip must sit at or above the arm top, not below it');
}
// 壁付け板棚：段数と、各棚板がwidth/depth/heightの範囲に収まること。
{
  const parts=run(`entryParts('wallPlankShelf',1.4,.3,1.42)`);
  const planks=parts.filter(p=>p.name.startsWith('plank-'));
  assert.equal(planks.length,5,'5 planks at .28 pitch should fit within height 1.42');
  const rails=parts.filter(p=>p.name.startsWith('rail-'));
  assert.equal(rails.length,2);
  for(const p of parts){
    const [x0,x1,z0,z1,y0,y1]=p.bounds;
    assert.ok(x0>=-.7-1e-9 && x1<=.7+1e-9 && z0>=-.15-1e-9 && z1<=.15+1e-9 && y0>=-1e-9 && y1<=1.42+1e-9, p.name);
  }
}
assert.throws(()=>run(`entryParts('wallPlankShelf',2.5,.3,1.42)`),/対応範囲外/);
console.log('Entry fittings (wall hook rail / wall plank shelf): catalog dimensions render and match the Blender part recipe; hook faces up; out-of-range rejected.');

// W08-H回帰: 範囲外の幅・奥行き・高さを持つ家具が1件混ざっていても、placeFurnitureItemの
// forEachループ全体が止まらず、その1件だけスキップされること（黒画面バグの再発防止。
// 実際に土間(room-1f-09)以外の部屋へ追加されたwallPlankShelfのdepthOverrideが0.15mまで
// 縮められ、対応範囲(0.22-0.4m)を外れて起きた）。
{
  const badItem={id:'test-bad-shape-dims',type:'wall-plank-shelf',room:'room-1f-09',level:1,
    x:11.69,z:2.12,rotation:180,width:.85,depth:.15,height:1,elevation:0};
  assert.doesNotThrow(()=>run(`placeFurnitureItem(${JSON.stringify(badItem)})`),
    'an out-of-range item must not crash the whole furniture build loop');
  assert.equal(run(`furnitureMeshes.has('test-bad-shape-dims')`),false,
    'the out-of-range item itself must be skipped (not added), while everything else keeps rendering');
}
console.log('Fault isolation: an out-of-range item is skipped instead of crashing furniture placement.');

// W08-H回帰: applySizeEditの保存前チェックは元々STORAGE_SHAPESにしか効いておらず、
// wallPlankShelf(ENTRY_SHAPES)のdepthをUI上で0.22m未満へ縮めても保存できてしまい
// (furnitureEdits/エクスポートJSONに残り)、次回の再読み込みで初めて上のフォルトアイソ
// レーションに引っかかっていた。保存する前にfpStorageErrorへ表示して弾くこと。
run(`setSelectedFurniture('fur-entry-03');`);
nodes.get('fpStorageError').textContent='';
run(`applySizeEdit('depth','.15');`);
assert.ok(nodes.get('fpStorageError').textContent.includes('対応範囲外'),
  'an out-of-range depth edit on a wallPlankShelf item must be rejected with an error message before saving');
assert.equal(run(`furnitureEdits['fur-entry-03']?.depth`),undefined,
  'the rejected depth must not be saved into furnitureEdits');
run(`applySizeEdit('depth','.3');`);
assert.equal(run(`furnitureEdits['fur-entry-03'].depth`),.3,'a subsequent valid edit must still be accepted');
run(`resetSelected();`);
console.log('Size-edit panel: out-of-range wall-plank-shelf depth rejected before saving; valid edit still accepted.');
