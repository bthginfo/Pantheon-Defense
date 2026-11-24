"""A shared tangent-space texture gives the exported heroes their woven and tooled surfaces."""
from math import cos, sin, sqrt, tau

import bpy
from mathutils import Vector
from mathutils.noise import noise_vector


def add_detail_uv(mesh,normals,surfaces):
    layer=mesh.uv_layers.new(name='Surface grain')
    for face,n,tile in zip(mesh.polygons,normals,surfaces):
        dominant=max(range(3),key=lambda axis:abs(n[axis]))
        horizontal,vertical=((1,2),(0,2),(0,1))[dominant]
        for loop,index in zip(face.loop_indices,face.vertices):
            local=mesh.vertices[index].co
            u=.5+.45*local[horizontal]
            v=.075+.398*local[vertical] if vertical==2 else .5+.43*local[vertical]
            # A margin in each tile protects against interpolation across neighbouring materials.
            layer.data[loop].uv=((tile+max(.016,min(.984,u)))/4,max(.016,min(.984,v)))
    return layer


def detail_image():
    side=144
    image=bpy.data.images.new('Woven wool, beaten metal and leather micro relief',width=side*4,height=side,alpha=False)
    image.colorspace_settings.name='Non-Color'
    phases=[tau*i/side for i in range(side)]
    pixels=[]
    for y in phases:
        for tile in range(4):
            for x in phases:
                if tile==1:
                    nx=.092*cos(x*28+.24*sin(y*23))*(.67+.33*sin(y*26))
                    ny=.081*cos(y*31+.27*sin(x*28))*(.68+.31*sin(x*25))
                elif tile==2:
                    noise=noise_vector(Vector((2.75*x,2.35*y,.7)))
                    scrape=max(0.,cos(3*x+74*y+.62*sin(x*14)))**18
                    nx=.12*noise.x+.038*scrape*sin(13*x)
                    ny=.13*noise.y+.079*scrape*sin(x*24+y*9)
                elif tile==3:
                    noise=noise_vector(Vector((4.25*x,3.97*y,1.4)))
                    nx,ny=.127*noise.x,.134*noise.y
                else:
                    nx,ny=0.,0.
                pixels.extend((.50+nx/2,.50+ny/2,.50+sqrt(1.-nx*nx-ny*ny)/2,1.))
    image.pixels.foreach_set(pixels)
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
    links.new(normal.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
