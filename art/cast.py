"""Build the field characters, export a single skinned mesh, and render the collection."""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import CATALOG, MODELS, PORTRAITS, SOURCES, attach, clean, empty, look_at, material, palette, prism, rgba, sheet, span

TAU = math.tau
GOLD = "e7b678"

def soften(obj, value=.08):
    for face in obj.data.polygons:
        face.use_smooth = True
    if value:
        bevel = obj.modifiers.new("Rounded edges", "BEVEL")
        bevel.width = value
        bevel.segments = 2
        bevel.affect = 'EDGES'
        normals = obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
        normals.weight = 45
    return obj

def leather_box(name, xyz, dims, mat, parent, angles=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = attach(bpy.context.object,name,mat,parent)
    obj.scale = dims
    obj.rotation_euler = angles
    return soften(obj,.13)

def oval(name, xyz, dims, mat, parent, sides=12, rings=7):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=sides, ring_count=rings, radius=1, location=xyz)
    obj=attach(bpy.context.object,name,mat,parent)
    obj.scale=dims
    return soften(obj,0)

def section(name, profile, mat, parent, sides=12, tilt=0):
    vertices=[]
    for z,rx,ry,x,y in profile:
        for i in range(sides):
            angle=i*TAU/sides + tilt
            vertices.append((x+rx*math.cos(angle),y+ry*math.sin(angle),z))
    faces=[tuple(reversed(range(sides)))]
    for r in range(1,len(profile)):
        start=(r-1)*sides
        faces.extend((start+i,start+(i+1)%sides,start+sides+(i+1)%sides,start+sides+i)
                     for i in range(sides))
    faces.append(tuple(range(len(vertices)-sides,len(vertices))))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    attach(obj,name,mat,parent)
    return soften(obj,0)

def round_rod(name, a, b, base, top, mat, parent, sides=8):
    a,b=Vector(a),Vector(b)
    direction=b-a
    length=direction.length
    obj=section(name,[(0,base*.85,base*.85,0,0),(.12*length,base,base,0,0),
                     (.85*length,top,top,0,0),(length,top*.82,top*.82,0,0)],mat,parent,sides)
    obj.location=a
    obj.rotation_euler=direction.to_track_quat("Z","Y").to_euler()
    return obj

def edge(name, points, faces, mat, parent, thickness=.026):
    obj=sheet(name,points,faces,mat,parent,thickness)
    bevel=obj.modifiers.new("Dressed edge","BEVEL")
    bevel.width=.016
    bevel.segments=2
    return obj

def suit(item, theme):
    accent=item["color"]
    result=palette(theme,accent)
    look=item.get("model",{})
    seed=random.Random(item["id"])
    result["skin"]=material("Face",seed.choice(("bf8b6f","d4a78a","b97955","a86751","e2b193")))
    result["skin_deep"]=material("Cheek",seed.choice(("955e48","ac755f","bd886d")))
    result["steel"]=material("Tinned bronze", "d3c6a5" if theme=="aegean" else "b1c0c8",.22)
    result["bright"]=material("Inlay",GOLD,.21)
    result["black"]=material("Dark leather","232731")
    result["ivory"]=material("Linen", "ebd9b8")
    result["hair"]=material("Hair",seed.choice(("292833","392b2b","604034","20252a","594352")))
    if theme=="rift":
        result["skin"]=result["stone"]
        result["skin_deep"]=result["shade"]
        result["bright"]=result["glow"]
    if look.get("shape") in ("spirit","seer"):
        result["cloth"]=result["accent"]
    return result

