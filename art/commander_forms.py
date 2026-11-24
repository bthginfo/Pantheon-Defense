"""Lofted fabrics, rolled metal edges and bas-relief shapes for Thekla and Marcus."""
from math import cos, sin, tau

from mathutils import Vector

from forge import material
from geometry import mesh_object, volume


FINISHES = {
    'bronze': ('9d7044', .76, .41, .31), 'brass': ('c79956', .76, .34, .26),
    'gold dark': ('8b5e39', .70, .39, .14), 'iron': ('494749', .61, .39, .25),
    'iron edge': ('75716f', .66, .31, .14), 'dark iron': ('353335', .66, .44, .24),
    'linen': ('cab797', 0, .81, .11), 'linen light': ('e1cba6', 0, .77, .09),
    'linen shadow': ('a38b6c', 0, .82, .13), 'weft': ('ddbc8c', 0, .78, .11),
    'teal': ('20404a', 0, .84, .24), 'teal light': ('30515a', 0, .82, .21),
    'teal lining': ('202d34', 0, .86, .22), 'paint blue': ('24434b', .13, .63, .37),
    'red': ('682d2c', 0, .84, .25), 'red fold': ('82403b', 0, .83, .23),
    'red lining': ('432629', 0, .85, .20), 'paint red': ('713029', .10, .59, .38),
    'hem red': ('a25b45', 0, .74, .18), 'hem blue': ('31464c', 0, .72, .15),
    'hide': ('5b3d30', 0, .73, .19), 'hide edge': ('8c654b', 0, .68, .15),
    'hide dark': ('382c28', 0, .75, .16), 'wood': ('6a4d33', 0, .68, .19),
    'hair': ('2b2423', 0, .60, .17), 'hair warmth': ('47372e', 0, .63, .16),
    'grey hair': ('675c55', 0, .66, .19), 'beard': ('42362f', 0, .66, .20),
    'lip': ('965449', 0, .66, .05), 'flush': ('bd7056', 0, .71, .10),
    'white': ('dfd3ba', 0, .31, .03), 'iris': ('674a34', 0, .34, .04),
    'pupil': ('231b1a', 0, .25, 0), 'skin thekla': ('ab7552', 0, .64, .11),
    'skin marcus': ('9f6b4b', 0, .65, .14),
}


def paints():
    result={}
    for key,(rgb,metal,rough,variation) in FINISHES.items():
        shade=material(key,rgb,metal)
        shade.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=rough
        shade['Surface variation']=variation
        if metal>.18:
            shade['Micro relief']=2
        elif key.startswith(('hide','wood','paint ')):
            shade['Micro relief']=3
        elif key.startswith(('linen','teal','red','hem','weft')):
            shade['Micro relief']=1
        result[key]=shade
    return result


def strips(name, parent, columns, rows, sample, pigments, assign=None, lining=.0, smooth=True):
    """Sample a cloth pattern or a sheet of raised metal with real drape at each grid point."""
    verts=[sample(s,t) for t in rows for s in columns]
    width=len(columns)
    faces=[(a,a+1,a+width+1,a+width) for row in range(len(rows)-1)
           for column in range(width-1) for a in (row*width+column,)]
    obj=mesh_object(name,verts,faces,None,parent,smooth)
    for pigment in pigments:
        obj.data.materials.append(pigment)
    if assign:
        for face in obj.data.polygons:
            row,column=divmod(face.index,width-1)
            face.material_index=assign((columns[column]+columns[column+1])/2,(rows[row]+rows[row+1])/2)
    if lining:
        shell=obj.modifiers.new('Thickness at cut edge','SOLIDIFY')
        shell.thickness=lining
        if len(pigments)>2:
            shell.material_offset_rim=len(pigments)-1
    return obj


def tube(name,parent,path,sections,pigment,sides=7,across=(1.,0.,0.),smooth=True):
    """Extrude oval cross-sections along a sculpted path. Each section has width and depth."""
    points=[Vector(p) for p in path]
    direction=Vector(across)
    rings=[]
    for i,(point,(width,depth)) in enumerate(zip(points,sections)):
        tangent=(points[min(len(points)-1,i+1)]-points[max(0,i-1)]).normalized()
        right=direction-tangent*direction.dot(tangent)
        if right.length_squared<.001:
            right=tangent.orthogonal()
        right.normalize()
        outward=tangent.cross(right).normalized()
        rings.append([tuple(point+right*(width*cos(a))+outward*(depth*sin(a)))
                      for a in (tau*k/sides for k in range(sides))])
    return volume(name,rings,pigment,parent,smooth)


def piping(name,parent,path,radius,pigment,sides=6):
    return tube(name,parent,path,[(radius,radius)]*len(path),pigment,sides,across=(.38,.73,.26))


def relief(name,parent,outline,place,front,rim=None,thickness=.004,bevel=.06):
    """A shaped badge, with a bevel formed against an arbitrary curved surface."""
    count=len(outline)
    center=Vector(tuple(sum(p[i] for p in outline)/count for i in (0,1)))
    pts=[place(*(center.lerp(Vector(p),scale)),depth) for scale,depth in ((1.,0.),(1.,thickness*.4),(1.-bevel,thickness))
         for p in outline]
    faces=[tuple(range(count-1,-1,-1))]
    for row in (0,1):
        lower,upper=row*count,(row+1)*count
        for i in range(count):
            j=(i+1)%count
            faces.append((lower+i,lower+j,upper+j,upper+i))
    faces.append(tuple(range(2*count,3*count)))
    obj=mesh_object(name,pts,faces,front,parent)
    if rim:
        obj.data.materials.append(rim)
        for face in list(obj.data.polygons)[1:-1]:
            face.material_index=1
    return obj


def stitched(name,parent,path,width,thread,count):
    points=[Vector(p) for p in path]
    total=sum((b-a).length for a,b in zip(points,points[1:]))
    distance=0.
    edge=0
    pts,faces=[],[]
    for i in range(1,count+1):
        marker=i*total/(count+1)
        while edge+1<len(points)-1 and marker>distance+(points[edge+1]-points[edge]).length:
            distance+=(points[edge+1]-points[edge]).length
            edge+=1
        tangent=(points[edge+1]-points[edge]).normalized()
        point=points[edge]+tangent*(marker-distance)
        across=tangent.cross(Vector((0,1,0))).normalized()
        if across.length_squared<.01:
            across=tangent.cross(Vector((0,0,1))).normalized()
        base=len(pts)
        pts.extend(tuple(point+tangent*(u*width)+across*(v*width)) for u,v in ((-1,.46),(.60,.96),(1,-.24),(-.58,-.81)))
        faces.append(tuple(range(base,base+4)))
    return mesh_object(name,pts,faces,thread,parent)


def angle_span(start,end,steps):
    return [start+(end-start)*index/steps for index in range(steps+1)]
