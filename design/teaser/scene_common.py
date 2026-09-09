"""Shared URDF visuals, square terrain and figure-eight reference for both engines."""
from pathlib import Path
import xml.etree.ElementTree as ET
import math
import numpy as np
from scipy.spatial.transform import Rotation

JACKAL_ROOT=Path('/media/soicroot/IU9/code/SimRealOffroad/assets/jackal')
SIDE=12.8
PERIOD=32.0
FPS=24
PLAYBACK_SPEED=2.0

def transform(node):
    out=np.eye(4)
    if node is not None:
        out[:3,3]=np.fromstring(node.get('xyz','0 0 0'),sep=' ')
        out[:3,:3]=Rotation.from_euler('xyz',np.fromstring(node.get('rpy','0 0 0'),sep=' ')).as_matrix()
    return out

def visuals(root=JACKAL_ROOT):
    urdf=ET.parse(root/'jackal.urdf').getroot()
    materials={m.get('name'):np.fromstring(m.find('color').get('rgba'),sep=' ') for m in urdf.findall('material')}
    links={l.get('name'):l for l in urdf.findall('link')}
    children={}
    for j in urdf.findall('joint'):
        if j.get('type')=='fixed':children.setdefault(j.find('parent').get('link'),[]).append(j)
    result=[]
    def visit(name,pose):
        for v in links[name].findall('visual'):
            geom=list(v.find('geometry'))[0];material=v.find('material');color=np.array([.2,.2,.2,1.])
            if material is not None:
                color=materials.get(material.get('name'),color)
                if material.find('color') is not None:color=np.fromstring(material.find('color').get('rgba'),sep=' ')
            if material is not None and material.get('name')=='yellow':color=np.array([.92,.64,.045,1.])
            if material is not None and material.get('name')=='blue':color=np.array([.08,.16,.20,1.])
            result.append(dict(link=name,kind=geom.tag,params=dict(geom.attrib),pose=pose@transform(v.find('origin')),color=color))
        for j in children.get(name,[]):visit(j.find('child').get('link'),pose@transform(j.find('origin')))
    visit('chassis_link',np.eye(4))
    return result

def quat_wxyz(matrix):
    q=Rotation.from_matrix(matrix).as_quat();return q[[3,0,1,2]]

def height(x,y,sample=0):
    base=.075*np.sin(1.8*x+.4)*np.cos(1.7*y)+.032*np.sin(4*x+2.3*y)
    base+=.16*np.exp(-((x+.9)**2+(y-.75)**2)/.5)
    base+=.11*np.exp(-((x-.85)**2+(y+.70)**2)/.4)
    base-=.07*np.exp(-((x-.65)**2+(y-.50)**2)/.30)
    base+=.22*np.exp(-((x+1.10)**2+(y-1.05)**2)/.20)
    base+=.18*np.exp(-((x-1.05)**2+(y+1.08)**2)/.20)
    if sample:
        phase=sample*.8
        base+=(.014+.005*sample)*np.sin(2.6*x+phase)*np.cos(2.2*y-phase)
        base-=.013*sample*np.exp(-((x+.15)**2+(y+.3)**2)/.45)
    return base

def reference(t):
    w=2*math.pi/PERIOD;q=w*t
    xy=np.array([.82*math.sin(q),.50*math.sin(2*q)])
    vel=w*np.array([.82*math.cos(q),1.0*math.cos(2*q)])
    acc=w*w*np.array([-.82*math.sin(q),-2.0*math.sin(2*q)])
    speed=np.linalg.norm(vel);yaw=math.atan2(vel[1],vel[0])
    yawrate=(vel[0]*acc[1]-vel[1]*acc[0])/(speed*speed)
    return xy,yaw,speed,yawrate

def control(t,x,y,yaw):
    xy,heading,speed,turn=reference(t)
    dx,dy=xy-np.array([x,y]);c,s=math.cos(yaw),math.sin(yaw)
    ex=c*dx+s*dy;ey=-s*dx+c*dy
    error=math.atan2(math.sin(heading-yaw),math.cos(heading-yaw))
    v=np.clip(speed*math.cos(error)+1.25*ex,-.20,.55)
    omega=np.clip(turn+3.8*math.sin(error)+2.5*ey,-1.8,1.8)
    return float(v),float(omega)


def terrain_pose(t, sample=0, compression=0.0, height_query=None, reference_query=reference):
    """Prescribed root pose fitting a plane to the four wheel support heights."""
    xy,yaw,speed,turn=reference_query(t)
    c,s=math.cos(yaw),math.sin(yaw)
    local=np.array([[.131,.187795],[.131,-.187795],[-.131,.187795],[-.131,-.187795]])
    world=local@np.array([[c,s],[-s,c]])+xy
    hs=(height(world[:,0],world[:,1],sample) if height_query is None else np.array([height_query(px,py) for px,py in world]))-compression
    design=np.column_stack([world[:,0]-xy[0],world[:,1]-xy[1],np.ones(4)])
    gx,gy,h=np.linalg.lstsq(design,hs,rcond=None)[0]
    up=np.array([-gx,-gy,1.]);up/=np.linalg.norm(up)
    forward=np.array([c,s,gx*c+gy*s]);forward/=np.linalg.norm(forward)
    left=np.cross(up,forward);left/=np.linalg.norm(left)
    rot=np.column_stack([forward,left,up])
    return np.array([xy[0],xy[1],h+.095/up[2]-.0345*up[2]]),rot,speed,turn
