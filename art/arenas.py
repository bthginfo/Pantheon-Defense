"""Build the three hand-modelled fortress dioramas and bake their Blender lighting."""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import ASSETS, MODELS, SOURCES, clean, empty, look_at, material, span, stone
from geometry import bevel_block as block, color_material, mesh_object, pigment_family, shell, studio, volume

# These are the local coordinates used by the circuit in the simulation. Blender is Z-up.
COLUMNS = (-4.35, -1.47, 1.47, 4.35)
ROWS = (-6.70, -5.0, -3.30, -1.60, 1.60, 3.30, 5.0, 6.70)
ROUTE = [(-6.48,-6.63),(-4.65,-8.94),(4.57,-8.94),(6.48,-6.69),
         (6.48,6.63),(4.65,8.94),(-4.57,8.94),(-6.48,6.69)]
PALETTES = {
    "aegean": {
        "pave":["e1cfac","ddc9a4","d0ba96","e8d7b5","d9c6a8","cfb995"],
        "wall":["b5a17e","c8b594","a29276","d6c4a2","b7a586"],
        "low":["989681","ad9d86","8c9386","bab09c","c2b394"],
        "grout":"a9977e","base":"ad9b7d","top":"f0d9ab","ink":"39565e",
        "mosaic":["3d747a","6ea19a","22565f","8bb5a4","deb275"],
        "zone":["d8c1a1","d7c7ad","dfcbab","d1bd9e","e4d3b4"],
        "blue":"467e83","red":"af725a","water":["0c4959","125565","146674","1b7280","247e89"],
        "surf":["3d9898","69b9b4","91c7bd","d2e3cf"],
        "wood":["825437","a37149","b48358","96633f"],
        "roof":["ae5a39","c16b42","cf7e53","9a4f36"],
        "leaf":["4e654b","6a7e4d","8d9a59","a1a767","798755"]
    },
    "rome": {
        "pave":["c1a58a","cbb095","ba9c86","d5b799","b29980","dcbd9a"],
        "wall":["ae795f","bd8a6a","8e6759","c49372","a8735d"],
        "low":["71594d","938174","897768","ad9379","9c8369"],
        "grout":"8f6957","base":"976d58","top":"dfbb8f","ink":"604343",
        "mosaic":["824e45","a36351","743f3f","c2895f","dab377"],
        "zone":["d5b597","cbb296","d1b08e","c3aa8d","ddbf9a"],
        "blue":"6c8883","red":"ae6257","water":["183d4b","214957","2b5461","396570","49777f"],
        "surf":["658d8c","82a5a0","b4c4aa","cfceb1"],
        "wood":["624538","876148","9a7755","6c4a37"],
        "roof":["824f45","a8654b","ba7651","9a553e"],
        "leaf":["48563d","667544","7d8051","7f9158","546643"]
    },
    "japan": {
        "pave":["b0b3a2","b8bdac","a5ad9c","c9c8b3","a7b0a0","c2c1aa"],
        "wall":["828d7c","9fa492","6c7877","b0af98","7a887e"],
        "low":["52696a","6b7a70","7d897e","959789","8f9a89"],
        "grout":"6c7b75","base":"76867d","top":"d7d0b3","ink":"294550",
        "mosaic":["43796e","609289","3b6571","7a9d8c","bd8e70"],
        "zone":["adbcad","bac5b2","b8c2af","adb7a9","c6cbb6"],
        "blue":"5d8f86","red":"b67064","water":["144655","1a5362","235d6a","3c747b","5e908c"],
        "surf":["608e85","7fa9a1","9bb8a8","cfd7b9"],
        "wood":["75554a","977365","ad8271","655047"],
        "roof":["37505c","516874","687f89","435978"],
        "leaf":["4f6e57","678267","7f9473","90a37f","738d74"]
    },
}


def course(theme):
    pts = ROUTE[:]
    if theme == "japan":
        pts[1], pts[5] = (-4.55,-8.70),(4.55,8.70)
    if theme == "rome":
        pts[2], pts[6] = (5.04,-8.94),(-5.04,8.94)
    return [Vector((x,-y)) for x,y in reversed(pts)]


