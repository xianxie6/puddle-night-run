# 把 three.js 示例 Soldier.glb（Mixamo 动捕，MIT）里的 Run / Idle 动作重定向到 Marisol，导出 跑/marisol.glb
# 用法: blender -b -P blender/retarget_mocap.py -- <marisol-original.glb> <Soldier.glb> <输出目录> [--preview Run 帧号 side|front]
import bpy, math, sys, os
from mathutils import Matrix, Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
TGT, SRC, OUT = argv[:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

bpy.ops.import_scene.gltf(filepath=SRC)
src = [o for o in scn.objects if o.type == 'ARMATURE'][0]; src.name = 'SRC'
src_actions = {a.name: a for a in bpy.data.actions}
src_meshes = [o for o in scn.objects if o.type != 'ARMATURE']
for o in src_meshes: bpy.data.objects.remove(o)
before = set(scn.objects)
bpy.ops.import_scene.gltf(filepath=TGT)
tgt = [o for o in scn.objects if o.type == 'ARMATURE' and o not in before][0]
for a in list(bpy.data.actions):
    if a.name not in src_actions: bpy.data.actions.remove(a)
tgt.animation_data_create(); tgt.animation_data.action = None
src.animation_data_create()
for tr in list(src.animation_data.nla_tracks): src.animation_data.nla_tracks.remove(tr)
def use_src(act):
    src.animation_data.action = act
    if hasattr(src.animation_data, 'action_slot') and len(getattr(act, 'slots', [])):
        src.animation_data.action_slot = act.slots[0]

def V(): bpy.context.view_layer.update()
RZ = Matrix.Rotation(math.pi, 4, 'Z')            # Soldier 面朝 +Y、左手在 -X；Marisol 面朝 -Y
RZq = RZ.to_quaternion()
M = 'mixamorig:'
sw = src.matrix_world; tw = tgt.matrix_world; twi = tw.inverted()
spb, tpb = src.pose.bones, tgt.pose.bones

def s_head(n): return RZ @ (sw @ spb[M + n].head)
def s_rot(n): return RZq @ (sw @ spb[M + n].matrix).to_3x3().normalized().to_quaternion()
def s_rest(n): return RZq @ (sw @ src.data.bones[M + n].matrix_local).to_3x3().normalized().to_quaternion()
def t_world(n): return tw @ tpb[n].matrix
def t_rest(n): return (tw @ tgt.data.bones[n].matrix_local).to_3x3().normalized().to_quaternion()

def set_rot(n, q, pos=None):
    W = t_world(n); p = pos if pos is not None else W.translation
    tpb[n].matrix = twi @ (Matrix.Translation(p) @ q.to_matrix().to_4x4()); V()

def match_dir(n, dsrc, tail_of=None):
    W = t_world(n); h = tw @ tpb[n].head; t = tw @ tpb[n].tail
    q = (t - h).normalized().rotation_difference(dsrc.normalized())
    set_rot(n, q @ W.to_3x3().normalized().to_quaternion())

DELTA = {'hips': 'Hips', 'spine': 'Spine2', 'head': 'Head'}
DIRS = []
for s, S in (('L', 'Left'), ('R', 'Right')):
    DIRS += [(f'thigh_{s}', f'{S}UpLeg', f'{S}Leg'), (f'shin_{s}', f'{S}Leg', f'{S}Foot'), (f'foot_{s}', f'{S}Foot', f'{S}ToeBase')]
for s, S in (('L', 'Left'), ('R', 'Right')):
    DIRS += [(f'upperarm_{s}', f'{S}Arm', f'{S}ForeArm'), (f'forearm_{s}', f'{S}ForeArm', f'{S}Hand'), (f'hand_{s}', f'{S}Hand', f'{S}HandMiddle1')]

src_hip_rest = RZ @ (sw @ src.data.bones[M + 'Hips'].head_local)
tgt_hip_rest = tw @ tgt.data.bones['hips'].head_local
leg_s = (sw @ src.data.bones[M + 'Hips'].head_local).z
leg_t = tgt_hip_rest.z
K = leg_t / leg_s
print('SCALE', round(K, 3))

def pose_frame():
    for b in tpb: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0)
    V()
    hp = s_head('Hips') - src_hip_rest
    pos = tgt_hip_rest + Vector((hp.x * K, 0, hp.z * K))       # 原地跑：去掉前后位移
    for n, sn in DELTA.items():
        q = s_rot(sn) @ s_rest(sn).inverted() @ t_rest(n)
        set_rot(n, q, pos if n == 'hips' else None)
    for n, a, b in DIRS:
        match_dir(n, s_head(b) - s_head(a))

def bake(name, out_name, frames):
    act = src_actions[name]; use_src(act)
    f0, f1 = act.frame_range
    new = bpy.data.actions.new(out_name); new.use_fake_user = True
    tgt.animation_data.action = new
    for i in range(frames + 1):
        t = f0 + (f1 - f0) * (i % frames) / frames
        scn.frame_set(int(t), subframe=t - int(t)); pose_frame()
        for b in tpb:
            b.keyframe_insert('rotation_quaternion', frame=i); b.keyframe_insert('location', frame=i)
    return new

def run_speed(frames=40):
    """支撑脚相对髋部向后滑的速度 = 实际奔跑速度"""
    act = src_actions['Run']; use_src(act); f0, f1 = act.frame_range
    dur = (f1 - f0) / scn.render.fps; pts = []
    for i in range(frames):
        t = f0 + (f1 - f0) * i / frames; scn.frame_set(int(t), subframe=t - int(t))
        pts.append(s_head('LeftToeBase') - s_head('Hips'))
    lowz = min(p.z for p in pts); v = []
    for i in range(frames):
        a, b = pts[i], pts[(i + 1) % frames]
        if a.z < lowz + .04 * leg_s: v.append(abs(b.y - a.y) / (dur / frames))
    return sum(v) / max(1, len(v)) * K, dur

spd, dur = run_speed()
print('RUN_SPEED', round(spd, 3), 'CYCLE', round(dur, 3))

run = bake('Run', 'Run', 20)
idle = bake('Idle', 'Idle', 60)
for a in (run, idle):
    tr = tgt.animation_data.nla_tracks.new(); tr.name = a.name; tr.strips.new(a.name, 0, a)
tgt.animation_data.action = None

if '--preview' in argv:
    i = argv.index('--preview'); act, fr, view = argv[i + 1], int(argv[i + 2]), argv[i + 3]
    bpy.data.objects.remove(src)
    for tr in list(tgt.animation_data.nla_tracks): tgt.animation_data.nla_tracks.remove(tr)
    A = bpy.data.actions[act]; tgt.animation_data.action = A
    if len(A.slots): tgt.animation_data.action_slot = A.slots[0]
    scn.frame_set(fr)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam)
    if view == 'side': cam.location = (3.2, 0, .8); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    else: cam.location = (0, -3.2, .8); cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.color_type = 'TEXTURE'
    scn.render.resolution_x, scn.render.resolution_y = 400, 500
    scn.render.filepath = os.path.join(OUT, f'rt_{act}_{fr}_{view}.png'); bpy.ops.render.render(write_still=True)
    sys.exit(0)

bpy.data.objects.remove(src)
for a in list(src_actions.values()): bpy.data.actions.remove(a)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'marisol.glb'), export_format='GLB', export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_yup=True)
print('EXPORTED')
