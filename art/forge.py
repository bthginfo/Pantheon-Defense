"""Model, animate and export Pantheon Defense's original low-poly cast."""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "public" / "assets"
MODELS = ASSETS / "models"
SOURCES = ROOT / "art" / "blend"
PORTRAITS = ASSETS / "portraits"
CATALOG = json.loads((ASSETS / "catalog.json").read_text())
for directory in (MODELS, SOURCES, PORTRAITS):
    directory.mkdir(parents=True, exist_ok=True)

PALETTES = {
    "aegean": {"cloth":"2a8f8e", "shade":"183f56", "trim":"e0ae59", "stone":"d8c1a1", "leather":"7e4940", "light":"f3dfaa"},
    "rome": {"cloth":"a23937", "shade":"432c3c", "trim":"cd884e", "stone":"c18a72", "leather":"623d33", "light":"f4c095"},
    "japan": {"cloth":"4c766f", "shade":"26354a", "trim":"bb9b60", "stone":"9aa492", "leather":"664036", "light":"d0e4bb"},
    "rift": {"cloth":"562e4a", "shade":"302738", "trim":"f08c54", "stone":"65546c", "leather":"573b49", "light":"faad71"},
}

def rgba(hex_code):
    text = hex_code.lstrip("#")
    srgb = [int(text[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(value / 12.92 if value <= 0.04045 else ((value + .055) / 1.055) ** 2.4
                 for value in srgb) + (1,)

def material(name, color, metallic=0, glow=0):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = .45 if metallic else .76
    if glow:
        shader.inputs["Emission Color"].default_value = mat.diffuse_color
        shader.inputs["Emission Strength"].default_value = glow
    return mat

def palette(faction, accent):
    colors = PALETTES[faction]
    mats = {key: material(f"{faction}.{key}", color, .35 if key == "trim" else 0)
            for key, color in colors.items()}
    mats.update(
        accent=material(f"{faction}.{accent}.detail", accent, .13),
        glow=material(f"{faction}.{accent}.light", accent, glow=1.6),
        skin=material("Warm clay", "c58b66"),
        linen=material("Natural linen", "eee2c2"),
        steel=material("Brushed iron", "9bb3b8", .55),
        ink=material("Indigo shadow", "242733"),
        wood=material("Oiled hardwood", "805438"),
    )
    return mats

def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def attach(obj, name, mat, parent):
    obj.name = name
    obj.parent = parent
    if mat is not None:
        obj.data.materials.append(mat)
    return obj

def empty(name, loc=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = loc
    return obj

def box(name, loc, dims, mat, parent, tilt=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = attach(bpy.context.object, name, mat, parent)
    obj.scale = dims
    obj.rotation_euler = tilt
    return obj

def stone(name, loc, dims, mat, parent, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    obj = attach(bpy.context.object, name, mat, parent)
    obj.scale = dims
    return obj

def prism(name, loc, radius, height, mat, parent, sides=8, top=None, tilt=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=radius, radius2=radius if top is None else top,
                                    depth=height, location=loc, rotation=tilt)
    return attach(bpy.context.object, name, mat, parent)

def span(name, point_a, point_b, radius, mat, parent, sides=6, top=None):
    a, b = Vector(point_a), Vector(point_b)
    axis = b - a
    obj = prism(name, (a + b) * .5, radius, axis.length, mat, parent, sides, top)
    obj.rotation_euler = axis.to_track_quat("Z", "Y").to_euler()
    return obj

def sheet(name, points, faces, mat, parent, solid=.018):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach(obj, name, mat, parent)
    if solid:
        modifier = obj.modifiers.new("Material thickness", "SOLIDIFY")
        modifier.thickness = solid
    return obj

def shield(root, m, faction, hero=False):
    if faction == "rome":
        box("Curved scutum", (.04, -.115, -.30), (.42, .09, .61), m["cloth"], root, (.07, 0, 0))
        for x in (-.19, .27):
            box("Scutum brass binding", (x, -.171, -.29), (.042, .025, .58), m["trim"], root)
        box("Scutum ridge", (.04, -.183, -.29), (.33, .045, .08), m["trim"], root)
        stone("Scutum boss", (.04, -.214, -.29), (.098, .048, .09), m["steel"], root, 2)
        return
    size = .29 if hero else .235
    prism("Shield bronze rim", (.015, -.13, -.29), size, .075, m["trim"], root, 12,
          tilt=(math.pi / 2, 0, 0))
    prism("Shield dyed face", (.015, -.177, -.29), size * .86, .023, m["cloth"], root, 12,
          tilt=(math.pi / 2, 0, 0))
    stone("Shield boss", (.015, -.20, -.29), (.07, .042, .07), m["light"], root, 2)
    for sign in (-1, 1):
        span("Shield wave inlay", (.015, -.196, -.28), (.015 + sign * size * .63, -.196, -.36),
             .018, m["trim"], root)

def spear(root, m, height=1.35, blade="spear"):
    span("Ash haft", (.02, -.055, -.77), (.02, -.055, height-.77), .037, m["wood"], root)
    end = height - .77
    prism("Bronze ferrule", (.02, -.055, end-.022), .055, .12, m["trim"], root, 6)
    if blade == "naginata":
        sheet("Curved naginata blade", [(0,-.056,end),(.125,-.056,end+.13),(.11,-.056,end+.45),
              (-.025,-.056,end+.51),(-.014,-.056,end+.22),(-.042,-.056,end+.06)],
              [(0,1,4,5),(1,2,3,4)], m["steel"], root, .03)
    else:
        stone("Forged leaf point", (.02, -.055, end+.16), (.073, .039, .22), m["steel"], root)
    for z in (-.57, -.47, .07):
        prism("Haft lashing", (.02, -.055, z), .044, .038, m["leather"], root, 6)

def bow(root, m):
    points = [(.04,-.08,-.69),(.12,-.18,-.47),(.175,-.26,-.18),(.11,-.26,.11),
              (.03,-.14,.40),(.05,-.035,.71)]
    for a, b in zip(points[:-1], points[1:]):
        span("Laminated bow limb", a, b, .035, m["wood"], root, 5, .022)
    span("Silk bowstring", points[0], points[-1], .009, m["linen"], root, 4)
    for z in (-.09, -.03, .03):
        prism("Woven grip", (.14,-.263,z), .044, .035, m["trim"], root, 6)

def staff(root, m, kind):
    span("Carved staff", (.05,-.09,-.82), (.05,-.09,.57), .044, m["wood"], root)
    prism("Fret binding", (.05,-.09,.54), .073, .17, m["trim"], root, 8)
    prism("Crown collar", (.05,-.09,.65), .117, .055, m["trim"], root, 8)
    stone("Conduit", (.05,-.09,.78), (.148,.13,.188), m["glow"], root, 1)
    for sign in (-1, 1):
        span("Crown branch", (.05,-.09,.61), (.05 + sign * .165,-.09,.82), .023, m["trim"], root)
        stone("Crown tip", (.05 + sign*.165, -.09,.82), (.042,.043,.06), m["trim"], root)
    if kind == "monk":
        prism("Staff bell", (.055,-.105,.62), .12, .14, m["trim"], root, 7, .057)

def character(data, faction="aegean", enemy=False):
    ident = data["id"]
    hero = data.get("kind") == "hero"
    m = palette(faction, data["color"])
    root = empty(ident)
    body = empty("Hips and coat", (0, 0, .83), root)
    head = empty("Head joint", (0, -.018, .53), body)
    left = empty("Shield arm", (-.265,-.005,.34), body)
    right = empty("Weapon arm", (.265,-.005,.34), body)
    legs = [empty("Left stride" if side < 0 else "Right stride", (side*.13,.01,.80), root) for side in (-1,1)]
    cape = empty("Cloth motion", (0,.165,.31), body)

    elite = ident in ("brute", "golem", "titan")
    spectral = ident in ("wisp", "kitsune", "moth")
    scale = 1.12 if hero else .95
    if enemy:
        scale = {"hound":.66,"wisp":.78,"moth":.72,"warden":1.15,"brute":1.15,"herald":1.03,"golem":1.48,"titan":1.75}.get(ident,.88)
    root.scale = (scale,)*3

    prism("Ribbed jerkin", (0,0,.19), .26 if not elite else .34, .45, m["cloth"], body, 6, .31)
    prism("Pleated hem", (0,0,-.14), .31, .29, m["cloth"], body, 7, .23)
    prism("Reinforced belt", (0,0,.015), .266, .081, m["leather"], body, 8)
    box("Belt buckle", (0,-.255,.02), (.115,.06,.1), m["trim"], body)
    stone("Chest plate", (0,-.155,.235), (.242,.112,.215), m["stone"] if enemy else m["trim"], body, 1)
    for z in (.09,.183,.275):
        box("Segmented cuirass", (.015,-.222,z), (.29,.054,.044), m["ink"] if enemy else m["accent"], body)
    for side in (-1,1):
        for z in (-.13,-.22):
            box("Hanging panels", (side * .145,-.227,z), (.104,.062,.108), m["shade"], body,
                (side*.06,0,side*.12))
        span("Chest harness", (side*.22,-.16,.40), (-side*.04,-.277,.075), .025, m["leather"], body)
    if elite:
        for idx in range(4):
            angle = idx * 1.57
            stone("Cracked shoulder basalt", (.37*math.cos(angle), .31*math.sin(angle), .22+idx*.04),
                  (.14,.16,.22), m["stone"], body)
        stone("Exposed ember heart", (0,-.263,.21), (.16,.061,.185), m["glow"], body)
    for arm in (left, right):
        stone("Forged pauldron", (0,0,.006), (.172,.163,.143), m["stone"] if enemy else m["trim"], arm, 2)
        span("Sleeve", (0,0,-.04), (.006,-.025,-.239), .092, m["cloth"], arm)
        span("Forearm", (.006,-.02,-.202), (.014,-.145,-.353), .083, m["skin"] if not enemy else m["stone"], arm)
        box("Guard plate", (.01,-.113,-.266), (.16,.10,.15), m["trim"], arm, (.34,0,0))
        stone("Gripping hand", (.013,-.15,-.35), (.079,.082,.094), m["skin"] if not enemy else m["stone"], arm)
    for leg in legs:
        span("Leg", (0,0,-.03), (0,.012,-.42), .107, m["shade"], leg, 6, .082)
        span("Greave", (0,.015,-.39), (0,-.014,-.67), .105, m["stone"] if enemy else m["trim"], leg, 6, .083)
        box("Knee plaque", (0,-.059,-.375), (.17,.098,.136), m["accent"], leg)
        stone("Boot", (0,-.073,-.72), (.112,.196,.082), m["leather"], leg, 2)

    face = m["stone"] if enemy else m["skin"]
    stone("Faceted jaw", (0,-.016,.08), (.171,.155,.186), face, head, 2)
    stone("Nose", (.006,-.16,.077), (.042,.052,.052), face, head)
    for side in (-1,1):
        box("Eyeline", (side*.068,-.154,.131), (.059,.031,.025), m["glow"] if enemy else m["ink"], head,
            (0, side*.11, 0))
        if hero or faction == "japan":
            box("Painted cheek", (side*.103,-.141,.03), (.043,.032,.055), m["accent"], head, (0,-side*.15,0))
    if faction in ("aegean", "rome") and ident not in ("oracle", "vesta", "ilios"):
        stone("Helmet bowl", (0, .026, .193), (.204,.172,.168), m["trim"], head, 2)
        box("Visor ridge", (0,-.144,.177), (.29,.066,.055), m["trim"], head)
        for side in (-1,1):
            box("Hinged cheek plate", (side*.151,-.04,.073), (.071,.16,.143), m["trim"], head, (0,side*.14,0))
        if hero or ident == "legionary":
            for step in range(7):
                angle = step * .32 - .9
                stone("Dyed crest bristles", (0, math.sin(angle)*.19,.22+math.cos(angle)*.16),
                      (.052,.125,.092), m["cloth"], head)
        else:
            prism("Helmet stem", (0,.03,.355), .074, .09, m["accent"], head, 6, .035)
    elif faction == "japan" and ident in ("ashigaru","yumi","raiden","akari"):
        prism("Lacquered helmet", (0,.019,.227), .246, .16, m["shade"], head, 8, .105)
        prism("Helm edge", (0,.019,.153), .258, .027, m["trim"], head, 8)
        for side in (-1,1):
            for z in (.022,.068,.113):
                box("Neck lamella", (side*.188,.031,z), (.065,.256,.05), m["cloth"], head, (0,side*.1,0))
            if hero:
                span("Helm crescent", (0,-.182,.22), (side*.165,-.174,.402), .032, m["trim"], head, 6, .012)
    else:
        stone("Braided hair or cowl", (0,.046,.192), (.174,.169,.171), m["shade"], head, 2)
        prism("Marked brow band", (0,.021,.155), .176, .049, m["accent"], head, 8)
        if ident in ("oracle","vesta","ilios","wisp"):
            stone("Brow stone", (0,-.153,.177), (.044,.038,.067), m["glow"], head)

    if enemy:
        for side in (-1,1):
            span("Obsidian horn", (side*.113,.028,.241), (side*.241,.025,.48 if elite else .32),
                 .066, m["stone"], head, 6, .009)
        if ident == "titan":
            for z in (.32,.53):
                span("Broken crown spire", (0,.006,z), (0,.016,z+.19), .085, m["glow"], head, 4, .005)
        if spectral:
            for index in range(4):
                angle = index*1.57
                stone("Cinder orbit", (.39*math.cos(angle), .28*math.sin(angle), .21+index*.087),
                      (.17,.129,.21), m["glow"], body)
        if ident == "hound":
            muzzle = stone("Long snout", (0,-.164,.045), (.12,.186,.102), m["stone"], head)
            muzzle.rotation_euler.x = -.13
            span("Tail", (0,.14,-.06), (0,.52,.21), .085, m["stone"], body, 6, .014)
        if ident in ("reaver","brute","golem","titan"):
            prism("Rift fist", (.015,-.181,-.391), .144 if elite else .1, .22, m["glow"], right, 5, .096)
        if ident == "herald":
            staff(right, m, ident)
        if ident == "warden":
            prism("Mirror frame", (.035,-.16,-.26), .335,.105,m["stone"],left,9,
                  tilt=(math.pi/2,0,0))
            prism("Blue shield face",(.035,-.23,-.26),.281,.07,m["accent"],left,9,
                  tilt=(math.pi/2,0,0))
            stone("Shield prism",(.035,-.276,-.26),(.177,.073,.196),m["glow"],left,1)
            spear(right,m,1.12,"naginata")
        if ident == "moth":
            for side, arm in ((-1,left),(1,right)):
                sheet("Faceted dusk wing",[(.0,.12,.0),(side*.96,.19,.60),(side*.88,.31,.12),
                      (side*.63,.28,-.39),(side*.17,.14,-.33)],
                      [(0,1,2),(0,2,3),(0,3,4)],m["accent"],arm,.047)
                span("Wing marking",(0,.107,.02),(side*.79,.24,.28),.022,m["glow"],arm,5)
                span("Curling antenna",(side*.05,.0,.26),(side*.23,-.04,.53),.027,m["shade"],head,6,.008)
    else:
        attack = data["attack"]
        if attack == "guard" or ident in ("peltast","veles"):
            shield(left, m, faction, hero)
            spear(right, m, 1.68 if hero else 1.42)
        elif attack == "arrow":
            bow(left, m)
            prism("Arrow quiver", (.159,.235,.02), .099, .51, m["wood"], body, 7, tilt=(.04,-.27,0))
            for index in range(3):
                span("Quiver arrow", (.13+index*.031,.257,.04), (.146+index*.029,.27,.55+index*.044),
                     .013, m["linen"], body, 5)
        elif attack == "stone":
            span("Sling strap", (.04,-.135,-.34), (.14,-.163,-.62), .018, m["leather"], right)
            stone("Sling cup", (.15,-.167,-.635), (.082,.055,.061), m["accent"], right)
        elif ident in ("akari","raiden"):
            spear(right, m, 1.83, "naginata")
            for index in range(5):
                direction = index*.25 - .5
                span("Painted war fan", (.015,-.16,-.35),
                     (.015 + math.sin(direction)*.30, -.158, -.35 + math.cos(direction)*.30),
                     .033, m["accent"], left, 5, .057)
        else:
            staff(right, m, ident)
        if ident == "kitsune":
            for side in (-1,1):
                span("Fox ear", (side*.107,.008,.243), (side*.179,.012,.434), .071, m["accent"], head, 5, .011)
            for index in (-1,0,1):
                span("Fox tail", (index*.075,.199,-.11), (index*.31,.52,.19 + abs(index)*.1),
                     .11, m["accent"], body, 7, .033)

    if hero or ident in ("oracle","signifer","herald","kitsune"):
        sheet("Dyed cape", [(-.20,0,0),(.20,0,0),(-.23,.109,-.34),(.245,.143,-.34),
                            (-.327,.19,-.69),(.33,.22,-.62),(0,.285,-.82)],
              [(0,1,2),(1,3,2),(2,3,6),(2,6,4),(3,5,6)], m["cloth"], cape, .037)
        span("Cape bottom weave", (-.325,.207,-.686), (0,.293,-.816), .021, m["accent"], cape, 5)
        span("Cape bottom weave", (0,.293,-.816), (.327,.234,-.617), .021, m["accent"], cape, 5)
    if ident in ("signifer","marcus","herald"):
        span("Standard pole", (.12,.20,-.26), (.12,.20,.96), .024, m["wood"], body)
        sheet("Field pennon", [(.10,.202,.89),(.52,.23,.89),(.51,.24,.54),(.29,.24,.65),(.10,.202,.55)],
              [(0,1,3),(1,2,3),(0,3,4)], m["accent"], body)
        stone("Standard finial", (.12,.20,.98), (.073,.066,.077), m["trim"], body)
    animate_character(root, body, head, left, right, legs, cape, data, spectral)
    return root

def pose(obj, frame, offset=(0,0,0), angles=(0,0,0), squeeze=(1,1,1)):
    loc, rot, scale = obj["rest_location"], obj["rest_rotation"], obj["rest_scale"]
    obj.location = [loc[i] + offset[i] for i in range(3)]
    obj.rotation_euler = [rot[i] + angles[i] for i in range(3)]
    obj.scale = [scale[i] * squeeze[i] for i in range(3)]
    obj.keyframe_insert("location", frame=frame, group=obj.name)
    obj.keyframe_insert("rotation_euler", frame=frame, group=obj.name)
    obj.keyframe_insert("scale", frame=frame, group=obj.name)

def mark_rest(items):
    for obj in items:
        obj["rest_location"] = list(obj.location)
        obj["rest_rotation"] = list(obj.rotation_euler)
        obj["rest_scale"] = list(obj.scale)

def save_action(items, name, last, sample):
    for obj in items:
        if obj.animation_data:
            obj.animation_data.action = None
    for frame in sorted(set((1, last, *sample.keys()))):
        directives = sample.get(frame, {})
        for obj in items:
            offset, angles, squeeze = directives.get(obj.name, ((0,0,0),(0,0,0),(1,1,1)))
            pose(obj, frame, offset, angles, squeeze)
    for obj in items:
        animation = obj.animation_data
        action = animation.action
        action.name = f"{name} • {obj.name}"
        animation.action = None
        track = animation.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 1, action)
        if hasattr(strip, "action_slot") and len(action.slots):
            strip.action_slot = action.slots[0]
    for obj in items:
        obj.location = obj["rest_location"]
        obj.rotation_euler = obj["rest_rotation"]
        obj.scale = obj["rest_scale"]

def animate_character(root, body, head, left, right, legs, cape, data, floating):
    rig = [root, body, head, left, right, *legs, cape]
    mark_rest(rig)
    one = (1,1,1)
    def t(x=0,y=0,z=0,a=0,b=0,c=0,s=one):
        return ((x,y,z),(a,b,c),s)
    save_action(rig, "Idle", 49, {
        13:{body.name:t(z=.025,a=.03),right.name:t(a=-.055),head.name:t(c=-.065),cape.name:t(a=.09)},
        25:{body.name:t(z=.042 if not floating else .15),left.name:t(a=.065),cape.name:t(a=.16)},
        37:{body.name:t(z=.019),head.name:t(c=.07),cape.name:t(a=.07)},
    })
    stride = .32 if not floating else .13
    walk = {}
    for frame, pulse in [(1,0),(5,1),(9,0),(13,-1),(17,0)]:
        walk[frame] = {
            legs[0].name:t(z=max(0,pulse)*.061,a=pulse*stride),
            legs[1].name:t(z=max(0,-pulse)*.061,a=-pulse*stride),
            left.name:t(a=-pulse*.25),
            right.name:t(a=pulse*.23),
            body.name:t(z=.045 + .045*abs(pulse) if not floating else .15 + .09*abs(pulse), c=.06*pulse),
            cape.name:t(a=.26+.08*abs(pulse), c=pulse*.08),
        }
    save_action(rig, "Walk", 17, walk)
    attack = data.get("attack", "guard")
    if attack in ("sun","frost","rally"):
        anticipation = {right.name:t(a=-.94,b=-.36), left.name:t(a=-.44), body.name:t(z=.048,c=.18), cape.name:t(a=.15)}
        contact = {right.name:t(a=-1.71,b=.16), left.name:t(a=-.6), body.name:t(y=-.07,a=-.11), head.name:t(a=-.12)}
    elif attack == "arrow":
        anticipation = {right.name:t(a=-.83,b=-.49),left.name:t(a=-1.29,b=.18),body.name:t(c=-.25),head.name:t(c=.2)}
        contact = {right.name:t(a=-.83,b=-.78),left.name:t(a=-1.36),body.name:t(y=-.051,c=.12),head.name:t(c=.12)}
    else:
        anticipation = {right.name:t(a=.53,b=-.31,c=-.24),left.name:t(a=-.25),body.name:t(y=.05,c=.21),cape.name:t(a=.1)}
        contact = {right.name:t(a=-1.42,b=.27),left.name:t(a=-.74),body.name:t(y=-.138,a=-.21),cape.name:t(a=.47)}
    save_action(rig, "Attack", 21, {6:anticipation,10:contact,15:{body.name:t(a=-.05),right.name:t(a=-.44)}})
    cast = {
        7:{body.name:t(z=.045,c=-.14),right.name:t(a=-1.49,b=.53),left.name:t(a=-1.15,b=-.62),head.name:t(a=.23)},
        15:{body.name:t(z=.15,a=-.15),right.name:t(a=-2.18,b=.41),left.name:t(a=-1.82,b=-.51),cape.name:t(a=.55)},
        23:{body.name:t(y=-.095,a=-.21),right.name:t(a=-.82),left.name:t(a=-.74),cape.name:t(a=.29)},
    }
    skill = data.get("skill")
    if skill == "phalanx":
        cast[7].update({left.name:t(a=-.94,b=-.25),body.name:t(z=-.075,y=.06,c=.18)})
        cast[15].update({left.name:t(a=-1.08,b=-.22),right.name:t(a=-1.40,b=.51),
                         body.name:t(y=-.105,z=-.07,a=-.22,c=-.12),legs[0].name:t(y=-.12,a=.21)})
    elif skill == "meteor":
        cast[15].update({body.name:t(z=.19,a=.21),right.name:t(a=-2.37,b=.16),head.name:t(a=.43),cape.name:t(a=.29)})
        cast[23].update({right.name:t(a=-1.14,b=.65),body.name:t(y=-.20,z=.04,a=-.26,c=.29)})
    elif skill == "salvo":
        cast[15].update({right.name:t(a=-1.68,b=-.26,c=.47),left.name:t(a=-.89,b=.61),
                         body.name:t(y=-.08,c=.40),head.name:t(c=-.35),cape.name:t(a=.47,c=-.18)})
    elif skill == "oath":
        cast[7].update({body.name:t(z=-.09),right.name:t(a=-1.1,b=-.82),left.name:t(a=-.88,b=.67)})
        cast[15].update({body.name:t(z=.08,a=.135),left.name:t(a=-1.61,b=-.89),right.name:t(a=-1.56,b=.86)})
    elif skill == "mist":
        cast[7].update({left.name:t(a=-.63,b=-.59,c=-.64),body.name:t(c=-.41),head.name:t(c=.21)})
        cast[15].update({left.name:t(a=-1.63,b=-.58,c=.58),right.name:t(a=-.94,b=.75),
                         body.name:t(y=-.07,z=.08,c=.36),cape.name:t(a=.4,c=-.34)})
    elif skill == "thunder":
        cast[7].update({root.name:t(z=.18),body.name:t(c=-.34),right.name:t(a=-1.45,b=-.34)})
        cast[15].update({root.name:t(z=.36,c=.37),body.name:t(a=-.18),right.name:t(a=-2.31,b=.61),
                         legs[0].name:t(a=-.64),legs[1].name:t(a=.34),cape.name:t(a=.70)})
        cast[23].update({root.name:t(y=-.12),body.name:t(z=-.10,a=-.34),right.name:t(a=-1.21,b=.63)})
    save_action(rig, "Cast", 37, cast)
    save_action(rig, "Hit", 13, {4:{body.name:t(y=.09,a=.23),head.name:t(a=.15),left.name:t(a=.28),
                                  right.name:t(a=.21),cape.name:t(a=-.21)}})
    save_action(rig, "Death", 30, {
        7:{root.name:t(z=.04,a=.22),left.name:t(a=-.48),right.name:t(a=-.6),head.name:t(a=.32)},
        16:{root.name:t(y=.29,z=.03,a=1.44,b=.25),left.name:t(b=-.47),right.name:t(b=.56),cape.name:t(a=.3)},
        30:{root.name:t(y=.43,z=-.09,a=1.61,b=.25,s=(.88,.88,.88)),left.name:t(b=-.69),right.name:t(b=.77),
            cape.name:t(a=.41),head.name:t(a=.1)},
    })

def building(data):
    ident, faction = data["id"], data["theme"]
    m = palette(faction, data["color"])
    root = empty(ident)
    mechanism = empty("Moving mechanism", (0,0,.54), root)
    focus = empty("Focus", (0,0,.66), mechanism)
    for index, dim in enumerate((1.18,1.08,.93)):
        box("Stacked plinth", (0,0,.075+index*.10), (dim,dim,.145), m["stone"] if index != 1 else m["shade"], root)
    for x in (-.41,.41):
        for y in (-.41,.41):
            stone("Inlaid corner boss", (x,y,.343), (.08,.08,.058), m["trim"], root)
    attack = data["attack"]
    if ident in ("ballista","scorpio"):
        for x in (-.32,.32):
            box("Stained timber brace", (x,.12,.55), (.2,.71,.38), m["wood"], root, (.19,0,0))
            for z in (.418,.654):
                box("Iron reinforcement", (x,.125,z), (.217,.727,.071), m["trim"], root)
        box("Firing bed", (0,-.11,.22), (.37,.88,.16), m["wood"], mechanism)
        box("Glass bolt runway", (0,-.14,.32), (.092,.82,.055), m["steel"], mechanism)
        for side in (-1,1):
            span("Torsion bow limb", (0,-.28,.34), (side*.63,-.49,.37), .085, m["wood"], mechanism, 6, .042)
            span("Torsion bow cord", (side*.63,-.49,.37), (0,.18,.343), .019, m["linen"], mechanism)
            prism("Torsion coil", (side*.31,-.15,.278), .122,.26, m["trim"], mechanism, 10)
        span("Readied shaft", (0,.20,.368), (0,-.58,.368), .027, m["wood"], mechanism)
        span("Readied head", (0,-.57,.367), (0,-.79,.366), .053, m["steel"], mechanism, 5, .005)
    elif ident in ("torii","yagura"):
        for side in (-1,1):
            span("Lacquered pillar", (side*.43,0,.29), (side*.39,0,1.26), .11, m["accent"], root, 6)
            prism("Copper post boot", (side*.43,0,.365), .15,.16, m["ink"], root, 8)
        box("Lintel", (0,0,1.11), (1.22,.21,.146), m["cloth"], root)
        sheet("Tiled eaves", [(-.69,-.39,1.26),(.69,-.39,1.26),(-.52,0,1.57),(.52,0,1.57),
                              (-.69,.39,1.26),(.69,.39,1.26)],
              [(0,1,3,2),(2,3,5,4)], m["shade"], root,.091)
        for x in (-.61,-.42,-.22,0,.22,.42,.61):
            span("Roof ridge bead", (x,-.365,1.32), (x*.83,0,1.61), .037, m["ink"], root, 5)
        box("Hanging plaque", (0,-.18,1.02), (.22,.04,.251), m["trim"], mechanism)
        stone("Talisman", (0,-.31,0), (.143,.13,.18), m["glow"], focus)
    elif ident in ("standard","bell"):
        span("Tall cedar post", (0,0,.25), (0,0,1.6), .088, m["wood"], root)
        span("Cross beam", (-.41,0,1.41), (.41,0,1.41), .058, m["trim"], root)
        if ident == "bell":
            prism("Ritual bronze bell", (0,0,.49), .32,.48,m["trim"],mechanism,10,.193)
            prism("Bell carved lip", (0,0,.25), .35,.072,m["accent"],mechanism,10)
            stone("Bell clapper", (0,0,.18), (.13,.12,.136), m["glow"], mechanism)
        else:
            sheet("Woven battle banner", [(-.34,0,.83),(.34,0,.83),(-.34,.04,.14),(.34,.04,.14),(0,.07,.27)],
                  [(0,1,4),(0,4,2),(1,3,4)], m["cloth"], mechanism, .034)
            prism("Hammered solar emblem", (0,-.051,.58), .172,.042,m["trim"],mechanism,10,
                  tilt=(math.pi/2,0,0))
            stone("Banner finial", (0,0,1.65), (.135,.12,.118), m["trim"], root)
    else:
        for side in (-1,1):
            prism("Fluted altar pillar", (side*.375,0,.68), .109,.68,m["stone"],root,8,.085)
            box("Pillar capital", (side*.375,0,1.029), (.30,.295,.13),m["trim"],root)
        prism("Offering basin", (0,0,.85), .225,.24,m["trim"],root,10,.42)
        prism("Basin rim", (0,0,.968), .45,.069,m["shade"],root,12)
        for index in range(5):
            theta = index*2.398
            flare = stone("Fire facets", (.181*math.cos(theta),.18*math.sin(theta),-.111+index*.058),
                          (.168,.134,.245), m["glow"] if index%2 else m["accent"], focus)
            flare.rotation_euler.x = math.sin(theta)*.34
            flare.rotation_euler.y = math.cos(theta)*.29
    rig = [mechanism, focus]
    mark_rest(rig)
    def transform(z=0, y=0, turn=0, scale=1):
        return ((0,y,z),(turn,0,0),(scale,)*3)
    save_action(rig,"Idle",37,{12:{focus.name:transform(z=.057,scale=.89),mechanism.name:transform(turn=.028)},
                              24:{focus.name:transform(z=.093,scale=1.11),mechanism.name:transform(turn=-.024)}})
    save_action(rig,"Attack",19,{5:{focus.name:transform(scale=1.48),mechanism.name:transform(y=.20,turn=-.185)},
                                11:{focus.name:transform(scale=.61),mechanism.name:transform(y=-.045,turn=.077)}})
    save_action(rig,"Cast",27,{11:{focus.name:transform(z=.15,scale=1.42),mechanism.name:transform(turn=.125)}})
    return root

def environment(ident):
    m = palette(ident, PALETTES[ident]["trim"])
    root = empty(f"{ident} landmark")
    box("Landmark stone bed", (0,0,.15), (3.78,1.22,.30), m["stone"], root)
    for x in (-1.36,1.36):
        box("Wall footing", (x,0,.34), (.92,1.10,.24), m["shade"], root)
        height = 1.81 if ident == "japan" else 1.53
        prism("Great pier", (x,0,.49+height*.5), .37,height,
              m["accent"] if ident == "japan" else m["stone"], root,8,.28)
        box("Pier cornice", (x,0,.54+height), (.91,.89,.20), m["trim"], root)
        for side in (-1,1):
            prism("Lantern stand", (x+side*.23,-.42,.54), .071,.46,m["shade"],root,6)
            stone("Oil lamp", (x+side*.23,-.43,.845), (.133,.117,.159),m["glow"],root)
    height = 2.32 if ident=="japan" else 2.07
    box("Gate lintel", (0,0,height), (3.83,.83,.28), m["cloth"], root)
    if ident == "japan":
        for z, width in ((2.56,4.11),(2.75,4.43)):
            box("Torii cross beam", (0,0,z), (width,.67,.21),m["shade"],root)
        for side in (-1,1):
            box("Rising eave", (side*2.17,0,2.85), (.68,.72,.156),m["shade"],root,(0,-side*.22,0))
    else:
        sheet("Pediment", [(-1.96,-.47,height+.12),(1.96,-.47,height+.12),(0,-.47,height+.87)],
              [(0,1,2)],m["stone"],root,.66)
        for side in (-1,1):
            span("Roof edge", (0,-.50,height+.88),(side*2.02,-.50,height+.15),.094,m["trim"],root,7)
    stone("Gate core", (0,0,height+.15), (.30,.18,.30),m["glow"],root,2)
    return root

def effect(ident):
    m = palette("aegean", {"bolt":"f8bd77","sun":"fbd36b","frost":"9fe7ed","spark":"fcbb9e"}[ident])
    root = empty(ident)
    pulse = empty("Pulse", (0,0,0), root)
    if ident == "bolt":
        span("Shaft",(0,.32,0),(0,-.36,0),.036,m["wood"],pulse)
        span("Point",(0,-.28,0),(0,-.51,0),.073,m["steel"],pulse,5,.008)
        for side in (-1,1):
            sheet("Fletching",[(0,.12,0),(side*.08,.29,0),(side*.07,.39,0),(0,.33,0)],
                  [(0,1,3),(1,2,3)],m["glow"],pulse)
    else:
        stone("Bright core",(0,0,0),(.148,.156,.148),m["glow"],pulse)
        for index in range(3):
            angle=index*2.094
            stone("Outer flakes",(.13*math.sin(angle),.12*math.cos(angle),.032),(.076,.073,.072),m["accent"],pulse)
    mark_rest([pulse])
    save_action([pulse],"Idle",19,{8:{pulse.name:((0,0,0),(0,0,.72),(1.19,)*3)}})
    return root

def batch_rigid_meshes():
    """Keep the editable parts in .blend and batch each articulated piece in the web export."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and len(obj.data.materials) == 1 and obj.parent:
            groups.setdefault((obj.parent, obj.data.materials[0]), []).append(obj)
    for (parent, mat), objects in groups.items():
        if len(objects) < 2:
            continue
        vertices, faces = [], []
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            matrix = parent.matrix_world.inverted() @ evaluated.matrix_world
            offset = len(vertices)
            vertices.extend(tuple(matrix @ vertex.co) for vertex in mesh.vertices)
            faces.extend(tuple(offset + index for index in polygon.vertices) for polygon in mesh.polygons)
            evaluated.to_mesh_clear()
        mesh = bpy.data.meshes.new(f"{parent.name} • {mat.name}")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(mesh.name, mesh)
        bpy.context.collection.objects.link(obj)
        attach(obj, mesh.name, mat, parent)
        for old in objects:
            bpy.data.objects.remove(old, do_unlink=True)

def export(root, ident):
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 49
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES / f"{ident}.blend"), compress=True)
    batch_rigid_meshes()
    bpy.ops.export_scene.gltf(filepath=str(MODELS / f"{ident}.glb"), export_format="GLB",
        export_yup=True, export_apply=True, export_animations=True, export_animation_mode="NLA_TRACKS",
        export_extras=False, export_cameras=False, export_lights=False)
    return root

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()

def portrait(root, ident, large=False, hero=False):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 680 if large else 250
    scene.render.resolution_y = 760 if large else 300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    settings = scene.display.shading
    settings.light = "STUDIO"
    settings.color_type = "MATERIAL"
    settings.show_shadows = True
    settings.show_cavity = True
    settings.cavity_type = "BOTH"
    settings.curvature_ridge_factor = 1.38
    settings.curvature_valley_factor = .86
    settings.show_specular_highlight = True
    settings.background_type = "WORLD"
    bpy.ops.object.camera_add(location=(3.05,-5.60,2.70))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.91 if hero else 2.70
    look_at(camera,(0,0,.87))
    scene.camera = camera
    scene.render.filepath = str(PORTRAITS / f"{ident}.png")
    if hero:
        for obj in [root, *root.children_recursive]:
            if obj.animation_data:
                for track in obj.animation_data.nla_tracks:
                    track.mute = track.name != "Cast"
        scene.frame_set(11 if ident in ("thekla","akari","marcus") else 13)
    else:
        scene.frame_set(1)
    bpy.ops.render.render(write_still=True)

def run():
    subset = set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    for data in CATALOG["actors"]:
        ident = data["id"]
        if subset and ident not in subset:
            continue
        clean()
        root = building(data) if data["kind"] == "building" else character(data,data["theme"])
        export(root, ident)
        portrait(root, ident, ident == "thekla", data["kind"] == "hero")
    for data in CATALOG["enemies"]:
        if subset and data["id"] not in subset:
            continue
        clean()
        export(character(data,"rift",True), data["id"])
    for faction in ("aegean", "rome", "japan"):
        ident = f"gate_{faction}"
        if subset and ident not in subset:
            continue
        clean()
        export(environment(faction), ident)
    for kind in ("bolt","sun","frost","spark"):
        ident=f"fx_{kind}"
        if subset and ident not in subset:
            continue
        clean()
        export(effect(kind), ident)

if __name__ == "__main__":
    run()
