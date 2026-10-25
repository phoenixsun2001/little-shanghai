import test from 'node:test';
import assert from 'node:assert/strict';
import {FlightController,distance,destination,bearing,routes} from '../dist/flight.js';
import {gcjToWgs84} from '../dist/coordinates.js';
const point=[121.49503,31.24191];
test('movement uses correct distance and heading in Shanghai',()=>{
 for(const h of [0,45,90,180,270,359]){const end=destination(point,h,1000);assert.ok(Math.abs(distance(point,end)-1000)<1e-5);assert.ok(Math.abs(((bearing(point,end)-h+540)%360)-180)<1e-6);}
});
test('reference coordinates align to WGS84 rather than shifting landmarks',()=>{
 const wgs=gcjToWgs84([121.49981,31.23967]);assert.ok(distance(wgs,point)<100);assert.ok(distance([121.49981,31.23967],point)>400);
});
test('all four sightseeing routes loop and stay in the Shanghai region',()=>{
 assert.equal(Object.keys(routes).length,4);
 for(const r of Object.values(routes)){assert.deepEqual(r.points[0],r.points.at(-1));assert.ok(r.points.length>=8);assert.ok(r.points.every(p=>p[0]>120.8&&p[0]<122.25&&p[1]>30.62&&p[1]<31.95));}
});
test('flight travels at the selected speed, pauses, resumes and accepts manual control',()=>{
 globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
 const map={stop(){},jumpTo(){},setCenter(){},triggerRepaint(){},getBearing:()=>-25,getPitch:()=>52};
 const f=new FlightController({map,city:{},onToast(){}});
 f.start(point);f.tick(1000);const start=[...f.position];f.tick(1080);assert.ok(Math.abs(distance(start,f.position)-4)<.001);
 f.pause();const paused=[...f.position];f.tick(1160);assert.deepEqual(paused,f.position);f.pause();f.tick(1240);assert.ok(distance(paused,f.position)>3.9);
 f.setRoute('river');assert.equal(f.route.name,'一江两岸');f.keys.add('ArrowLeft');f.tick(1320);assert.equal(f.route,null);f.stop(false);assert.equal(f.active,false);assert.equal(f.city.flight,null);
});
test('tree placement accepts polygon parks and skips point and line source features',async()=>{
 const {collectTrees}=await import('../dist/city.js');
 const map={getZoom:()=>15.5,getLayer:()=>true,getCenter:()=>({lng:121.5,lat:31.24}),queryRenderedFeatures:()=>[
  {geometry:{type:'Point',coordinates:[121.5,31.24]}},
  {geometry:{type:'LineString',coordinates:[[121.5,31.24],[121.501,31.24]]}},
  {geometry:{type:'Polygon',coordinates:[[[121.499,31.239],[121.501,31.239],[121.501,31.241],[121.499,31.241],[121.499,31.239]]]}}
 ]};
 const trees=collectTrees(map);assert.ok(trees.length>10);assert.ok(trees.length<=1000);assert.ok(trees.every(p=>p.every(Number.isFinite)));
});
