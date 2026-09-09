"""Detailed SimRealOffroad Jackal, Chrono SCM snow, scripted figure-eight with contact-driven snow deformation."""
import argparse,sys,math,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scene_common import JACKAL_ROOT,SIDE,PERIOD,FPS,PLAYBACK_SPEED,visuals,quat_wxyz,height,reference,control,terrain_pose
p=argparse.ArgumentParser();p.add_argument('--nfc-root',type=Path,default=Path('/home/soicroot/Youwei/research/CoRL25/NFC'));p.add_argument('--jackal-root',type=Path,default=JACKAL_ROOT);p.add_argument('--seconds',type=float,default=PERIOD);p.add_argument('--output',type=Path,default=Path('/tmp/nfc-figure8'));p.add_argument('--no-render',action='store_true');p.add_argument('--view',choices=['detail','overview'],default='detail');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.nfc_root))
from benchmark.chrono_jackal_terrain import chrono,veh,sens,_camera_frame,SNOW,_add_stl_visual
sens.SetSensorShaderDir(str(Path(sys.prefix)/'lib/sensor_ptx')+'/')
PATH_SCALE=4.5
rng=np.random.default_rng(27);y,x=np.mgrid[-SIDE/2:SIDE/2:257j,-SIDE/2:SIDE/2:257j];z=height(x,y);lo,hi=float(z.min()),float(z.max())
hmap=a.output/'snow-height.bmp';Image.fromarray(np.uint8(255*(z-lo)/(hi-lo))).save(hmap)
noise=rng.normal(size=(1024,1024));coarse=gaussian_filter(noise,10);coarse/=coarse.std();tex=np.clip(224+4*coarse+1.5*noise,205,244);rgb=np.stack([tex*.965,tex*.985,tex],axis=-1).astype('uint8');texture=a.output/'snow-texture.png';Image.fromarray(rgb).save(texture)
system=chrono.ChSystemSMC();system.SetCollisionSystemType(chrono.ChCollisionSystem.Type_BULLET);system.SetGravitationalAcceleration(chrono.ChVector3d(0,0,-9.81))
terrain=veh.SCMTerrain(system);terrain.SetPlane(chrono.ChCoordsysd(chrono.ChVector3d(0,0,0),chrono.CSYSNORM.rot));terrain.Initialize(str(hmap),SIDE,SIDE,lo,hi,.02);terrain.SetMeshWireframe(False);terrain.SetSoilParameters(1.0e6,*SNOW.values()[1:]);terrain.EnableBulldozing(False);terrain.SetBulldozingParameters(55.,1.,5,10);terrain.SetTexture(str(texture),2,2);terrain.SetColor(chrono.ChColor(.70,.75,.79))
material=chrono.ChContactMaterialSMC();material.SetFriction(.75);material.SetYoungModulus(2e7)
yaw0=reference(0)[1];rotation=chrono.QuatFromAngleZ(yaw0);base_z=float(height(0,0))+.095-.0345+.025
chassis=chrono.ChBodyEasyBox(.42,.31,.184,1000,True,True,material);chassis.SetMass(16.523);chassis.SetInertiaXX(chrono.ChVector3d(.3136,.3922,.4485));chassis.SetPos(chrono.ChVector3d(0,0,base_z+.092));chassis.SetRot(rotation);chassis.GetVisualModel().Clear();system.Add(chassis)
for item in visuals(a.jackal_root):
 pose=item['pose'].copy();pose[2,3]-=.092;q=quat_wxyz(pose[:3,:3]);frame=chrono.ChFramed(chrono.ChVector3d(*pose[:3,3]),chrono.ChQuaterniond(*q));kind=item['kind'];params=item['params'];color=item['color'][:3]
 if kind=='mesh':_add_stl_visual(chassis,a.jackal_root/'meshes'/Path(params['filename']).name,item['link'],color,frame)
 else:
  if kind=='box':shape=chrono.ChVisualShapeBox(*np.fromstring(params['size'],sep=' '))
  elif kind=='cylinder':
   shape=chrono.ChVisualShapeCylinder(float(params['radius']),float(params['length']));frame.SetRot(frame.GetRot()*chrono.QuatFromAngleX(math.pi/2))
  elif kind=='sphere':shape=chrono.ChVisualShapeSphere(float(params['radius']))
  else:continue
  shape.SetColor(chrono.ChColor(*color));chassis.AddVisualShape(shape,frame)
