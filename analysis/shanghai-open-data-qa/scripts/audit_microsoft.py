"""Verify official global index coverage by geometry, not country-name guesses."""
import csv,math,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'evidence/microsoft-dataset-links-2026-08-13.csv';rows=list(csv.DictReader(open(p)))
def tile_bounds(q):
 x=y=0
 for c in q:x=x*2+int(c in '13');y=y*2+int(c in '23')
 n=2**len(q)
 def lat(v):return math.degrees(math.atan(math.sinh(math.pi*(1-2*v/n))))
 return [x/n*360-180,lat(y+1),(x+1)/n*360-180,lat(y)]
bbox=[120.8526123,30.6777973,122.2429167,31.8746329]
selected=[]
for row in rows:
 a=tile_bounds(row['QuadKey'])
 if a[0]<=bbox[2] and a[2]>=bbox[0] and a[1]<=bbox[3] and a[3]>=bbox[1]:selected.append({**row,'bbox':a})
result={'source':'Microsoft GlobalMLBuildingFootprints','index':'https://bfppub.blob.core.windows.net/%24web/2026-08-13/dataset-links.csv','index_rows':len(rows),'index_sha256':hashlib.file_digest(open(p,'rb'),'sha256').hexdigest(),'shanghai_bbox':bbox,'intersecting_partitions':selected,'status':'available' if selected else 'not_covered_in_official_index','not_a_zero_completeness_measurement':True}
json.dump(result,open(ROOT/'evidence/microsoft-coverage-audit.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
