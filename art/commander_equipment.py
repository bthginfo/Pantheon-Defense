"""Thekla's sun shield and spear, and Marcus's scutum and sheathed gladius."""
from math import cos, pi, sin, tau

from mathutils import Euler, Vector

from commander_forms import angle_span, piping, relief, strips, tube
from commander_paint import paint_losses, shield_wash
from geometry import mesh_object, span, stone, volume


def thekla_spear(a,m):
    parent=a.part('RightHand')
    grip=a.hand_point('Right',.073)
    x,y=grip.x-.022,grip.y-.012
    def pick(z):
        return x+.065*(grip.z-z),y+.022*(grip.z-z),z
    path=[pick(z) for z in (.026,.059,.501,1.013,1.408,1.578,1.699)]
    tube('Eight-sided stained ash spear haft',parent,path,[(.016,.016),(.019,.019),(.019,.019),
        (.019,.019),(.018,.018),(.016,.016),(.013,.013)],m['ash'],8,across=(1,0,0),smooth=False)
    for z,r,length in ((.073,.020,.112),(1.611,.0185,.069),(1.684,.023,.089)):
        tube('Spun bronze on the heel or spear socket',parent,[pick(z+t*length) for t in (-.5,-.34,.33,.50)],
             [(r*.66,r*.66),(r,r),(r,r),(r*.72,r*.72)],m['bronze'],10,across=(1,0,0))
    for offset in (-.082,-.056,-.033,.002,.031,.068):
        z=grip.z+offset
        span('Leather lashing at the hand grip',pick(z-.008),pick(z+.008),.0195,m['hide'],parent,8,.0195)
    z0=1.680
    x0,y0,_=pick(z0)
    cross_sections=((.012,.014,.009),(.068,.029,.013),(.121,.046,.018),(.188,.029,.012),(.270,.0005,.0005))
    rows=[[(x0+dx,y0+dy,z0+h) for dx,dy in ((-w,0),(0,-d),(w,0),(0,d))] for h,w,d in cross_sections]
    blade=volume('Leaf-shaped spearhead, hammered steel on its bronze socket',rows,m['iron edge'],parent)
    blade.data.materials.append(m['iron'])
    for face in list(blade.data.polygons)[1:-1]:
        face.material_index=int((face.index-1)%4 in (1,2))


def boss(name,parent,place,m,r):
    rows=[]
    for k,d in ((1.20,.004),(1.18,.011),(1.01,.016),(.87,.029),(.54,.046),(.23,.055)):
        rows.append([place(cos(e)*r*k,sin(e)*r*k,d) for e in angle_span(0,tau,10)[:-1]])
    obj=volume(name,rows,m['bronze'],parent)
    obj.data.materials.append(m['brass'])
    for face in obj.data.polygons:
        if (face.index-1)//10 in (0,2):
            face.material_index=1


