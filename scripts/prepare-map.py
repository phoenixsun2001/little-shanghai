import json, math
from pathlib import Path
out=Path('dist/data')
s=json.load(open(Path(__file__).with_name('openfreemap-base-style.json')))
keep=[]
for l in s['layers']:
    id=l['id']; typ=l['type']; p=l.setdefault('paint',{})
    if typ=='symbol':
        if id not in ['highway-name-major','highway-name-minor','water_name_line_label','water_name_point_label','label_city','label_town','label_village','label_other']: continue
        lo=l.setdefault('layout',{}); lo.pop('icon-image',None); lo.pop('icon-size',None); lo.pop('icon-optional',None)
        lo['text-field']=['coalesce',['get','name:zh'],['get','name']]; lo['text-font']=['Noto Sans Regular']; lo['text-size']=11 if 'highway' in id else 13
        p['text-color']='#58675d'; p['text-halo-color']='#f3f0df'; p['text-halo-width']=1.5
        l['metadata']={'labels':True}
        if 'highway' in id: l['minzoom']=15.5
    elif id=='natural_earth': continue
    elif typ=='background':p['background-color']='#e5e6d2'
    elif id=='building':
        p['fill-color']='#cec4a6';p['fill-opacity']=0.7
    elif id=='building-3d':
        l['minzoom']=13.5
        l['filter']=['!=',['get','hide_3d'],True]
        p={'fill-extrusion-base':['coalesce',['get','render_min_height'],0],'fill-extrusion-height':['max',7,['coalesce',['get','render_height'],9]],'fill-extrusion-color':['step',['coalesce',['get','render_height'],9],'#c07858',14,'#c5b49a',26,'#ddd7c1',55,'#a7b9b5',110,'#b5c6c4',220,'#c7d2cb'],'fill-extrusion-opacity':1,'fill-extrusion-vertical-gradient':True};l['paint']=p
    elif typ=='fill':
        p.pop('fill-pattern',None);p.pop('fill-outline-color',None)
        if id=='water':p['fill-color']='#86b9b6';p['fill-antialias']=True
        elif id=='park' or 'wood' in id:p['fill-color']='#90aa75';p['fill-opacity']=1
        elif 'grass' in id:p['fill-color']='#a8bc85'
        elif 'wetland' in id:p['fill-color']='#afc3a1'
        elif 'residential' in id:p['fill-color']='#dddcc6'
        elif 'school' in id:p['fill-color']='#d4d3b8'
        elif 'hospital' in id:p['fill-color']='#e3d4c3'
        elif 'sand' in id:p['fill-color']='#e6d9b5'
        elif 'aeroway' in id:p['fill-color']='#bcc4b3'
        elif 'road_area' in id:p['fill-color']='#b2b7a8'
        else:p['fill-color']='#c3cdab'
    elif typ=='line':
        p.pop('line-pattern',None)
        if 'waterway' in id:p['line-color']='#86b9b6'
        elif 'boundary' in id:p['line-color']='#a7ae97';p['line-opacity']=0.45
        elif 'casing' in id:p['line-color']='#dedac2'
        elif 'rail' in id:p['line-color']='#a2a796'
        elif 'path' in id:p['line-color']='#ded6b9'
        elif id=='park_outline':p['line-color']='#90aa75'
        else:p['line-color']='#9da69e'
    keep.append(l)
s['layers']=keep;s.pop('sprite',None);s['sources'].pop('ne2_shaded',None)
s['light']={'anchor':'map','color':'#fff5df','intensity':0.48,'position':[1.3,210,48]}
s['name']='Little Shanghai · Miniature';s['metadata']={'attribution':'OpenFreeMap / OpenMapTiles / OpenStreetMap'}
json.dump(s,open(out/'miniature-style.json','w'),ensure_ascii=False,separators=(',',':'))
# DataV municipality boundaries use GCJ-02; convert to the WGS84 base map.
a=6378245.0;ee=0.00669342162296594323

def delta(lng,lat):
    x=lng-105;y=lat-35
    tlat=-100+2*x+3*y+.2*y*y+.1*x*y+.2*math.sqrt(abs(x))
    tlng=300+x+2*y+.1*x*x+.1*x*y+.1*math.sqrt(abs(x))
    tlat+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    tlat+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
    tlat+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    tlng+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    tlng+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
    tlng+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    rad=lat/180*math.pi;magic=1-ee*math.sin(rad)**2;sq=math.sqrt(magic)
    return tlng*180/(a/sq*math.cos(rad)*math.pi),tlat*180/(a*(1-ee)/(magic*sq)*math.pi)
def inverse(p):
    lng,lat=p[:2];x,y=lng,lat
    for _ in range(4):
        dx,dy=delta(x,y);x=lng-dx;y=lat-dy
    return [round(x,7),round(y,7)]
def transform(c):return inverse(c) if isinstance(c[0],(float,int)) else [transform(x) for x in c]
b=json.load(open(out/'shanghai-districts.json'))
for f in b['features']:
    f['geometry']['coordinates']=transform(f['geometry']['coordinates'])
    for key in ['center','centroid']:
        if key in f['properties']:f['properties'][key]=inverse(f['properties'][key])
json.dump(b,open(out/'shanghai-wgs84.json','w'),ensure_ascii=False,separators=(',',':'))
print('Prepared style and WGS84 boundaries for all 16 Shanghai districts.')

# Suppress source building volumes only at the four landmarks drawn as custom models.
polygons=[]
for p,r in [([121.49981,31.23967],155),([121.5055,31.2336],110),([121.5076,31.2365],100),([121.5051,31.2353],105)]:
    x,y=inverse(p)
    if p[0]==121.49981:x,y=121.49503,31.24191
    if p[0]==121.5055:x,y=121.50115,31.23548
    ring=[[x+math.cos(i*math.pi/16)*r/(111320*math.cos(y*math.pi/180)),y+math.sin(i*math.pi/16)*r/111320] for i in range(33)]
    polygons.append([ring])
for l in s['layers']:
    if l['id']=='building-3d':
        l['filter']=['all',['!=',['get','hide_3d'],True],['!',['within',{'type':'MultiPolygon','coordinates':polygons}]]]
        l['paint']['fill-extrusion-height']=['*',.75,['max',7,['coalesce',['get','render_height'],9]]]
    if 'highway-name' in l['id']:
        l['minzoom']=16.4;l['paint']['text-halo-width']=1;l['paint']['text-color']='#7c8370';l['layout']['text-size']=10
json.dump(s,open(out/'miniature-style.json','w'),ensure_ascii=False,separators=(',',':'))
