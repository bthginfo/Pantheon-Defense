"""Posed anatomy and portrait sculpture shared by the two commander assets."""
from collections import defaultdict
from gzip import open as gzip_open
from json import load
from math import cos, sin
from pathlib import Path

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from forge import empty
from geometry import mesh_object

class Anatomy:
    def __init__(self, name):
        with gzip_open(Path(__file__).with_name('reference-data')/f'{name}-anatomy.json.gz','rt') as source:
            self.data = load(source)
        self.name = name
        self.guides = {name:Vector(point) for name,point in self.data['joints'].items()}
        self.old = {name:Vector(point) for name,point in self.guides.items()}
        self.pivots = {'Figure':Vector((0,0,0)), 'Body':self.guides['pelvis'],
                       'Head':self.guides['neck'], 'Mantle':self.guides['spine-1']+Vector((0,.095,.103))}
        self.root = empty('Figure')
        self.bones = {'Figure':self.root}
        self.transforms = {}
        self._bone('Body','Figure')
        self._bone('Head','Body')
        self._bone('Mantle','Body')
        for turn, side, source in ((1, 'Left', 'l'),(-1, 'Right', 'r')):
            self._place_limbs(turn,side,source)

    def _bone(self,name,parent):
        offset=self.pivots[name]-self.pivots[parent]
        self.bones[name]=empty(name,offset,self.bones[parent])

    def _place_limbs(self, turn, side, source):
        shoulder, elbow, wrist = [self.old[f'{source}-{place}'] for place in ('shoulder','elbow','hand')]
        hip, knee, ankle = [self.old[f'{source}-{place}'] for place in ('upper-leg','knee','ankle')]
        if self.name=='thekla':
            if turn>0:
                posed_elbow=shoulder+Vector((.149,-.050,-.230))
                posed_wrist=posed_elbow+Vector((.121,-.155,-.049))
                hand_vector=(.08,-.90,.31)
                width_axis=(-.30,.25,.93)
                curl=.64
            else:
                posed_elbow=shoulder+Vector((-.155,-.023,-.214))
                posed_wrist=posed_elbow+Vector((-.126,-.153,.139))
                hand_vector=(-.13,-.94,.09)
                width_axis=(-.09,.03,.99)
                curl=.94
            posed_knee=Vector((.104,-.060,.478) if turn>0 else (-.139,.052,.466))
            posed_ankle=Vector((.144,-.101,ankle.z) if turn>0 else (-.206,.103,ankle.z))
        else:
            if turn>0:
                posed_elbow=shoulder+Vector((.150,-.033,-.239))
                posed_wrist=posed_elbow+Vector((.137,-.213,-.096))
                hand_vector=(.21,-.97,-.04)
                width_axis=(-.96,-.22,.14)
                curl=.57
            else:
                posed_elbow=shoulder+Vector((-.122,-.040,-.267))
                posed_wrist=posed_elbow+Vector((-.052,-.040,-.241))
                hand_vector=(-.033,-.30,-.94)
                width_axis=(-.21,-.91,.35)
                curl=.38
            posed_knee=Vector((.145,-.072,.496) if turn>0 else (-.173,.034,.472))
            posed_ankle=Vector((.213,-.143,ankle.z) if turn>0 else (-.259,.076,ankle.z))
        self.guides[f'{source}-elbow']=posed_elbow
        self.guides[f'{source}-hand']=posed_wrist
        self.guides[f'{source}-knee']=posed_knee
        self.guides[f'{source}-ankle']=posed_ankle
        limb_points = {'Arm':shoulder,'Forearm':posed_elbow,'Hand':posed_wrist,
                       'Leg':hip,'Shin':posed_knee,'Foot':posed_ankle}
        self.pivots.update({side+bone:where for bone,where in limb_points.items()})
        for suffix, parent in (('Arm','Body'),('Forearm',side+'Arm'),('Hand',side+'Forearm'),
                               ('Leg','Figure'),('Shin',side+'Leg'),('Foot',side+'Shin')):
            self._bone(side+suffix,parent)
        self.transforms[side+'Arm']=segment(shoulder,elbow,shoulder,posed_elbow)
        self.transforms[side+'Forearm']=segment(elbow,wrist,posed_elbow,posed_wrist)
        inward=1. if source=='l' or self.name=='thekla' else -1.
        self.transforms[side+'Hand']=hand_transform(self.old,source,posed_wrist,hand_vector,width_axis,curl,inward)
        self.transforms[side+'Leg']=segment(hip,knee,hip,posed_knee)
        self.transforms[side+'Shin']=segment(knee,ankle,posed_knee,posed_ankle)
        rotation = Matrix.Rotation(.13*turn,3,'Z')
        self.transforms[side+'Foot']=lambda point: posed_ankle+rotation@(point-ankle)
        for marker in ('foot-1','foot-2'):
            self.guides[f'{source}-{marker}']=self.transforms[side+'Foot'](self.old[f'{source}-{marker}'])

    def part(self,name):
        return self.bones[name]

    def joint(self,name):
        return self.guides[name]

    def hand_point(self,side,in_front=.042):
        abbreviation = 'l' if side=='Left' else 'r'
        source=self.old[f'{abbreviation}-hand']
        pointing=(self.old[f'{abbreviation}-finger-3-1']-source).normalized()
        return self.transforms[side+'Hand'](source+pointing*in_front)

    def sculpt(self,skin,lip,flush,stubble):
        positions=[]
        for raw,groups in zip(self.data['positions'],self.data['weights']):
            point=Vector(raw)
            if not groups:
                positions.append(point)
                continue
            posed=Vector((0,0,0))
            for name,weight in groups:
                transform=self.transforms.get(name)
                posed+=(transform(point) if transform else point)*weight
            positions.append(posed/sum(weight for _,weight in groups))
        self.hands={side:[point for point,groups in zip(positions,self.data['weights'])
                         if any(group==side+'Hand' and strength>.55 for group,strength in groups)]
                    for side in ('Left','Right')}
        mesh=mesh_object('Posed skin with sculpted eyelids, fingers and knees',positions,
                         self.data['faces'],skin,self.part('Figure'),smooth=True)
        groups=defaultdict(list)
        for i,weights in enumerate(self.data['weights']):
            for name,amount in weights:
                groups[name,amount].append(i)
        bone_groups={name:mesh.vertex_groups.new(name=name) for name in dict.fromkeys(name for name,_ in groups)}
        for (name,value),indices in groups.items():
            bone_groups[name].add(indices,value,'REPLACE')
        self._paint_skin(mesh,skin,lip,flush,stubble)
        simplified=mesh.modifiers.new('Preserve the visible anatomy with fewer game triangles','DECIMATE')
        simplified.ratio=.76
        triangles=[face for face in self.data['faces'] if all(positions[i].z > self.joint('neck').z-.012 for i in face)]
        self.portrait=BVHTree.FromPolygons(positions,triangles)
        return mesh

    def _paint_skin(self,mesh,skin,lip,flush,stubble):
        colors=mesh.data.color_attributes.new(name='Artist pigment',type='FLOAT_COLOR',domain='CORNER')
        mouth=set(self.data['lip_vertices'])
        eyes=self.joint('l-eye')
        head=self.joint('head')
        for face in mesh.data.polygons:
            for loop,index in zip(face.loop_indices,face.vertices):
                x,y,z=self.data['positions'][index]
                hue=Vector(skin.diffuse_color[:3])
                if z>head.z-.09 and abs(x)<.102 and y<-.05:
                    cheek=max(0.,1.-abs(abs(x)-.054)/.04)*max(0.,1.-abs(z-(eyes.z-.033))/.037)
                    hue=hue.lerp(Vector(flush.diffuse_color[:3]),.31*cheek)
                    if index in mouth:
                        hue=hue.lerp(Vector(lip.diffuse_color[:3]),.60 if self.name=='thekla' else .52)
                    if self.name=='marcus' and abs(x)<.089:
                        line=eyes.z-.094+.098*(abs(x)/.086)**2.05
                        tint=.36*max(0.,1.-abs(z-line)/.018)
                        hue=hue.lerp(Vector(stubble.diffuse_color[:3]),tint)
                colors.data[loop].color=(*hue,1.)

    def face_depth(self,x,z):
        hit,_,_,_=self.portrait.ray_cast(Vector((x,-.62,z)),Vector((0,1,0)),.84)
        return None if hit is None else hit.y

    def bind(self):
        # Components are sculpted in common coordinates while the armature pivots sit at the joints.
        for obj in self.root.children_recursive:
            if obj.type=='MESH':
                obj.location-=self.pivots[obj.parent.name]
        return self.root