def sun_shield(a,m):
    parent=a.part('LeftForearm')
    held=a.hand_point('Left')
    center=Vector((held.x+.028,held.y-.057,held.z-.046))
    tilt=Euler((-.113,.086,.086)).to_matrix()
    radius=.366
    curvature=.067
    sectors=16
    inverse=tilt.transposed()
    clearance=[]
    for point in a.hands['Left']:
        x,y,z=inverse@(point-center)
        r=(x*x+z*z)/(radius*radius)
        if r<.95:
            clearance.append(y+curvature*(1.-r))
    if clearance:
        center+=tilt@Vector((0.,min(0.,min(clearance)-.014),0.))
    def place(x,z,d):
        radial=(x*x+z*z)/(radius*radius)
        curved=-curvature*(1.-min(1.1,radial))
        return tuple(center+tilt@Vector((x,curved-d,z)))
    rim=[(.012,-.045),(.62,-.043),(.942,-.040),(1.008,-.025),(1.026,-.008),
         (1.013,.010),(.972,.017),(.927,.010),(.890,.001),(.70,0.),(.46,0.),(.20,0.),(.006,0.)]
    rows=[[place(r*radius*cos(t),r*radius*sin(t),d) for t in angle_span(0,tau,sectors)[:-1]] for r,d in rim]
    shield=volume('Hammered aspis with bevelled bronze rim and broad painted faces',rows,m['paint blue'],parent)
    for shade in (m['wood'],m['bronze'],m['brass'],m['gold dark']):
        shield.data.materials.append(shade)
    for face in shield.data.polygons:
        row=(face.index-1)//sectors
        face.material_index=1 if row<2 else 4 if row==2 else 2 if row in (3,4,6) else 3 if row in (5,7) else 0
    shield_wash(shield,center,inverse,radius,radius,True)
    paint_losses('Irregular drybrush along the inside of the bronze rim',parent,place,
                 [(-.241,.153,.033,.010,.24),(-.280,.118,.018,.005,.27),
                  (-.183,.213,.027,.009,-.18),(.092,.247,.026,.009,.49),
                  (.284,-.091,.024,.007,-.50),(.237,-.158,.043,.009,.57),
                  (.200,-.207,.023,.005,.72),(-.155,-.241,.025,.007,-.73),
                  (-.277,-.082,.018,.005,-.02)],
                 [m['scuffed turquoise'],m['verdigris']])
    for index in range(sectors):
        steps=((.09,.857),(.09,.808),(.83,.808),(.83,.860),(.34,.860),(.34,.831),(.64,.831))
        path=[]
        for share,extent in steps:
            q=(index+share)*tau/sectors
            r=radius*extent
            path.append(place(r*cos(q),r*sin(q),.0052))
        piping('Terracotta key pattern painted around the aspís',parent,path,.0024,m['hem red'],5)
    for index in range(8):
        phase=index*tau/8+.18
        def ray(extent,angle,depth):
            return place(radius*extent*cos(phase+angle),radius*extent*sin(phase+angle),depth)
        # A central hammer ridge runs through each ray. The polygon edges turn with the shield.
        long=index%2==0
        tip=.810 if long else .754
        sections=[(.144,-.060,.178,.004),(.30,-.079,.142,.012),
                  (.479,-.017,.106,.017),(.656,.090,.047,.013),(tip,.185,.002,.006)]
        if not long:
            sections[-2]=(.620,.076,.052,.012)
        vertices=[]
        for r,arc,width,lift in sections:
            vertices.extend((ray(r,arc-width,.003),ray(r,arc,lift),ray(r,arc+width,.003)))
        faces=[(i,i+3,i+4,i+1) for i in range(0,len(vertices)-3,3)]
        faces.extend((i+1,i+4,i+5,i+2) for i in range(0,len(vertices)-3,3))
        sun=mesh_object('Swept bronze ray chased into two faces',vertices,faces,m['brass'],parent)
        sun.data.materials.append(m['bronze'])
        for face in list(sun.data.polygons)[len(sections)-1:]:
            face.material_index=1
    boss('Domed raised sun at the hub of the aspis',parent,place,m,.067)
    for q in angle_span(0,tau,sectors)[:-1]:
        p=place(.358*cos(q),.358*sin(q),.021)
        obj=stone('Heat-darkened bronze pin in the shield rim',p,(.0048,.0041,.0048),m['brass'],parent,1)
        for f in obj.data.polygons:
            f.use_smooth=True
    for x in (-.106,.09):
        path=[place(x,-.113,-.056),place(x,-.059,-.136),place(x,.040,-.141),place(x,.110,-.054)]
        tube('Fitted leather hand strap underneath the aspis',parent,path,[(.015,.008)]*4,m['hide'],8,across=(1,0,0))


