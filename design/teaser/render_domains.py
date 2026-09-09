"""Eight handcrafted ground-height samples with open-frame Jackal visuals."""
import os
os.environ.setdefault('MUJOCO_GL', 'egl')
import argparse
import copy
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scene_common import SIDE, PERIOD, FPS, PLAYBACK_SPEED, height, reference, terrain_pose, quat_wxyz

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, default=PERIOD)
parser.add_argument('--output', type=Path, default=Path('/tmp/nfc-figure8'))
parser.add_argument('--no-render', action='store_true')
parser.add_argument('--view', choices=['detail','overview'], default='detail')
a = parser.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
TILE = 540
ROBOT_CENTERS = [(x, y) for y in (-4., 0., 4.) for x in (-4., 0., 4.) if (x, y) != (0, 0)]
# Distinct, reproducible motion per robot AND per environment. Integer lap counts
# retain a seamless 32-second cycle while phases, speeds and paths differ.
ROUTES = []
for env in range(8):
    env_routes = []
    for robot, center in enumerate(ROBOT_CENTERS):
        rng = np.random.default_rng(2700 + env*131 + robot*17)
        env_routes.append(dict(center=(np.array(center)+rng.uniform(-.10,.10,2)).tolist(),
                               amplitudes=rng.uniform([.85,.55],[1.2,.80]).tolist(),
                               rotation=float(rng.uniform(-math.pi,math.pi)),
                               phase=float(rng.uniform(0,2*math.pi)),
                               direction=1 if (env+robot)%2 else -1,
                               laps=1+(env+2*robot)%3//2,
                               speed_modulation=float(rng.uniform(.12,.28))))
    ROUTES.append(env_routes)


def robot_reference(t, env, robot):
    route = ROUTES[env][robot]
    omega = route['direction']*2*math.pi*route['laps']/PERIOD
    wave = omega*t+route['phase']
    q = wave+route['speed_modulation']*math.sin(wave)
    dq = omega*(1+route['speed_modulation']*math.cos(wave))
    ddq = -omega**2*route['speed_modulation']*math.sin(wave)
    ax, ay = route['amplitudes']
    local = np.array([ax*math.sin(q),ay*math.sin(2*q)])
    velocity = np.array([ax*math.cos(q)*dq,2*ay*math.cos(2*q)*dq])
    acceleration = np.array([ax*(-math.sin(q)*dq*dq+math.cos(q)*ddq),
                             ay*(-4*math.sin(2*q)*dq*dq+2*math.cos(2*q)*ddq)])
    c, s = math.cos(route['rotation']), math.sin(route['rotation'])
    rotate = np.array([[c,-s],[s,c]])
    xy = rotate@local+route['center']
    velocity, acceleration = rotate@velocity, rotate@acceleration
    speed = float(np.linalg.norm(velocity))
    turn = float((velocity[0]*acceleration[1]-velocity[1]*acceleration[0])/(speed*speed))
    return xy, math.atan2(velocity[1],velocity[0]), speed, turn
LOSSES = [.12, .24, .36, .48, .60, .72, .84, .96]
# Low-gloss reds span pink through burgundy; avoid lighting clipping them all to scarlet.
TIRE_COLORS = np.array([
    [.88, .48, .45], [.74, .31, .28], [.61, .19, .16], [.50, .105, .09],
    [.42, .060, .065], [.34, .030, .050], [.27, .014, .038], [.20, .007, .028],
])
# Match Chrono perspective and viewing direction at the requested terrain size.
CAMERA_TARGET = np.array([0., 0., -.225]) * (SIDE/2.8)
CAMERA_POSITION = np.array([0., 1.55, 4.275]) * (SIDE/2.8)
# Match the angle exactly, then leave enough distance for the whole snow reference
# and lower support surface, including their vertical edges.
CAMERA_OFFSET = (CAMERA_POSITION - CAMERA_TARGET) * 1.21
CAMERA_POSITION = CAMERA_TARGET + CAMERA_OFFSET
CAMERA_DISTANCE = float(np.linalg.norm(CAMERA_OFFSET))
CAMERA_ELEVATION = -math.degrees(math.atan2(CAMERA_OFFSET[2], CAMERA_OFFSET[1]))
CAMERA_FOV = math.degrees(.565)
if a.view == 'detail':
    CAMERA_POSITION = np.array([1.6,2.,1.55])
    CAMERA_TARGET = np.array([0.,0.,.08])
    CAMERA_OFFSET = CAMERA_POSITION-CAMERA_TARGET
    CAMERA_DISTANCE = float(np.linalg.norm(CAMERA_OFFSET))
    CAMERA_ELEVATION = -math.degrees(math.atan2(CAMERA_OFFSET[2],np.linalg.norm(CAMERA_OFFSET[:2])))
    CAMERA_FOV = math.degrees(.70)
