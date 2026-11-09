# 用法: blender -b -P blender/build_girl.py -- <输出目录>
# 程序化生成：女孩模型 + 骨骼 + 蒙皮权重 + Run / Idle 动画，导出 girl.glb
import bpy, bmesh, math, sys, os
from mathutils import Vector

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.getcwd()
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = 30

def mat(name, color, rough=0.6, emit=None, strength=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m

SKIN  = mat('skin',  (0.90, 0.66, 0.53), 0.55)
SHIRT = mat('shirt', (0.86, 0.88, 0.90), 0.8)
SKIRT = mat('skirt', (0.06, 0.09, 0.20), 0.7)
SOCK  = mat('sock',  (0.92, 0.92, 0.92), 0.85)
SHOE  = mat('shoe',  (0.28, 0.12, 0.05), 0.45)
HAIR  = mat('hair',  (0.025, 0.014, 0.010), 0.38)
SCARF = mat('scarf', (0.62, 0.05, 0.05), 0.6)
EYE   = mat('eye',   (0.02, 0.015, 0.02), 0.15)
SHINE = mat('shine', (1, 1, 1), 0.2, emit=(1, 1, 1), strength=2.0)
BLUSH = mat('blush', (0.95, 0.45, 0.42), 0.6)

# ---------------- 骨骼定义 (Blender: Z 向上, 脸朝 -Y) ----------------
BONES = {  # name: (head, tail, parent)
    'hips':      ((0, 0, .86),  (0, 0, 1.02), None),
    'spine':     ((0, 0, 1.02), (0, 0, 1.17), 'hips'),
    'chest':     ((0, 0, 1.17), (0, 0, 1.30), 'spine'),
    'neck':      ((0, 0, 1.30), (0, 0, 1.36), 'chest'),
    'head':      ((0, 0, 1.36), (0, 0, 1.62), 'neck'),
    'tail1':     ((0, .11, 1.53), (0, .19, 1.36), 'head'),
    'tail2':     ((0, .19, 1.36), (0, .20, 1.12), 'tail1'),
}
for s, x in (('L', 1), ('R', -1)):
    BONES.update({
        f'thigh.{s}':   ((.085*x, 0, .84), (.088*x, -.01, .47), 'hips'),
        f'shin.{s}':    ((.088*x, -.01, .47), (.088*x, .01, .09), f'thigh.{s}'),
        f'foot.{s}':    ((.088*x, .01, .09), (.088*x, -.11, .03), f'shin.{s}'),
        f'upperarm.{s}':((.155*x, 0, 1.255), (.19*x, .005, 1.02), 'chest'),
        f'forearm.{s}': ((.19*x, .005, 1.02), (.205*x, -.01, .80), f'upperarm.{s}'),
        f'hand.{s}':    ((.205*x, -.01, .80), (.21*x, -.015, .71), f'forearm.{s}'),
    })

# ---------------- 身体：Skin 修改器长出有机形体 ----------------
nodes = {  # name: (pos, radius_x, radius_y)
    'pelvis': ((0, 0, .86), .118, .085), 'waist': ((0, 0, 1.0), .092, .07),
    'chest': ((0, 0, 1.16), .112, .078), 'neckb': ((0, 0, 1.29), .045, .045), 'neckt': ((0, 0, 1.38), .038, .038),
}
edges = [('pelvis', 'waist'), ('waist', 'chest'), ('chest', 'neckb'), ('neckb', 'neckt')]
for s, x in (('L', 1), ('R', -1)):
    nodes.update({
        f'hip{s}': ((.08*x, 0, .80), .074, .074), f'knee{s}': ((.088*x, -.01, .47), .048, .05),
        f'calf{s}': ((.088*x, .005, .33), .046, .048), f'ankle{s}': ((.088*x, .01, .1), .032, .034),
        f'heel{s}': ((.088*x, .02, .04), .036, .036), f'toe{s}': ((.088*x, -.10, .035), .038, .03),
        f'sho{s}': ((.15*x, 0, 1.25), .046, .046), f'elb{s}': ((.19*x, .005, 1.02), .033, .033),
        f'wri{s}': ((.205*x, -.01, .80), .026, .024), f'hand{s}': ((.21*x, -.015, .73), .032, .02),
    })
    edges += [('pelvis', f'hip{s}'), (f'hip{s}', f'knee{s}'), (f'knee{s}', f'calf{s}'), (f'calf{s}', f'ankle{s}'),
              (f'ankle{s}', f'heel{s}'), (f'heel{s}', f'toe{s}'), ('chest', f'sho{s}'), (f'sho{s}', f'elb{s}'),
              (f'elb{s}', f'wri{s}'), (f'wri{s}', f'hand{s}')]
names = list(nodes)
me = bpy.data.meshes.new('body'); me.from_pydata([nodes[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
body = bpy.data.objects.new('Body', me); scn.collection.objects.link(body)
sk = body.modifiers.new('skin', 'SKIN'); sk.use_smooth_shade = True
for i, n in enumerate(names):
    d = me.skin_vertices[0].data[i]; d.radius = (nodes[n][1], nodes[n][2]); d.use_root = (n == 'pelvis')
sub = body.modifiers.new('sub', 'SUBSURF'); sub.levels = sub.render_levels = 2
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.modifier_apply(modifier='skin'); bpy.ops.object.modifier_apply(modifier='sub')
for m in (SKIN, SHIRT, SOCK, SHOE): body.data.materials.append(m)
for p in body.data.polygons:
    c = p.center; ax = abs(c.x)
    if c.z < .075: p.material_index = 3                          # 鞋
    elif c.z < .30 and ax < .14: p.material_index = 2            # 袜子
    elif ax < .135 and .80 < c.z < 1.31: p.material_index = 1     # 上衣
    elif ax >= .135 and c.z > 1.08: p.material_index = 1          # 短袖
bpy.ops.object.shade_smooth()

parts = []
def add(obj, m, bone=None):
    obj.data.materials.append(m)
    for p in obj.data.polygons: p.use_smooth = True
    obj['bone'] = bone or ''
    parts.append(obj); return obj

def sphere(name, loc, r, scale=(1, 1, 1), seg=40, ring=28):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=ring, radius=r, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True); return o

# 头 + 脸
head = add(sphere('Head', (0, -.005, 1.455), .112, (1, .96, 1.07)), SKIN, 'head')
for x in (1, -1):
    add(sphere('Eye', (.042*x, -.098, 1.445), .019, (1, .45, 1.35), 16, 12), EYE, 'head')
    add(sphere('Shine', (.036*x, -.106, 1.457), .0055, (1, .5, 1), 8, 6), SHINE, 'head')
    add(sphere('Blush', (.066*x, -.088, 1.415), .016, (1, .3, .6), 12, 8), BLUSH, 'head')
    add(sphere('Ear', (.11*x, .0, 1.445), .02, (.5, .8, 1.2), 12, 8), SKIN, 'head')

# 头发：头盔状发壳 + 刘海 + 马尾
hair = sphere('Hair', (0, .006, 1.47), .123, (1.02, 1.0, 1.06), 48, 32)
bm = bmesh.new(); bm.from_mesh(hair.data)
cut = [v for v in bm.verts if (v.co.z < -.02 and v.co.y < -.03) or v.co.z < -.085]
bmesh.ops.delete(bm, geom=cut, context='VERTS'); bm.to_mesh(hair.data); bm.free()
sol = hair.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = .012
bpy.context.view_layer.objects.active = hair; bpy.ops.object.modifier_apply(modifier='sol')
add(hair, HAIR, 'head')
for i, x in enumerate((-.06, -.02, .025, .065)):        # 刘海几缕
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=.03, depth=.09, location=(x, -.105, 1.47))
    o = bpy.context.object; o.rotation_euler = (math.radians(180 - 12), 0, math.radians(x * 120)); o.scale = (1, .45, 1)
    bpy.ops.object.transform_apply(rotation=True, scale=True); add(o, HAIR, 'head')
# 马尾（Skin 链）
tm = bpy.data.meshes.new('tail'); tp = [(0, .11, 1.53), (0, .17, 1.44), (0, .2, 1.32), (0, .2, 1.2), (0, .19, 1.1)]
tm.from_pydata(tp, [(i, i+1) for i in range(4)], [])
tail = bpy.data.objects.new('Tail', tm); scn.collection.objects.link(tail)
m = tail.modifiers.new('skin', 'SKIN')
for i, r in enumerate((.04, .055, .052, .038, .008)):
    tm.skin_vertices[0].data[i].radius = (r, r*.8); tm.skin_vertices[0].data[i].use_root = i == 0
tail.modifiers.new('sub', 'SUBSURF').levels = 2
bpy.context.view_layer.objects.active = tail
bpy.ops.object.modifier_apply(modifier='skin'); bpy.ops.object.modifier_apply(modifier='sub')
add(tail, HAIR, 'auto')
add(sphere('Ribbon', (0, .12, 1.54), .028, (1.8, .6, 1), 16, 10), SCARF, 'head')

# 围巾 & 裙子
bpy.ops.mesh.primitive_torus_add(major_radius=.058, minor_radius=.024, location=(0, 0, 1.305))
add(bpy.context.object, SCARF, 'chest')
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=.25, radius2=.125, depth=.24, location=(0, 0, .77), end_fill_type='NOTHING')
skirt = bpy.context.object
bm = bmesh.new(); bm.from_mesh(skirt.data)
for v in bm.verts:                                  # 百褶
    if v.co.z < 0:
        a = math.atan2(v.co.y, v.co.x); k = 1 + .06 * math.sin(a * 16)
        v.co.x *= k; v.co.y *= k
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > .1], cuts=3)
bm.to_mesh(skirt.data); bm.free()
sol = skirt.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = .008
bpy.context.view_layer.objects.active = skirt; bpy.ops.object.modifier_apply(modifier='sol')
add(skirt, SKIRT, 'skirt')

