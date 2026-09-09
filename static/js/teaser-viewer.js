// Eight independent scenes share one on-demand WebGL canvas.
import * as THREE from './vendor/three/three.module.min.js';
import { OrbitControls } from './vendor/three/OrbitControls.js';
import { SIDE, snowHeight, groundHeight, routeState, supportPose } from './teaser-motion.mjs';
import config from '../data/teaser-domains.json';

export async function createViewer(host) {
  const viewport=host.querySelector('.viewer-viewport');
  const toolbar=document.querySelector('.viewer-toolbar');
  const pauseButton=toolbar.querySelector('[data-pause]');
  const followButton=toolbar.querySelector('[data-follow]');
  const video=document.querySelector('[data-teaser-real]');
  const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.15;
  viewport.prepend(renderer.domElement);
  renderer.domElement.setAttribute('aria-hidden','true');

  let running=!reducedMotion.matches, enabled=false, visible=false, raf=0, last=0, time=0;
  let width=1,height=1;
  const environments=[];
  const frameMaterial=new THREE.MeshStandardMaterial({color:'#959da3',roughness:.83,metalness:.03});
  const wheelMaterial=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.83,metalness:.03});
  const groundMaterial=new THREE.MeshStandardMaterial({color:'#d2d3d4',roughness:.9});
  // Merge the chassis once, then instance it: two robot draw calls per terrain.
  const rods=[];
  function rod(start,end,radius) {
    const first=new THREE.Vector3(...start),second=new THREE.Vector3(...end);
    const direction=second.clone().sub(first);
    const geometry=new THREE.CylinderGeometry(radius,radius,direction.length(),10).toNonIndexed();
    geometry.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize()));
    geometry.translate(...first.add(second).multiplyScalar(.5).toArray());
    rods.push(geometry);
  }
  for(const yy of [-.125,.125])rod([-.21,yy,.11],[.21,yy,.11],.014);
  for(const xx of [-.21,.21])rod([xx,-.125,.11],[xx,.125,.11],.014);
  rod([-.21,-.125,.11],[.21,.125,.11],.009);rod([-.21,.125,.11],[.21,-.125,.11],.009);
  for(const xx of [-.131,.131]) {
    rod([xx,-.187795,.0345],[xx,.187795,.0345],.014);
    for(const yy of [-.125,.125])rod([xx,yy,.0345],[xx,yy,.11],.012);
  }
  rod([.09,0,.13],[.23,0,.13],.01);
  for(const yy of [-.045,.045])rod([.23,0,.13],[.16,yy,.13],.009);
  const chassisGeometry=new THREE.BufferGeometry();
  for(const attribute of ['position','normal']) {
    const values=new Float32Array(rods.reduce((sum,g)=>sum+g.attributes[attribute].array.length,0));
    let offset=0;
    for(const geometry of rods){values.set(geometry.attributes[attribute].array,offset);offset+=geometry.attributes[attribute].array.length;}
    chassisGeometry.setAttribute(attribute,new THREE.BufferAttribute(values,3));
  }
  rods.forEach(geometry=>geometry.dispose());
  const wheelGeometry=new THREE.CylinderGeometry(.095,.095,.04,24);
  const lines=[];
  for(let axis=0;axis<2;axis++)for(let fixed=-SIDE/2;fixed<=SIDE/2;fixed+=.25) {
    for(let start=-SIDE/2;start<SIDE/2;start+=.125)for(const t of [start,Math.min(start+.10,SIDE/2)]) {
      const x=axis===0?t:fixed,y=axis===0?fixed:t;lines.push(x,y,snowHeight(x,y)+.008);
    }
  }
  const gridGeometry=new THREE.BufferGeometry();
  gridGeometry.setAttribute('position',new THREE.Float32BufferAttribute(lines,3));
  const gridMaterial=new THREE.LineBasicMaterial({color:0x677078,transparent:true,opacity:.28,depthWrite:false});
  const wheelCenters=[[.131,.187795],[.131,-.187795],[-.131,.187795],[-.131,-.187795]];
  const bodyMatrix=new THREE.Matrix4(),wheelMatrix=new THREE.Matrix4(),localWheel=new THREE.Matrix4();
  const rotation=new THREE.Matrix4(),quaternion=new THREE.Quaternion();
  const forward=new THREE.Vector3(),left=new THREE.Vector3(),up=new THREE.Vector3(),position=new THREE.Vector3();
  const unit=new THREE.Vector3(1,1,1),wheelQuaternion=new THREE.Quaternion(),wheelAxis=new THREE.Vector3(0,1,0);
  const grey=new THREE.Color('#717980');

  for(let index=0;index<8;index++) {
    const scene=new THREE.Scene();scene.background=new THREE.Color('#e3e3e3');
    const camera=new THREE.PerspectiveCamera(40,1,.025,80);camera.up.set(0,0,1);
    const panel=document.createElement('div');panel.className='viewer-tile';panel.tabIndex=0;
    panel.setAttribute('role','group');
    panel.setAttribute('aria-label',`Simulation sample ${index+1}. Drag to orbit, scroll to zoom, arrow keys to pan.`);
    const number=document.createElement('span');number.className='viewer-number';number.textContent=String(index+1).padStart(2,'0');
    const depth=document.createElement('span');depth.className='viewer-depth';
    panel.append(number,depth);viewport.append(panel);
    const controls=new OrbitControls(camera,panel);
    controls.enableDamping=false;controls.minDistance=.65;controls.maxDistance=30;
    controls.maxPolarAngle=Math.PI/2-.06;controls.listenToKeyEvents(panel);controls.zoomToCursor=true;
    const hemi=new THREE.HemisphereLight(0xffffff,0x777777,2.3);hemi.position.set(0,0,10);scene.add(hemi);
    const light=new THREE.DirectionalLight(0xfffaf5,3.2);light.castShadow=true;
    light.shadow.mapSize.set(512,512);
    Object.assign(light.shadow.camera,{left:-2,right:2,top:2,bottom:-2,near:.1,far:25});
    light.shadow.bias=-.00015;light.shadow.normalBias=.008;scene.add(light,light.target);
    const fill=new THREE.DirectionalLight(0xe8edf3,.9);fill.position.set(4,-5,6);scene.add(fill);
    const chassis=new THREE.InstancedMesh(chassisGeometry,frameMaterial,8);
    const wheels=new THREE.InstancedMesh(wheelGeometry,wheelMaterial,32);
    for(const mesh of [chassis,wheels]) {
      mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);scene.add(mesh);
    }
    config.samples[index].robots.forEach((robot,i)=>{
      for(let j=0;j<4;j++)wheels.setColorAt(i*4+j,j===0?new THREE.Color().setRGB(...robot.tire_rgba.slice(0,3),THREE.LinearSRGBColorSpace):grey);
    });
    const ground=(x,y)=>groundHeight(x,y,index,config.samples[index].depth_parameter_m);
    const terrainGeometry=new THREE.PlaneGeometry(SIDE,SIDE,128,128);
    const vertices=terrainGeometry.attributes.position;
    for(let i=0;i<vertices.count;i++)vertices.setZ(i,ground(vertices.getX(i),vertices.getY(i)));
    terrainGeometry.computeVertexNormals();terrainGeometry.computeBoundingSphere();
    const terrain=new THREE.Mesh(terrainGeometry,groundMaterial);terrain.receiveShadow=true;scene.add(terrain);
    scene.add(new THREE.LineSegments(gridGeometry,gridMaterial));
    const environment={index,scene,camera,controls,panel,depth,light,ground,chassis,wheels,
      selected:(-2*index%8+8)%8,following:false,previous:new THREE.Vector3(),focus:new THREE.Vector3(),angles:new Float64Array(32)};
    environments.push(environment);
    controls.addEventListener('change',invalidate);
  }

  function updateRobots(dt) {
    for(const env of environments) {
      config.samples[env.index].robots.forEach((robot,i)=>{
        const state=routeState(time,robot.route),pose=supportPose(state,env.ground);
        position.fromArray(pose.position);
        rotation.makeBasis(forward.fromArray(pose.forward),left.fromArray(pose.left),up.fromArray(pose.up));
        quaternion.setFromRotationMatrix(rotation);bodyMatrix.compose(position,quaternion,unit);
        env.chassis.setMatrixAt(i,bodyMatrix);
        for(let j=0;j<4;j++) {
          env.angles[i*4+j]+=(state.speed+(j%2===0?-1:1)*state.turn*.37559/2)/.095*dt;
          wheelQuaternion.setFromAxisAngle(wheelAxis,env.angles[i*4+j]);
          localWheel.compose(new THREE.Vector3(...wheelCenters[j],.0345),wheelQuaternion,unit);
          env.wheels.setMatrixAt(i*4+j,wheelMatrix.multiplyMatrices(bodyMatrix,localWheel));
        }
        if(i===env.selected)env.focus.copy(position).add(new THREE.Vector3(0,0,.08));
      });
      env.chassis.instanceMatrix.needsUpdate=true;env.wheels.instanceMatrix.needsUpdate=true;
      if(env.following) {
        const delta=env.focus.clone().sub(env.previous);env.camera.position.add(delta);env.controls.target.add(delta);
        env.light.target.position.copy(env.focus);env.light.position.copy(env.focus).add(new THREE.Vector3(-3,4,9));
      }
      env.previous.copy(env.focus);
      env.depth.textContent=`Δh ${(snowHeight(env.focus.x,env.focus.y)-env.ground(env.focus.x,env.focus.y)).toFixed(2)} m`;
    }
  }
  function frameRobots() {
    for(const env of environments) {
      env.following=true;env.controls.target.copy(env.focus);
      env.camera.position.copy(env.focus).add(new THREE.Vector3(1.6,2,1.47));env.previous.copy(env.focus);
      env.light.target.position.copy(env.focus);env.light.position.copy(env.focus).add(new THREE.Vector3(-3,4,9));
      Object.assign(env.light.shadow.camera,{left:-2,right:2,top:2,bottom:-2});env.light.shadow.camera.updateProjectionMatrix();
      env.controls.update();
    }
    followButton.setAttribute('aria-pressed','true');invalidate();
  }
  function frameTerrains() {
    for(const env of environments) {
      env.following=false;env.controls.target.set(0,0,0);
      const direction=new THREE.Vector3(1,1.25,1.167).normalize();
      const horizontal=new THREE.Vector3().crossVectors(new THREE.Vector3(0,0,1),direction).normalize();
      const vertical=new THREE.Vector3().crossVectors(direction,horizontal).normalize();
      const tangent=Math.tan(THREE.MathUtils.degToRad(env.camera.fov/2));let distance=0;
      for(const x of [-SIDE/2,SIDE/2])for(const y of [-SIDE/2,SIDE/2])for(const z of [-.45,.45]) {
        const point=new THREE.Vector3(x,y,z);
        distance=Math.max(distance,point.dot(direction)+Math.abs(point.dot(vertical))/tangent,
          point.dot(direction)+Math.abs(point.dot(horizontal))/(tangent*env.camera.aspect));
      }
      env.camera.position.copy(direction.multiplyScalar(distance*1.05));env.controls.update();
      env.light.target.position.set(0,0,0);env.light.position.set(-3,4,9);
      Object.assign(env.light.shadow.camera,{left:-8,right:8,top:8,bottom:-8});env.light.shadow.camera.updateProjectionMatrix();
    }
    followButton.setAttribute('aria-pressed','false');invalidate();
  }
  function syncPause() {pauseButton.textContent=running?'Pause':'Play';pauseButton.setAttribute('aria-pressed',String(!running));}
  function invalidate() {if(enabled&&visible&&!document.hidden&&!raf)raf=requestAnimationFrame(tick);}
  function tick(now) {
    raf=0;if(!enabled||!visible||document.hidden){last=0;return;}
    if(last&&now-last<1000/24){invalidate();return;}
    const dt=last?Math.min((now-last)/1000,.1):0;last=now;
    if(running){time=(time+dt*2)%32;updateRobots(dt*2);}
    renderer.setScissorTest(true);
    for(const env of environments) {
      const col=env.index%4,row=Math.floor(env.index/4);
      const x=Math.round(col*width/4),right=Math.round((col+1)*width/4);
      const y=Math.round((1-row)*height/2),top=Math.round((2-row)*height/2);
      renderer.setViewport(x,y,right-x,top-y);renderer.setScissor(x,y,right-x,top-y);
      env.controls.update();renderer.render(env.scene,env.camera);
    }
    if(running)invalidate();
  }
  function stop() {cancelAnimationFrame(raf);raf=0;last=0;}
  function resize() {
    const bounds=viewport.getBoundingClientRect();if(!bounds.width||!bounds.height)return;
    width=bounds.width;height=bounds.height;renderer.setSize(width,height,false);
    environments.forEach(env=>{env.camera.aspect=(width/4)/(height/2);env.camera.updateProjectionMatrix();});invalidate();
  }
  followButton.addEventListener('click',frameRobots);
  toolbar.querySelector('[data-whole]').addEventListener('click',frameTerrains);
  pauseButton.addEventListener('click',()=>{
    running=!running;last=0;syncPause();
    if(running)video.play().catch(()=>{});else video.pause();invalidate();
  });
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)invalidate();else stop();}).observe(viewport);
  new ResizeObserver(resize).observe(viewport);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else invalidate();});
  reducedMotion.addEventListener('change',event=>{if(event.matches){running=false;video.pause();syncPause();invalidate();}});
  renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();stop();host.dispatchEvent(new CustomEvent('viewer-error'));});
  syncPause();updateRobots(0);frameRobots();resize();
  return {
    setActive(value){enabled=value;if(value){visible=true;last=0;resize();invalidate();if(running)video.play().catch(()=>{});}else stop();},
    pause(){running=false;syncPause();invalidate();}
  };
}