CAMERA_AZIMUTH = math.degrees(math.atan2(-CAMERA_OFFSET[1],-CAMERA_OFFSET[0]))%360
FOCUS_ROBOTS = [(-2*k)%8 for k in range(8)]
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',32)
DEPTHS = [.055, .12, .23, .085, .19, .27, .10, .165]
HFIELD_BASE, HFIELD_RANGE = -.45, .90
# World-fixed dashed snow reference covering the complete square terrain.
# Precompute endpoints once; render only the nearby portion in tracking views.
GRID_SPACING, GRID_DASH_PERIOD, GRID_DASH_LENGTH = .25, .125, .10
GRID_SEGMENTS = []
for axis in range(2):
    for fixed in np.arange(-SIDE/2, SIDE/2+1e-6, GRID_SPACING):
        for start in np.arange(-SIDE/2, SIDE/2, GRID_DASH_PERIOD):
            end = min(start+GRID_DASH_LENGTH, SIDE/2)
            p1 = [start, fixed] if axis == 0 else [fixed, start]
            p2 = [end, fixed] if axis == 0 else [fixed, end]
            GRID_SEGMENTS.append([[*p1, float(height(*p1))+.008],
                                  [*p2, float(height(*p2))+.008]])
GRID_SEGMENTS = np.asarray(GRID_SEGMENTS)
GRID_MIDPOINTS = GRID_SEGMENTS.mean(axis=1)



def ground_height(x, y, k):
    """Possible support height under a shared observed snow surface, in meters."""
    x, y = np.asarray(x), np.asarray(y)
    phase = k * .83
    px, py = x*2.8/SIDE, y*2.8/SIDE
    hollow = np.exp(-((px - .48*np.cos(phase))**2 + (py - .45*np.sin(phase))**2)/.55)
    compression = DEPTHS[k] * (.42 + .58*hollow)
    compression += (.018 + .012*(k % 3)) * (1 + np.sin(2.5*px+phase)*np.cos(2.1*py-phase))
    return height(x, y) - compression


def tire_color(loss):
    return np.array([np.interp(loss, LOSSES, TIRE_COLORS[:, c]) for c in range(3)])


def capsule(body, p1, p2, radius, rgba, **extra):
    return ET.SubElement(body, 'geom', type='capsule', fromto=' '.join(map(str, (*p1, *p2))),
                         size=str(radius), rgba=' '.join(map(str, rgba)), contype='0',
                         conaffinity='0', **extra)


