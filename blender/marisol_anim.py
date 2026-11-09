# 给《请记住我》里的 Marisol 加 Run / Idle 动画，导出到 跑/marisol.glb
# 用法: blender -b -P blender/marisol_anim.py -- <src.glb> <out_dir> [--preview 帧号]
import bpy, math, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
scn = bpy.context.scene; scn.render.fps = 30
rig = [o for o in scn.objects if o.type == 'ARMATURE'][0]
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
rig.animation_data_create(); rig.animation_data.action = None
pb = rig.pose.bones
print('BONES', [b.name for b in pb])

S = -1.0
from mathutils import Matrix
def reset():
    for b in pb: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    bpy.context.view_layer.update()

def wrot(name, axis, ang):
    """绕骨骼头部、按骨架空间的世界轴旋转（axis: 'X' 侧向轴 / 'Y' 前后轴 / 'Z' 竖直轴）"""
    b = pb[name]; M = b.matrix.copy(); p = M.translation.copy()
    R = Matrix.Rotation(ang, 4, axis)
    b.matrix = Matrix.Translation(p) @ R @ Matrix.Translation(-p) @ M
    bpy.context.view_layer.update()

ARM_DOWN = float(os.environ.get('ARM_DOWN', '0.85'))   # 静止是 A 字手，先把手臂放下来

def arms(swingL, swingR, elbowL, elbowR):
    for side, sw, el, sg in (('L', swingL, elbowL, 1), ('R', swingR, elbowR, -1)):
        wrot(f'upperarm_{side}', 'Y', sg * ARM_DOWN)       # 放下
        wrot(f'upperarm_{side}', 'X', sw)                  # 前后摆
        wrot(f'forearm_{side}', 'X', el)                   # 屈肘（前臂向前抬）

def run_pose(ph):
    reset(); s = math.sin(ph)
    pb['hips'].location = (0, abs(math.cos(ph)) * .05 - .04, 0); bpy.context.view_layer.update()
    wrot('hips', 'X', S * .1); wrot('hips', 'Z', s * .12)
    wrot('spine', 'X', S * .08); wrot('spine', 'Z', -s * .22)
    wrot('head', 'X', -S * .12)
    for side, p2 in (('L', ph), ('R', ph + math.pi)):
        ls, lc = math.sin(p2), math.cos(p2); lift = max(0, -lc)
        wrot(f'thigh_{side}', 'X', S * (ls * .65 + .15))
        wrot(f'shin_{side}', 'X', -S * (.2 + 1.4 * lift * (1 if ls > -.3 else .5) + .25 * max(0, -ls)))
        wrot(f'foot_{side}', 'X', -S * (.1 + .3 * max(0, ls) - .3 * lift))
    arms(-S * (s * .65 - .1), S * (s * .65 + .1), S * (.6 + .35 * max(0, -s)), S * (.6 + .35 * max(0, s)))

def idle_pose(ph):
    reset(); b = math.sin(ph)
    pb['hips'].location = (0, b * .005 - .005, 0); bpy.context.view_layer.update()
    wrot('spine', 'X', S * b * .02)
    wrot('head', 'X', S * .04 * math.sin(ph * .5)); wrot('head', 'Z', .08 * math.sin(ph * .5 + 1))
    arms(S * .05, S * .05, S * .25, S * .25)

def bake(name, fn, frames):
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data.action = act
    for f in range(frames + 1):
        fn(2 * math.pi * f / frames)
        for b in pb:
            b.keyframe_insert('rotation_quaternion', frame=f); b.keyframe_insert('location', frame=f)
    return act

run = bake('Run', run_pose, 20); idle = bake('Idle', idle_pose, 90)
for a in (run, idle):
    tr = rig.animation_data.nla_tracks.new(); tr.name = a.name; tr.strips.new(a.name, 0, a)
rig.animation_data.action = None

if '--preview' in argv:
    rig.animation_data.action = run; scn.frame_set(int(argv[argv.index('--preview') + 1]))
    mn = Vector((9, 9, 9)); mx = Vector((-9, -9, -9))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam)
    view = os.environ.get('VIEW', 'side')
    if view == 'side': cam.location = (3.2, 0, .8); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    else: cam.location = (0, -3.2, .8); cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam
    scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.color_type = 'TEXTURE'
    scn.render.resolution_x, scn.render.resolution_y = 500, 600
    scn.render.filepath = os.path.join(OUT, f'm_{view}.png'); bpy.ops.render.render(write_still=True)
    sys.exit(0)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'marisol.glb'), export_format='GLB', export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_yup=True)
print('EXPORTED')