wheels=[];speeds=[];track=.37559;radius=.095
for k,(xx,yy) in enumerate([(.131,.187795),(.131,-.187795),(-.131,.187795),(-.131,-.187795)]):
 wx=math.cos(yaw0)*xx-math.sin(yaw0)*yy;wy=math.sin(yaw0)*xx+math.cos(yaw0)*yy;pos=chrono.ChVector3d(wx,wy,base_z+.0345)
 wheel=chrono.ChBodyEasyCylinder(chrono.ChAxis_Y,radius,.04,1150,True,True,material);wheel.SetMass(.477);wheel.SetInertiaXX(chrono.ChVector3d(.0013,.0024,.0013));wheel.SetPos(pos);wheel.SetRot(rotation);wheel.GetVisualModel().Clear();_add_stl_visual(wheel,a.jackal_root/'meshes/jackal-wheel.stl','Jackal wheel',(.07,.075,.08),chrono.ChFramed(chrono.ChVector3d(),chrono.QuatFromAngleX(math.pi/2)));system.Add(wheel)
 frame=chrono.ChFramed(pos,rotation*chrono.QuatFromAngleX(-math.pi/2))
 if k==0:
  joint=chrono.ChLinkLockRevolute();joint.Initialize(wheel,chassis,frame);speeds.append(None)
 else:
  motor=chrono.ChLinkMotorRotationSpeed();motor.Initialize(wheel,chassis,frame);speed=chrono.ChFunctionConst(0);motor.SetSpeedFunction(speed);speeds.append(speed)
 wheels.append(wheel)
manager=cam=writer=None
if not a.no_render:
 manager=sens.ChSensorManager(system);manager.SetVerbose(False);manager.scene.AddAreaLight(chrono.ChVector3f(-1,1,5),chrono.ChColor(.32,.36,.40),40.,chrono.ChVector3f(2,0,0),chrono.ChVector3f(0,2,0));manager.scene.AddPointLight(chrono.ChVector3f(-3,-4,2),chrono.ChColor(.85,.82,.76),30.)
 anchor=chrono.ChBody();anchor.SetFixed(True);system.Add(anchor)
 pos=np.array([1.6,2.0,1.55]) if a.view=='detail' else np.array([0,3.1,8.55])*(SIDE/5.6);lookat=np.array([0,0,.08]) if a.view=='detail' else np.array([0,0,-.45])*(SIDE/5.6);direction=lookat-pos;cyaw=math.atan2(direction[1],direction[0]);cpitch=math.atan2(-direction[2],np.linalg.norm(direction[:2]));rot=chrono.QuatFromAngleZ(cyaw)*chrono.QuatFromAngleY(cpitch)
 cam=sens.ChCameraSensor(anchor,FPS/PLAYBACK_SPEED,chrono.ChFramed(chrono.ChVector3d(*pos),rot),1080,1080,.70 if a.view=='detail' else .565,2,sens.PINHOLE,True,2.2,False);cam.SetLag(0);cam.SetCollectionWindow(0);cam.PushFilter(sens.ChFilterRGBA8Access());manager.AddSensor(cam)
 writer=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1080','-r',str(FPS),'-i','-','-an','-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output/'chrono-snow.mp4')],stdin=subprocess.PIPE)