models, datas, renderers, cameras, records = [], [], [], [], []
wheel_angles = np.zeros((8, 8, 4))
for k in range(8):
    root = ET.Element('mujoco')
    ET.SubElement(root, 'compiler', angle='radian')
    visual = ET.SubElement(root, 'visual')
    ET.SubElement(visual, 'global', offwidth=str(TILE), offheight=str(TILE), orthographic='false', fovy=str(CAMERA_FOV))
    ET.SubElement(visual, 'quality', shadowsize='2048', offsamples='4')
    ET.SubElement(visual, 'headlight', ambient='.50 .50 .50', diffuse='.12 .12 .12', specular='0 0 0')
    defaults = ET.SubElement(root, 'default')
    ET.SubElement(defaults, 'geom', material='matte')
    asset = ET.SubElement(root, 'asset')
    ET.SubElement(asset, 'material', name='matte', specular='.08', shininess='.15')
    ET.SubElement(asset, 'hfield', name='ground', nrow='257', ncol='257', size=f'{SIDE/2} {SIDE/2} {HFIELD_RANGE} .025')
    ET.SubElement(asset, 'texture', name='sky', type='skybox', builtin='flat', rgb1='.88 .88 .88', rgb2='.88 .88 .88', width='32', height='192')
    # An elevation texture and sparse contours make the height hypotheses legible.
    y, x = np.mgrid[-SIDE/2:SIDE/2:257j, -SIDE/2:SIDE/2:257j]
    h = ground_height(x, y, k)
    assert h.min() > HFIELD_BASE and h.max() < HFIELD_BASE + HFIELD_RANGE
    ty, tx = np.mgrid[-SIDE/2:SIDE/2:1025j, -SIDE/2:SIDE/2:1025j]
    th = ground_height(tx,ty,k)
    normalized = np.clip((th+.30)/.58, 0, 1)
    low, high = np.array([204, 205, 206]), np.array([235, 235, 235])
    rgb = low[None, None, :] + normalized[:, :, None]*(high-low)[None, None, :]
    contour = np.abs((th/.055+.5) % 1-.5) < .025
    if a.view=='overview':rgb[contour] *= .88
    texture = a.output/f'ground-{k+1}.png'
    Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).save(texture)
    ET.SubElement(asset, 'texture', name='elevation', type='2d', file=str(texture))
    ET.SubElement(asset, 'material', name='ground_mat', texture='elevation', texuniform='false', reflectance='0', specular='.04')
    red = tire_color(LOSSES[k])
    ET.SubElement(asset, 'material', name='red_tire', rgba=' '.join(map(str, (*red, 1))), emission='0', specular='0')
    world = ET.SubElement(root, 'worldbody')
    # A broad cluster of dim lights produces softer overlapping contact shadows.
    for dx, dy in ((-.28,-.20),(-.10,-.20),(.08,-.20),(-.28,.02),(-.10,.02),(.08,.02)):
        ET.SubElement(world, 'light', pos='-3 4 9', dir=f'{dx} {dy} -1',
                      diffuse='.065 .065 .065', specular='0 0 0', directional='true')
    ET.SubElement(world, 'geom', type='hfield', hfield='ground', pos=f'0 0 {HFIELD_BASE}', material='ground_mat')
    robot = ET.SubElement(world, 'body', name='jackal')
    ET.SubElement(robot, 'freejoint')
    ET.SubElement(robot, 'inertial', pos='0 0 .09', mass='16.523', diaginertia='.31 .39 .45')
    frame_color = (.60, .63, .65, 1)
    # Open chassis rails, crossmembers and exposed axles; no shell or fenders.
    for yy in (-.125, .125):
        capsule(robot, (-.21, yy, .11), (.21, yy, .11), .014, frame_color)
    for xx in (-.21, .21):
        capsule(robot, (xx, -.125, .11), (xx, .125, .11), .014, frame_color)
    capsule(robot, (-.21, -.125, .11), (.21, .125, .11), .009, frame_color)
    capsule(robot, (-.21, .125, .11), (.21, -.125, .11), .009, frame_color)
    for xx in (-.131, .131):
        capsule(robot, (xx, -.187795, .0345), (xx, .187795, .0345), .014, frame_color)
        for yy in (-.125, .125):
            capsule(robot, (xx, yy, .0345), (xx, yy, .11), .012, frame_color)
    # Small arrow at the front helps read heading throughout the figure-eight.
    capsule(robot, (.09, 0, .13), (.23, 0, .13), .01, frame_color)
    for yy in (-.045, .045):
        capsule(robot, (.23, 0, .13), (.16, yy, .13), .009, frame_color)
    for name, xx, yy in [('fl', .131, .187795), ('fr', .131, -.187795), ('rl', -.131, .187795), ('rr', -.131, -.187795)]:
        wheel = ET.SubElement(robot, 'body', name=name, pos=f'{xx} {yy} .0345')
        ET.SubElement(wheel, 'joint', name=name, axis='0 1 0')
        attributes = dict(material='red_tire') if name == 'fl' else dict(rgba='.48 .50 .52 1')
        ET.SubElement(wheel, 'geom', type='cylinder', size='.095 .02', euler='1.570796 0 0', mass='.477', **attributes)
        # A slightly darker red spoke shows wheel rotation while leaving the full tire red.
        spoke = (*red*.66, 1) if name == 'fl' else (.52, .54, .54, 1)
        for side in (-.016, .016):
            capsule(wheel, (-.07, side, 0), (.07, side, 0), .004, spoke)
    # Eight separated open-frame instances share the terrain but sample different impairments.
    world.remove(robot)
    robot_records = []
    for i, center in enumerate(ROBOT_CENTERS):
        color_index = (i + 3*k) % 8
        color = tire_color(LOSSES[color_index])
        material_name = f'red_tire_{i}'
        ET.SubElement(asset, 'material', name=material_name, rgba=' '.join(map(str, (*color, 1))), emission='0', specular='0')
        instance = copy.deepcopy(robot)
        fl = instance.find("body[@name='fl']")
        fl.find("geom[@type='cylinder']").set('material', material_name)
        fl.find("geom[@type='cylinder']").set('name', 'fl_tire')
        for spoke in fl.findall("geom[@type='capsule']"):
            spoke.set('rgba', ' '.join(map(str, (*color*.66, 1))))
        for node in instance.iter():
            if node.get('name'):
                node.set('name', f"r{i}_{node.get('name')}")
        world.append(instance)
        robot_records.append(dict(robot=i+1, route=ROUTES[k][i],
                                  front_left_drive_loss=LOSSES[color_index], tire_rgba=[*map(float, color), 1.0], frames=[]))
    model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
    model.hfield_data[:] = ((h-HFIELD_BASE)/HFIELD_RANGE).ravel()
    data = mujoco.MjData(model)
    assert model.nq == 88
    models.append(model)
    datas.append(data)
    records.append(dict(sample=k+1, depth_parameter_m=DEPTHS[k],
                        terrain_size_m=[SIDE, SIDE], terrain_height_range_m=[float(h.min()), float(h.max())],
                        snow_depth_range_m=[float((height(x,y)-h).min()), float((height(x,y)-h).max())], robots=robot_records))
    if not a.no_render:
        camera = mujoco.MjvCamera()
        camera.lookat[:] = CAMERA_TARGET
        camera.distance = CAMERA_DISTANCE
        camera.azimuth = CAMERA_AZIMUTH
        camera.elevation = CAMERA_ELEVATION
        camera.orthographic = 0
        cameras.append(camera)
        renderers.append(mujoco.Renderer(model, TILE, TILE, max_geom=len(GRID_SEGMENTS)+1000))

