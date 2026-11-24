"""Fitted adult head sculpts shaped from the two CC0 anatomy meshes in reference-data."""
from functools import lru_cache
from gzip import open as gzip_open
from json import load
from math import exp
from pathlib import Path
from random import Random

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from commander_portraits import beard, eyes
from forge import empty, material
from geometry import mesh_object


WOMEN = {
    'toxotes', 'oracle', 'peltast', 'selene_cult', 'melia', 'harmonia', 'astra', 'thalassa',
    'vesta', 'livia', 'aurelia', 'octavia', 'cassia', 'tessen', 'kitsune', 'miko',
    'akari', 'tomoe', 'sayo', 'hana',
}


@lru_cache(maxsize=2)
def portrait_geometry(donor):
    path=Path(__file__).with_name('reference-data')/f'{donor}-anatomy.json.gz'
    with gzip_open(path,'rt') as source:
        data=load(source)
    eye_height=data['joints']['l-eye'][2]
    visible=[all(data['positions'][index][2]>eye_height-.151 for index in face)
             for face in data['faces']]
    faces=[face for face,keep in zip(data['faces'],visible) if keep]
    indices=sorted({index for face in faces for index in face})
    remap={index:local for local,index in enumerate(indices)}
    lip_indices=set(data['lip_vertices'])
    return ([data['positions'][index] for index in indices],
            [tuple(remap[index] for index in face) for face in faces],
            {local for local,index in enumerate(indices) if index in lip_indices},
            data['joints'])


class Portrait:
    def __init__(self,head,donor,joints,mesh):
        self.head=head
        self.name=donor
        self.joints=joints
        self.eye_height=joints['l-eye'][2]
        self.surface=BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(face.vertices) for face in mesh.polygons])

    def part(self,_name):
        return self.head

    def joint(self,name):
        x,y,z=self.joints[name]
        return Vector((x,y,z-self.eye_height))

    def face_depth(self,x,z):
        front,_,_,_=self.surface.ray_cast(Vector((x,-.63,z)),Vector((0,1,0)),.83)
        return None if front is None else front.y


def sculpt_head(parent,m,ident,broad,with_beard):
    donor='thekla' if ident in WOMEN else 'marcus'
    points,faces,lips,joints=portrait_geometry(donor)
    rng=Random(ident+' face planes')
    jaw,cheek,nose=(rng.uniform(-w,w) for w in (.15,.11,.009))
    eye=Vector(joints['l-eye'])
    sx,sy,sz=2.075*broad,1.94,1.79
    head=empty('Portrait sculpture',(0.,-.134-eye.y*sy,.239),parent)
    head.scale=(sx,sy,sz)
    sculpted=[]
    for x,y,z in points:
        height=z-eye.z
        cheekbone=exp(-((height+.035)/.044)**2)
        chin=exp(-((height+.086)/.030)**2)
        bridge=exp(-(x/.025)**2-((height+.036)/.038)**2)
        facing=max(0.,min(1.,(-y-.073)/.065))
        sculpted.append((x*(1.+jaw*chin+cheek*cheekbone*facing),y-nose*bridge*facing,height))
    obj=mesh_object('Sculpted cheekbones, nose, eyelids and jaw',sculpted,faces,m['body'],head,True)
    paint=obj.data.color_attributes.new(name='Artist pigment',type='FLOAT_COLOR',domain='CORNER')
    base=Vector(m['body'].diffuse_color[:3])
    blush=Vector(m['blush'].diffuse_color[:3])
    for loop in obj.data.loops:
        i=loop.vertex_index
        x,y,z=sculpted[i]
        front=max(0.,min(1.,(-y-.070)/.068))
        cheekbone=exp(-((abs(x)-.049)/.027)**2-((z+.028)/.032)**2)
        shadow=exp(-((abs(x)-.059)/.035)**2-((z+.067)/.030)**2)
        hue=base.lerp(blush,.29*cheekbone*front+(.46 if i in lips else 0))
        hue*=1.+.12*cheekbone*front-.15*shadow*front
        paint.data[loop.index].color=(*hue,1.)
    p=Portrait(head,donor,joints,obj.data)
    decimate=obj.modifiers.new('Preserve the facial planes at roster scale','DECIMATE')
    decimate.ratio=.37
    eyes(p,{**m,'white':m['sclera']})
    if with_beard:
        beard(p,{**m,'beard':m['hair'],'hair warmth':m['hair edge'],'grey hair':material('Tempered grey beard','777067')})
