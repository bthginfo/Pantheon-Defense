"""Render inspection photos from the actual rigged Blender files used for the game."""
from argparse import ArgumentParser
from pathlib import Path
import sys

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from forge import SOURCES, look_at, material, rgba
from geometry import mesh_object


VIEWS = {
    'hero': ((.72,-6.1,1.60),(.002,-.044,1.117),2.445, (850,1090)),
    'three-quarter': ((-2.65,-6.3,1.62),(.004,-.044,1.117),2.445, (850,1090)),
    'front': ((.001,-6.1,1.53),(.002,-.044,1.116),2.445, (820,1080)),
    'profile': ((-5.7,-.35,1.57),(.002,-.11,1.116),2.445, (820,1080)),
    'back': ((-.57,5.7,1.71),(.002,-.020,1.116),2.445, (820,1080)),
    'head': ((-.36,-4.,1.83),(.024,-.034,1.661),.515, (800,800)),
    'finish': ((.58,-5.6,1.57),(.13,-.09,1.197),1.64, (860,930)),
    'action': ((1.14,-6.1,2.08),(.002,-.086,1.087),2.680, (840,1090)),
}


def light(name, location, target, energy, width, color):
    lamp=bpy.data.lights.new(name,'AREA')
    lamp.shape='DISK'
    lamp.size=width
    lamp.energy=energy
    lamp.color=color
    obj=bpy.data.objects.new(name,lamp)
    bpy.context.scene.collection.objects.link(obj)
    obj.location=location
    look_at(obj,target)


def studio(scene):
    for obj in list(scene.objects):
        if obj.type=='LIGHT':
            bpy.data.objects.remove(obj,do_unlink=True)
    scene.render.film_transparent=False
    scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=rgba('9a9995')
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.46
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.33
    floor=material('Warm charcoal studio floor','433c3a')
    shader=floor.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value=.87
    mesh_object('Ground plane for contact shadows',[(-150,-150,-.006),(150,-150,-.006),
                (150,150,-.006),(-150,150,-.006)],[(0,1,2,3)],floor,None)
    light('Broad warm key',(-2.2,-3.1,4.9),(0,0,1.1),513,2.8,(1.,.83,.69))
    light('Soft cool fill',(3.9,-3.2,3.3),(0,0,1.3),175,3.4,(.81,.87,1.))
    light('Warm edge on wool and bronze',(1.9,1.8,3.8),(0,0,1.25),351,2.50,(1.,.82,.68))
    light('Long reflection on armour',(-1.3,-2.15,2.25),(0,0,1.21),91,2.40,(1.,.93,.84))


def render(name, source, output, views, draft):
    bpy.ops.wm.open_mainfile(filepath=str(source/f'{name}.blend'))
    scene=bpy.context.scene
    studio(scene)
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.resolution_percentage=65 if draft else 100
    scene.eevee.taa_render_samples=16 if draft else 42
    arm=bpy.data.objects[f'{name} rig']
    for label in views:
        eye,center,scale,dimensions=VIEWS[label]
        if label=='three-quarter' and name=='thekla':
            center=(.036,-.044,1.013)
            scale=2.26
        if label=='head' and name=='marcus':
            eye=eye[0],eye[1],eye[2]+.073
            center=center[0],center[1],center[2]+.073
            scale=.561
        scene.camera.location=eye
        scene.camera.data.ortho_scale=scale
        look_at(scene.camera,center)
        scene.render.resolution_x,scene.render.resolution_y=dimensions
        for clip in arm.animation_data.nla_tracks:
            clip.mute=clip.name!=('Attack' if label=='action' else 'Idle')
        scene.frame_set(13 if label=='action' else 1)
        scene.render.filepath=str(output/f'{name}-{label}.png')
        bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    cli=ArgumentParser(description=__doc__)
    cli.add_argument('--source',type=Path,default=SOURCES)
    cli.add_argument('--output',type=Path,required=True)
    cli.add_argument('--actors',nargs='+',choices=('thekla','marcus'),default=['thekla','marcus'])
    cli.add_argument('--views',nargs='+',choices=VIEWS,default=list(VIEWS))
    cli.add_argument('--draft',action='store_true')
    args=cli.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output.mkdir(parents=True,exist_ok=True)
    for name in args.actors:
        render(name,args.source,args.output,args.views,args.draft)