# ---------------- 合并 & 蒙皮 ----------------
arm_data = bpy.data.armatures.new('Rig'); rig = bpy.data.objects.new('Rig', arm_data); scn.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
for n, (h, t, p) in BONES.items():
    b = arm_data.edit_bones.new(n); b.head = h; b.tail = t
    b.roll = 0
for n, (h, t, p) in BONES.items():
    if p: arm_data.edit_bones[n].parent = arm_data.edit_bones[p]; arm_data.edit_bones[n].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

def seg_dist(p, a, b):
    a, b = Vector(a), Vector(b); ab = b - a
    t = max(0, min(1, (p - a).dot(ab) / ab.length_squared)); return (p - (a + ab * t)).length, t

def weigh(obj, mode):
    vg = {n: obj.vertex_groups.new(name=n) for n in BONES}
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        if mode not in ('auto', 'skirt', ''):
            vg[mode].add([v.index], 1.0, 'REPLACE'); continue
        cands = list(BONES)
        if mode == 'auto': cands = ['head', 'tail1', 'tail2']
        if mode == '':  # 身体：手臂与躯干、左右腿互不串
            side = 'L' if p.x > 0 else 'R'
            cands = [n for n in BONES if not n.startswith('tail') and n != 'head' and not n.endswith('.' + ('R' if side == 'L' else 'L'))]
        if mode == 'skirt':
            side = 'L' if p.x > 0 else 'R'
            ws = {'hips': 1.0}
            depth = max(0, (.86 - p.z) / .2)
            ws[f'thigh.{side}'] = depth * .9 * min(1, abs(p.x) / .12)
            tot = sum(ws.values())
            for n, w in ws.items(): vg[n].add([v.index], w / tot, 'REPLACE')
            continue
        ds = sorted(((seg_dist(p, BONES[n][0], BONES[n][1])[0], n) for n in cands))[:3]
        ws = [(1 / max(d, 1e-4) ** 6, n) for d, n in ds]; tot = sum(w for w, _ in ws)
        for w, n in ws: vg[n].add([v.index], w / tot, 'REPLACE')

