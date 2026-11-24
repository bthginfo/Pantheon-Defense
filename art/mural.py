"""Render the three landscape panels used by the game lobby."""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import ASSETS, box, clean, empty, look_at, material, palette, prism, sheet, span, stone

SCENES = ASSETS / "scenes"
SCENES.mkdir(exist_ok=True)

COLORS = {
    "aegean": ("4f8a91", "4c7979", "abc493", "e1c098", "557f7b", "4e919c", "dd995f"),
    "rome": ("8c8a77", "636c63", "a8ad70", "d4ad8e", "a05d51", "755348", "ee9a63"),
    "japan": ("628d8b", "506d75", "9cb58e", "bec2a7", "436479", "a65f59", "e7ab86"),
}

def island(root, mats, x, y, r, scale):
    land, rock, grass = mats
    for i in range(3):
        z = -.75 + i * .29 * scale
        base = prism("Layered limestone island", (x,y,z), r*(1-i*.065), .54*scale, (rock,land,grass)[i], root, 11, r*(.95-i*.065))
        base.scale.y = .57 + i * .025
        base.rotation_euler.z = -.26
    for i in range(25):
        a = i*2.399
        angle = math.cos(i*1.77) * .32
        position = (x + r*(.82 + angle)*math.sin(a),y + r*(.47+angle*.24)*math.cos(a),-.58)
        s = .29 + math.sin(i*.87)**2 * .58
        stone("Shore boulder", position, (s,.63*s,.84*s), rock if i%4 else land, root)

def tree(root, x, y, z, h, faction, dark, light, wood):
    span("Trunk", (x,y,z),(x+.08,y,z+.67*h),.062*h,wood,root)
    if faction == "aegean":
        for index in range(5):
            angle=index*2.399
            stone("Olive leaf cluster",(x+math.sin(angle)*h*.23,y+math.cos(angle)*h*.23,z+(.73+index*.066)*h),
                  (.34*h,.38*h,.31*h),dark if index%3 else light,root,1)
    else:
        for i in range(3):
            size=h*(.44-i*.11)
            prism("Terraced needles",(x,y,z+(.52+i*.24)*h),size,.55*h,dark if i%2 else light,root,7,.045)

def temple(root, x, y, z, size, faction, m, stone_mat, roof):
    for i in range(3):
        box("Foundation steps",(x,y,z+.11*i),(size*(3.3-i*.31),size*(1.95-i*.22),.18),stone_mat,root)
    if faction == "japan":
        for side in (-1,1):
            span("Vermilion post",(x+size*.89*side,y,z+.23),(x+size*.78*side,y,z+size*1.77),.122*size,m["accent"],root,7)
        for k,w in enumerate((1.8,2.45,2.83)):
            box("Sweeping lintel",(x,y,z+size*(1.34+.25*k)),(size*w,.32*size,.17*size),roof if k>0 else m["accent"],root)
        for side in (-1,1):
            box("Upturned eave",(x+side*size*1.4,y,z+size*1.91),(.45*size,.35*size,.12*size),roof,root,(0,-side*.24,0))
    else:
        for dx in (-1.19,-.59,0,.59,1.19):
            for dy in (-.58,.53):
                span("Doric column",(x+size*dx,y+size*dy,z+.26),(x+size*dx,y+size*dy,z+size*1.43),
                     .126*size,stone_mat,root,9,.087*size)
                box("Entablature plate",(x+size*dx,y+size*dy,z+size*1.43),(.34*size,.33*size,.13*size),m["trim"],root)
        box("Temple architrave",(x,y,z+size*1.54),(3.17*size,1.64*size,.18*size),stone_mat,root)
        sheet("Temple roof", [(x-1.66*size,y-.88*size,z+size*1.65),(x+1.66*size,y-.88*size,z+size*1.65),
            (x-1.50*size,y,z+size*2.11),(x+1.50*size,y,z+size*2.11),
            (x-1.66*size,y+.88*size,z+size*1.65),(x+1.66*size,y+.88*size,z+size*1.65)],
            [(0,1,3,2),(2,3,5,4),(0,2,4),(1,5,3)],roof,root,.055)
        for n in range(12):
            p=x+size*(n/11*3.18-1.59)
            span("Roof batten",(p,y-.89*size,z+size*1.67),(x+(p-x)*.9,y,z+size*2.13),.018*size,m["trim"],root,5)
    for dx in (-1.28,1.28):
        prism("Harbor lantern",(x+dx*size,y-.82*size,z+.35),size*.102,.39,m["trim"],root,6)
        stone("Lamp",(x+dx*size,y-.82*size,z+.59),(.075,.07,.10),m["glow"],root)

def roof_house(root,x,y,z,s,m,roof):
    box("Quay house",(x,y,z+.36*s),(1.00*s,.74*s,.72*s),m["stone"],root)
    box("Deep doorway",(x-.12*s,y-.382*s,z+.247*s),(.22*s,.025,.48*s),m["shade"],root)
    for sign in (-1,1):
        box("Terracotta eave",(x,y+sign*.23*s,z+.78*s),(1.15*s,.50*s,.10*s),roof,root,(sign*.31,0,0))