def outline(points, margin):
    corners = []
    for i, p in enumerate(points):
        a = (p-points[i-1]).normalized()
        b = (points[(i+1)%len(points)]-p).normalized()
        n = Vector((a.y,-a.x))
        m = Vector((b.y,-b.x))
        corners.append(p+(n+m)*margin/max(.5,1+n.dot(m)))
    return corners


def rings(points, heights):
    return [[(v.x*factor, v.y*factor,z) for v in points] for z,factor in heights]

def inlay(name,x,y,z,w,d,pigment,root):
    mesh_object(name,[(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z)],
                [(0,1,2,3)],pigment,root)


def sections(name, inside, outside, width, z, thickness, colors, root, rng, irregular=False):
    for i, a in enumerate(inside):
        j = (i+1)%len(inside)
        b, c, d = inside[j], outside[i], outside[j]
        count = max(1,round((b-a).length/width))
        breaks = [0]+[(k+(.24*rng.uniform(-1,1) if irregular else 0))/count for k in range(1,count)]+[1]
        for start, end in zip(breaks,breaks[1:]):
            left = start+.009*(end-start)
            right = end-.009*(end-start)
            p = [a.lerp(b,left), c.lerp(d,left), c.lerp(d,right), a.lerp(b,right)]
            p = [(v.x,v.y) for v in p]
            facing = sum(x*y2-x2*y for (x,y),(x2,y2) in zip(p,p[1:]+p[:1]))
            if facing < 0:
                p.reverse()
            middle = sum((Vector(v) for v in p), Vector((0,0)))/4
            inset = [middle.lerp(Vector(v),.929) for v in p]
            h = rng.uniform(-.008,.008) if irregular else 0
            volume(name, [
                [(x,y,z-thickness) for x,y in p],
                [(x,y,z+h-.026) for x,y in p],
                [(v.x,v.y,z+h) for v in inset],
            ], rng.choice(colors), root)


def paving(root, theme, rng, points, m):
    base = outline(points, .78)
    volume("Sculpted island limestone bed", rings(base,[(-1.13,.91),(-.76,1.04),(-.29,1.012),(.25,1.0)]),m["base"],root)
    lower = outline(points, .92)
    sections("Cut stone retaining blocks", outline(points,.53), lower, .82, -.34, .35, m["wall"], root,rng,True)
    sections("Staggered masonry", outline(points,.55), outline(points,.84), 1.06, -.027, .35,m["wall"],root,rng,True)
    sections("Hewn seawall caps", outline(points,.69), outline(points,.92), .75,.285,.18,m["pave"],root,rng,True)
    if theme == "japan":
        sections("Cedar parapet rail",outline(points,.84),outline(points,.94),1.05,.46,.103,m["wood"],root,rng)
    else:
        sections("Glazed wall band",outline(points,.79),outline(points,.86),.24,.065,.13,m["mosaic"],root,rng)
    inner, mid, outer = outline(points,-.70),outline(points,-.11),outline(points,.69)
    sections("Inner flagstone", inner, mid, .84,.333,.16,m["pave"],root,rng,True)
    sections("Outer flagstone", mid, outer, .94,.330,.15,m["pave"],root,rng,True)
    sections("Path trim",outline(points,-.77),outline(points,-.68),.89,.34,.100,m["wall"],root,rng)
    for y in (-4.19,4.19):
        block("Training court stone bed",(0,y,.277),(11.55,6.88,.151),m["grout"],root,.065)
        for x in (-5.69,5.69):
            block("Inlaid court edge",(x,y,.34),(.13,6.89,.044),m["top"],root,.013)
        for edge_y in (y-3.44,y+3.44):
            block("Inlaid court edge",(0,edge_y,.34),(11.46,.12,.046),m["top"],root,.016)
            for i in range(37):
                x=(i-18)*.301
                inlay("Small tessera",x,edge_y,.397,.267,.069,m["mosaic"][i%5],root)
    for j,y in enumerate(ROWS):
        for i,x in enumerate(COLUMNS):
            tint=m["zone"][(i+2*j+rng.randrange(3))%len(m["zone"])]
            root_color=m["blue" if y<0 else "red"]
            block("Hand-dressed formation slab",(x,-y,.322),(2.815,1.591,.13),tint,root,.039)
            for side in (-1,1):
                block("Corner camp inlay",(x+side*1.17,-y-.59,.393),(.095,.095,.014),root_color,root,.006,math.pi/4)
    # A single low mosaic wall-to-wall plaza keeps all unit silhouettes visible.
    block("Forum mosaic mortar",(0,0,.279),(11.46,1.31,.155),m["ink"],root)
    for i in range(43):
        x=(i-21)*.261
        for j in range(5):
            y=(j-2)*.245
            wave=2*math.sin(i*.48)+2
            index=4 if j in (0,4) else (3 if abs(j-wave)<1 else (i+j)%3)
            inlay("Water-and-laurel tessera",x,y,.365,.254,.236,m["mosaic"][index],root)
    bowl=m["mosaic"][2]
    shell("Low font foundation",[(.34,.6,.42,0,0),(.40,.57,.40,0,0),(.46,.50,.36,0,0)],
        m["top"],root,12)
    shell("Reflecting mosaic well",[(.457,.424,.282,0,0),(.465,.424,.282,0,0)],bowl,root,12)


