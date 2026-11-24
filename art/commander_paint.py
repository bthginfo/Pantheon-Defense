"""Bake the commanders' illustrated tones into the same vertex colours Bevy uses."""
from math import sin

from mathutils import Vector
from mathutils.noise import noise_vector

from forge import rgba
from geometry import mesh_object

# Shadow and glaze pigments are chosen independently from the middle coat.
PIGMENTS = {
    'bronze': ('5c3947', 'f0c184', .73),
    'brass': ('83513f', 'ffdfa0', .60),
    'gold dark': ('473342', 'c68b55', .51),
    'iron': ('212437', '758997', .76),
    'iron edge': ('353e53', 'a4b1b7', .70),
    'dark iron': ('1f2231', '63768a', .64),
    'linen': ('897065', 'f6e3b3', .72),
    'linen light': ('b69874', 'fff0cc', .58),
    'linen shadow': ('745b59', 'd5c09a', .61),
    'weft': ('9b7758', 'f1d29a', .49),
    'teal': ('132a3a', '5b9b8d', .84),
    'teal light': ('234459', '7da992', .70),
    'teal lining': ('142333', '4c767d', .62),
    'red': ('352238', 'a15347', .78),
    'red fold': ('502737', 'b56551', .69),
    'red lining': ('312235', 'ac695a', .62),
    'hem red': ('684044', 'd49068', .63),
    'hide': ('372932', 'b68466', .51),
    'hide edge': ('563a38', 'd6ab78', .47),
    'hide dark': ('272631', '85624a', .52),
    'wood': ('392a31', '9f7852', .52),
    'ash': ('242837', '88674f', .56),
}
PROFILES = {name: (rgba(shadow), rgba(glaze), strength)
            for name, (shadow, glaze, strength) in PIGMENTS.items()}
BRUSH_LIGHT = Vector((-.46, -.32, .81)).normalized()


def brush_colour(profile, colour, point, normal):
    """Put opaque glaze on ridges and coloured wash in the folds, in bind coordinates."""
    shadow,glaze,strength=profile
    x,y,z=point
    stroke=noise_vector(Vector((15.2*x+5.1*z,12.3*y,19.7*z)))[0]
    dry_brush=noise_vector(Vector((29.1*x-3.6*z,30.6*y,64.*z)))[1]
    light=.42+.41*normal.dot(BRUSH_LIGHT)+.23*stroke+.043*dry_brush
    cool=min(.64,max(0.,(.65-light)*1.10))*strength
    warm=min(.56,max(0.,(light-.47)*1.25))*strength
    grain=1.+.057*dry_brush+.055*stroke
    return tuple(grain*(base*(1-cool-warm)+dark*cool+bright*warm)
                 for base,dark,bright in zip(colour[:3],shadow[:3],glaze[:3]))


def paint_losses(name, parent, place, marks, pigments):
    """Place asymmetric patches of thin paint along the exposed shield surface."""
    vertices,faces=[],[]
    for x,z,width,depth,slope in marks:
        start=len(vertices)
        outline=((-1.,.13),(-.54,.74),(.19,.58),(.97,.02),(.41,-.29),(-.24,-.56))
        vertices.extend(place(x+u*width,z+v*depth+u*width*slope,.0042) for u,v in outline)
        faces.append(tuple(range(start,start+len(outline))))
    mesh=mesh_object(name,vertices,faces,pigments[0],parent)
    mesh.data.materials.append(pigments[1])
    for face in mesh.data.polygons:
        face.material_index=int(face.index%3==0)


def shield_wash(obj, centre, inverse, width, height, greek):
    """Glaze each shield in its own space, so the paint turns with the arm."""
    paint='paint blue' if greek else 'paint red'
    shadow, glaze=map(rgba,('172e32','5d876c') if greek else ('422230','b1654a'))
    attr=obj.data.color_attributes.new(name='Artist pigment',type='FLOAT_COLOR',domain='CORNER')
    for face in obj.data.polygons:
        finish=obj.data.materials[face.material_index]
        colour=finish.diffuse_color
        for loop,index in zip(face.loop_indices,face.vertices):
            if finish.name!=paint:
                attr.data[loop].color=colour
                continue
            x,_,z=inverse@(obj.data.vertices[index].co-centre)
            u,v=x/width,z/height
            stroke=noise_vector(Vector((3.3*u+2.6*v,4.6*v+1.13*u,1.7)))[0]
            bristle=noise_vector(Vector((9.1*u-5.2*v,17.1*v,3.4)))[1]
            uneven=.44+.35*v-.20*u+.18*stroke
            dark=min(.73,max(0.,(.53-uneven)*1.44))
            lift=min(.60,max(0.,(uneven-.38)*1.19))
            ridge=1+.062*bristle
            attr.data[loop].color=(*(ridge*(base*(1-dark-lift)+low*dark+high*lift)
                                    for base,low,high in zip(colour[:3],shadow[:3],glaze[:3])),1.)


def mantle_stamp(obj, columns, rows, greek):
    """Follow the actual cloth ridges with soft pigment bands."""
    shades=('36746c','70a899') if greek else ('8f3b3d','b55e4e')
    deep,bright=map(rgba,shades)
    attr=obj.data.color_attributes.new(name='Artist pigment',type='FLOAT_COLOR',domain='CORNER')
    for face in obj.data.polygons:
        base=obj.data.materials[face.material_index].diffuse_color
        for loop,index in zip(face.loop_indices,face.vertices):
            row,column=divmod(index,len(columns))
            u,t=columns[column],rows[row]
            amount=0.
            wash=deep
            if face.material_index==0:
                crest=.5+.5*sin(3.6+19.2*u+1.3*t)
                ripple=.5+.5*sin(4.2+35.0*u+3.1*t)
                bound=max(0.,1.-abs(t-.53-.095*sin(9*u))/.44)
                amount=.26*bound*crest+.08*ripple*bound
                peak=max(0.,(crest-.52)*1.9)*max(0.,.89-u)
                wash=tuple(a+(b-a)*peak for a,b in zip(deep,bright))
            attr.data[loop].color=(*(base[i]*(1-amount)+wash[i]*amount for i in range(3)),1.)