def build_puppet(item, enemy=False):
    ident=item["id"]
    theme=item.get("theme","rift")
    hero=item.get("kind")=="hero"
    variant=item.get("model",{})
    shape=variant.get("shape",
        {"titan":"titan","golem":"titan","brute":"bulwark","herald":"banner","wisp":"spirit","moth":"spirit","hound":"runner","warden":"bulwark"}.get(ident,"duelist"))
    weapon=variant.get("weapon",{"warden":"spear","herald":"staff","titan":"hammer","golem":"hammer"}.get(ident,"sword"))
    mats=suit(item,theme)
    actor_scale=1.09 if hero else .93
    if enemy:
        actor_scale={"hound":.74,"wisp":.72,"moth":.73,"brute":1.03,"golem":1.36,"titan":1.63}.get(ident,.89)
    broad={"titan":1.21,"bulwark":1.10,"regent":1.07,"smith":1.08,"runner":.89,"seer":.89,"spirit":.91}.get(shape,1)
    armored=shape in ("bulwark","regent","titan","smith")
    robed=shape in ("robe","seer","spirit","banner")
    root=empty("Figure")
    hips=empty("Body",(0,0,.78),root)
    head=empty("Head",(0,0,.47),hips)
    left=empty("LeftArm",(-.25*broad,0,.34),hips)
    right=empty("RightArm",(.25*broad,0,.34),hips)
    legs=[empty("LeftLeg",(-.13,.018,.75),root),empty("RightLeg",(.13,.018,.75),root)]
    mantle=empty("Mantle",(0,.16,.30),hips)
    root.scale=(actor_scale,)*3
    ink,cloth,edge_mat,skin=mats["shade"],mats["cloth"],mats["trim"],mats["skin"]
    accent=mats["accent"]

    section("Tailored coat",[
        (-.27,.23*broad,.154,0,.016),(-.18,.258*broad,.166,0,.016),
        (.03,.216*broad,.139,0,0),(.14,.218*broad,.147,0,0),
        (.285,.287*broad,.155,0,.013),(.386,.273*broad,.141,0,.027),
        (.443,.163*broad,.115,0,.008)],cloth,hips)
    if robed:
        hem=.405 if shape=="robe" else .355
        section("Layered lower robe",[(-.55,hem,.191,0,0),(-.49,hem+.016,.207,0,.010),
             (-.28,.267,.164,0,.007),(-.08,.203,.141,0,.0)], ink, hips, 14)
        for side in (-1,1):
            edge("Split silk panel",[(.033*side,-.160,-.06),(.176*side,-.135,-.09),
                 (.291*side,-.172,-.445),(.126*side,-.197,-.51)],[(0,1,2,3)],accent,hips,.024)
    else:
        for i in range(6):
            angle=(i-2.5)*.56
            p=(math.sin(angle)*.222*broad,-math.cos(angle)*.156,-.201)
            leather_box("Hanging plated lamella",p,(.102,.075,.207),edge_mat if i%2==0 else ink,hips,(.13,angle*.19,angle))
    section("Wrapped waist binding",[(-.11,.229*broad,.159,0,0),(-.08,.254*broad,.168,0,0),
        (-.013,.224*broad,.158,0,0)], mats["leather"], hips)
    oval("Belt clasp",(0,-.17,-.054),(.075,.028,.058),mats["bright"],hips)

    if armored or enemy:
        visor=section("Curved breastplate",[(.072,.167*broad,.067,0,-.113),
          (.121,.218*broad,.073,0,-.105),(.276,.274*broad,.101,0,-.071),
          (.365,.244*broad,.083,0,-.071),(.387,.202*broad,.055,0,-.065)],
          mats["stone"] if enemy else edge_mat,hips,14)
        for i in range(3):
            round_rod("Inlaid rope",(-.13*broad,-.183,.153+.062*i),(.16*broad,-.183,.168+.056*i),
                      .015,.016,cloth if not enemy else mats["black"],hips)
    else:
        for side in (-1,1):
            round_rod("Sloped tunic piping",(side*.205,-.082,.356),(-side*.064,-.175,-.023),
                      .030,.022,mats["ivory"] if robed else edge_mat,hips)
    if hero or shape=="titan":
        oval("Chest heraldry",(0,-.207,.269),(.089,.037,.09),accent,hips,10,6)
        oval("Set jewel",(0,-.239,.276),(.043,.015,.038),mats["bright"],hips,10,6)

    # The gloves and pauldrons follow their own joints. The legs retain a tapered boot silhouette.
    for i, arm in enumerate([left,right]):
        side=-1 if i==0 else 1
        round_rod("Tunic sleeve",(0,.002,-.02),(.026*side,-.016,-.201),.106 if armored else .081,.07,cloth,arm)
        oval("Fitted shoulder cap",(side*.032,.005,-.005),
             (.152 if armored else .112,.135 if armored else .095,.100),edge_mat if armored else accent,arm,12,7)
        if armored or hero:
            for k in range(2):
                oval("Overlapping shoulder plate",(side*(.069+.022*k),0,-.06-.05*k),
                     (.10,.115-.01*k,.049),mats["bright"] if k==0 and hero else ink,arm)
        round_rod("Tapered forearm",(.023*side,-.024,-.176),(.026*side,-.113,-.324),.07,.061,
                  edge_mat if armored else skin,arm)
        oval("Gloved fingers",(.025*side,-.132,-.315),(.067,.062,.061),mats["leather"],arm)
    for i, leg in enumerate(legs):
        side=-1 if i==0 else 1
        round_rod("Tapered trouser",(0,0,-.023),(side*.031,.007,-.376),.102,.071,ink,leg)
        oval("Padded knee",(side*.027,-.046,-.362),(.082,.060,.080),accent,leg,10,6)
        round_rod("Layered greave",(side*.034,.013,-.35),(side*.038,.016,-.61),.088,.066,
                  edge_mat if armored else mats["leather"],leg)
        oval("Reinforced boot",(side*.038,-.052,-.677),(.096,.163,.072),mats["black"],leg,12,6)
        leather_box("Boot clasp",(side*.037,-.091,-.625),(.105,.116,.036),accent,leg)

    # Face and headwear have separate shapes so the silhouettes stay legible at board scale.
    section("Facial planes",[(.008,.087,.085,0,-.011),(.043,.132,.113,0,.0),
       (.123,.165,.132,0,.011),(.222,.17,.142,0,.028),(.29,.139,.113,0,.035),
       (.31,.069,.073,0,.025)],skin,head,16)
    oval("Nose bridge",(0,-.119,.122),(.029,.045,.041),skin,head,10,6)
    oval("Lip",(0,-.102,.066),(.036,.018,.010),mats["skin_deep"],head,10,6)
    for side in (-1,1):
        oval("Upper eyelid",(side*.068,-.119,.163),(.041,.019,.018),mats["hair"],head,10,6)
        oval("Eye shine",(side*.068,-.134,.167),(.019,.009,.012),mats["glow"] if enemy else mats["ivory"],head,10,6)
        oval("Ear",(side*.152,.016,.115),(.035,.039,.060),skin,head)
        if hero or shape=="seer":
            oval("Earring",(side*.164,.010,.073),(.023,.024,.044),mats["bright"],head,10,6)

    if shape in ("seer","robe","spirit"):
        section("Layered hood",[(.196,.173,.143,0,.035),(.252,.192,.149,0,.044),
            (.313,.168,.125,0,.053),(.368,.100,.083,0,.07),(.394,.031,.033,0,.074)],ink,head,14)
        round_rod("Headband",(-.144,-.087,.20),(.150,-.085,.202),.024,.024,accent,head,8)
        if hero or shape=="spirit":
            oval("Brow jewel",(0,-.115,.223),(.042,.023,.052),mats["bright"],head,9,6)
            for sign in (-1,1):
                round_rod("Upturned crest",(sign*.072,-.041,.278),(sign*.15,-.014,.427),.025,.013,edge_mat,head)
    elif theme=="japan":
        head_mat=ink if not hero else edge_mat
        section("Lacquered kabuto",[(.211,.181,.139,0,.044),(.247,.216,.159,0,.056),(.300,.183,.142,0,.057),
              (.381,.110,.091,0,.058),(.392,.038,.041,0,.052)],head_mat,head,14)
        for side in (-1,1):
            for i in range(3):
                leather_box("Hanging lacquer band",(side*.164,.032,.204-.043*i),(.060,.193,.048),cloth,head,(0,side*.13,0))
            if hero:
                round_rod("Gilded kuwagata",(side*.046,-.110,.257),(side*.180,-.105,.430),.031,.017,mats["bright"],head)
    elif armored or hero:
        section("Forged helmet",[(.187,.179,.139,0,.034),(.244,.204,.154,0,.040),(.312,.176,.132,0,.037),
            (.371,.104,.087,0,.037),(.385,.029,.052,0,.035)],edge_mat,head,14)
        for side in (-1,1):
            leather_box("Hammered cheek guard",(side*.147,-.034,.126),(.055,.112,.14),edge_mat,head,(0,side*.16,0))
        if hero or shape=="regent":
            section("Shaped cloth crest",[(.326,.054,.168,0,.03),(.383,.047,.180,0,.023),
               (.431,.037,.143,0,0),(.466,.019,.099,0,-.026)],accent,head,12)
    else:
        section("Carved hair",[(.219,.167,.144,0,.043),(.290,.172,.149,0,.038),
            (.324,.103,.086,0,.048),(.338,.040,.034,0,.051)],mats["hair"],head,14)
        oval("Twined cloth band",(0,.021,.241),(.178,.150,.032),accent,head)
    if enemy:
        for sign in (-1,1):
            round_rod("Carved rift horn",(sign*.113,.056,.283),(sign*.235,.049,.441 if armored else .367),.058,.017,mats["stone"],head)
        if shape in ("bulwark","titan"):
            for sign in (-1,1):
                oval("Basalt shoulder knot",(sign*.31,.13,.23),(.117,.139,.173),ink,hips,9,6)
            oval("Rift heart",(0,-.185,.252),(.109,.039,.146),mats["glow"],hips)
        if ident=="hound":
            oval("Long carved snout",(0,-.185,.102),(.115,.141,.071),ink,head,10,6)
            round_rod("Tapered tail",(0,.12,-.092),(0,.45,.112),.085,.026,mats["stone"],hips)
        if ident=="moth":
            for side,arm in ((-1,left),(1,right)):
                edge("Rounded lunar wing",[(0,.043,-.067),(side*.61,.084,.287),
                     (side*.93,.14,.32),(side*.71,.22,-.124),(side*.39,.24,-.32)],
                     [(0,1,2),(0,2,3),(0,3,4)],accent,arm)
    if hero or robed or shape=="banner":
        edge("Brocade mantle",[(-.21,0,0),(.21,0,0),(-.245,.095,-.31),(.234,.095,-.31),
             (-.321,.188,-.66),(.313,.203,-.60),(0,.265,-.772)],
             [(0,1,2),(1,3,2),(2,3,6),(2,6,4),(3,5,6)],cloth,mantle,.036)
        for sign in (-1,1):
            round_rod("Mantle border",(sign*.313,.189,-.653),(0,.260,-.762),.020,.015,mats["bright"],mantle)
    if ident=="kitsune":
        for sign in (-1,1):
            round_rod("Fox ear",(sign*.112,.025,.28),(sign*.153,.008,.436),.061,.007,accent,head)
            round_rod("Flared fox tail",(sign*.071,.146,-.24),(sign*.315,.46,.13),.099,.037,accent,hips)
    equipment(weapon,shape,theme,mats,left,right,hips,enemy,item)
    return root,shape,weapon

