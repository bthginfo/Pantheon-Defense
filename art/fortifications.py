"""Original Blender structures, mechanical actions, and readable spell projectiles."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from cast import bake_skin, pose, select_export
from figures import cut, emblem, fabric_panel, pin
from forge import CATALOG, MODELS, PORTRAITS, SOURCES, clean, empty, material, span
from geometry import bevel_block as block, color_material, mesh_object, shell, silhouette, studio, torus_mesh


ACCENTS = {
    "aegean": ("d8c3a0","b4a186","557e76","b89860","93664b","50616a","efd0a0","cf9263"),
    "rome": ("c6a084","a27763","895353","c39868","80604c","5e6267","e5ba8b","d49462"),
    "japan": ("b8b5a0","848d83","a76058","bd9f71","896557","475969","e3c195","96b2ad"),
}


def palette(data):
    b=ACCENTS[data["theme"]]
    return {key:material(key,value,metallic) for key,value,metallic in [
        ("stone",b[0],0),("foundation",b[1],0),("accent",b[2],0),("gold",b[3],.17),
        ("wood",b[4],0),("hem",b[5],0),("fillet",b[6],.15),("light",b[7],0),
        ("dark wood","5a4b42",0),("metal","a2aaa6",.26),("fabric","dbba95",0),
    ]}


def plinth(root,m,shape="bevel"):
    if shape=="round":
        shell("Fluted drum footing",[(0,.565,.48,0,0),(.08,.626,.57,0,0),
             (.18,.595,.55,0,0),(.236,.53,.49,0,0)],m["foundation"],root,12)
        torus_mesh("Inlaid marble base ring",(0,0,.21),.475,.021,m["gold"],root,24)
    else:
        for height,w,d,paint in (
            (.049,1.46,1.14,"foundation"),(.133,1.38,1.04,"stone"),(.207,1.25,.95,"foundation")):
            block("Each course of the hewn masonry plinth",(0,0,height),(w,d,.123),m[paint],root,.052)
        for x in (-.54,.54):
            for y in (-.38,.38):
                pin("Inset base coin",(x,y,.275),.052,m["gold"],root)


def roof(parent, width, length, z, h,m):
    for side in (-1,1):
        points=[(x*width, side*y*length, z+lift*h) for x,y,lift in [
            (-.60,.57,-.02),(.60,.57,-.02),(.53,.34,.122),(.38,0,.71),(-.38,0,.71),(-.53,.34,.122)]]
        faces=[(0,1,2,5),(5,2,3,4)] if side<0 else [(5,2,1,0),(4,3,2,5)]
        obj=mesh_object("Hand-cut roof sweep",points,faces,m["hem"],parent)
        obj.modifiers.new("Visible ceramic thickness","SOLIDIFY").thickness=.059
        for i in range(11):
            x=(i-5)*width*.10
            points=[(x,side*length*.57,z-.009),(x*.9,side*length*.32,z+.145*h),
              (x*.71,0,z+.74*h)]
            for a,b in zip(points,points[1:]):
                span("Raised fish-scale ceramic ridge",a,b,.033,m["foundation"] if i in (0,10) else m["hem"],parent,7,.026)
    span("Carved hip ridge",(-.43*width,0,z+.754*h),(.43*width,0,z+.754*h),.052,m["gold"],parent,8)


def ballista(data,root,m):
    plinth(root,m)
    base=empty("Mechanism",(0,0,.465),root)
    focus=empty("Focus",(0,-.24,.267),base)
    roman=data["id"]=="scorpio"
    for side in (-1,1):
        for z,y,tilt in ((.32,.115,0),(.53,.166,.374)):
            post=block("Mortised seasoned timber cheek",(side*.311,y,z),(.19,.75,.226),
                 m["dark wood"] if roman else m["wood"],root,.048)
            post.rotation_euler.x=tilt
        for j in range(3):
            block("Fitted iron brace",(side*.31,.126+.064*j,.470+.072*j),(.230,.109,.109),
                  m["hem"],root,.023)
        span("A-frame mortise brace",(side*.445,.333,.255),(side*.280,.119,.692),.066,m["wood"],root,8)
        shell("Wound torsion spring and its casting",[
            (.12,.106,.103,side*.294,-.185),(.17,.121,.121,side*.294,-.185),(.37,.117,.117,side*.294,-.185),
            (.42,.094,.095,side*.294,-.185)
        ],m["gold"],base,9,True)
        for z in (.18,.243,.305):
            torus_mesh("Individual torsion string coil",(side*.294,-.184,z),.112,.015,m["dark wood"],base,12,5)
        for k,(x,z) in enumerate(((.31,.30),(.46,.31),(.655,.325),(.747,.354))):
            if k:
                y=-.31+(k-1)*.045
                p=block("Laminated composite bow limb",(side*x,y,z),(.217,.106,.079),
                        m["wood"] if k!=2 else m["gold"],base,.025,side*.28)
        span("Drawn sinew rope",(side*.745,-.200,.36),(0,.337,.381),.013,m["fabric"],base,6)
    block("Central bronze lined rail",(0,.015,.242),(.307,1.173,.160),m["wood"],base,.041)
    for side in (-1,1):
        block("Iron edges of the grooved flight rail",(side*.079,.013,.334),(.053,1.115,.050),m["metal"],base,.017)
    span("Loaded shaft attached to the release",(0,.44,.367),(0,-.414,.367),.025,m["wood"],base,7)
    tip=silhouette("Planar forged bolt head",[(-.052,.324),(.052,.324),(.025,.381),(0,.518),(-.027,.378)],
                   .07,m["metal"],focus)
    tip.location=(0,-.238,-.246)
    tip.rotation_euler.x=-math.pi/2
    for n in range(2):
        x=(n-.5)*.179
        block("Recessed winch spool collar",(x,.522,.188),(.11,.137,.153),m["gold"],base,.025)
    return base,focus


def flame(root,m,source,style):
    x,y,z=source
    for i in range(6):
        a=math.tau*i/6
        rad=.107+.026*math.sin(i*2.)
        colors=(m["light"],m["gold"],m["fillet"])
        p=(x+rad*math.cos(a),y+rad*math.sin(a),z+.063+(.030*i))
        flame=cut("Layered facets of flame or spirit light",root,p,(.091,.093,.206 if i%2 else .164),
                  colors[i%len(colors)],2 if i==0 else 1)
        flame.rotation_euler.x=math.sin(a)*.39
        flame.rotation_euler.y=math.cos(a)*.35


def brazier(data,root,m):
    ident=data["id"]
    plinth(root,m,"round")
    turn=empty("Mechanism",(0,0,.68),root)
    glow=empty("Focus",(0,0,.48 if ident=="beacon" else .268),turn)
    if ident=="beacon":
        for i in range(5):
            z=.31+.147*i
            radius=.436-.048*i
            shell("Tapering courses of the lighthouse",[(z-.056,radius,radius,0,0),
               (z+.051,radius*1.02,radius*1.02,0,0)],m["stone"] if i%2 else m["foundation"],root,10)
        h=1.034
        shell("Open annular lantern ledge",[(h-.095,.375,.375,0,0),(h,.447,.447,0,0),
            (h+.076,.454,.454,0,0)],m["gold"],root,12)
        for i in range(6):
            a=i*math.tau/6
            p=(math.cos(a)*.362,math.sin(a)*.362,h+.258)
            block("Seaward lantern spokes",p,(.052,.065,.367),m["accent"],root,.014,a)
        torus_mesh("Cast lantern railing",(0,0,h+.409),.360,.026,m["dark wood"],root,20)
        shell("Pitched copper lantern roof",[(h+.405,.42,.42,0,0),(h+.475,.416,.416,0,0),
            (h+.645,.146,.146,0,0),(h+.68,.062,.062,0,0)],m["hem"],root,12)
        flame(glow,m,(0,0,0),"sea")
    else:
        stairs=ident=="sun_shrine"
        for i in range(4 if stairs else 3):
            a=i*math.tau/(4 if stairs else 3)+.48
            t=(math.cos(a)*.308,math.sin(a)*.278,.234)
            span("Slender cast pedestal support",t,(t[0]*.85,t[1]*.85,.79),.059,m["gold"] if stairs else m["hem"],root,8,.077)
            pin("Ornate cast shoulder at the join",(t[0]*.89,t[1]*.89,.72),.085,m["fillet"],root)
        shell("Wide reeded fire bowl",[(.65,.207,.207,0,0),(.72,.208,.208,0,0),(.84,.408,.408,0,0),
               (.902,.447,.447,0,0),(.941,.43,.43,0,0)],m["accent"] if stairs else m["hem"],root,16)
        torus_mesh("Decorative fire bowl lip",(0,0,.93),.428,.037,m["gold"],root,22)
        for i in range(4):
            a=i*math.tau/4
            pin("Cradled fire bowl boss",(.393*math.cos(a),.393*math.sin(a),.853),.053,m["fillet"],root)
        if stairs:
            for z,w in ((.08,.71),(.16,.655),(.24,.603)):
                block("Low offering stairs",(0,-.481-z*.20,z),(w,.371,.126),m["stone"],root,.028)
        flame(glow,m,(0,0,0),"sun")
    return turn,glow


def gateway(data,root,m):
    ident=data["id"]
    plinth(root,m)
    turn=empty("Mechanism",(0,-.021,.989),root)
    charm=empty("Focus",(0,-.096,-.140),turn)
    if ident=="torii":
        for side in (-1,1):
            x=side*.468
            span("Tapered scarlet torii trunk",(x,0,.249),(x*.89,0,1.390),.12,m["accent"],root,8,.089)
            shell("Stone base socket",[(.214,.18,.18,x,0),(.299,.158,.158,x,0),
                (.361,.138,.138,x,0)],m["hem"],root,9)
            for z in (.59,1.02):
                torus_mesh("Carved lacquer collar",(x*(1-.11*((z-.249)/1.141)),0,z),.101,.015,m["gold"],root,16)
        block("Lower lintel with exposed joinery",(0,0,1.088),(1.396,.159,.141),m["accent"],root,.036)
        curved=[(-.822,1.417),(-.628,1.317),(-.32,1.291),(.32,1.291),(.628,1.317),
            (.822,1.417),(.804,1.506),(.562,1.442),(-.562,1.442),(-.804,1.506)]
        silhouette("Outer upward-cut torii beam",curved,.251,m["hem"],root)
        block("Red inner torii lintel",(0,0,1.279),(1.466,.228,.130),m["accent"],root,.024)
    else:
        for side in (-1,1):
            for y in (-.28,.30):
                block("Square timber watchtower joist",(side*.397,y,.72),(.151,.15,.962),m["wood"],root,.022)
        for side in (-1,1):
            for i in range(6):
                x=(i-2.5)*.129
                block("Ventilated plank balustrade",(x,.419*side,.92),(.117,.061,.375),
                    m["accent"] if i%2==0 else m["wood"],root,.017)
        block("Deck railing belt",(0,0,1.099),(1.049,.997,.100),m["dark wood"],root,.029)
        roof(root,.99,.87,1.325,.51,m)
    block("Hanging lacquered plaque",(0,-.108,-.006),(.307,.081,.254),m["wood"],turn,.029)
    emblem("moon" if ident=="torii" else "sun",turn,0,-.159,-.003,.46,m)
    cut("Carved charm",charm,(0,0,-.01),(.086,.027,.176),m["light"],1)
    return turn,charm


def standard(data,root,m):
    is_bell=data["id"]=="bell"
    plinth(root,m,"round" if is_bell else "bevel")
    turn=empty("Mechanism",(0,0,1.397),root)
    charm=empty("Focus",(0,-.026,-.192),turn)
    if is_bell:
        for side in (-1,1):
            span("Bracketed cedar post",(side*.554,0,.198),(side*.505,0,1.588),.087,m["wood"],root,8,.071)
            strut=block("Wooden angular bracket",(side*.467,0,1.344),(.46,.184,.114),m["hem"],root,.028)
            strut.rotation_euler.y=side*.502
        block("Temple support beam",(0,0,1.421),(1.312,.163,.131),m["accent"],root,.021)
        roof(root,1.22,.903,1.54,.356,m)
        shell("Cast weathered bell body",[(-.631,.356,.356,0,0),(-.557,.349,.349,0,0),(-.324,.277,.277,0,0),
            (-.121,.227,.227,0,0),(-.031,.151,.152,0,0)],m["gold"],turn,16)
        torus_mesh("Raised patina on the bell mouth",(0,0,-.605),.351,.033,m["accent"],turn,24)
        for i in range(7):
            a=i*math.tau/7
            pin("Cast nodule in the bell rim",(.324*math.cos(a),.324*math.sin(a),-.492),.035,m["hem"],turn)
        span("Hanging brass clapper",(0,0,-.158),(0,0,-.535),.037,m["wood"],charm,8)
        cut("Heavy bell clapper",(charm),(0,0,-.507),(.10,.10,.089),m["fillet"],2)
    else:
        span("Engraved legion standard post",(0,0,.188),(0,0,1.733),.070,m["dark wood"],root,9,.042)
        for z in (.40,.96,1.61):
            torus_mesh("Polished standard collar",(0,0,z),.067,.027,m["gold"],root,17)
        span("Hung standard crossbar",(-.435,0,.037),(.435,0,.037),.041,m["gold"],turn,8)
        fabric_panel("Folded decorated military standard",turn,.353,.324,.745,.06,.13,m,center=(0,-.016,.007),cascade=True)
        emblem("wing",turn,0,-.075,-.309,1.13,m)
        cut("Brass standard finial",(root),(0,0,1.78),(.17,.061,.084),m["gold"],1)
        span("Small pennant",(-.28,-.036,-.073),(-.301,-.081,-.263),.030,m["fillet"],turn,7)
    return turn,charm


def animate(arm,weapon):
    bones=arm.pose.bones
    for bone in bones:
        bone.rotation_mode="QUATERNION"
    recoil=.207 if weapon else .072
    for name,duration,keys in [
        ("Idle",42,{12:(.016,-.020,.052,1.084),28:(-.012,.03,.083,.940)}),
        ("Attack",25,{6:(-.214,recoil,.044,1.38),13:(.073,-.061,-.030,.79),19:(.026,-.017,.033,1.08)}),
        ("Cast",37,{11:(.138,-.068,.124,1.35),22:(-.172,.059,.170,1.23)}),
    ]:
        for frame in sorted({1,*keys,duration}):
            turn,shift,lift,grow=keys.get(frame,(0.,0.,0.,1.))
            for bone in bones:
                if bone.name=="Mechanism":
                    offset,rot,scale=pose((0,shift,0),(turn,0,0))
                elif bone.name=="Focus":
                    offset,rot,scale=pose((0,0,lift),(0,.21*turn,0),grow)
                else:
                    offset,rot,scale=pose()
                bone.location=offset
                bone.rotation_quaternion=Euler(rot,"XYZ").to_quaternion()
                bone.scale=scale
                for field in ("location","rotation_quaternion","scale"):
                    bone.keyframe_insert(field,frame=frame,group=bone.name)
        animation=arm.animation_data
        action=animation.action
        action.name=name
        animation.action=None
        track=animation.nla_tracks.new()
        track.name=name
        strip=track.strips.new(name,1,action)
        if hasattr(strip,"action_slot") and action.slots:
            strip.action_slot=action.slots[0]
        track.mute=True


def structure(data):
    clean()
    m=palette(data)
    root=empty("Fortification")
    item=data["id"]
    if item in ("ballista","scorpio"):
        ballista(data,root,m)
    elif item in ("torii","yagura"):
        gateway(data,root,m)
    elif item in ("standard","bell"):
        standard(data,root,m)
    else:
        brazier(data,root,m)
    arm,skin=bake_skin(root,data)
    animate(arm,item in ("ballista","scorpio"))
    scene,camera=studio((3.2,-5.4,3.55),(0,0,.84),330,370,2.52,samples=9,transparent=True)
    scene.render.fps=30
    scene.frame_set(1)
    select_export(arm,skin)
    for track in arm.animation_data.nla_tracks:
        track.mute=False
    bpy.ops.export_scene.gltf(filepath=str(MODELS/f"{item}.glb"),export_format="GLB",use_selection=True,
        export_animation_mode="NLA_TRACKS",export_all_vertex_colors=False,export_lights=False,export_cameras=False)
    for track in arm.animation_data.nla_tracks:
        track.mute=track.name!="Idle"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES/f"{item}.blend"),compress=True)
    scene.frame_set(15)
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.filepath=str(PORTRAITS/f"{item}.png")
    bpy.ops.render.render(write_still=True)


def projectile(name):
    clean()
    root=empty("Formed projectile")
    colors={"bolt":("ebe1c6","a76547","aac2b8"),"spark":("ffdd91","e8a163","b38277"),
        "frost":("d5fbf0","7dd9d0","4c93a9"),"sun":("ffe2a0","f9ae6b","d07955")}
    inner,edge,trail=[material("Light facet "+c,c) for c in colors[name]]
    if name=="bolt":
        span("Balanced tapered bolt shaft",(0,.36,0),(0,-.31,0),.037,edge,root,8)
        span("Hammered broadhead",(0,-.26,0),(0,-.521,0),.079,inner,root,6,.008)
        for k in range(3):
            a=math.tau*k/3
            p=(.084*math.cos(a), .307, .084*math.sin(a))
            mesh_object("Bolt flight vanes",[(0,.188,0),(0,.383,0),p],[(0,1,2)],trail,root)
    else:
        cut("Cut colour core",root,(0,-.078,0),(.129,.208,.134),inner,2)
        for k in range(4):
            a=math.tau*k/4
            p=(.107*math.cos(a),.103,.112*math.sin(a))
            span("Long tapered fine light shard",p,(p[0]*.45,.319,p[2]*.51),.065,edge if k%2 else trail,root,6,.003)
        loop=torus_mesh("Tapered trail bank",(0,.121,0),.132,.017,edge,root,16,5)
        loop.rotation_euler.x=math.pi/2
    bpy.context.view_layer.update()
    parts=[p for p in root.children_recursive if p.type=="MESH"]
    points,faces,colors=[],[],[]
    for obj in parts:
        start=len(points)
        points.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        for f in obj.data.polygons:
            faces.append(tuple(start+i for i in f.vertices))
            colors.append(tuple(obj.data.materials[f.material_index].diffuse_color))
    pigment=color_material("Blender painted light",unlit=True)
    mesh=mesh_object("Styled projectile",points,faces,pigment,None)
    color=mesh.data.color_attributes.new(name="Pigment",type="BYTE_COLOR",domain="CORNER")
    mesh.data.color_attributes.active_color=color
    for f,c in zip(mesh.data.polygons,colors):
        for i in f.loop_indices:
            color.data[i].color=c
    originals=bpy.data.collections.new("Editable projectile construction")
    bpy.context.scene.collection.children.link(originals)
    for obj in [*parts,root]:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        originals.objects.link(obj)
    originals.hide_render=True
    originals.hide_viewport=True
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    bpy.ops.export_scene.gltf(filepath=str(MODELS/f"fx_{name}.glb"),export_format="GLB",use_selection=True,
        export_animations=False,export_all_vertex_colors=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES/f"fx_{name}.blend"),compress=True)


if __name__=="__main__":
    args=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    for item in CATALOG["actors"]:
        if item["kind"]=="building" and (not args or item["id"] in args):
            structure(item)
    for name in ("bolt","spark","frost","sun"):
        if not args or f"fx_{name}" in args:
            projectile(name)
