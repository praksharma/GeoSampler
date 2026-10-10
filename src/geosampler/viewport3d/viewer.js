// Application shell adapted from PyniteGUI; see THIRD_PARTY.md.
import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {OrientationGizmo} from './gizmo.js';

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 10000);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.autoClear=false;
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;
controls.screenSpacePanning=true;
const notify = index => window.geoBridge?.orientation(index);
const gizmo = new OrientationGizmo(camera,controls,renderer,orient,notify,stopMotion);
controls.addEventListener('start',()=>notify(7));
const grid = new THREE.GridHelper(20,20,0xa8b5b8,0xe2e7e8);
grid.rotation.x=Math.PI/2; // XY reference plane.
scene.add(grid);
const axes = new THREE.AxesHelper(3);
scene.add(axes);
scene.add(new THREE.HemisphereLight(0xffffff,0x708080,2));
const light = new THREE.DirectionalLight(0xffffff,2);
light.position.set(1,2,3);scene.add(light);
function stopMotion(){const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;}
function resize(){
  const width=Math.max(innerWidth,1),height=Math.max(innerHeight,1);
  camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height);
}
function orient(index){
  if(index<0||index>6)return;
  gizmo.cancel();stopMotion();
  const direction=[[1,.7,1],[0,0,1],[0,1,0],[1,0,0],[0,0,-1],[0,-1,0],[-1,0,0]][index];
  camera.up.set(0,index===2||index===5?0:1,index===2?-1:index===5?1:0);
  controls.target.set(0,0,0);
  camera.position.copy(new THREE.Vector3(...direction).normalize().multiplyScalar(15 / Math.sin(THREE.MathUtils.degToRad(camera.fov/2)) / Math.min(1,camera.aspect)));
  controls.update();notify(index);
}
function appearance(config){
  scene.background=new THREE.Color(config.canvas);
  grid.material.color.set(config.grid);
  grid.visible=config.showGrid;axes.visible=config.showAxes;
}
window.geoViewer={orient,appearance,reset:()=>orient(0)};
renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();window.geoReportFailure('Graphics context lost. Restart the application.');});
addEventListener('resize',resize);
resize();appearance({canvas:'#fafcfc',grid:'#e2e7e8',showGrid:true,showAxes:true});orient(0);
const clock=new THREE.Clock();
renderer.setAnimationLoop(()=>{gizmo.update(clock.getDelta());controls.update();renderer.clear();renderer.render(scene,camera);gizmo.render();});
window.geoRendererReady=true;window.geoBridge?.ready();