def render(faction):
    clean()
    root = empty(faction)
    sea, rock, grass, clay, roof, accent, glow = COLORS[faction]
    m = palette(faction,accent)
    m["glow"] = material("Warm brazier",glow,glow=2.7)
    sea_mat = material("Painted sea",sea)
    rock_mat = material("Cliff shade",rock)
    grass_mat = material("Coarse grass",grass)
    clay_mat = material("Sunlit sandstone",clay)
    roof_mat = material("Glazed roof",roof)
    light_leaf = material("Old leaves", "c3b87e" if faction=="rome" else "abb98d")
    dark_leaf = material("Cypress and olive", "547a64" if faction=="aegean" else "4b7160")
    foam = material("Sea foam", "a3c5b5")
    riffle = material("Sea ribbon", "709fa0")
    box("Wide inland sea", (0,0,-1.25),(118,100,.20),sea_mat,root)
    for index,(x,y,r,h) in enumerate([(1.5,2,9.5,1.6),(14.2,5.9,6.6,1.5),(-13.6,6,7.3,1.3),
                                     (2.1,17.7,13,1.8),(20.4,14,6,1.2),(-9,-5,3.2,1.2)]):
        island(root,(clay_mat,rock_mat,grass_mat),x,y,r,h)
    random.seed(41)
    for n in range(125):
        x=random.uniform(-27,29)
        y=random.uniform(-14,25)
        if (((x-1.5)/10)**2+((y-2)/5.5)**2<1.16 or ((x-14)/7)**2+((y-5)/4)**2<1.12):
            continue
        box("Thin painted wave",(x,y,-1.13),(random.uniform(.22,1.24),random.uniform(.028,.074),.017),
            foam if n%7==0 else riffle,root,(0,0,.075*math.sin(n)))
    for index, (x,y,s) in enumerate([(4.2,2.7,1.68),(12.1,6.1,1.18),(-12,5.35,.82),(.2,15.7,.92)]):
        temple(root,x,y,.13,s,faction,m,clay_mat,roof_mat)
        for n in range(5):
            box("Quay flagstone",(x+(n-2)*.68,y-2.0*s,.12),(.62,.61,.105),clay_mat,root)
    for n,(x,y,s) in enumerate([(0.9,1.1,.89),(-.33,.11,.73),(-2.6,2.05,1.23),(7.24,2.1,.98),
                                  (8.28,2.84,.87),(11.4,4.16,.77),(13.7,4.99,.82)]):
        roof_house(root,x,y,.12,s,m,roof_mat)
        box("Paired pier footings",(x,y-.79,.008),(.70,.35,.18),clay_mat,root)
    for index in range(48):
        angle=index*2.399
        r=1.42+(index%7)*1.02
        x=1.5+r*math.sin(angle)
        y=2+r*.51*math.cos(angle)
        if x > -.2 and x<7.3 and y>-.4 and y<4.0:
            continue
        tree(root,x,y,.15,.57+.71*math.sin(index*.91)**2,faction,dark_leaf,light_leaf,m["wood"])
    for n in range(3):
        x=9.50+n*1.36
        y=-2.61+n*.89
        stone("Cargo skiff", (x,y,-.9),(.63,.24,.16),m["wood"],root,2)
        span("Skiff mast",(x,y,-.83),(x,y,-.12),.022,m["wood"],root)
        sheet("Linen sail",[(x,y,-.18),(x+.53,y,-.65),(x,y,-.65)],[(0,1,2)],m["linen"],root,.02)
    for x,y,z,s in [(-5.9,-1.2,-.32,.55),(-4.4,-1.6,-.27,.68),(9.3,4.8,.18,1),(7.1,5.9,.05,.88)]:
        tree(root,x,y,z,s,faction,dark_leaf,light_leaf,m["wood"])
    # Render the same faceted lighting language as the board with a warmer directional key.
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 16
    scene.world = bpy.data.worlds.new("Coastal haze")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.31,.42,.52,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .43
    bpy.ops.object.light_add(type="SUN",location=(2,-3,15))
    sun=bpy.context.object
    sun.data.energy=2.05
    sun.data.angle=.23
    sun.data.color=(1,.82,.64)
    look_at(sun,(1,1.65,0))
    bpy.ops.object.light_add(type="AREA",location=(-9,-9,16))
    fill=bpy.context.object
    fill.data.energy=2150
    fill.data.shape="DISK"
    fill.data.size=9
    fill.data.color=(.65,.82,1)
    look_at(fill,(3,1,0))
    bpy.ops.object.camera_add(location=(9.6,-25,16.5))
    camera=bpy.context.object
    camera.data.type="ORTHO"
    camera.data.ortho_scale=31
    look_at(camera,(1.8,3.35,.9))
    scene.camera=camera
    scene.view_settings.view_transform="AgX"
    scene.render.resolution_x=1560
    scene.render.resolution_y=820
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="WEBP"
    scene.render.image_settings.quality=86
    scene.render.filepath=str(SCENES/f"{faction}.webp")
    bpy.ops.render.render(write_still=True)

for faction in ("aegean","rome","japan"):
    render(faction)
