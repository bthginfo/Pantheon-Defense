"""Assemble Blender armatures, bake the original character meshes, and render their portraits."""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import CATALOG, MODELS, PORTRAITS, SOURCES, clean, look_at
from figures import humanoid
from geometry import color_material, studio

TAU = math.tau


def bake_skin(root, data):
    bpy.context.view_layer.update()
    refs=[root]+[obj for obj in root.children_recursive if obj.type=="EMPTY"]
    shape_collection=bpy.data.collections.new("Editable components")
    bpy.context.scene.collection.children.link(shape_collection)
    mesh_parts=[obj for obj in root.children_recursive if obj.type=="MESH"]
    positions=[]
    faces=[]
    pigment=[]
    normals=[]
    smoothing=[]
    weights=defaultdict(list)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for obj in mesh_parts:
        evaluated=obj.evaluated_get(depsgraph)
        surface=evaluated.to_mesh()
        points=[tuple(evaluated.matrix_world @ v.co) for v in surface.vertices]
        offset=len(positions)
        positions.extend(points)
        weights[obj.parent.name].extend(range(offset,offset+len(points)))
        matrix=evaluated.matrix_world.to_3x3().inverted().transposed()
        for face in surface.polygons:
            faces.append(tuple(offset+index for index in face.vertices))
            pigment.append(tuple(surface.materials[face.material_index].diffuse_color))
            normals.append((matrix @ face.normal).normalized())
            smoothing.append(face.use_smooth)
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
    mesh.color_attributes.active_color=attribute
    bvh=BVHTree.FromPolygons(positions,faces)
    probes=[Vector(x).normalized() for x in ((-.42,-.77,.77),(.57,-.24,.61),(.23,.57,.61))]
    light=[0.]*len(mesh.vertices)
    count=[0]*len(mesh.vertices)
    for face,color,normal,smooth in zip(mesh.polygons,pigment,normals,smoothing):
        face.use_smooth=smooth
        site=face.center+normal*.014
        enclosed=sum(bvh.ray_cast(site+ray*.012,ray,.115)[2] is not None for ray in probes if ray.dot(normal)>.13)
        tint=.95-.088*enclosed+.11*max(0.,normal.z)
        for i in face.vertices:
            light[i]+=tint
            count[i]+=1
    for face,color in zip(mesh.polygons,pigment):
        for loop,i in zip(face.loop_indices,face.vertices):
            tint=light[i]/count[i]
            attribute.data[loop].color=(color[0]*tint,color[1]*tint,color[2]*tint,1.)
    mat=color_material("Painted metal edges, textile and clay")
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
        if shape=="hound":
            frames=bound_hound(name,frames)
        elif shape=="moth":
            frames=flutter(name,frames,duration)
        elif shape=="wisp":
            frames=float_wisp(name,frames,duration)
        else:
            for posture in frames.values():
                for side in ("Left","Right"):
                    arm_pose=posture.get(side+"Arm")
                    if arm_pose:
                        angle=arm_pose[1][0]
                        posture[side+"Forearm"]=pose(rotation=(max(-.60,min(.23,angle*.44)),0,0))
        for frame in sorted({1,duration,*frames}):
            targets=frames.get(frame,{})
            for bone in bones:
                pos,angles,scale=targets.get(bone.name,pose())
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

def bound_hound(name,frames):
    if name=="Walk":
        for frame,posture in frames.items():
            phase=math.sin((frame-1)*TAU/32)
            posture.update({
                "Body":pose((0,0,abs(phase)*.073),(.09*phase,0,0)),
                "Head":pose(rotation=(-.12*phase,0,0)),
                "LeftLeg":pose(rotation=(.64*phase,0,0)),
                "RightLeg":pose(rotation=(-.64*phase,0,0)),
                "LeftArm":pose(rotation=(-.64*phase,0,0)),
                "RightArm":pose(rotation=(.64*phase,0,0)),
                "Mantle":pose(rotation=(.17*phase,0,-.27*phase)),
            })
    return frames