weigh(body, '')
for o in parts: weigh(o, o['bone'])
bpy.ops.object.select_all(action='DESELECT')
for o in [body] + parts: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
girl = bpy.context.object; girl.name = 'Girl'
girl.parent = rig; mod = girl.modifiers.new('rig', 'ARMATURE'); mod.object = rig

# ---------------- 动画 ----------------
rig.animation_data_create()
pb = rig.pose.bones
for b in pb: b.rotation_mode = 'XYZ'

def key_all(f):
    for b in pb:
        b.keyframe_insert('rotation_euler', frame=f); b.keyframe_insert('location', frame=f)

def reset():
    for b in pb: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)

S = float(sys.argv[sys.argv.index('--sign') + 1]) if '--sign' in sys.argv else -1.0

def run_pose(ph):
    reset(); s, c = math.sin(ph), math.cos(ph)
    pb['hips'].location = (0, abs(math.cos(ph)) * .055 - .045, 0)   # bone Y = 世界 Z
    pb['hips'].rotation_euler = (S * .12, s * .12, 0)
    pb['spine'].rotation_euler = (S * .06, -s * .14, 0)
    pb['chest'].rotation_euler = (0, -s * .12, 0)
    pb['neck'].rotation_euler = (-S * .1, 0, 0)
    pb['head'].rotation_euler = (-S * .06, s * .1, 0)
    for side, p2 in (('L', ph), ('R', ph + math.pi)):
        ls, lc = math.sin(p2), math.cos(p2)
        lift = max(0, -lc)                       # 摆动腿抬起
        pb[f'thigh.{side}'].rotation_euler = (S * (ls * .65 + .15), 0, 0)
        pb[f'shin.{side}'].rotation_euler = (-S * (.2 + 1.4 * lift * (1 if ls > -.3 else .5) + .25 * max(0, -ls)), 0, 0)
        pb[f'foot.{side}'].rotation_euler = (-S * (.1 + .3 * max(0, ls) - .3 * lift), 0, 0)
    # 右手摆臂，左手提灯
    pb['upperarm.R'].rotation_euler = (-S * (math.sin(ph) * .8 - .1), 0, -.14)
    pb['forearm.R'].rotation_euler = (S * (1.2 + .45 * max(0, -s)), 0, 0)
    pb['upperarm.L'].rotation_euler = (S * (math.sin(ph) * .8 + .1), 0, .14)
    pb['forearm.L'].rotation_euler = (S * (1.2 + .45 * max(0, s)), 0, 0)
    pb['tail1'].rotation_euler = (S * (-.5 + .15 * math.sin(2 * ph)), 0, .25 * c)
    pb['tail2'].rotation_euler = (S * (-.25 + .2 * math.sin(2 * ph - .8)), 0, .2 * math.cos(ph - .7))

