// Application shell adapted from PyniteGUI; see THIRD_PARTY.md.
import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {OrientationGizmo} from './gizmo.js';
import {LineSegments2} from './vendor/lines/LineSegments2.js';
import {LineSegmentsGeometry} from './vendor/lines/LineSegmentsGeometry.js';
import {LineMaterial} from './vendor/lines/LineMaterial.js';
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(38,1,.01,10000);
const renderer=new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.autoClear=false;
document.body.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;controls.screenSpacePanning=true;
const notify=index=>window.geoBridge?.orientation(index);
const gizmo=new OrientationGizmo(camera,controls,renderer,orient,notify,stopMotion);
controls.addEventListener('start',()=>notify(7));
const grid=new THREE.GridHelper(20,20,0xa8b5b8,0xe2e7e8);grid.rotation.x=Math.PI/2;scene.add(grid);
const axes=new THREE.AxesHelper(3);scene.add(axes);
scene.add(new THREE.HemisphereLight(0xffffff,0x708080,2));
const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(1,2,3);scene.add(light);
let objects=[],faces=[],edges=[],documentId='',mode='face',selected=new Set(),hover=null;
let center=new THREE.Vector3(),radius=15,down=null;
const raycaster=new THREE.Raycaster();
const key=o=>`${o.userData.dimension}:${o.userData.tag}`;
let palette={face:0x75a8b5,edge:0x304650};
let sampleObjects=[];
function stopMotion(){const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;}
function resize(){camera.aspect=Math.max(innerWidth,1)/Math.max(innerHeight,1);camera.updateProjectionMatrix();renderer.setSize(Math.max(innerWidth,1),Math.max(innerHeight,1));}
function fit(direction){
  controls.target.copy(center);
  const distance=radius/Math.sin(THREE.MathUtils.degToRad(camera.fov/2))/Math.min(1,camera.aspect);
  camera.position.copy(center).addScaledVector(direction.clone().normalize(),distance);
  camera.near=Math.max(distance/10000,1e-8);camera.far=distance*100;camera.updateProjectionMatrix();controls.update();
}
function orient(index){
  if(index<0||index>6)return;
  gizmo.cancel();stopMotion();
  camera.up.set(0,index===2||index===5?0:1,index===2?-1:index===5?1:0);
  fit(new THREE.Vector3(...[[1,.7,1],[0,0,1],[0,1,0],[1,0,0],[0,0,-1],[0,-1,0],[-1,0,0]][index]));notify(index);
}
function recolor(){
  for(const object of objects){
    const id=key(object),isSelected=selected.has(id),isHovered=hover===id;
    const color=isSelected?0xe89a34:isHovered?0x41c4b8:object.userData.dimension===2?palette.face:palette.edge;
    object.material.color.set(color);
    const highlight=object.userData.highlight;
    if(highlight){
      highlight.visible=isSelected||isHovered;
      highlight.material.color.set(color);
      highlight.material.linewidth=isSelected?6:4;
    }
  }
}
function appearance(config){
  scene.background=new THREE.Color(config.canvas);grid.material.color.set(config.grid);
  grid.visible=config.showGrid;axes.visible=config.showAxes;
  const dark=new THREE.Color(config.canvas).getHSL({}).l<.4;
  palette={face:dark?0x6196ad:0x75a8b5,edge:dark?0xd0e4ec:0x304650};recolor();
}
function loadGeometry(data){
  for(const object of objects){scene.remove(object);object.traverse(part=>{part.geometry?.dispose();part.material?.dispose();});}
  objects=[];faces=[];edges=[];selected.clear();hover=null;down=null;documentId=data.document;
  const box=new THREE.Box3();
  for(const entity of data.entities){
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(entity.positions,3));
    let object;
    if(entity.dimension===2){
      geometry.computeVertexNormals();
      object=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:palette.face,side:THREE.DoubleSide,roughness:.65,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));faces.push(object);
    }else{object=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({color:palette.edge}));edges.push(object);}
    object.userData={dimension:entity.dimension,tag:entity.tag};
    if(entity.dimension===1){
      // Screen-space ribbons: native WebGL lines remain one pixel on most GPUs.
      const highlight=new LineSegments2(new LineSegmentsGeometry().setPositions(entity.positions),
        new LineMaterial({color:0xe89a34,linewidth:6,worldUnits:false,depthTest:true,depthWrite:false}));
      highlight.visible=false;
      object.add(highlight);object.userData.highlight=highlight;
    }
    objects.push(object);scene.add(object);box.expandByObject(object);
  }
  box.getCenter(center);radius=Math.max(box.getSize(new THREE.Vector3()).length()*.6,1e-6);
  grid.position.copy(center);grid.position.z=box.min.z-radius*.005;grid.scale.setScalar(radius/8);
  axes.position.copy(box.min);axes.scale.setScalar(radius/8);
  orient(data.dimension===2?1:0);recolor();
}
function setMode(value){
  mode=value==='edge'?'edge':'face';hover=null;down=null;recolor();
  // Distinct cursors accompany the explicit toolbar modes.
  renderer.domElement.style.cursor=mode==='face'?'crosshair':'cell';
}
function setSelection(values){selected=new Set(values.map(([d,t])=>`${d}:${t}`));recolor();}
function pickAt(x,y){
  const rect=renderer.domElement.getBoundingClientRect();
  raycaster.setFromCamera(new THREE.Vector2((x-rect.left)/rect.width*2-1,1-(y-rect.top)/rect.height*2),camera);
  const surface=raycaster.intersectObjects(faces,false)[0];
  if(mode==='face')return surface?.object||null;
  // Approximate a six-pixel tolerance in world units at the orbit target depth.
  const tolerance=12*camera.position.distanceTo(controls.target)*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))/Math.max(rect.height,1);
  raycaster.params.Line.threshold=tolerance;
  const hits=raycaster.intersectObjects(edges,false);
  // Do not select edges hidden behind a nearer face.
  return hits.find(hit=>!surface||hit.distance<=surface.distance+tolerance*2)?.object||null;
}
renderer.domElement.addEventListener('pointerdown',event=>{if(event.button===0)down={x:event.clientX,y:event.clientY,moved:false};});
renderer.domElement.addEventListener('pointermove',event=>{
  if(down&&Math.hypot(event.clientX-down.x,event.clientY-down.y)>4)down.moved=true;
  const object=event.buttons?null:pickAt(event.clientX,event.clientY);
  hover=object?key(object):null;recolor();
});
renderer.domElement.addEventListener('pointerleave',()=>{hover=null;recolor();});
renderer.domElement.addEventListener('pointercancel',()=>{down=null;});
renderer.domElement.addEventListener('pointerup',event=>{
  const start=down;down=null;
  if(event.button!==0||!start||start.moved||Math.hypot(event.clientX-start.x,event.clientY-start.y)>4)return;
  const object=pickAt(event.clientX,event.clientY);
  window.geoBridge?.picked(documentId,object?.userData.dimension||0,object?.userData.tag||0,event.ctrlKey||event.metaKey||event.shiftKey);
});
function setSamples(config){
  for(const object of sampleObjects){scene.remove(object);object.geometry.dispose();object.material.dispose();}
  sampleObjects=[];
  const colors=[0xf15a9b,0x388bef,0xb070ec,0x22b98a,0xe3b938];
  for(const [index,batch] of config.batches.entries()){
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.Float32BufferAttribute(batch.coordinates.flat(),3));
    const object=new THREE.Points(geometry,new THREE.PointsMaterial({color:colors[index%colors.length],size:4,sizeAttenuation:false,depthTest:!config.through,depthWrite:false}));
    object.visible=config.visible;object.renderOrder=2;
    scene.add(object);sampleObjects.push(object);
  }
}
function diagnostics(){
  const gl=renderer.getContext(),extension=gl.getExtension('WEBGL_debug_renderer_info');
  return {renderer:gl.getParameter(extension?extension.UNMASKED_RENDERER_WEBGL:gl.RENDERER),
    vendor:gl.getParameter(extension?extension.UNMASKED_VENDOR_WEBGL:gl.VENDOR),
    version:gl.getParameter(gl.VERSION),lost:gl.isContextLost(),sampleCount:sampleObjects.reduce((n,o)=>n+o.geometry.attributes.position.count,0)};
}
window.geoViewer={orient,appearance,loadGeometry,setMode,setSelection,setSamples,diagnostics,reset:()=>orient(0)};
renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();window.geoReportFailure('Graphics context lost. Restart the application.');});
addEventListener('resize',resize);resize();appearance({canvas:'#fafcfc',grid:'#e2e7e8',showGrid:true,showAxes:true});orient(0);setMode('face');
const clock=new THREE.Clock();renderer.setAnimationLoop(()=>{gizmo.update(clock.getDelta());controls.update();renderer.clear();renderer.render(scene,camera);gizmo.render();});
window.geoRendererReady=true;window.geoBridge?.ready();