def eagle(parent,place,m):
    def mark(name,outline,pigment,depth,lift=.004):
        relief(name,parent,outline,lambda x,z,d:place(x,z,d+lift),pigment,m['gold dark'],depth,.09)
    for side in (-1,1):
        tips=((.214,.239),(.217,.179),(.205,.122),(.186,.067),(.162,.018))
        for i,(tipx,tipz) in reversed(list(enumerate(tips))):
            rootx=.045+.005*i
            rootz=.103-.029*i
            wing=[(rootx,rootz-.018),(rootx+.025,rootz+.024),(tipx-.040,tipz-.011),
                  (tipx,tipz),(tipx-.021,tipz-.042),(tipx-.055,tipz-.054),(rootx+.022,rootz-.027)]
            mark('Individual swept flight feather',[(side*x,z) for x,z in wing],
                 m['brass'] if i%2==0 else m['bronze'],.0044,.004+.0009*(4-i))
        leading=[(.035,.105),(.064,.151),(.116,.176),(.159,.214),(.200,.255),(.188,.208),
                 (.145,.161),(.108,.126),(.074,.088)]
        mark('Raised leading edge of the eagle wing',[(side*x,z) for x,z in leading],m['brass'],.006,.011)
        foot=[(.028,-.045),(.064,-.067),(.101,-.074),(.120,-.094),(.102,-.093),
              (.089,-.107),(.083,-.093),(.068,-.098),(.061,-.084),(.026,-.073)]
        mark('Talons curling back toward the tail',[(side*x,z) for x,z in foot],m['bronze'],.0033)
    tail=[(-.037,-.051),(.040,-.052),(.066,-.134),(.030,-.122),(.002,-.161),(-.024,-.126),(-.067,-.139)]
    mark('Fan of tail feathers',tail,m['brass'],.0055)
    body=[(-.032,.152),(-.046,.188),(-.029,.222),(.014,.239),(.061,.217),(.051,.196),(.019,.204),
          (.007,.169),(.035,.142),(.064,.095),(.055,.001),(.032,-.081),(-.006,-.095),(-.041,-.072),
          (-.059,.004),(-.057,.080)]
    mark('Hooked head and breast of the eagle',body,m['bronze'],.005,.010)
    facets=[(-.033,.137),(-.004,.165),(.030,.124),(.050,.064),(.029,-.048),(-.004,-.072),(-.034,-.045),(-.048,.049)]
    points=[place(x,z,.017) for x,z in facets]
    points.append(place(-.008,.056,.033))
    eagle_breast=mesh_object('Raised ridge through the chest of the eagle',points,
                            [(i,len(facets),(i+1)%len(facets)) for i in range(len(facets))],m['brass'],parent)
    eagle_breast.data.materials.append(m['bronze'])
    for index in (2,3,4):
        eagle_breast.data.polygons[index].material_index=1
    stone('Eye sunk into the bronze head of the eagle',place(.021,.218,.019),(.0042,.0019,.0042),m['gold dark'],parent,1)