def equipment(kind,shape,theme,m,left,right,hips,enemy,item):
    shield_held=shape in ("bulwark","regent") or item["id"]=="warden"
    if shield_held:
        if theme=="rome":
            leather_box("Rounded legionary scutum",(0,-.178,-.293),(.397,.085,.55),m["shade"],left,(.09,0,0))
            leather_box("Scutum enamel",(0,-.224,-.291),(.348,.054,.493),m["cloth"],left,(.09,0,0))
        else:
            oval("Curved shield rim",(0,-.167,-.298),(.244,.070,.260),m["trim"],left,18,10)
            oval("Dyed shield face",(0,-.209,-.30),(.209,.043,.229),m["accent"],left,17,9)
        oval("Shield boss",(0,-.252,-.30),(.07,.038,.076),m["steel"],left,14,8)
        for side in (-1,1):
            round_rod("Enamel shield inlay",(.028*side,-.253,-.30),(.15*side,-.230,-.254),.013,.012,m["bright"],left)
    if kind in ("spear","glaive","javelin","hammer","staff","banner"):
        extended=kind in ("spear","glaive","banner")
        a=(.025,-.14,-.78)
        b=(.025,-.14,.70 if extended else .54)
        round_rod("Carved shaft",a,b,.029,.033,m["wood"],right)
        for z in (-.42,-.31,.20):
            oval("Wrapped grip",(.025,-.142,z),(.05,.046,.042),m["leather"],right,9,6)
        if kind=="hammer":
            leather_box("Rounded bronze maul",(.025,-.139,.554),(.335,.224,.166),m["trim"],right)
            oval("Maul inlay",(.025,-.261,.556),(.095,.025,.066),m["glow"] if enemy else m["accent"],right)
        elif kind=="banner":
            round_rod("Banner crosspiece",(-.156,-.14,.605),(.37,-.14,.605),.026,.026,m["trim"],right)
            edge("Dyed standard",[(-.12,-.136,.60),(.325,-.136,.60),(.325,-.096,.175),
                (.080,-.057,.23),(-.12,-.086,.14)],[(0,1,3),(1,2,3),(0,3,4)],m["accent"],right)
            oval("Standard emblem",(.095,-.159,.438),(.066,.018,.088),m["bright"],right,10,7)
        elif kind=="staff":
            round_rod("Crown collar",(.023,-.142,.47),(.023,-.142,.608),.075,.084,m["trim"],right)
            oval("Polished conduit",(.023,-.142,.669),(.128,.096,.147),m["glow"],right,9,7)
            for sign in (-1,1):
                round_rod("Conduit spine",(.03,-.141,.485),(sign*.142,-.143,.714),.019,.011,m["bright"],right)
        else:
            z=b[2]
            edge("Shaped blade",[(.002,-.143,z-.06),(.094,-.143,z+.103),
                (.106 if kind=="glaive" else .027,-.143,z+.34),(-.062,-.143,z+.122),(-.019,-.143,z-.06)],
                [(0,1,2,3,4)],m["steel"],right,.026)
    elif kind=="bow":
        points=[(.01,-.095,-.81),(.102,-.223,-.53),(.163,-.264,-.16),(.114,-.267,.13),(.058,-.193,.43),(.06,-.073,.72)]
        for a,b in zip(points[:-1],points[1:]):
            round_rod("Laminated bow limb",a,b,.030,.026,m["wood"],left)
        round_rod("Bowstring",points[0],points[-1],.012,.012,m["ivory"],left)
        round_rod("Tied quiver",(.19,.168,-.28),(.23,.196,.36),.087,.08,m["leather"],hips)
        for i in range(3):
            round_rod("Fletched arrow",(.20+.034*i,.2,.321),(.22+.04*i,.2,.542+.035*i),.015,.012,m["ivory"],hips)
    elif kind=="fan":
        ribs=[]
        center=(.03,-.155,-.29)
        for i in range(7):
            angle=(i-3)*.21
            endpoint=(center[0]+math.sin(angle)*.35,-.169,center[2]+math.cos(angle)*.36)
            ribs.append(endpoint)
            round_rod("Fan rib",center,endpoint,.012,.009,m["trim"],right,6)
        edge("Silk fan",[center,*ribs],[(0,j,j+1) for j in range(1,7)],m["accent"],right,.018)
    elif kind=="sling":
        round_rod("Tanned sling",(.010,-.104,-.303),(.13,-.164,-.550),.019,.017,m["leather"],right)
        oval("Sling pocket",(.13,-.168,-.592),(.085,.048,.061),m["steel"],right)
    else:
        round_rod("Wrapped sword grip",(.022,-.139,-.498),(.027,-.142,-.242),.035,.034,m["leather"],right)
        leather_box("Sword crossguard",(.025,-.145,-.239),(.169,.072,.043),m["trim"],right)
        blade_len=.39 if shape=="runner" else .53
        edge("Recurved sword",[(.002,-.14,-.23),(.092,-.14,-.21),(.106,-.14,blade_len*.54),(.04,-.14,blade_len),
             (-.008,-.14,blade_len*.49)],[(0,1,2,3,4)],m["steel"],right,.030)

