"""Hand-painted colour and tangent-space relief on the same game-ready UV atlas."""
from math import cos, radians, sin, sqrt, tau
from random import Random

import bpy
import numpy as np
from mathutils import Vector
from mathutils.noise import noise_vector


TILES = (
    (),
    ('linen', 'linen light', 'linen shadow', 'weft'),
    ('bronze', 'brass', 'gold dark'),
    ('hide', 'hide edge', 'hide dark'),
    ('teal', 'teal light', 'teal lining', 'red', 'red fold', 'red lining', 'hem red', 'hem blue'),
    ('paint blue', 'paint red', 'verdigris', 'scuffed turquoise', 'faded madder', 'screened oxblood'),
    ('iron', 'dark iron', 'iron edge'),
    ('wood', 'ash'),
)
SURFACES = {name: tile for tile, family in enumerate(TILES) for name in family}
ATLAS_COLUMNS = 4
ATLAS_ROWS = 2

# Base pigment, scumble shadow and dry highlight. Each surface has a different stroke direction.
BRUSH_RECIPES = (
    None,
    ((.95,.92,.84),(.69,.61,.48),(1.,.99,.95),64,.19,.026),        # Linen
    ((.93,.88,.79),(.48,.64,.58),(1.,.97,.84),36,.108,.043),      # Bronze
    ((.92,.86,.82),(.63,.54,.53),(.99,.95,.85),79,.097,.033),     # Hide
    ((.91,.94,.87),(.62,.69,.73),(.99,1.,.92),68,.235,.045),      # Wool
    ((.88,.92,.87),(.54,.63,.64),(.98,1.,.91),53,.211,.039),      # Painted shields
    ((.89,.94,.96),(.58,.66,.71),(.97,.99,1.),12,.133,.022),      # Iron and steel
    ((.89,.84,.77),(.58,.56,.50),(.99,.93,.81),86,.235,.019),     # Ash and timber
)


def add_detail_uv(mesh,normals,surfaces,projections):
    layer=mesh.uv_layers.new(name='Surface grain')
    for face,n,tile,(centre,scale) in zip(mesh.polygons,normals,surfaces,projections):
        dominant=max(range(3),key=lambda axis:abs(n[axis]))
        horizontal,vertical=((1,2),(0,2),(0,1))[dominant]
        tx,ty=tile%ATLAS_COLUMNS,tile//ATLAS_COLUMNS
        for loop,index in zip(face.loop_indices,face.vertices):
            local=mesh.vertices[index].co
            if tile in (2,6) or (tile==4 and scale>2.):
                u=.5+scale*(local[horizontal]-centre[horizontal])
                v=.5+scale*(local[vertical]-centre[vertical])
            else:
                u=.5+.45*local[horizontal]
                v=.075+.398*local[vertical] if vertical==2 else .5+.43*local[vertical]
            # A margin in each tile protects against interpolation across neighbouring materials.
            layer.data[loop].uv=((tx+max(.016,min(.984,u)))/ATLAS_COLUMNS,
                                (ty+max(.016,min(.984,v)))/ATLAS_ROWS)
    return layer


