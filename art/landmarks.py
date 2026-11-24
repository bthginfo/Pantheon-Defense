"""Regional landmarks and low stonework for the three fortress arenas."""
from math import cos, pi, sin, tau

from forge import empty
from geometry import bevel_block as block, mesh_object, shell, span, torus_mesh, volume


def face_panel(name, polygon, z, pigment, parent):
    return mesh_object(name, [(x,y,z) for x,y in polygon],[tuple(range(len(polygon)))],pigment,parent)


def terrace_tile(parent, x, y, pigment, highlights, rng,theme):
    """Carve the edges and lay a quiet directional stone pattern into each cell."""
    width, depth = 2.807, 1.589
    a,b,c,d=(value+rng.uniform(-.009,.018) for value in (.056,.077,.051,.041))
    w,h=width/2,depth/2
    edge=[(-w+a,-h),(w-b,-h),(w,-h+b),(w,h-c),(w-c,h),(-w+d,h),(-w,h-d),(-w,-h+a)]
    rings=[[(x+vx*amount,y+vy*amount,z) for vx,vy in edge]
           for z,amount in ((.252,.976),(.346,1.0),(.386,.977))]
    vertices=[p for ring in rings for p in ring]
    vertices.append((x+rng.uniform(-.57,.57),y+rng.uniform(-.30,.30),.382))
    count=len(edge)
    faces=[tuple(range(count-1,-1,-1))]
    for tier in (0,1):
        for i in range(count):
            a=tier*count+i
            b=tier*count+(i+1)%count
            faces.append((a,b,b+count,a+count))
    for i in range(count):
        faces.append((2*count+i,2*count+(i+1)%count,3*count))
    mesh=mesh_object("Fitted stone with bevelled edges and hand-painted planes",vertices,faces,pigment,parent)
    for paint in highlights:
        mesh.data.materials.append(paint)
    for face in mesh.data.polygons:
        if count < face.index <= 2*count:
            face.material_index=1
        if face.index>2*count and face.index%5==0:
            face.material_index=2
    for index in range(3):
        start=-1.10+index*.42+rng.uniform(-.13,.17)
        end=start+.44+rng.uniform(.10,.52)
        depth=rng.uniform(-.53,.52)
        splay=rng.uniform(-.14,.14)
        if theme=="rome":
            splay*=.58
        elif theme=="japan":
            splay=-.18+.066*index
        reach=.031+rng.random()*.019
        polygon=[(x+start,y+depth),(x+(start+end)*.49,y+depth+splay),
            (x+end,y+depth+splay+.031),(x+(start+end)*.60,y+depth+splay+reach)]
        face_panel("Dry-brushed stone vein",polygon,.389+index*.0002,highlights[index%len(highlights)],parent)
    return mesh


def leaf_ornament(parent,x,y,theta,length,width,pigment,z):
    points=[(-.50,0),(-.14,-.55),(.19,-.53),(.50,0),(.24,.43),(-.17,.55)]
    def place(u,v):
        a,b=u*length,v*width
        return (x+a*cos(theta)-b*sin(theta),y+a*sin(theta)+b*cos(theta))
    face_panel("Laurel leaf in coloured stone", [place(u,v) for u,v in points], z, pigment,parent)


