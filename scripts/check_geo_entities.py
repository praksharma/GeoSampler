"""Check entity identity and display tessellation for the two reference geometries.
Run: uv run --with gmsh==4.15.2 python scripts/check_geo_entities.py
This is a backend feasibility check, not a viewport mouse-picking test.
"""
import gmsh,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'examples/geometries/cfdbench'
report={'gmsh_version':gmsh.__version__,'cases':[]}
gmsh.initialize()
gmsh.option.setNumber('General.Terminal',0)
try:
 for filename in ['annulus_unstructured.geo','sphere_unstructured.geo']:
  gmsh.clear();gmsh.open(str(root/filename))
  entities=gmsh.model.getEntities()
  case={'file':filename,'counts':{str(d):len(gmsh.model.getEntities(d)) for d in range(4)},'groups':[], 'entities':[]}
  for d,t in gmsh.model.getPhysicalGroups():
   case['groups'].append({'dimension':d,'tag':t,'entities':list(map(int,gmsh.model.getEntitiesForPhysicalGroup(d,t)))})
  gmsh.model.mesh.generate(2)
  for d,t in entities:
   if d not in (1,2):continue
   gmsh.model.setVisibility(entities,0)
   gmsh.model.setVisibility([(d,t)],1)
   visible=[list(e) for e in entities if gmsh.model.getVisibility(*e)]
   assert visible==[[d,t]],(d,t,visible)
   types,tags,nodes=gmsh.model.mesh.getElements(d,t)
   count=sum(map(len,tags));assert count>0,(d,t)
   boundary=[list(e) for e in gmsh.model.getBoundary([(d,t)],oriented=False)]
   case['entities'].append({'dimension':d,'tag':t,'type':gmsh.model.getType(d,t),'boundary':boundary,'display_elements':count,'individually_addressable':True})
  gmsh.model.setVisibility(entities,1)
  nt,coords,_=gmsh.model.mesh.getNodes()
  points={int(t):tuple(coords[i*3:i*3+3]) for i,t in enumerate(nt)}
  radii=[]
  for _,face in gmsh.model.getEntities(2):
   _,_,nodeblocks=gmsh.model.mesh.getElements(2,face)
   for block in nodeblocks:
    radii.extend(math.sqrt(sum(float(v)**2 for v in points[int(n)])) for n in block)
  case['surface_node_radius_range']=[min(radii),max(radii)]
  if filename.startswith('annulus'):
   assert min(radii)>=.5-1e-8 and max(radii)<=1+1e-8
  else:
   assert max(abs(r-1) for r in radii)<1e-8
  report['cases'].append(case)
finally:gmsh.finalize()
print(json.dumps(report,indent=2))