def detail_image():
    side=96
    image=bpy.data.images.new('Woven wool, beaten metal and leather micro relief',
                              width=side*ATLAS_COLUMNS,height=side*ATLAS_ROWS,alpha=False)
    image.colorspace_settings.name='Non-Color'
    phases=[tau*i/side for i in range(side)]
    pixels=[]
    for row in range(ATLAS_ROWS):
        for y in phases:
            for column in range(ATLAS_COLUMNS):
                tile=row*ATLAS_COLUMNS+column
                for x in phases:
                    if tile in (1,4):
                        nx=.075*cos(x*28+.24*sin(y*23))*(.67+.33*sin(y*26))
                        ny=.072*cos(y*31+.27*sin(x*28))*(.68+.31*sin(x*25))
                    elif tile in (2,6):
                        noise=noise_vector(Vector((2.75*x,2.35*y,.7)))
                        scrape=max(0.,cos(3*x+74*y+.62*sin(x*14)))**18
                        nx=.10*noise.x+.038*scrape*sin(13*x)
                        ny=.11*noise.y+.069*scrape*sin(x*24+y*9)
                    elif tile in (3,5,7):
                        noise=noise_vector(Vector((4.25*x,3.97*y,1.4)))
                        nx,ny=.103*noise.x,.114*noise.y
                    else:
                        nx,ny=0.,0.
                    pixels.extend((.50+nx/2,.50+ny/2,.50+sqrt(1.-nx*nx-ny*ny)/2,1.))
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def painted_image():
    """Lay down discrete brush marks with dry edges and bristle ridges."""
    side=256
    width,height=side*ATLAS_COLUMNS,side*ATLAS_ROWS
    atlas=np.ones((height,width,4),dtype=np.float32)
    v,u=np.mgrid[0:side,0:side]/(side-1)
    for tile,recipe in enumerate(BRUSH_RECIPES):
        if recipe is None:
            continue
        ground,dark,light,direction,length,breadth=recipe
        rng=Random(79+tile)
        pigment=np.empty((side,side,3),dtype=np.float32)
        pigment[:]=ground
        for i in range(105):
            x0,y0=rng.uniform(-.06,1.06),rng.uniform(-.06,1.06)
            angle=radians(direction+rng.uniform(-25.,24.))
            long=length*rng.uniform(.38,1.47)
            wide=breadth*rng.uniform(.30,1.48)
            along=((u-x0)*cos(angle)+(v-y0)*sin(angle))/long
            across=((v-y0)*cos(angle)-(u-x0)*sin(angle))/wide
            fringe=.10*np.sin(13*along+3*across+rng.uniform(0.,tau))
            shape=1.-(np.abs(along)**2.8+np.abs(across-fringe)**1.52)
            bristles=.76+.24*np.sin(41*across+2.7*np.sin(4.2*along+1.7*i))
            opacity=rng.uniform(.22,.68)*np.clip(shape*4.4,0.,1.)*bristles
            colour=np.asarray(light if i%5 in (0,1) else dark)
            pigment+=(colour-pigment)*opacity[:,:,None]
        x,y=side*(tile%ATLAS_COLUMNS),side*(tile//ATLAS_COLUMNS)
        atlas[y:y+side,x:x+side,:3]=pigment
    image=bpy.data.images.new('Scumble, bristle marks and worn pigment',width=width,height=height,alpha=False)
    image.pixels.foreach_set(atlas.ravel())
    image.pack()
    return image


def apply_detail(mat,uv):
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    coords=nodes.new('ShaderNodeUVMap')
    coords.uv_map=uv.name
    texture=nodes.new('ShaderNodeTexImage')
    texture.image=detail_image()
    texture.extension='EXTEND'
    normal=nodes.new('ShaderNodeNormalMap')
    normal.uv_map=uv.name
    normal.inputs['Strength'].default_value=.46
    links.new(coords.outputs['UV'],texture.inputs['Vector'])
    links.new(texture.outputs['Color'],normal.inputs['Color'])
    shader=nodes['Principled BSDF']
    links.new(normal.outputs['Normal'],shader.inputs['Normal'])

    painted=nodes.new('ShaderNodeTexImage')
    painted.image=painted_image()
    painted.extension='EXTEND'
    links.new(coords.outputs['UV'],painted.inputs['Vector'])
    multiply=nodes.new('ShaderNodeMix')
    multiply.data_type='RGBA'
    multiply.blend_type='MULTIPLY'
    multiply.inputs[0].default_value=1.
    base=shader.inputs['Base Color']
    links.new(base.links[0].from_socket,multiply.inputs[6])
    links.new(painted.outputs['Color'],multiply.inputs[7])
    links.new(multiply.outputs[2],base)
