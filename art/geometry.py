"""Small mesh construction, lighting, and baking utilities for the Blender sources."""
from math import cos, pi, sin, tau

import bpy
from mathutils import Vector

from forge import attach, look_at, material, rgba


def mesh_object(name, points, faces, pigment, parent, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    attach(obj, name, pigment, parent)
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    return obj


def volume(name, rings, pigment, parent, smooth=False):
    size = len(rings[0])
    faces = [tuple(reversed(range(size)))]
    for index in range(len(rings) - 1):
        a, b = index * size, (index + 1) * size
        for i in range(size):
            j = (i + 1) % size
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple(range((len(rings) - 1) * size, len(rings) * size)))
    return mesh_object(name, [p for ring in rings for p in ring], faces, pigment, parent, smooth)


def rectangle(width, length, corner):
    x, y = width / 2, length / 2
    c = min(corner, x * .48, y * .48)
    return [
        (-x + c, -y), (x - c, -y), (x, -y + c), (x, y - c),
        (x - c, y), (-x + c, y), (-x, y - c), (-x, -y + c),
    ]


def bevel_block(name, center, size, pigment, parent, bevel=.036, angle=0):
    width, length, height = size
    b = min(bevel, height * .29, width * .18, length * .18)
    layers = [
        (-height / 2, width - 2*b, length - 2*b),
        (-height / 2 + b, width, length),
        (height / 2 - b, width, length),
        (height / 2, width - 2*b, length - 2*b),
    ]
    rings = [[(x, y, z) for x, y in rectangle(w, d, b * 1.1)] for z, w, d in layers]
    obj = volume(name, rings, pigment, parent)
    obj.location = center
    obj.rotation_euler.z = angle
    return obj


def shell(name, profile, pigment, parent, sides=12, smooth=False, rotation=0):
    """Each height in the profile supplies two radii and a horizontal offset."""
    rings = [
        [(x + rx * cos(rotation + tau * i / sides),
          y + ry * sin(rotation + tau * i / sides), z) for i in range(sides)]
        for z, rx, ry, x, y in profile
    ]
    return volume(name, rings, pigment, parent, smooth)


def silhouette(name, outline, thickness, pigment, parent):
    """Extrude a counterclockwise outline in the XZ plane toward the viewer."""
    if sum(x1*z2-x2*z1 for (x1,z1),(x2,z2) in zip(outline,outline[1:]+outline[:1])) < 0:
        outline = outline[::-1]
    count = len(outline)
    vertices = [(x, y, z) for y in (-thickness / 2, thickness / 2) for x, z in outline]
    faces = [tuple(range(count)), tuple(reversed(range(count, 2*count)))]
    for i in range(count):
        j = (i+1) % count
        faces.append((j,i,count+i,count+j))
    return mesh_object(name, vertices, faces, pigment, parent)


def torus_mesh(name, origin, major, tube, pigment, parent, steps=20, sides=6, facing=False):
    points = []
    for i in range(steps):
        angle = tau * i / steps
        for j in range(sides):
            phase = tau * j / sides
            radius = major + tube * cos(phase)
            offset = (radius * cos(angle), radius * sin(angle), tube * sin(phase))
            if facing:
                offset = (offset[0], -offset[2], offset[1])
            points.append(tuple(a + b for a, b in zip(origin, offset)))
    faces = [
        (i*sides+j, ((i+1)%steps)*sides+j, ((i+1)%steps)*sides+(j+1)%sides, i*sides+(j+1)%sides)
        for i in range(steps) for j in range(sides)
    ]
    # The major path follows the rim and the smaller cross-section follows the tube.
    return mesh_object(name, points, faces, pigment, parent, smooth=True)


def pigment_family(name, colors, metallic=0):
    return [material(f"{name} {index+1}", color, metallic) for index,color in enumerate(colors)]


def color_material(name, attribute="Pigment", unlit=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (1,1,1,1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    vertex = nodes.new("ShaderNodeVertexColor")
    vertex.layer_name = attribute
    color = vertex.outputs["Color"]
    if unlit:
        emission=nodes.new("ShaderNodeEmission")
        camera_only=nodes.new("ShaderNodeLightPath")
        mix=nodes.new("ShaderNodeMixShader")
        links.new(color, emission.inputs["Color"])
        links.new(camera_only.outputs["Is Camera Ray"],mix.inputs[0])
        links.new(emission.outputs[0],mix.inputs[1])
        links.new(emission.outputs[0],mix.inputs[2])
        links.new(mix.outputs[0],nodes.get("Material Output").inputs["Surface"])
    else:
        primary=nodes.get("Principled BSDF")
        primary.inputs["Roughness"].default_value=.68
        primary.inputs["Metallic"].default_value=.035
        links.new(color,primary.inputs["Base Color"])
    return mat


def studio(camera_location, target, width, height, scale, samples=12, transparent=False):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=width
    scene.render.resolution_y=height
    scene.render.resolution_percentage=100
    scene.render.film_transparent=transparent
    scene.eevee.taa_render_samples=samples
    scene.world=bpy.data.worlds.new("Cool diffuse sky")
    scene.world.use_nodes=True
    world=scene.world.node_tree.nodes.get("Background")
    world.inputs["Color"].default_value=(*rgba("8196a6")[:3],1)
    world.inputs["Strength"].default_value=.36
    scene.view_settings.view_transform="AgX"
    scene.view_settings.look="AgX - Medium High Contrast"
    bpy.ops.object.camera_add(location=camera_location)
    camera=bpy.context.object
    camera.name="Art review camera"
    camera.data.type="ORTHO"
    camera.data.ortho_scale=scale
    look_at(camera,target)
    scene.camera=camera
    for name, location, power, size, color in [
        ("Sunlit key", (-3.8,-4.4,6.2), 585, 4.2, (1,.82,.63)),
        ("Sky fill", (3.9,-1.2,4.1), 355, 5.0, (.62,.81,1)),
        ("Warm edge", (2.0,4.3,4.1), 690, 3.4, (1,.69,.49)),
    ]:
        light=bpy.data.lights.new(name,"AREA")
        light.energy=power
        light.size=size
        light.color=color
        obj=bpy.data.objects.new(name,light)
        scene.collection.objects.link(obj)
        obj.location=location
        look_at(obj,target)
    return scene, camera