scene_option=mujoco.MjvOption()

writer = None
if not a.no_render:
    writer = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                               '-s', f'{4*TILE}x{2*TILE}', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-crf', '20',
                               '-preset', 'fast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(a.output/'domains.mp4')], stdin=subprocess.PIPE)
for frame in range(round(a.seconds*FPS/PLAYBACK_SPEED)):
    t = (frame+1)*PLAYBACK_SPEED/FPS
    canvas = np.full((2*TILE, 4*TILE, 3), 255, dtype=np.uint8) if writer else None
    for k, (model, data) in enumerate(zip(models, datas)):
        for i, center in enumerate(ROBOT_CENTERS):
            route_query = lambda time: robot_reference(time, k, i)
            pose, rotation, v, w = terrain_pose(t, height_query=lambda xx, yy: ground_height(xx, yy, k), reference_query=route_query)
            q = i*11
            data.qpos[q:q+3], data.qpos[q+3:q+7] = pose, quat_wxyz(rotation)
            left, right = (v-w*.37559/2)/.095, (v+w*.37559/2)/.095
            wheel_angles[k, i] += np.array([left, right, left, right])*PLAYBACK_SPEED/FPS
            data.qpos[q+7:q+11] = wheel_angles[k, i]
            records[k]['robots'][i]['frames'].append(dict(t=t, x=float(pose[0]), y=float(pose[1]), z=float(pose[2]), yaw=route_query(t)[1], speed=v))
        data.qvel[:] = 0
        data.time = t
        mujoco.mj_forward(model, data)
        if writer:
            renderer = renderers[k]
            focus = FOCUS_ROBOTS[k]
            subject = data.qpos[focus*11:focus*11+3]
            if a.view == 'detail':
                cameras[k].lookat[:] = subject+CAMERA_TARGET
            renderer.update_scene(data, cameras[k], scene_option=scene_option)
            # Line primitives do not cast shadows. The grid remains fixed in world
            # coordinates as the camera follows the robot. Frustum culling drops
            # only offscreen segments, retaining the grid all the way to the horizon.
            scene = renderer.scene
            segments = GRID_SEGMENTS
            if a.view == 'detail':
                forward = -CAMERA_OFFSET/CAMERA_DISTANCE
                right = np.cross(forward, [0.,0.,1.])
                right /= np.linalg.norm(right)
                up = np.cross(right,forward)
                relative = GRID_MIDPOINTS-(subject+CAMERA_POSITION)
                depth = relative@forward
                limit = depth*math.tan(math.radians(CAMERA_FOV)/2)+.12
                visible = (depth>0)&(np.abs(relative@right)<limit)&(np.abs(relative@up)<limit)
                segments = GRID_SEGMENTS[visible]
            # Fade reference lines immediately around each robot so a floating
            # snow-surface line cannot obscure the red tire or chassis silhouette.
            centers = data.qpos.reshape(8,11)[:,:2]
            distance = np.linalg.norm(segments.mean(axis=1)[:,None,:2]-centers[None,:,:],axis=2).min(axis=1)
            opacity = .26*np.clip((distance-.32)/.20,0,1)
            for (first, second), alpha in zip(segments, opacity):
                if alpha < .01:
                    continue
                geom = scene.geoms[scene.ngeom]
                mujoco.mjv_initGeom(geom, mujoco.mjtGeom.mjGEOM_LINE,
                                   np.zeros(3), np.zeros(3), np.eye(3).ravel(),
                                   np.array([.35,.38,.41,alpha],dtype=np.float32))
                mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_LINE,1.,first,second)
                scene.ngeom += 1
            im=Image.fromarray(renderer.render())
            if a.view == 'detail':
                draw=ImageDraw.Draw(im)
                draw.text((16,14),f'{k+1:02}',font=FONT,fill=(50,46,47),stroke_width=2,stroke_fill=(250,249,246))
                depth=float(height(*subject[:2])-ground_height(*subject[:2],k))
                draw.text((16,TILE-48),f'Δh {depth:.2f} m',font=FONT,fill=(50,46,47),stroke_width=2,stroke_fill=(250,249,246))
            row, col = divmod(k, 4)
            canvas[row*TILE:(row+1)*TILE, col*TILE:(col+1)*TILE] = np.asarray(im)
    if writer:
        if frame in (0, 96, 192, 288, 383):
            Image.fromarray(canvas).save(a.output/f'domains-{frame:03}.jpg')
        writer.stdin.write(canvas.tobytes())
    if frame % 48 == 0:
        print('FRAME', frame, 'environments', len(models), 'robots', 8*len(models), flush=True)
