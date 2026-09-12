import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url);
const html=fs.readFileSync(new URL('interior-white-model.html',root),'utf8');
const slice=(a,b)=>html.slice(html.indexOf(a),html.indexOf(b,html.indexOf(a)));
const ctx=vm.createContext({console,document:{createElement:()=>({width:0,height:0,getContext:()=>({fillRect(){},strokeRect(){}})})}});
const run=code=>vm.runInContext(code,ctx);
run(fs.readFileSync(new URL('vendor/three.min.js',root),'utf8'));
run(fs.readFileSync(new URL('generated/house-data.js',root),'utf8'));
run(`const groups={floor1:new THREE.Group()}; const M1={floorSlab:new THREE.MeshBasicMaterial()}; const toScene=(x,z)=>[x,z];`);
run(slice('function pointInPolygon(', 'const ROOM_PROBE_OFFSET'));
run(slice('function clipFloorPolygon(', '// ---- 2F床スラブ'));
const area=geometry=>{
 const pos=geometry.getAttribute('position'),ix=geometry.index;
 let total=0;for(let i=0;i<(ix?ix.count:pos.count);i+=3){
  const a=ix?ix.getX(i):i,b=ix?ix.getX(i+1):i+1,c=ix?ix.getX(i+2):i+2;
  total+=Math.abs((pos.getX(b)-pos.getX(a))*(pos.getY(c)-pos.getY(a))-
    (pos.getY(b)-pos.getY(a))*(pos.getX(c)-pos.getX(a)))/2;
 }return total;
};
const result=run(`(()=>{
 const high=groups.floor1.children.filter(m=>m.material===M1.floorSlab);
 const low=groups.floor1.children.filter(m=>m.material===tileFloorMat);
 return {high:high.reduce((n,m)=>n+(${area.toString()})(m.geometry),0),
 low:low.reduce((n,m)=>n+(${area.toString()})(m.geometry),0),count:low.length};})()`);
const source=JSON.parse(fs.readFileSync(new URL('data/house.json',root),'utf8'));
const rectangleArea=source.footprints.filter(f=>f.level===1).reduce((sum,f)=>sum+(f.x1-f.x0)*(f.z1-f.z0),0);
const polyArea=pts=>Math.abs(pts.reduce((sum,p,i)=>{const q=pts[(i+1)%pts.length];return sum+p[0]*q[1]-p[1]*q[0]},0))/2;
const lowered=source.rooms.filter(r=>r.floorOffsetM<0);
assert.equal(result.count,4);
assert.ok(Math.abs(result.low-lowered.reduce((n,r)=>n+polyArea(r.polygon),0))<1e-5,result.low);
assert.ok(Math.abs(result.high+result.low-rectangleArea)<1e-5,[result.high,result.low,rectangleArea]);
run(`let walkLevel=1;let walkPos={x:1.5,z:1.2};const stairProgressAt=()=>null;`);
run(slice('function currentWalkY(){','function updateWalkCamera(){'));
assert.ok(Math.abs(run('currentWalkY()')-(source.levels.fl1-.1))<1e-6);
run('walkPos={x:1.5,z:2.2}');assert.ok(Math.abs(run('currentWalkY()')-source.levels.fl1)<1e-6);
console.log('Four tile planes, exact floor area partition, and walk-height transition passed.');