def slabs(root, a, b, z, colors, rng):
    down = a.lerp(b,.52)
    phi = math.atan2(b.y-a.y,b.x-a.x)
    for i in range(3):
        at = down + Vector((math.cos(phi),math.sin(phi)))*((i-1)*.50)
        block("Shore footing stratum",(at.x,at.y,z-i*.09),(.58+rng.random()*.2,.37,.25),rng.choice(colors),root,.055,phi)


def sea_and_shore(root, theme, points, m, rng):
    # Several rings of differently coloured triangles create an underwater shelf.
    coast=outline(points, .92)
    edges=[]
    for i,a in enumerate(coast):
        for k in range(5):
            b=coast[(i+1)%len(coast)]
            p=a.lerp(b,k/5)
            n=p.normalized()
            edges.append(p+n*rng.uniform(-.12, .39))
    sea_rings = [
        [p*factor+Vector((rng.uniform(-.42,.42),rng.uniform(-.35,.35))) for p in edges]
        for factor in (1.02,1.12,1.25,1.49,1.92,2.65,4.0)
    ]
    count=len(edges)
    verts=[(p.x,p.y,-.94) for ring in sea_rings for p in ring]
    faces=[]
    for r in range(len(sea_rings)-1):
        for i in range(count):
            j=(i+1)%count
            a,b,c,d=r*count+i,r*count+j,(r+1)*count+j,(r+1)*count+i
            faces.extend(((a,d,c),(a,c,b)) if (i+r)%2 else ((a,d,b),(b,d,c)))
    faces.append(tuple(range(count)))
    sheet=mesh_object("Faceted, mineral-tone tidal water",verts,faces,None,root)
    for color in m["water"]:
        sheet.data.materials.append(color)
    for i, face in enumerate(sheet.data.polygons):
        face.material_index=min(4,max(0,4-i//(count*2)+rng.choice((-1,0,0,0,1))))
    for i, p in enumerate(edges):
        shore=p*1.035
        n=p.normalized()
        b=edges[(i+1)%len(edges)]
        t=(b-p).normalized()
        if rng.random()<.86:
            center=shore+n*rng.uniform(-.02,.22)
            size=.21+rng.random()*.36
            crag=stone("Angular shore boulder",(center.x,center.y,-.66-sqrt_noise(i)*.12),
                (size*1.61,size*1.19,.31+rng.random()*.35),rng.choice(m["low"]),root,1 if i%3 else 2)
            crag.rotation_euler=(rng.uniform(-.3,.3),rng.uniform(-.4,.4),rng.random()*math.tau)
        if i%2:
            slabs(root,p*1.018,b*1.024,-.55,m["low"],rng)
        for j in range(rng.randint(1,3)):
            origin=shore+n*(.34+(.155*j))+t*rng.uniform(-.36,.36)
            width=rng.uniform(.27,.75)
            ripple=m["surf"][min(3,j+int(rng.random()<.37))]
            surface=[origin-t*width,origin+t*width*.91,origin+t*.27+n*.046,origin-t*.25+n*.07]
            mesh_object("Broken surf ribbon",[(a.x,a.y,-.925+.002*j) for a in surface],[(0,1,2,3)],ripple,root)
    for i in range(39):
        ang=rng.random()*math.tau
        x=math.cos(ang)*rng.uniform(9.,21.)
        y=math.sin(ang)*rng.uniform(11.6,22.0)
        if abs(x)<7.8 and abs(y)<10.2:
            continue
        w=rng.uniform(.14,.83)
        y-=.28
        mesh_object("Streak of sea glint",[(x-w,y,-.921),(x+w,y+.02,-.92),(x-w*.22,y+.067,-.919)],
            [(0,1,2)],m["surf"][rng.randrange(2)],root)


def sqrt_noise(i):
    return .5+.5*math.sin(i*1.73)


def column(root,x,y,height,m,base=.31):
    block("Carved square column foot",(x,y,base+.09),(.52,.52,.18),m["top"],root,.026)
    shell("Moulded pillar",[
        (base+.17,.18,.18,x,y),(base+.24,.152,.152,x,y),
        (base+height-.19,.126,.126,x,y),(base+height-.11,.189,.189,x,y),
        (base+height-.057,.189,.189,x,y),
    ],m["pave"][3],root,10)
    block("Pillar cornice",(x,y,base+height),(.50,.46,.14),m["top"],root,.028)


def pediment(root, origin, width, depth, lift, m, theme):
    x,y,z=origin
    if theme=="japan":
        for side in (-1,1):
            points=[(x+u*width, y+side*t*depth, z+v*lift) for t,v,u in [
                (.58,0,-.55),(.58,0,.55),(.37,.13,.48),(0,.62,.33),(0,.62,-.33),(.37,.13,-.48)]]
            end=[(0,1,2,5),(5,2,3,4)] if side<0 else [(5,2,1,0),(4,3,2,5)]
            mesh_object("Raised lacquer eaves",points,end,m["roof"][1],root)
        for i in range(9):
            u=(i-4)/9
            for side in (-1,1):
                span("Curved ceramic rib",(x+u*width,y+side*.54*depth,z+.012),
                    (x+u*width*.67,y,z+.64*lift),.025,m["roof"][0],root,5,.017)
    else:
        box_points=[(x+u*width,y+v*depth,z+h*lift) for v in (-.52,.52) for u,h in ((-.53,0),(.53,0),(0,.6))]
        mesh_object("Carved pediment core",box_points,[(0,1,2),(3,5,4),(0,2,5,3),(1,4,5,2),(0,3,4,1)],m["top"],root)
        for side in (-1,1):
            for i in range(6):
                t=(i+.46)/6
                near=x+side*.53*width*t
                pz=z+.6*lift*(1-t)+.023
                span("Terracotta roof ridges",(near,y-.54*depth,pz),(near,y+.56*depth,pz),
                     .046,m["roof"][i%len(m["roof"])],root,5,.038)


def architecture(main, theme, m, rng):
    for side in (-1,1):
        arch=empty("Entrance temple", (side*2.56,side*9.93,.13),main)
        if side < 0:
            arch.rotation_euler.z=math.pi
        depth=1.02
        block("Temple stone landing",(0,0,.08),(2.03,depth,.27),m["wall"][1],arch,.066)
        for s in (-1,1):
            if theme=="japan":
                for x in (s*.70, s*.41):
                    block("Vermilion shrine post",(x,0,.68),(.13,.13,1.11),m["red"],arch,.021)
                block("White paper panel",(s*.55,0,.66),(.30,.061,.54),m["top"],arch,.013)
            else:
                column(arch,s*.67,-.21,.99,m,.205)
                block("Recessed portal pilaster",(s*.58,.29,.63),(.24,.28,.86),m["wall"][0],arch)
        block("Door in shadow",(0,.36,.64),(.69,.17,.85),m["ink"],arch)
        block("Architrave",(0,0,1.185),(1.81,.80,.15),m["top"],arch,.035)
        pediment(arch,(0,0,1.28),1.80,.92,.46,m,theme)
        for step in range(4):
            block("Harbor stair",(0,-.51-.156*step,.212-.094*step),
                  (1.32+.05*step,.328,.17),m["pave"][step],arch,.032)
        stairs=empty("Stairs down to the water",(-side*2.27,side*9.81,-.04),main)
        if side<0:
            stairs.rotation_euler.z=math.pi
        for i in range(7):
            block("Dressed quay stair",(0,.187*i,.05-i*.135),(1.97,.29,.229),
                  rng.choice(m["wall"]),stairs,.051)
        for x in (-1.09,1.09):
            block("Stone stair pier",(x,.03,.15),(.27,.42,.58),m["pave"][1],stairs,.046)
        if theme != "japan":
            for x,y in ((-.91*side,9.76*side),(.89*side,9.7*side),(-3.8*side,9.64*side)):
                column(main,x,y,.84 if x*side>.2 else .63,m,.245)
        if theme=="rome":
            for y in (-7.2,-5.24,-3.22,3.22,5.24,7.2):
                x=side*7.32
                block("Terracotta outer bastion pier",(x,y,-.005),(.52,.50,.80),m["wall"][1],main,.063)
                block("Stone parapet cap",(x,y,.43),(.59,.60,.16),m["top"],main,.045)
                block("Crenel",(x,y,.56),(.32,.26,.18),m["wall"][2],main,.025)
        if side==1 or theme!="rome":
            pier=empty("Quayside shelter",(-6.47*side,9.07*side,-.31),main)
            pier.rotation_euler.z=side*.59
            for x in (-.55,.55):
                for y in (-.54,.57):
                    block("Weathered pine support",(x,y,.05),(.15,.15,1.19),m["wood"][0],pier,.016)
            for n in range(8):
                block("Overlapping boardwalk plank",(0,-.75+.194*n,-.12),(1.37,.18,.11),m["wood"][n%4],pier,.024)
            pediment(pier,(0,0,.73),1.52,1.56,.66,m,theme)
        for n in range(4):
            x=side*(6.89+rng.uniform(0,.39))
            y=side*([-8.07,-4.66,1.04,6.63][n])+rng.uniform(-.21,.21)
            h=rng.uniform(.82,1.37)
            planting(main,theme,x,y,-.08,h,m,rng, blossom=theme=="japan" and n%2==0)


def harbor_detail(root,theme,m):
    for side in (-1,1):
        if theme=="rome":
            for i in range(4):
                x=(-5.52+i*.94)*side
                base=(x,side*10.06,-.19)
                block("Projecting Roman brick buttress",base,(.45,.64,.86),m["wall"][i%4],root,.065)
                block("Dressed keystone above the quay",(base[0],base[1],.256),(.54,.69,.14),m["top"],root,.033)
            continue
        launch=empty("Dinghy at the antique harbor",(-4.785*side,-side*10.98,-.80),root)
        launch.rotation_euler.z=side*1.24
        hull=[(-.40,-.54),(-.32,-.98),(0,-1.14),(.32,-.99),(.40,-.50),(.43,.43),
              (.29,.86),(0,.974),(-.29,.85),(-.43,.43)]
        layers=[[(x*stretch,y*stretch,z) for x,y in hull] for z,stretch in [(-.17,.52),(-.065,.84),
            (.124,1.0),(.181,1.014)]]
        volume("Shaped keel and plank hull",layers,m["wood"][1],launch)
        for i in range(6):
            block("Visible planking in the dinghy",(0,-.64+i*.247,.179),(.648,.225,.044),m["wood"][i%4],launch,.029)
        for a,b in zip(hull,hull[1:]+hull[:1]):
            span("Raised curved gunwale",(*a,.192),(*b,.192),.027,m["wood"][0],launch,6)
        for i in (-1,1):
            span("Oar resting over the side",(i*.062,.21,.226),(i*.61,-.37,.165),.027,m["wood"][2],launch,6,.017)
        if theme=="aegean" and side==1:
            span("Short pine mast",(0,-.22,.16),(0,-.20,1.14),.039,m["wood"][0],launch,8,.019)
            span("Rigged clamped yard",(-.31,-.19,1.08),(.306,-.232,1.033),.022,m["wood"][1],launch,7)
            points=[(-.28,-.207,1.067),(.27,-.249,1.021),(.25,-.071,.52),(-.22,-.034,.571),
                    (0,-.305,.779)]
            canvas=mesh_object("Billow in the linen sail",points,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],m["top"],launch)
            canvas.modifiers.new("Woven linen thickness","SOLIDIFY").thickness=.014
        else:
            block("Low tied cargo on the boat",(0,-.42,.27),(.42,.31,.19),m["roof"][1],launch,.043)


def planting(root,theme,x,y,z,h,m,rng,blossom=False):
    o=(x,y,z)
    if theme=="rome":
        span("Cypress trunk",o,(x,y,z+h*.57),.077,m["wood"][0],root,7,.038)
        shell("Tapered Italian cypress",[(z+.18*h,.15,.16,x,y),(z+.47*h,.29,.26,x,y),
            (z+.94*h,.13,.14,x+.05*h,y),(z+1.37*h,.025,.04,x+.07*h,y)],m["leaf"][1],root,7,False,.34)
    else:
        mid=Vector((x+.12*h,y-.05*h,z+.57*h))
        span("Weathered branching trunk",o,mid,.109*h,m["wood"][0],root,7,.065*h)
        pink=pigment_family("Sakura petal facets",["d59b9a","e9b8aa","edc7b9","bf828d"]) if blossom else None
        for k in range(5):
            t=k*math.tau/5+rng.uniform(0,.39)
            point=mid+Vector((math.cos(t)*h*.41,math.sin(t)*h*.41,h*(.36+rng.uniform(0,.21))))
            span("Angular branch",mid,point,.052*h,m["wood"][1],root,6,.02*h)
            s=.31*h
            crown=stone("Sakura canopy" if blossom else "Olive foliage",point,
                (1.23*s,s,.74*s),rng.choice(pink or m["leaf"]),root,1 if k%2 else 2)
            crown.rotation_euler.z=rng.random()*math.tau
    for k in range(3):
        t=rng.random()*math.tau
        size=.17+rng.random()*.10
        stone("Moss and shoreline growth",(x+math.cos(t)*.49,y+math.sin(t)*.4,z+.12),
            (size,.90*size,.74*size),rng.choice(m["leaf"]),root,1)


def rifts(root,theme,m):
    route=[(ROUTE[0][0],-ROUTE[0][1]),(ROUTE[4][0],-ROUTE[4][1])]
    light=pigment_family("Rift glass",["6a426e","a66c99","ce91be","eab2cf","f5dcca"])
    for x,y in route:
        portal=empty("Rift vault",(x*1.105,y*1.03,.24),root)
        portal.rotation_euler.z=(-.26 if x>0 else math.pi-.26)
        block("Rift footing",(0,0,.07),(1.24,.55,.21),m["ink"],portal,.062)
        for side in (-1,1):
            for h in range(3):
                block("Dark weathered portal pier",(side*.469,0,.24+.265*h),(.29,.48,.30),
                      m["wall"][(h+1)%4],portal,.049,side*.014*h)
        for i in range(8):
            a=math.pi*(i+.5)/8
            obj=block("Cut arch voussoir",(.46*math.cos(a),0,.91+.465*math.sin(a)),
                      (.26,.44,.287),m["pave"][(i+2)%5],portal,.042)
            obj.rotation_euler.y=-a
        center=Vector((0,-.089,.65))
        pts=[tuple(center)]
        for i in range(12):
            a=math.tau*i/12
            pts.append((math.cos(a)*.403,-.088,.68+math.sin(a)*.516))
        faces=[(0,i+1,(i+1)%12+1) for i in range(12)]
        prism=mesh_object("Facet-cut translucent-looking portal",pts,faces,None,portal)
        for mat in light: prism.data.materials.append(mat)
        for i,f in enumerate(prism.data.polygons): f.material_index=[1,2,3,2,1,0][i%6]
        for i in range(3):
            block("Warm rift reflections",(-.41+.37*i,-.12,.105),(.25,.30,.021),light[i+1],portal,.015)


def bake(main,theme):
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    pieces=[obj for obj in main.children_recursive if obj.type=="MESH"]
    points, faces, metadata = [], [], []
    for obj in pieces:
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        start=len(points)
        points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
        normal_matrix=evaluated.matrix_world.to_3x3().inverted().transposed()
        for polygon in mesh.polygons:
            indices=tuple(start+i for i in polygon.vertices)
            pigment=mesh.materials[polygon.material_index].diffuse_color
            faces.append(indices)
            metadata.append((tuple(pigment), (normal_matrix @ polygon.normal).normalized(), obj.name))
        evaluated.to_mesh_clear()
    bvh=BVHTree.FromPolygons(points,faces)
    shade_rays=[Vector(d).normalized() for d in ((-.53,-.64,.99),(-.44,-.62,1.01),(-.53,-.51,1.13))]
    ao_rays=[Vector(d).normalized() for d in ((.8,0,.5),(-.8,0,.5),(0,.8,.5),(0,-.8,.5))]
    pigment=color_material("Daylight baked onto carved stone and coast",unlit=True)
    mesh=mesh_object("Arena mesh with portable baked lighting",points,faces,pigment,None)
    attribute=mesh.data.color_attributes.new(name="Pigment",type="BYTE_COLOR",domain="CORNER")
    mesh.data.color_attributes.active_color=attribute
    for face,(color,n,name) in zip(mesh.data.polygons,metadata):
        center=face.center
        sky=.6+.40*max(0.,n.z)
        if name.startswith(("Faceted, mineral","Streak","Broken surf","Rift glass","Facet-cut")):
            values=[color]*len(face.loop_indices)
        else:
            light=max(.0,n.dot(shade_rays[0]))
            shadow=1-sum(bvh.ray_cast(center+n*.014+ray*.004,ray,10.)[2] is not None
                         for ray in shade_rays)/3
            values=[]
            for index in face.vertices:
                site=points[index].lerp(center,.19)+n*.021
                occupied=sum(bvh.ray_cast(site+ray*.015,ray,.49)[2] is not None
                             for ray in ao_rays if ray.dot(n) > -.04)
                contact=1-.084*occupied
                amount=(.43+.23*sky+light*shadow*.52)*contact
                warmth=shadow*light
                v=points[index]
                grain=.974+.036*math.sin(v.x*2.173+v.y*3.219+v.z*3.691)
                amount*=grain
                values.append((color[0]*amount*(.925+.14*warmth),
                               color[1]*amount*(.984+.043*warmth),
                               color[2]*amount*(1.13-.11*warmth),1.))
        for loop, value in zip(face.loop_indices,values):
            attribute.data[loop].color=value
    source=bpy.data.collections.new("Editable masonry, scenery, and site layout")
    bpy.context.scene.collection.children.link(source)
    for obj in [*main.children_recursive,main]:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        source.objects.link(obj)
    source.hide_viewport=True
    source.hide_render=True
    mesh.name="Portrait arena with baked illumination"
    return mesh


def build(theme, review):
    clean()
    rng=random.Random(theme)
    m={k: pigment_family(k,v) if isinstance(v,list) else material(k,v) for k,v in PALETTES[theme].items()}
    root=empty(theme+" coast")
    path=course(theme)
    paving(root,theme,rng,path,m)
    sea_and_shore(root,theme,path,m,rng)
    architecture(root,theme,m,rng)
    harbor_detail(root,theme,m)
    rifts(root,theme,m)
    mesh=bake(root,theme)
    scene,camera=studio((6.1,-31.8,25.0),(0,0,-.26),1280,840,27.3,samples=10)
    scene.view_settings.view_transform="Standard"
    scene.view_settings.look="None"
    scene.render.image_settings.file_format="WEBP"
    scene.render.image_settings.quality=89
    scene.render.filepath=str(ASSETS/"scenes"/f"{theme}.webp")
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    mesh["terrain_theme"]=theme
    mesh["formation_cells"]=32
    bpy.ops.export_scene.gltf(filepath=str(MODELS/f"arena_{theme}.glb"), export_format="GLB",
        use_selection=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,
        export_all_vertex_colors=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCES/f"arena_{theme}.blend"),compress=True)
    bpy.ops.render.render(write_still=True)
    if review:
        scene.render.resolution_x=820
        scene.render.resolution_y=820
        for direction, place in (("reverse",(-7,26,24)),("top",(0,-.02,33)),("side",(-18,-20,8))):
            camera.location=place
            camera.data.ortho_scale=22.2
            look_at(camera,(0,0,-.10))
            scene.render.filepath=f"/tmp/pd-atelier/{theme}-{direction}.webp"
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    args=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    requested=args.intersection(PALETTES)
    for name in PALETTES:
        if not requested or name in requested:
            build(name,"--review" in args)
