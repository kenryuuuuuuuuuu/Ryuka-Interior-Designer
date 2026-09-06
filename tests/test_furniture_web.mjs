// Exercise the viewer's real furniture functions with its bundled Three.js.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root = new URL('../', import.meta.url);
const html = fs.readFileSync(new URL('interior-white-model.html', root), 'utf8');
const source = (a,b) => html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const nodes = new Map();
let downloaded;
const ctx = vm.createContext({console, Number, Math, Blob:class {constructor(parts){downloaded=JSON.parse(parts[0]);}},
  URL:{createObjectURL:()=>'',revokeObjectURL(){}},
  localStorage:{getItem:()=>null,setItem(){}},
  document:{getElementById(id){if(!nodes.has(id))nodes.set(id,{style:{}});return nodes.get(id);},
    createElement:()=>({click(){}}),body:{appendChild(){},removeChild(){}}}});
const run = code=>vm.runInContext(code,ctx);
run(fs.readFileSync(new URL('vendor/three.min.js',root),'utf8'));
run(fs.readFileSync(new URL('generated/house-data.js',root),'utf8'));
run(`const labels=[]; const groups={furniture1:new THREE.Group(),furniture2:new THREE.Group()};
  const toScene=(x,z)=>[x,z];
  function makeLabel(label,x,y,z){return {pos:new THREE.Vector3(x,y,z),div:{remove(){}}};}
  let editMode=true,selectedFurnitureId='fur-045';
  function setSelectedFurniture(id){selectedFurnitureId=id;updateFurniturePanel();}`);
run(source('const FURNITURE_BOX','// ---- 家具編集パネル'));
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