def forum(parent,theme,m):
    block("Long forum mosaic substrate",(0,0,.27),(11.52,1.22,.179),m["ink"],parent,.037)
    tiles=m["mosaic"]
    n=91
    step=11.42/n
    vertices,faces,pigments=[],[],[]
    half_x,half_y=step*.478,.055
    for i in range(n):
        x=(i-(n-1)/2)*step
        for j in range(9):
            y=(j-4)*.119
            if j in (0,8):
                index=4 if i%4 else 1
            elif j in (1,7):
                crease=(i//4)%4
                index=4 if (i%4 in (0,1) and (crease==1 or crease==2)) else 2
            elif theme=="japan":
                center=((x+.51+int(j>4)*.24)%1.03)-.515
                distance=(center*center+(y+.54)**2)**.5
                index=4 if min(abs(distance-d) for d in (.37,.54,.73,.91))<.040 else (0 if i%3 else 2)
            elif theme=="rome":
                index=2 if i%6 else 0
            else:
                wave=.111*sin(x*3.18)
                index=3 if abs(y-wave)<.102 else (1 if abs(y-wave+.162)<.040 else 2)
            start=len(vertices)
            vertices.extend(((x-half_x,y-half_y,.370),(x+half_x,y-half_y,.370),
                             (x+half_x,y+half_y,.370),(x-half_x,y+half_y,.370)))
            faces.append((start,start+1,start+2,start+3))
            pigments.append(index)
    tessera=mesh_object("Individually laid mosaic tesserae",vertices,faces,None,parent)
    for tile in tiles:
        tessera.data.materials.append(tile)
    for polygon,index in zip(tessera.data.polygons,pigments):
        polygon.material_index=index
    if theme=="rome":
        for direction in (-1,1):
            for i in range(1,14):
                x=direction*(.53+i*.341)
                for side in (-1,1):
                    leaf_ornament(parent,x,side*(.118+.039*sin(i*.92)),direction*side*.61,
                                  .29,.107,tiles[4],.376)
    elif theme=="aegean":
        for direction in (-1,1):
            for i in range(1,7):
                x=direction*(1.94+i*.346)
                for side in (-1,1):
                    leaf_ornament(parent,x,side*(.14-.04*sin(i*.93)),direction*side*.57,
                                  .288,.106,tiles[4],.376)
    trim = tiles[4]
    shell("Raised bronze rim of the shallow font",[(.361,.55,.444,0,0),(.409,.50,.413,0,0),
         (.458,.497,.401,0,0)],trim,parent,16)
    shell("Polished water surface in the font",[(.450,.449,.356,0,0),(.461,.429,.332,0,0)],tiles[2],parent,16)
    torus_mesh("Reflected rim inside the fountain",(0,0,.463),.321,.012,tiles[3],parent,20)
    boss=tiles[4] if theme!="japan" else tiles[3]
    for side in (-1,1):
        for height in (-.158,.158):
            leaf_ornament(parent,side*.689,height,side*pi/4,.196,.107,boss,.377)


def pillar(parent, x,y,z,height,m,w=.18,fluted=False):
    block("Double square limestone foot",(x,y,z+.075),(.46,.46,.15),m["wall"][1],parent,.035)
    block("Moulded low plinth",(x,y,z+.151),(.39,.39,.09),m["top"],parent,.021)
    r=lambda n:w*n
    body=[(z+.18,r(1.0),r(1.0),x,y),(z+.24,r(.903),r(.903),x,y),
          (z+height-.22,r(.727),r(.727),x,y),(z+height-.13,r(.835),r(.835),x,y)]
    shell("Tapered carved column shaft",body,m["pave"][2],parent,14,True,pi/14)
    if fluted:
        for i in range(10):
            a=i*tau/10
            span("Carved vertical flute ledge",(x+r(.943)*cos(a),y+r(.943)*sin(a),z+.247),
                 (x+r(.757)*cos(a),y+r(.757)*sin(a),z+height-.195),.013,m["pave"][0],parent,5,.008)
    torus_mesh("Turned collar under the capital",(x,y,z+height-.13),r(.94),.023,m["top"],parent,14)
    block("Doric square abacus",(x,y,z+height-.05),(.388,.378,.103),m["top"],parent,.026)


def wedged_arch(root,x,y,z,rise,width,depth,m,curve_material):
    """Visible voussoirs with an actual opening between the jambs."""
    half=width/2
    rim=.144
    height=rise+half
    for side in (-1,1):
        for row in range(3):
            length=rise/3+.024
            block("Cased arch jamb",(x+side*(half+rim*.42),y,z+length*(row+.46)),
                 (rim+.05,depth,length),m["wall"][(row+1)%len(m["wall"])],root,.018)
    for index in range(11):
        a=pi*(index+.032)/11
        b=pi*(index+.968)/11
        points=[(x+rad*cos(angle),d,z+rise+rad*sin(angle))
                for d in (y-depth/2,y+depth/2)
                for rad,angle in ((half,a),(half+rim,a),(half+rim,b),(half,b))]
        mesh_object("Chiselled stone arch wedge",points,
                    [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],
                    curve_material[index%len(curve_material)],root)
    block("Proud arch keystone",(x,y-.027,z+height+.091),(.151,depth+.036,.164),m["top"],root,.026)


def greek_temple(root,x,y,direction,m,small=False):
    house=empty("Temple of the coastal oath",(x,y,.257),root)
    if direction<0:
        house.rotation_euler.z=pi
    scale=.86 if small else 1.19
    house.scale=(scale,)*3
    for i,w in enumerate((2.82,2.68,2.49)):
        block("Three stone podium steps",(0,-.11,.083*i+.028),(w,1.21-.10*i,.105),
              m["pave"][i],house,.031)
    block("Recessed cella back wall",(0,.28,.728),(2.13,.261,1.05),m["wall"][1],house,.053)
    block("Door recess under the portico",(0,.131,.677),(.557,.059,.809),m["ink"],house,.015)
    for x in (-1.044,-.455,.455,1.044):
        pillar(house,x,-.271,.218,1.25,m,w=.138,fluted=True)
    block("Continuous carved limestone architrave",(0,0,1.493),(2.57,1.043,.151),m["top"],house,.034)
    block("Painted frieze background",(0,-.525,1.496),(2.36,.040,.089),m["mosaic"][1],house,.011)
    block("Fitted ceramic ridge cap",(0,-.500,2.078),(.118,.24,.073),m["roof"][1],house,.024)
    for i in range(14):
        block("Carved tooth of the Doric frieze",((i-6.5)*.167,-.564,1.565),(.088,.045,.126),m["pave"][3],house,.014)
    gable=[(-1.295,-.57,1.611),(1.295,-.57,1.611),(0,-.56,2.076),
           (-1.295,.56,1.609),(1.295,.56,1.609),(0,.54,2.078)]
    mesh_object("Solid triangular gable",gable,
                [(0,1,2),(3,5,4),(0,2,5,3),(1,4,5,2),(0,3,4,1)],m["top"],house)
    for side in (-1,1):
        span("Jade glaze inlaid along the pediment slope",(side*1.192,-.581,1.633),(0.,-.581,2.057),
             .032,m["mosaic"][0],house,6,.027)
    crest=torus_mesh("Hammered solar disk set into the temple gable",(0,-.584,1.764),.114,.020,
                      m["mosaic"][4],house,12,5)
    crest.rotation_euler.x=pi/2
    for side in (-1,1):
        for j in range(8):
            frac=(j+.45)/8
            x=side*1.294*frac
            z=2.081-.462*frac
            for i in range(5):
                a=-.63+i*.242
                span("Visible overlapping terracotta barrel tile",(x,a,z+.033),(x,a+.246,z-.010),
                     .037,m["roof"][(j+i)%len(m["roof"])],house,6,.029)
    for side in (-1,1):
        s=side*.823
        shell("Glazed oil amphora",[(.206,.086,.087,s,-.63),(.283,.130,.124,s,-.63),
              (.479,.115,.107,s,-.63),(.533,.068,.067,s,-.63),(.563,.079,.079,s,-.63)],
              m["roof"][2],house,10,True)
    return house


def roman_bastion(root,x,y,m):
    tower=empty("Brick crenellated Roman bastion",(x,y,-.346),root)
    for h,w,d in ((.127,1.31,1.04),(.37,1.24,1.02),(.77,1.13,.98),(1.317,1.17,.99),(1.53,1.24,1.05)):
        block("Terracotta masonry mass",(0,0,h),(w,d,.34 if h<.5 else .45),m["wall"][1],tower,.051)
    for side in (-1,1):
        for i in range(8):
            h=.25+i*.153
            for j in range(4):
                x=(j-1.5)*.269+(i%2)*.030
                block("Alternating dressed terracotta stretcher",(x,side*.486,h),(.245,.061,.120),
                      m["roof"][(i+j)%len(m["roof"])],tower,.016)
        for i in (-1,0,1):
            block("Red crenel with pale stone coping",(i*.441,side*.449,1.846),(.22,.201,.26),
                  m["wall"][0],tower,.028)
            block("Coping block",(i*.441,side*.449,1.988),(.24,.218,.081),m["top"],tower,.022)
        block("Shadowed arrow slit",(side*.02,side*.526,1.196),(.088,.047,.257),m["ink"],tower,.014)
    return tower


def cedar_roof(parent,width,depth,z,m):
    for side in (-1,1):
        points=[(x*width,y*depth*side,z+h) for x,y,h in
            ((-.6,.64,-.02),(.60,.64,-.02),(.523,.46,.045),(.40,0,.59),(-.40,0,.59),(-.523,.46,.045))]
        faces=[(0,1,2,5),(5,2,3,4)] if side<0 else [(5,2,1,0),(4,3,2,5)]
        roof=mesh_object("Winged cedar-and-slate shrine roof",points,faces,m["roof"][1],parent)
        roof.modifiers.new("Slate layer","SOLIDIFY").thickness=.071
        for j in range(11):
            x=(j-5)*width*.106
            a=(x, side*depth*.612,z+.014)
            b=(x*.915,side*depth*.448,z+.072)
            c=(x*.702,0,z+.618)
            span("Curved glazed tile course",a,b,.031,m["roof"][j%4],parent,7,.027)
            span("Upper glazed tile course",b,c,.029,m["roof"][(j+1)%4],parent,7,.025)
    span("Central rolled ridge",(-.433*width,0,z+.633),(.433*width,0,z+.633),.058,m["roof"][3],parent,8)


def shinto_pavilion(parent,x,y,direction,m):
    root=empty("Shrine with red lacquer and shoji",(x,y,.22),parent)
    if direction<0:
        root.rotation_euler.z=pi
    block("Wide stone threshold",(0,0,.117),(2.71,1.15,.25),m["wall"][1],root,.071)
    block("Raised cedar porch",(0,-.05,.274),(2.54,1.071,.092),m["wood"][1],root,.032)
    block("Rear wall in warm limestone",(0,.329,.747),(2.32,.157,.89),m["top"],root,.024)
    for x in (-1.161,-.665,.665,1.161):
        span("Slim lacquer-painted pillar",(x,-.385,.287),(x,-.385,1.376),.074,m["red"],root,6,.061)
        block("Bronze shoe at foot of post",(x,-.385,.354),(.174,.16,.125),m["wood"][0],root,.018)
    for side in (-1,1):
        x=side*.91
        block("Rice paper in inset wooden frame",(x,-.318,.793),(.397,.049,.64),m["top"],root,.016)
        for j in range(1,4):
            block("Fine cedar shoji lintel",(x,-.353,.468+.157*j),(.398,.027,.028),m["wood"][0],root,.007)
        block("Fine cedar shoji upright",(x,-.353,.786),(.025,.03,.642),m["wood"][0],root,.006)
    block("Shadow in the centre gate",(0,.203,.798),(1.17,.088,.93),m["ink"],root,.020)
    for row in range(2):
        block("Lacquered entrance tie-beam",(0,-.339,1.246+row*.115),(2.62,.141,.061),
              m["red"],root,.024)
    cedar_roof(root,2.48,1.17,1.414,m)
    for side in (-1,1):
        x=side*.900
        span("Hanging shrine lantern post",(x,-.462,1.308),(x,-.54,1.080),.019,m["wood"][0],root,6)
        shell("Paper lantern ribbed shell",[(.847,.096,.094,x,-.54),(.911,.152,.132,x,-.54),
              (1.05,.143,.132,x,-.54),(1.111,.094,.091,x,-.54)],m["top"],root,11,True)
    return root


def stone_lantern(root,x,y,z,m):
    block("Granite lantern base",(x,y,z+.069),(.31,.31,.14),m["low"][2],root,.038)
    span("Octagonal stone lamp post",(x,y,z+.111),(x,y,z+.517),.093,m["low"][1],root,8,.071)
    block("Lit inset lantern glass",(x,y,z+.588),(.181,.175,.171),m["top"],root,.023)
    for a in (-1,1):
        for b in (-1,1):
            block("Small lantern frame pin",(x+a*.101,y+b*.101,z+.596),
                  (.039,.036,.185),m["low"][1],root,.010)
    shell("Pitched lantern cap",[(z+.66,.198,.198,x,y),(z+.697,.207,.207,x,y),
          (z+.827,.081,.081,x,y)],m["low"][3],root,8,False,pi/8)


def coastal_steps(root,m,direction,side_x):
    y=direction*9.78
    parent=empty("Stair down through the layered waterline",(side_x,y,-.033),root)
    if direction<0:
        parent.rotation_euler.z=pi
    for i in range(8):
        z=.158-i*.128
        width=1.72+.036*i
        block("Individually faced quay step",(0,.124+i*.186,z),(width,.294,.202),
               m["pave"][(i+2)%len(m["pave"])],parent,.027)
        for side in (-1,1):
            block("Stone stringer",(side*.911,.124+i*.186,z+.05),(.22,.302,.219),
                   m["wall"][i%len(m["wall"])],parent,.028)


def regional_sites(root,theme,m):
    for side in (-1,1):
        if theme=="aegean":
            greek_temple(root,side*1.13,side*10.29,side,m,small=side<0)
            for x in (-3.42,-2.58,2.73,3.48):
                pillar(root,x,side*9.801,.212,1.07+(x*side*.043),m,w=.149,fluted=True)
        elif theme=="rome":
            gate=empty("Triumphal wall above the water arcade",(side*1.069,side*10.015,.192),root)
            if side<0:
                gate.rotation_euler.z=pi
            wedged_arch(gate,0,0,.03,.522,.944,.312,m,m["pave"])
            for x in (-.956,.956):
                pillar(gate,x,-.021,0,1.248,m,w=.14)
            block("Inscribed stone band without lettering",(0,0,1.351),(2.61,.676,.257),m["top"],gate,.067)
            for j in range(13):
                block("Glazed terracotta dentil",((j-6)*.174,-.397,1.301),(.100,.039,.075),
                      m["roof"][j%4],gate,.012)
            for j in range(7):
                x=(j-3)*.358
                span("Tiled red stone crown on the triumphal arch",(x,-.410,1.512),
                     (x,.42,1.512),.054,m["roof"][j%4],gate,6,.052)
            for t in (-1,1):
                roman_bastion(root,t*5.32,side*9.48,m)
            for i in range(4):
                x=(-4.26+i*.96)*side
                wedged_arch(root,x,side*10.123,-.75,.382,.573,.231,m,m["wall"])
        else:
            shinto_pavilion(root,side*1.185,side*10.042,side,m)
            for x in (-3.65,3.54):
                stone_lantern(root,x,side*9.75,.196,m)
            torii=empty("Open torii away from the combat path",(-side*5.39,side*9.69,.229),root)
            torii.rotation_euler.z=side*.48
            for x in (-.52,.52):
                span("Inclined cinnabar torii pillar",(x,0,0),(x*.87,0,1.225),.087,m["red"],torii,8,.059)
                block("Fitted stone foot of the gate",(x,0,.084),(.244,.239,.149),m["low"][2],torii,.031)
            block("Red lintel below the curved upper bar",(0,0,.998),(1.401,.141,.107),m["red"],torii,.024)
            line=[(-.809,0,1.279),(-.543,0,1.191),(0,0,1.176),(.543,0,1.191),(.809,0,1.279)]
            for a,b in zip(line,line[1:]):
                span("Stepped curved torii roof",a,b,.055,m["roof"][0],torii,7,.047)
    coastal_steps(root,m,1,-2.36)
    coastal_steps(root,m,-1,2.36)