if writer:
    writer.stdin.close()
    assert writer.wait() == 0
for renderer in renderers:
    renderer.close()
(a.output/'domains-manifest.json').write_text(json.dumps(dict(
    engine='MuJoCo', camera_view=a.view, focus_robots=FOCUS_ROBOTS, inference='none; handcrafted illustrative posterior samples',
    motion='prescribed terrain-following figure-eight and rolling wheels; not a policy or physical parameter evaluation',
    layout=[2,4], robots_per_environment=8, robot_scale=1.0, wheel_radius_m=.095, wheel_width_m=.04, camera=dict(projection='perspective', position_m=CAMERA_POSITION.tolist(), target_m=CAMERA_TARGET.tolist(), elevation_deg=CAMERA_ELEVATION, fov_deg=CAMERA_FOV, matches='Chrono viewing direction and FOV; detail follows a selected original-scale robot'), robot_visual='open-frame Jackal with full red front-left tire',
    terrain_size_m=[SIDE,SIDE], snow_reference='world-fixed dashed grid across the entire observed snow surface in every environment',
    grid=dict(spacing_m=GRID_SPACING, dash_period_m=GRID_DASH_PERIOD, dash_length_m=GRID_DASH_LENGTH, extent_m=[SIDE,SIDE]),
    rendering_style='matte gray chassis and terrain, broad six-light illumination, red front-left tires',
    reference='independent rotated figure-eights; per-robot amplitudes, centers, phase, direction, lap count and smooth speed modulation', playback_speed=PLAYBACK_SPEED, samples=records), indent=2))
print('FINISHED', flush=True)