def flutter(name,frames,duration):
    if name not in ("Walk","Idle","Cast","Spawn"):
        return frames
    for frame in range(1,duration,4):
        phase=math.sin((frame-1)*TAU/16)
        pose_frame=frames.setdefault(frame,{})
        pose_frame.update({
            "LeftArm":pose(rotation=(.12+.17*phase,.86*phase,0)),
            "RightArm":pose(rotation=(.12+.17*phase,-.86*phase,0)),
            "Body":pose((0,0,.082*abs(phase)),(.11*phase,0,0)),
        })
    return frames


def float_wisp(name,frames,duration):
    if name not in ("Walk","Idle","Cast","Spawn"):
        return frames
    for frame in range(1,duration,5):
        phase=math.sin((frame-1)*TAU/50)
        key=frames.setdefault(frame,{})
        key["Body"]=pose((0,0,.12*phase),(0,0,.11*phase))
        key["Mantle"]=pose(rotation=(.16*phase,phase*.77,(frame-1)*TAU/60))
    return frames


def select_export(arm,skin):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    skin.select_set(True)
    bpy.context.view_layer.objects.active=arm


def furnish(item, enemy=False, review=False):
    clean()
    if enemy:
        from beasts import enemy_model
        root,shape,weapon=enemy_model(item)
    else:
        root,shape,weapon=humanoid(item)
    arm,skin=bake_skin(root,item)
    animate(arm,shape,weapon,item)
    significant=item["id"] in ("thekla","marcus","akari")
    height=1.37 if item["id"]=="titan" else 1.14 if item["id"]=="golem" else .97
    scale=3.63 if item["id"]=="titan" else 2.95 if item["id"]=="golem" else 2.58 if significant else 2.27
    scene,camera=studio((3.1,-7.6,2.74),(.02,0,height),580 if significant else 264,
        710 if significant else 334,scale,samples=22 if significant else 10,transparent=True)
    scene.render.fps=30
    scene.frame_start=1
    scene.frame_end=61
    scene.frame_set(1)
    select_export(arm,skin)
    for track in arm.animation_data.nla_tracks:
        track.mute=False
    bpy.ops.export_scene.gltf(filepath=str(MODELS/f"{item['id']}.glb"),export_format="GLB",
        use_selection=True,export_yup=True,export_apply=False,export_animations=True,
        export_animation_mode="NLA_TRACKS",export_skins=True,export_cameras=False,export_lights=False,
        export_all_vertex_colors=False)
    for track in arm.animation_data.nla_tracks:
        track.mute=track.name!="Idle"
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES/f"{item['id']}.blend"),compress=True)
    if not enemy:
        hero=item["kind"]=="hero"
        scene.frame_set(9 if hero else 20)
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGBA"
        scene.render.filepath=str(PORTRAITS/f"{item['id']}.png")
        bpy.ops.render.render(write_still=True)
    if review:
        Path("/tmp/pd-atelier").mkdir(exist_ok=True)
        scene.frame_set(1)
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGBA"
        scene.render.resolution_x=460
        scene.render.resolution_y=560
        camera.data.ortho_scale=max(scale,2.72)
        for label,xyz in (("front",(0,-6,2.0)),("side",(6,-.04,2.28)),("back",(0,6,2.32)),
                          ("three-quarter",(3.5,-6.2,3.12))):
            camera.location=xyz
            look_at(camera,(0,0,height))
            scene.render.filepath=f"/tmp/pd-atelier/{item['id']}-{label}.png"
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    arguments=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    review="--review" in arguments
    arguments.discard("--review")
    for item in CATALOG["actors"]:
        if item["kind"]!="building" and (not arguments or item["id"] in arguments):
            furnish(item,review=review)
    for item in CATALOG["enemies"]:
        if not arguments or item["id"] in arguments:
            furnish(item,True,review)