def scutum(a,m):
    parent=a.part('LeftForearm')
    grip=a.hand_point('Left')
    top=grip.z+.003
    bottom=.018
    height=(top-bottom)*.5
    center=Vector((grip.x+.003,grip.y+.038,(top+bottom)*.5))
    tilt=Euler((-.087,.041,-.105)).to_matrix()
    width=.270
    def place(x,z,d):
        curve=.090*abs(x)+.101*max(0.,abs(x)-.110)
        return tuple(center+tilt@Vector((x,curve-d,z)))
    corner=.042
    extent=width-.039
    lower=[(x,-height) for x in (-extent,-.110,0.,.110,extent)]
    upper=[(x,height) for x,_ in reversed(lower)]
    outline=[*lower,(width,-height+corner),(width,height-corner),
             *upper,(-width,height-corner),(-width,-height+corner)]
    rings=[[place(x*k,z*k,d) for x,z in outline] for k,d in ((.985,-.047),(1.,-.041),(1.009,-.011),(.992,.001))]
    count=len(outline)
    sides=[(row*count+i,row*count+(i+1)%count,(row+1)*count+(i+1)%count,(row+1)*count+i)
           for row in range(len(rings)-1) for i in range(count)]
    base=mesh_object('Chamfered frame around Marcus’s curved scutum',
                     [point for ring in rings for point in ring],sides,m['wood'],parent)
    base.data.materials.append(m['gold dark'])
    for face in base.data.polygons:
        face.material_index=int(face.index//count>=1)
    near_corner=corner/(height*2)
    levels=[0,near_corner,.18,.37,.60,.83,1.-near_corner,1.]
    def panels(u,t,scale,depth):
        z=height*(2*t-1)
        bevel=max(0.,(abs(z)-height+corner)/corner)
        x=(width-.039*bevel)*(2*u-1)
        return place(x*scale,z*scale,depth)
    painted_hide=strips('Crimson hide over five broad faces of the scutum',parent,
                        [0,.09,.277,.5,.723,.91,1.],levels,
                        lambda u,t:panels(u,t,.992,.0028),[m['paint red']],smooth=False)
    shield_wash(painted_hide,center,tilt.transposed(),width,height,False)
    paint_losses('Short worn brush strokes in the madder pigment around the eagle',parent,place,
                 [(-.182,.410,.037,.007,.58),(-.207,.386,.022,.007,.41),
                  (-.176,.373,.034,.004,.69),(.166,.384,.022,.004,-.66),
                  (.209,.329,.015,.008,-.68),(.214,-.216,.017,.009,.41),
                  (-.183,-.310,.037,.007,.73),(-.209,-.339,.024,.009,.70),
                  (.172,-.390,.039,.006,.48),(.204,-.424,.014,.007,-.41)],
                 [m['faded madder'],m['screened oxblood']])
    piping('Rolled bronze frame following the clipped corners of the scutum',parent,
           [place(x,z,.001) for x,z in [*outline,outline[0]]],.0109,m['bronze'],8)
    piping('Thin reflected highlight on the inside of the rim',parent,
           [place(x*.964,z*.978,.0047) for x,z in [*outline,outline[0]]],.0032,m['brass'],6)
    for side in (-1,1):
        for z in (-.434,-.272,-.10,.093,.26,.438):
            p=place(side*(width-.011),z,.008)
            stone('Bronze nail holding the red covering',p,(.0044,.0027,.0044),m['brass'],parent,1)
    def emblem(x,z,d):
        return place(x*.91,z*.91-.021,d)
    eagle(parent,emblem,m)
    seams=[0,.164,.169,.274,.332,.337,.5,.663,.668,.726,.831,.836,1.]
    def boards(u,t):
        if .164<u<.169 or .332<u<.337 or .663<u<.668 or .831<u<.836:
            return 2
        return 1 if .337<u<.663 else 0
    strips('Bent timber slats visible on the inside of the shield',parent,seams,levels,
           lambda u,t:panels(u,t,.985,-.047),[m['wood'],m['hide edge'],m['hide dark']],boards,smooth=False,reverse=True)
    brace=[(-.157,-.027),(.147,-.029),(.163,-.011),(.147,.023),(-.139,.024),(-.160,.008)]
    relief('Small carved wooden crosspiece under the handle',parent,brace,
           lambda x,z,d:place(x,z,-.048-d),m['hide edge'],m['hide dark'],.016,.13)
    center_handle=[place(-.075,-.018,-.055),place(-.040,-.011,-.097),
                   place(.044,.002,-.097),place(.075,.016,-.055)]
    tube('Leather-covered grip joined to the scutum crosspiece',parent,center_handle,
         [(.020,.009)]*4,m['hide dark'],7,across=(0.,0.,1.),smooth=False)


def gladius(a,m):
    parent=a.part('Body')
    hip=a.joint('pelvis')
    top=hip+Vector((-.185,-.073,.037))
    end=top+Vector((-.142,-.059,-.397))
    axis=(top-end).normalized()
    path=[end.lerp(top,i) for i in (0,.042,.16,.46,.82,.98,1.)]
    tube('Tapered leather sheath shaped to the wedge-cut blade',parent,path,
         [(.007,.003),(.021,.010),(.035,.013),(.039,.015),(.039,.016),(.041,.016),(.036,.015)],
         m['hide dark'],8,across=(1,0,0),smooth=False)
    for dx in (-.027,.027):
        route=[tuple(end.lerp(top,h)+Vector((dx,-.014,0))) for h in (.18,.33,.67,.83)]
        piping('Raised waxed seam on the scabbard front',parent,route,.0021,m['hide edge'],5)
    for t in (.074,.86,.98):
        point=end.lerp(top,t)
        tube('Bronze collar around the scabbard',parent,[point+axis*s for s in (-.013,-.010,.012,.014)],
             [(.030,.012),(.035,.016),(.035,.016),(.030,.012)],m['bronze'],8,across=(1,0,0))
    tube('Proud bronze guard and handle core',parent,[top+axis*t for t in (0,.016,.026,.085,.112)],
         [(.045,.027),(.049,.029),(.020,.020),(.024,.021),(.019,.020)],m['bronze'],10,across=(1,0,0))
    for amount in (.033,.047,.059,.071,.083):
        mid=top+axis*amount
        span('Raised scabbard grip wrap',mid-axis*.005,mid+axis*.005,.022,m['hide edge'],parent,8,.021)
    pommel=stone('Spherical worn bronze pommel',top+axis*.117,(.027,.025,.026),m['brass'],parent,2)
    for face in pommel.data.polygons:
        face.use_smooth=True
    path=[top+Vector((.020,-.001,.020)),top+Vector((.012,-.015,-.032)),top+Vector((-.030,-.002,-.072))]
    tube('Loop on the belt securing the scabbard',parent,path,[(.014,.005)]*3,m['hide'],8,across=(1,0,0))


def equipment(a,m):
    if a.name=='thekla':
        thekla_spear(a,m)
        sun_shield(a,m)
    else:
        gladius(a,m)
        scutum(a,m)