def bake_skin(root, data):
    bpy.context.view_layer.update()
    refs=[root]+[obj for obj in root.children_recursive if obj.type=="EMPTY"]
    shape_collection=bpy.data.collections.new("Editable components")
    bpy.context.scene.collection.children.link(shape_collection)
    mesh_parts=[obj for obj in root.children_recursive if obj.type=="MESH"]
    positions=[]
    faces=[]
    pigment=[]
    weights=defaultdict(list)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for obj in mesh_parts:
        evaluated=obj.evaluated_get(depsgraph)
        surface=evaluated.to_mesh()
        points=[tuple(evaluated.matrix_world @ v.co) for v in surface.vertices]
        offset=len(positions)
        positions.extend(points)
        weights[obj.parent.name].extend(range(offset,offset+len(points)))
        for face in surface.polygons:
            faces.append(tuple(offset+index for index in face.vertices))
            pigment.append(tuple(obj.data.materials[face.material_index].diffuse_color))
        evaluated.to_mesh_clear()

    skeleton=bpy.data.armatures.new("Articulated rig")
    arm=bpy.data.objects.new(data["id"]+" rig",skeleton)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for ghost in refs:
        bone=skeleton.edit_bones.new(ghost.name)
        bone.head=ghost.matrix_world.translation
        bone.tail=bone.head+Vector((0,.19,0))
        if ghost.parent in refs:
            bone.parent=skeleton.edit_bones[ghost.parent.name]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.show_in_front=True

    mesh=bpy.data.meshes.new(data["id"]+" color and skin")
    mesh.from_pydata(positions,[],faces)
    mesh.update()
    attribute=mesh.color_attributes.new(name="Pigment",type="BYTE_COLOR",domain="CORNER")
    for face,palette_color in zip(mesh.polygons,pigment):
        face.use_smooth=True
        for i in face.loop_indices:
            attribute.data[i].color=palette_color
    mat=material("Baked textile, flesh and bronze","ffffff",.05)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=.61
    node=mat.node_tree.nodes.new("ShaderNodeVertexColor")
    node.layer_name="Pigment"
    mat.node_tree.links.new(node.outputs["Color"],mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    mesh.materials.append(mat)
    skin=bpy.data.objects.new(data["id"],mesh)
    bpy.context.collection.objects.link(skin)
    skin.parent=arm
    for bone,vertex_indices in weights.items():
        skin.vertex_groups.new(name=bone).add(vertex_indices,1.0,"REPLACE")
    modifier=skin.modifiers.new("Pose deformation","ARMATURE")
    modifier.object=arm
    modifier.use_deform_preserve_volume=True

    for obj in [*mesh_parts,*refs]:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        shape_collection.objects.link(obj)
    shape_collection.hide_render=True
    shape_collection.hide_viewport=True
    return arm,skin

def pose(offset=(0,0,0), rotation=(0,0,0), scale=1):
    return offset,rotation,(scale,scale,scale) if isinstance(scale,(int,float)) else scale

def animate(arm,shape,weapon,item):
    bones=arm.pose.bones
    for bone in bones:
        bone.rotation_mode="QUATERNION"
    def learn(name,duration,frames):
        for frame in sorted({1,duration,*frames}):
            targets=frames.get(frame,{})
            for bone in bones:
                pos,angles,scale=targets.get(bone.name,pose())
                from mathutils import Euler
                bone.location=pos
                bone.rotation_quaternion=Euler(angles,"XYZ").to_quaternion()
                bone.scale=scale
                for property in ("location","rotation_quaternion","scale"):
                    bone.keyframe_insert(property,frame=frame,group=bone.name)
        animation=arm.animation_data
        action=animation.action
        action.name=name
        animation.action=None
        track=animation.nla_tracks.new()
        track.name=name
        strip=track.strips.new(name,1,action)
        if hasattr(strip,"action_slot") and len(action.slots):
            strip.action_slot=action.slots[0]
        track.mute=True
    airy=shape=="spirit"
    walk={
        frame:{"Body":pose((0,.014,pow(abs(pulse),1.4)*.041),(.035,.0,.078*pulse)),
             "Head":pose(rotation=(.015,.0,-.057*pulse)),
             "LeftArm":pose(rotation=(-.28*pulse,-.08,.12)),
             "RightArm":pose(rotation=(.26*pulse,.065,-.10)),
             "LeftLeg":pose((0,0,max(0,pulse)*.083),(.48*pulse,0,.015)),
             "RightLeg":pose((0,0,max(0,-pulse)*.083),(-.48*pulse,0,-.015)),
             "Mantle":pose(rotation=(.16+abs(pulse)*.10,0,.16*pulse))}
        for frame,pulse in [(1,0),(5,.81),(9,1),(13,.49),(17,0),(21,-.81),(25,-1),(29,-.49),(33,0)]
    }
    if airy:
        for frame,values in walk.items():
            wave=math.sin(frame*TAU/32)
            values["Body"]=pose((0,0,.110+wave*.072),(.026,0,.09*wave))
            values["LeftArm"]=pose(rotation=(-.12+wave*.19,-.35*wave,.26))
            values["RightArm"]=pose(rotation=(-.12+wave*.19,.35*wave,-.26))
    learn("Walk",33,walk)
    learn("Idle",61,{
        15:{"Body":pose((0,0,.022),(.025,.006,.022)),"Mantle":pose(rotation=(.06,.02,.06))},
        30:{"Body":pose((0,0,.037 if not airy else .11),(.032,.0,-.019)),
            "Head":pose(rotation=(.033,.0,-.041)),"LeftArm":pose(rotation=(-.08,.02,-.015)),
            "RightArm":pose(rotation=(.045,0,.03)),"Mantle":pose(rotation=(.14,.02,-.021))},
        45:{"Body":pose((0,0,.021),(.021,-.031,0)),"Head":pose(rotation=(.0,.025,.045))},
    })
    if weapon in ("bow","sling"):
        wind={"LeftArm":pose(rotation=(-1.18,.04,.30)),"RightArm":pose(rotation=(-.51,-.64,.03)),
              "Body":pose((0,.045,.015),(.034,.0,-.37)),"Head":pose(rotation=(.0,0,.25))}
        release={"LeftArm":pose(rotation=(-1.44,.07,.13)),"RightArm":pose(rotation=(-.86,-.58,-.21)),
                 "Body":pose((0,-.048,.038),(-.13,.0,-.06)),"Mantle":pose(rotation=(.17,0,.11))}
    elif weapon in ("staff","fan","banner"):
        wind={"RightArm":pose(rotation=(-.77,.47,-.56)),"LeftArm":pose(rotation=(-.44,.23,.34)),
             "Body":pose((0,.019,.025),(.068,.0,-.29))}
        release={"RightArm":pose(rotation=(-1.50,-.39,.32)),"LeftArm":pose(rotation=(-.78,-.15,-.14)),
                 "Body":pose((0,-.064,.084),(-.16,.0,.22)),"Mantle":pose(rotation=(.37,0,-.17))}
    else:
        weight=1.15 if shape in ("titan","smith") else 1
        wind={"RightArm":pose(rotation=(.53*weight,-.24,-.35)),"LeftArm":pose(rotation=(-.31,.11,.16)),
              "Body":pose((0,.061,-.028),(.068,.0,.44))}
        release={"RightArm":pose(rotation=(-1.40*weight,.26,.13)),"LeftArm":pose(rotation=(-.60,-.14,-.10)),
              "Body":pose((0,-.112,.027),(-.22,.0,-.215)),
              "LeftLeg":pose((0,-.12,.023),(.23,0,0)),"Mantle":pose(rotation=(.36,0,-.16))}
    learn("Attack",28,{7:wind,12:release,16:release,22:{"Body":pose((0,-.031,0),(-.046,0,0))}})

    cast_seed=random.Random(item["id"]+" cast")
    swing=cast_seed.uniform(.2,.72)
    if weapon in ("glaive","sword","hammer"):
        learn("Cast",47,{
            8:{"Body":pose((0,.061,-.06),(.13,0,-swing)),"RightArm":pose(rotation=(-.47,.65,-.37)),
               "LeftArm":pose(rotation=(-.49,-.33,.29))},
            16:{"Figure":pose((0,-.045,.22 if shape=="duelist" else .09),(.01,0,swing*.62)),
              "RightArm":pose(rotation=(-2.04,.51,.68)),"LeftArm":pose(rotation=(-1.06,-.20,-.48)),
              "Body":pose((0,-.067,.04),(-.18,0,swing)),"Mantle":pose(rotation=(.51,0,.29))},
            26:{"RightArm":pose(rotation=(-1.19,-.41,swing)),"Body":pose((0,-.072,-.035),(-.20,0,.28)),
              "Mantle":pose(rotation=(.33,0,-.22))}
        })
    else:
        learn("Cast",47,{
            8:{"RightArm":pose(rotation=(-1.19,.54,-.53)),"LeftArm":pose(rotation=(-.79,-.41,.37)),
               "Body":pose((0,.008,.041),(.13,0,-swing)),"Head":pose(rotation=(.14,0,swing*.4))},
            16:{"RightArm":pose(rotation=(-1.96,.48,swing)),"LeftArm":pose(rotation=(-1.41,-.43,-swing)),
               "Body":pose((0,-.053,.115),(-.16,0,swing)),"Mantle":pose(rotation=(.40,0,-.19))},
            25:{"RightArm":pose(rotation=(-1.42,.29,.15)),"LeftArm":pose(rotation=(-.75,-.31,-.18)),
               "Body":pose((0,-.075,-.065),(-.24,0,.09))},
        })
    learn("Hit",18,{4:{"Body":pose((0,.105,-.047),(.23,.11,.10)),
                     "Head":pose(rotation=(.145,-.10,.081)),"LeftArm":pose(rotation=(.29,-.19,0))},
                     9:{"Body":pose((0,.039,-.027),(.092,0,-.032))}})
    learn("Death",38,{6:{"Figure":pose((0,.034,.057),(.18,0,.16)),
                         "RightArm":pose(rotation=(-.58,.36,.04))},
                        19:{"Figure":pose((0,.274,.164),(1.1,.18,.37)),
                         "LeftArm":pose(rotation=(-.93,-.32,-.41)),"RightArm":pose(rotation=(-.52,.37,.49))},
                        38:{"Figure":pose((0,.426,-.038),(1.55,.16,.48),.91),
                            "Body":pose(rotation=(-.12,0,0)),"Mantle":pose(rotation=(.22,0,-.17))}})
    learn("Spawn",25,{
        1:{"Figure":pose((0,0,-.28),(0,0,-.11),.74),"Body":pose(rotation=(-.19,0,0))},
        10:{"Figure":pose((0,0,.155),(0,0,.05),1.05),"RightArm":pose(rotation=(-.86,.38,0)),
            "LeftArm":pose(rotation=(-.37,-.12,0))},
        17:{"Figure":pose((0,0,-.035),(0,0,-.02),(.98,.98,.93))},
    })
    learn("Ascend",37,{10:{"Figure":pose((0,0,.19),(0,0,-.34),1.04),"Mantle":pose(rotation=(.48,0,.24))},
                      20:{"Figure":pose((0,0,.26),(0,0,.36),1.06),"RightArm":pose(rotation=(-1.24,.45,0)),
                          "LeftArm":pose(rotation=(-1.12,-.32,0))}})
    learn("Celebrate",54,{13:{"RightArm":pose(rotation=(-1.78,.44,.24)),"Figure":pose((0,0,.09),(0,0,.20))},
                         26:{"RightArm":pose(rotation=(-1.1,.33,-.16)),"LeftArm":pose(rotation=(-1.24,-.40,-.16)),
                             "Figure":pose((0,0,.13),(0,0,-.18))},39:{"Figure":pose((0,0,.04))}})

def furnish(item, enemy=False):
    clean()
    root,shape,weapon=build_puppet(item,enemy)
    arm,skin=bake_skin(root,item)
    animate(arm,shape,weapon,item)
    scene=bpy.context.scene
    scene.render.fps=30
    scene.frame_start=1
    scene.frame_end=61
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    skin.select_set(True)
    bpy.context.view_layer.objects.active=arm
    for track in arm.animation_data.nla_tracks:
        track.mute=False
    bpy.ops.export_scene.gltf(filepath=str(MODELS/f"{item['id']}.glb"),export_format="GLB",
       use_selection=True,export_yup=True,export_apply=False,export_animations=True,
       export_animation_mode="NLA_TRACKS",export_skins=True,export_cameras=False,export_lights=False)
    for track in arm.animation_data.nla_tracks:
        track.mute=track.name!="Idle"
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES/f"{item['id']}.blend"),compress=True)
    if not enemy:
        render_card(arm,item)