def segment(start,end,placed_start,placed_end):
    before,after=end-start,placed_end-placed_start
    rotate=before.rotation_difference(after)
    axis=before.normalized()
    stretch=after.length/before.length-1
    def apply(point):
        distance=point-start
        return placed_start+rotate@(distance+axis*(distance.dot(axis)*stretch))
    return apply


def hand_transform(joints,side,goal,direction,width,curl,inward):
    wrist=joints[side+'-hand']
    knuckles=joints[side+'-finger-3-1']
    toward=(knuckles-wrist).normalized()
    span=joints[side+'-finger-2-1']-joints[side+'-finger-5-1']
    across=(span-toward*span.dot(toward)).normalized()
    depth=toward.cross(across).normalized()
    end=Vector(direction).normalized()
    thickness=Vector(width)
    radial=(thickness-end*thickness.dot(end)).normalized()
    normal=end.cross(radial).normalized()
    pivot=(knuckles-wrist).length*.91
    def apply(point):
        delta=point-wrist
        length,wide,deep=delta.dot(toward),delta.dot(across),delta.dot(depth)
        if length>pivot:
            tip=length-pivot
            curvature=curl*(40. if curl>.86 else 25.5)
            angle=tip*curvature
            length=pivot+sin(angle)/curvature
            deep+=inward*(1.-cos(angle))/curvature
        return goal+end*length+radial*wide+normal*deep
    return apply