# This is an illustrative prescribed motion, not autonomous-policy evidence.
# A small support-height offset presses the rolling wheels into the SCM surface.
wheel_angles=np.zeros(4)
start=system.GetChTime();telemetry=[]
for f in range(round(a.seconds*FPS/PLAYBACK_SPEED)):
 target=start+(f+1)*PLAYBACK_SPEED/FPS
 while system.GetChTime()<target:
  t=system.GetChTime()-start
  shift=(PATH_SCALE-1)*reference(t)[0]
  rootpos,rot,v,w=terrain_pose(t,compression=.010,height_query=lambda px,py: terrain.GetInitHeight(chrono.ChVector3d(float(px+shift[0]),float(py+shift[1]),1.0)))
  rootpos[:2]+=shift;v*=PATH_SCALE
  q=quat_wxyz(rot);cq=chrono.ChQuaterniond(*q)
  chassis.SetPos(chrono.ChVector3d(*(rootpos+rot@np.array([0,0,.092]))));chassis.SetRot(cq)
  chassis.SetPosDt(chrono.ChVector3d(0,0,0));chassis.SetAngVelParent(chrono.ChVector3d(0,0,0))
  for k,(xx,yy) in enumerate([(.131,.187795),(.131,-.187795),(-.131,.187795),(-.131,-.187795)]):
   velocity=v+(-1 if k in (0,2) else 1)*w*track/2
   wheel_angles[k]+=velocity*.001/radius
   wp=rootpos+rot@np.array([xx,yy,.0345])
   wheels[k].SetPos(chrono.ChVector3d(*wp));wheels[k].SetRot(cq*chrono.QuatFromAngleY(wheel_angles[k]));wheels[k].SetPosDt(chrono.ChVector3d(0,0,0));wheels[k].SetAngVelParent(chrono.ChVector3d(0,0,0))
  yaw=reference(t)[1]
  terrain.Synchronize(system.GetChTime());terrain.Advance(.001);system.DoStepDynamics(.001)
  if manager:
   if a.view=='detail':anchor.SetPos(chrono.ChVector3d(*rootpos))
   manager.Update()
 pos=chassis.GetPos();ref=PATH_SCALE*reference((f+1)*PLAYBACK_SPEED/FPS)[0];sink=max(terrain.GetInitHeight(w.GetPos())-terrain.GetHeight(w.GetPos()) for w in wheels);telemetry.append(dict(t=(f+1)*PLAYBACK_SPEED/FPS,x=pos.x,y=pos.y,z=pos.z,yaw=yaw,command_v=v,command_w=w,error=float(np.linalg.norm(ref-[pos.x,pos.y])),max_sinkage=float(sink)))
 if cam:
  im=_camera_frame(cam)
  if im is None:raise RuntimeError('No Chrono camera frame')
  if f in (0,96,192,288,383):Image.fromarray(im).save(a.output/f'chrono-{f:03}.jpg')
  writer.stdin.write(np.ascontiguousarray(im).tobytes())
 if f%48==0:print('FRAME',f,'xy',round(pos.x,2),round(pos.y,2),'error',round(telemetry[-1]['error'],3),flush=True)
if writer:writer.stdin.close();assert writer.wait()==0
(a.output/'chrono-manifest.json').write_text(json.dumps(dict(engine='Chrono SCM + OptiX',camera_view=a.view,camera_offset_m=([1.6,2.0,1.55] if a.view=='detail' else None),asset_root=str(a.jackal_root),terrain_size_m=[SIDE,SIDE],terrain_height_range_m=[lo,hi],reference='x=3.69sin(2pi*t/32), y=2.25sin(4pi*t/32)',robot_scale=1.0,wheel_radius_m=.095,wheel_width_m=.04,path_scale=PATH_SCALE,playback_speed=PLAYBACK_SPEED,front_left='black tire, no drive motor; passive rolling pose prescribed for illustration',motion='scripted terrain-following figure-eight, not a controller evaluation',compression_offset_m=.010,snow_parameters=[1.0e6,*SNOW.values()[1:]],frames=telemetry),indent=2))
print('FINISHED',flush=True)
