"""Build the three hand-modelled fortress dioramas and bake their Blender lighting."""
import math
import random
import sys
from argparse import ArgumentParser
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.noise import noise_vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import ASSETS, MODELS, SOURCES, clean, empty, look_at, material
from geometry import bevel_block as block, color_material, mesh_object, pigment_family, shell, span, stone, studio, volume
from landmarks import forum, regional_sites, terrace_tile, wedged_arch

# These are the local coordinates used by the circuit in the simulation. Blender is Z-up.
COLUMNS = (-4.35, -1.47, 1.47, 4.35)
ROWS = (-6.70, -5.0, -3.30, -1.60, 1.60, 3.30, 5.0, 6.70)
ROUTE = [(-6.48,-6.63),(-4.65,-8.94),(4.57,-8.94),(6.48,-6.69),
         (6.48,6.63),(4.65,8.94),(-4.57,8.94),(-6.48,6.69)]
PALETTES = {
    "aegean": {
        "pave":["e4d1ac","d9c3a0","d0b690","e8d5b2","d7bf99","c4aa83"],
        "wall":["b5a17e","c8b594","a29276","d6c4a2","b7a586"],
        "low":["989681","ad9d86","8c9386","bab09c","c2b394"],
        "grout":"a9977e","base":"ad9b7d","top":"f0d9ab","ink":"39565e",
        "mosaic":["3d747a","6ea19a","22565f","8bb5a4","deb275"],
        "zone":["d8c4a1","d6c3a4","dfccab","d0b998","e1cfad"],
        "lane":["bcaa89","c8b491","c0ad8a","cdb795","bbab8f"],
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
        "zone":["d3b89a","cbb397","d6b798","c6ac91","ddbd9a"],
        "lane":["b28a70","b78d75","c0967b","ad856e","c39e80"],
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
        "zone":["b2beb0","b8c5b6","b9c4b4","adb9ac","c4ccbb"],
        "lane":["8e9f97","99a79a","91a199","a5aea1","8c9b93"],
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
            if irregular:
                # Clip the two longest corners before beveling this flagstone.
                p = [p[0].lerp(p[3], .047),p[0].lerp(p[1],.13),p[1],
                     p[2].lerp(p[1],.061),p[2].lerp(p[3],.145),p[3]]
            p = [(v.x,v.y) for v in p]
            facing = sum(x*y2-x2*y for (x,y),(x2,y2) in zip(p,p[1:]+p[:1]))
            if facing < 0:
                p.reverse()
            middle = sum((Vector(v) for v in p), Vector((0,0)))/len(p)
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
    lower = outline(points, 1.03)
    sections("Cut stone retaining blocks", outline(points,.53), lower, .82, -.34, .35, m["wall"], root,rng,True)
    sections("Staggered masonry", outline(points,.55), outline(points,.84), 1.06, -.027, .35,m["wall"],root,rng,True)
    sections("Hewn seawall caps", outline(points,.69), outline(points,.92), .75,.285,.18,m["pave"],root,rng,True)
    if theme == "japan":
        sections("Cedar parapet rail",outline(points,.84),outline(points,.94),1.05,.46,.103,m["wood"],root,rng)
    else:
        sections("Glazed wall band",outline(points,.79),outline(points,.86),.24,.065,.13,m["mosaic"],root,rng)
    inner, mid, outer = outline(points,-.70),outline(points,-.11),outline(points,.69)
    sections("Hewn flagstones on the inner enemy path", inner, mid, .646,.333,.16,m["lane"],root,rng,True)
    sections("Broad flagstones along the outer enemy path", mid, outer, .784,.330,.15,m["lane"],root,rng,True)
    sections("Path trim",outline(points,-.77),outline(points,-.68),.89,.34,.100,m["wall"],root,rng)
    sections("Glazed course tracing the outer path",outline(points,.48),outline(points,.57),.63,.345,.050,
             (m["mosaic"][0],m["mosaic"][2],m["mosaic"][1]),root,rng)
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
            index=m["zone"].index(tint)
            accents=[m["zone"][(index+offset)%len(m["zone"])] for offset in (1,2)]
            terrace_tile(root,x,-y,tint,accents,rng,theme)
            for side in (-1,1):
                block("Small diamond of the camp inlay",(x+side*1.18,-y-.608,.391),
                      (.092,.092,.014),root_color,root,.009,math.pi/4)
    forum(root,theme,m)


def shoreline_details(root,theme,m):
    """Make the shoreline read as a Greek harbour, Roman embankment or Japanese shrine."""
    for side in (-1,1):
        if theme=="aegean":
            stoa=empty("Open harbour colonnade",(7.42*side,2.44*side,-.22),root)
            stoa.rotation_euler.z=-side*math.pi/2
            block("Cut limestone pier below the colonnade",(0,0,-.031),(2.63,.91,.253),m["wall"][1],stoa,.073)
            for x in (-1.03,-.36,.36,1.03):
                shell("Carved pier column",[(.102,.095,.095,x,0),(.258,.081,.081,x,0),
                      (.955,.059,.059,x,0),(1.01,.112,.106,x,0)],m["top"],stoa,10)
            block("Long jade frieze against the sun",(0,0,1.071),(2.47,.52,.153),m["mosaic"][0],stoa,.033)
            for i in range(11):
                block("Cut warm cap stone",(i*.222-1.114,0,1.172),(.207,.65,.115),
                      m["pave"][i%len(m["pave"])],stoa,.024)
        elif theme=="rome":
            ramp=empty("Terracotta-faced seawall gallery",(7.50*side,2.86*side,-.71),root)
            ramp.rotation_euler.z=-side*math.pi/2
            for i in range(3):
                x=(i-1)*.76
                wedged_arch(ramp,x,0.,-.018,.285,.429,.322,m,m["wall"])
            block("Continuous flagstone cornice over the seaside arches",(0.,0.,.737),(2.49,.458,.173),
                  m["top"],ramp,.042)
            for i in range(9):
                block("Glazed brick course above the carved arches",(i*.265-1.061,0.,.847),
                      (.243,.52,.082),m["roof"][i%4],ramp,.018)
        else:
            bridge=empty("Cedar stair and shore landing",(7.39*side,2.60*side,-.39),root)
            bridge.rotation_euler.z=-side*math.pi/2
            for i in range(8):
                x=i*.256-.898
                h=.036-.067*(x*x)
                tread=block("Split cedar deck board",(x,0,h),(.232,.821,.092),m["wood"][i%4],bridge,.026)
                tread.rotation_euler.y=.09*x
            for x in (-.91,0.,.91):
                for sign in (-1,1):
                    block("Red lantern-bridge post",(x,sign*.372,.126),(.097,.109,.462),m["red"],bridge,.021)
            for sign in (-1,1):
                span("Carved cedar rail linking the posts",(-1.04,sign*.372,.309),(1.04,sign*.372,.309),
                     .044,m["wood"][0],bridge,6)


def slabs(root, a, b, z, colors, rng):
    down = a.lerp(b,.52)
    phi = math.atan2(b.y-a.y,b.x-a.x)
    for i in range(3):
        at = down + Vector((math.cos(phi),math.sin(phi)))*((i-1)*.50)
        block("Shore footing stratum",(at.x,at.y,z-i*.09),(.58+rng.random()*.2,.37,.25),rng.choice(colors),root,.055,phi)


def sea_and_shore(root, theme, points, m, rng):
    # Draw the shore and the open water from the same coloured triangulated surface.
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
        for factor in (1.02,1.12,1.25,1.49,1.92,2.65,8.0)
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
        face.material_index=min(4,max(0,4-i//(count*2)))
    for i, p in enumerate(edges):
        shore=p*1.035
        n=p.normalized()
        b=edges[(i+1)%len(edges)]
        t=(b-p).normalized()
        if rng.random()<.86:
            center=shore+n*rng.uniform(-.02,.22)
            size=.26+rng.random()*.39
            crag=stone("Angular shore boulder",(center.x,center.y,-.68-sqrt_noise(i)*.12),
                (size*1.70,size*1.22,.37+rng.random()*.41),rng.choice(m["low"]),root,1 if i%3 else 2)
            crag.rotation_euler=(rng.uniform(-.3,.3),rng.uniform(-.4,.4),rng.random()*math.tau)
        if i%2:
            slabs(root,p*1.018,b*1.024,-.55,m["low"],rng)
        else:
            bank=(p+b)*.505
            rock=stone("Upper ledge of the rugged coast",(bank.x,bank.y,-.345),
                 (.66,.63,.485),m["wall"][i%len(m["wall"])],root,1)
            rock.rotation_euler.z=math.atan2(t.y,t.x)
            if i%4==0:
                for offset in (-.26,.13):
                    leaves=bank+t*offset-n*.07
                    stone("Low moss against the retaining stone",(leaves.x,leaves.y,-.011),
                          (.197,.128,.089),m["leaf"][i%5],root,1)
        if i%3!=1:
            n1=b.normalized()
            p0=p.lerp(b,.09)+n*.38
            p1=p.lerp(b,.93)+n1*.39
            p2=p1+n1*.086
            p3=p0+n*.066
            mesh_object("Fragment of white tide foam",[(q.x,q.y,-.922) for q in (p0,p1,p2,p3)],
                        [(0,1,2,3)],m["surf"][2 if i%2 else 3],root)
        for j in range(rng.randint(1,3)):
            origin=shore+n*(.34+(.155*j))+t*rng.uniform(-.36,.36)
            width=rng.uniform(.27,.75)
            ripple=m["surf"][min(3,j+int(rng.random()<.37))]
            surface=[origin-t*width,origin-t*.27-n*.031,origin+t*.27-n*.043,
                     origin+t*width*.91,origin+t*.24+n*.047,origin-t*.25+n*.056]
            mesh_object("Broken surf ribbon",[(a.x,a.y,-.925+.002*j) for a in surface],
                        [(0,1,5),(1,2,4,5),(2,3,4)],ripple,root)
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
    regional_sites(main,theme,m)
    for side in (-1,1):
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
            h=rng.uniform(1.02,1.58)
            planting(main,theme,x,y,-.08,h,m,rng, blossom=theme=="japan" and n%2==0)
        for x in (-4.12,3.90):
            h={"aegean":1.34,"rome":2.04,"japan":1.78}[theme]
            planting(main,theme,x,side*10.55,-.103,h,m,rng,blossom=theme=="japan")


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
        middle=Vector((x+.06*h,y+.063*h,z+.37*h))
        mid=Vector((x+.18*h,y-.094*h,z+.62*h))
        span("Gnarled lower trunk",o,middle,.117*h,m["wood"][0],root,7,.089*h)
        span("Tapered knot of the trunk",middle,mid,.081*h,m["wood"][1],root,7,.051*h)
        pink=pigment_family("Sakura petal facets",["ca8990","df9fad","edb9bb","f4ccbb","bb7b85"]) if blossom else None
        for k in range(7):
            t=k*math.tau/7+rng.uniform(0,.39)
            reach=rng.uniform(.28,.53)*h
            point=mid+Vector((math.cos(t)*reach,math.sin(t)*reach,h*(.28+rng.uniform(0,.36))))
            span("Visible angular branch",mid,point,.049*h,m["wood"][1],root,6,.013*h)
            for fan in range(2):
                s=(.203+fan*.026+rng.uniform(-.035,.046))*h
                tip=point+Vector((math.cos(t+.85*fan)*s,-math.sin(t+.85*fan)*s,.083*h*fan))
                crown=stone("Clustered cherry blossom" if blossom else "Angular olive crown",tip,
                    (1.26*s,s,.82*s),rng.choice(pink or m["leaf"]),root,1 if k%2 else 2)
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
        block("Worn sill where the rift meets the path",(0,-.274,.113),(1.168,.244,.111),
              m["lane"][2],portal,.037)
        for side in (-1,1):
            if theme=="japan":
                span("Cinnabar timber of the rift gate",(side*.496,0.,.128),(side*.422,0.,1.309),
                     .118,m["red"],portal,8,.087)
                shell("Slate seat for the lacquered pillar",[(.15,.183,.155,side*.495,0),
                      (.25,.169,.143,side*.495,0),(.332,.148,.129,side*.484,0)],m["low"][2],portal,8)
            else:
                for h in range(3):
                    block("Dark weathered portal pier",(side*.469,0,.24+.265*h),(.29,.48,.30),
                          m["wall"][(h+1)%4],portal,.049,side*.014*h)
                if theme=="aegean":
                    shell("Limestone pilaster facing the rift mouth",[(.212,.081,.077,side*.481,-.255),
                          (.32,.058,.060,side*.481,-.255),(.861,.056,.057,side*.481,-.256),
                          (.934,.097,.082,side*.481,-.255)],m["pave"][3],portal,10)
                else:
                    block("Recessed red-glazed tab on the fortress jamb",(side*.474,-.248,.624),
                          (.146,.045,.340),m["roof"][2],portal,.024)
        if theme=="japan":
            block("Lacquered transom crossing the rift gate",(0,0.,1.224),(1.289,.279,.129),
                  m["red"],portal,.029)
            outline=[(-.753,1.423),(-.48,1.335),(0.,1.313),(.48,1.335),(.753,1.423)]
            for a,b in zip(outline,outline[1:]):
                span("Swept indigo lintel at the rift gate",(a[0],0,a[1]),(b[0],0,b[1]),
                     .086,m["roof"][0],portal,6,.077)
            for i in (-1,0,1):
                block("Folded paper strip below the rift lintel",(i*.203,-.151,1.134),
                      (.034,.033,.149),m["top"],portal,.010,.12*i)
        else:
            for i in range(8):
                a=math.pi*(i+.5)/8
                obj=block("Cut arch voussoir",(.46*math.cos(a),0,.91+.465*math.sin(a)),
                          (.26,.44,.287),m["pave"][(i+2)%5] if theme=="aegean" else m["wall"][i%5],portal,.042)
                obj.rotation_euler.y=-a
            if theme=="rome":
                block("Heavy keystone with an iron cap",(0,-.246,1.363),(.198,.136,.240),m["top"],portal,.037)
            else:
                for sign in (-1,1):
                    block("Jade accent set into an arch springing",(sign*.480,-.245,.940),(.304,.077,.103),
                          m["mosaic"][0],portal,.025)
        center=Vector((0,-.089,.65))
        pts=[tuple(center)]
        for i in range(12):
            a=math.tau*i/12
            pts.append((math.cos(a)*.403,-.088,.68+math.sin(a)*.516))
        faces=[(0,i+1,(i+1)%12+1) for i in range(12)]
        prism=mesh_object("Facet-cut translucent-looking portal",pts,faces,None,portal)
        for mat in light: prism.data.materials.append(mat)
        for i,f in enumerate(prism.data.polygons): f.material_index=[1,2,3,2,1,0][i%6]
        paint=prism.data.color_attributes.new(name="Artist pigment",type="FLOAT_COLOR",domain="CORNER")
        for face in prism.data.polygons:
            for loop,index in zip(face.loop_indices,face.vertices):
                paint.data[loop].color=light[4 if index==0 else face.material_index].diffuse_color
        for i in range(3):
            block("Warm rift reflections",(-.41+.37*i,-.12,.105),(.25,.30,.021),light[i+1],portal,.015)


def bake(main,theme,m):
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
        painted=mesh.color_attributes.get("Artist pigment")
        for polygon in mesh.polygons:
            indices=tuple(start+i for i in polygon.vertices)
            pigment=mesh.materials[polygon.material_index].diffuse_color
            faces.append(indices)
            washes=[tuple(painted.data[i].color) for i in polygon.loop_indices] if painted else None
            metadata.append((tuple(pigment), (normal_matrix @ polygon.normal).normalized(), obj.name,washes))
        evaluated.to_mesh_clear()
    bvh=BVHTree.FromPolygons(points,faces)
    shade_rays=[Vector(d).normalized() for d in ((-.70,-.61,1.20),(-.63,-.70,1.17),(-.75,-.53,1.18))]
    deep=tuple(m["water"][0].diffuse_color)
    shallow=tuple(m["water"][4].diffuse_color)
    rift_sites=[Vector((x*1.105,-y*1.03,.50)) for x,y in (ROUTE[0],ROUTE[4])]
    ao_rays=[Vector(d).normalized() for d in ((.8,0,.5),(-.8,0,.5),(0,.8,.5),(0,-.8,.5))]
    pigment=color_material("Daylight baked onto carved stone and coast",unlit=True)
    mesh=mesh_object("Arena mesh with portable baked lighting",points,faces,pigment,None)
    attribute=mesh.data.color_attributes.new(name="Pigment",type="BYTE_COLOR",domain="CORNER")
    mesh.data.color_attributes.active_color=attribute
    for face,(color,n,name,washes) in zip(mesh.data.polygons,metadata):
        center=face.center
        sky=.6+.40*max(0.,n.z)
        if washes:
            values=washes
        elif name.startswith("Faceted, mineral"):
            values=[]
            for index in face.vertices:
                v=points[index]
                distance=math.hypot(v.x/7.7,v.y/10.37)
                transition=max(0.,min(1.,1.01-(distance-0.89)*1.78))
                wave=.009+.010*math.sin(v.x*1.81+v.y*.51)+.007*math.sin(v.x*.42-v.y*1.61)
                light=.962+wave*3.2
                values.append(tuple((deep[k]*(1-transition)+shallow[k]*transition)*light+.011*color[k]
                                    for k in range(3))+(1.,))
        elif name.startswith(("Streak","Broken surf","Fragment of white","Facet-cut")):
            values=[color]*len(face.loop_indices)
        else:
            daylight=max(0.,n.dot(shade_rays[0]))
            values=[]
            for index in face.vertices:
                v=points[index]
                site=v.lerp(center,.21)+n*.023
                shadow=1-sum(bvh.ray_cast(site+ray*.007,ray,11.)[2] is not None
                             for ray in shade_rays)/len(shade_rays)
                occupied=sum(bvh.ray_cast(site+ray*.011,ray,.39)[2] is not None
                             for ray in ao_rays if ray.dot(n)>-.04)
                contact=1-.072*occupied
                light=daylight*shadow
                amount=(.47+.185*sky+.602*light)*contact
                grain=(.987+.026*math.sin(v.x*3.13-v.y*2.49+v.z*4.11))
                # Broad, directional glaze brings out the cut planes without adding a draw call.
                scale=.041 if name.startswith(("Fitted stone","Training court","Dry-brushed")) else .081
                rake=noise_vector(Vector((1.8*v.x+.72*v.y,.55*v.y+2.1*v.z,.4+v.x*.59)))[0]
                scumble=noise_vector(Vector((v.x*3.9+v.y*2.2,v.y*.74,v.z*7.5)))[1]
                amount*=grain*(1.+scale*(rake+.45*scumble))
                halo=sum(max(0.,1.-(v-gate).length/1.07)**2 for gate in rift_sites)*max(0.,n.z)
                values.append((color[0]*amount*(.921+.186*light)+.069*halo,
                               color[1]*amount*(.972+.048*light)+.007*halo,
                               color[2]*amount*(1.15-.198*light)+.093*halo,1.))
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


def build(theme, review_directory,output=None):
    clean()
    rng=random.Random(theme)
    m={k: pigment_family(k,v) if isinstance(v,list) else material(k,v) for k,v in PALETTES[theme].items()}
    root=empty(theme+" coast")
    path=course(theme)
    paving(root,theme,rng,path,m)
    sea_and_shore(root,theme,path,m,rng)
    architecture(root,theme,m,rng)
    harbor_detail(root,theme,m)
    shoreline_details(root,theme,m)
    rifts(root,theme,m)
    mesh=bake(root,theme,m)
    scene,camera=studio((9.8,-32.1,22.0),(0,0,-.23),1280,880,27.1,samples=18)
    scene.view_settings.view_transform="Standard"
    scene.view_settings.look="None"
    scene.render.image_settings.file_format="WEBP"
    scene.render.image_settings.quality=89
    models,sources,scenes=MODELS,SOURCES,ASSETS/"scenes"
    if output:
        models,sources,scenes=(output/name for name in ("models","blend","scenes"))
        for path in (models,sources,scenes):
            path.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(scenes/f"{theme}.webp")
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    mesh["terrain_theme"]=theme
    mesh["formation_cells"]=32
    bpy.ops.export_scene.gltf(filepath=str(models/f"arena_{theme}.glb"), export_format="GLB",
        use_selection=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,
        export_all_vertex_colors=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(sources/f"arena_{theme}.blend"),compress=True)
    bpy.ops.render.render(write_still=True)
    if review_directory:
        scene.render.resolution_x=820
        scene.render.resolution_y=820
        for direction, place, scale in (("reverse",(-7,26,24),25.),("top",(0,-.02,33),25.7),
                                        ("side",(-18,-20,13),25.1)):
            camera.location=place
            camera.data.ortho_scale=scale
            look_at(camera,(0,0,-.10))
            scene.render.filepath=str(review_directory/f"{theme}-{direction}.webp")
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    cli=ArgumentParser(description=__doc__)
    cli.add_argument("themes",nargs="*",metavar="THEME")
    cli.add_argument("--review",type=Path,metavar="DIRECTORY")
    cli.add_argument("--output",type=Path,metavar="DIRECTORY")
    args=cli.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.review:
        args.review.mkdir(parents=True,exist_ok=True)
    for name in PALETTES:
        if not args.themes or name in args.themes:
            build(name,args.review,args.output)