def render_card(arm,item):
    scene=bpy.context.scene
    hero=item.get("kind")=="hero"
    large=item["id"] in ("thekla","marcus","akari")
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=660 if large else 300
    scene.render.resolution_y=770 if large else 360
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    shading=scene.display.shading
    shading.light="STUDIO"
    shading.color_type="VERTEX"
    shading.show_shadows=True
    shading.show_cavity=True
    shading.cavity_type="BOTH"
    shading.curvature_ridge_factor=.65
    shading.curvature_valley_factor=.74
    shading.show_specular_highlight=True
    bpy.ops.object.camera_add(location=(2.6,-5.8,2.53))
    camera=bpy.context.object
    camera.data.type="ORTHO"
    camera.data.ortho_scale=2.71 if not hero else 3.15
    look_at(camera,(0,0,.86))
    scene.camera=camera
    frame=11 if hero else 19
    for track in arm.animation_data.nla_tracks:
        track.mute=track.name!=("Cast" if hero else "Idle")
    scene.frame_set(frame)
    scene.render.filepath=str(PORTRAITS/f"{item['id']}.png")
    bpy.ops.render.render(write_still=True)

def main():
    subset=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    for item in CATALOG["actors"]:
        if item["kind"]=="building" or (subset and item["id"] not in subset):
            continue
        furnish(item)
    for item in CATALOG["enemies"]:
        if not subset or item["id"] in subset:
            furnish(item,True)

if __name__=="__main__":
    main()