def idle_pose(ph):
    reset(); b = math.sin(ph)
    pb['hips'].location = (0, b * .006 - .006, 0)
    pb['chest'].rotation_euler = (S * b * .02, 0, 0)
    pb['head'].rotation_euler = (S * .04 * math.sin(ph * .5), .08 * math.sin(ph * .5 + 1), 0)
    for side in 'LR':
        pb[f'thigh.{side}'].rotation_euler = (0, 0, 0)
    pb['upperarm.R'].rotation_euler = (0, 0, -.1)
    pb['forearm.R'].rotation_euler = (-S * .15, 0, 0)
    pb['upperarm.L'].rotation_euler = (S * (.1 + b * .02), 0, .1)
    pb['forearm.L'].rotation_euler = (-S * .35, 0, 0)
    pb['tail1'].rotation_euler = (S * (-.15 + b * .03), 0, 0)
    pb['tail2'].rotation_euler = (S * -.05, 0, .04 * b)

def bake(name, fn, frames):
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data.action = act
    for f in range(0, frames + 1, 1):
        fn(2 * math.pi * f / frames); key_all(f)
    return act

RUN_FRAMES = 20   # 0.667s 一个周期（两步）
run = bake('Run', run_pose, RUN_FRAMES)
idle = bake('Idle', idle_pose, 90)
for a in (run, idle):
    tr = rig.animation_data.nla_tracks.new(); tr.name = a.name
    tr.strips.new(a.name, 0, a)
rig.animation_data.action = None

if '--preview' in sys.argv:
    rig.animation_data.action = run; scn.frame_set(int(sys.argv[sys.argv.index('--preview') + 1]))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam)
    cam.location = (2.6, -.4, 1.0); cam.rotation_euler = (math.radians(88), 0, math.radians(82)); scn.camera = cam
    cam.data.lens = 50
    l = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scn.collection.objects.link(l); l.rotation_euler = (.6, .3, .8)
    scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'MATERIAL'
    scn.render.resolution_x, scn.render.resolution_y = 500, 600
    scn.render.filepath = os.path.join(OUT, 'preview.png'); bpy.ops.render.render(write_still=True)
    sys.exit(0)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'girl.glb'), export_format='GLB', export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_apply=False, export_yup=True)
print('EXPORTED', os.path.join(OUT, 'girl.glb'))
