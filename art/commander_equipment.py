"""Thekla's sun shield and spear, and Marcus's scutum and sheathed gladius."""
from math import cos, pi, sin, tau

from mathutils import Euler, Vector

from commander_forms import angle_span, piping, relief, strips, tube
from geometry import mesh_object, span, stone, volume


def thekla_spear(a,m):
    parent=a.part('RightHand')
    grip=a.hand_point('Right',.073)
    x,y=grip.x-.021,grip.y-.011
    def pick(z):
        return x+.060*(1.29-z),y+.018*(1.29-z),z
    path=[pick(z) for z in (.026,.059,.501,1.013,1.408,1.76,1.967)]
    tube('Tapered oiled ash spear haft',parent,path,[(.014,.014),(.015,.015),(.015,.015),
        (.016,.016),(.015,.015),(.013,.013),(.012,.012)],m['wood'],12,across=(1,0,0))
    for z,r,length in ((.073,.016,.103),(1.876,.015,.056),(1.944,.021,.072)):
        tube('Spun bronze on the heel or spear socket',parent,[pick(z+t*length) for t in (-.5,-.34,.33,.50)],
             [(r*.66,r*.66),(r,r),(r,r),(r*.72,r*.72)],m['bronze'],10,across=(1,0,0))
    for offset in (-.080,-.056,-.033,.002,.031,.064):
        z=grip.z+offset
        span('Leather lashing at the hand grip',pick(z-.007),pick(z+.008),.016,m['hide'],parent,10,.016)
    z0=1.94
    x0,y0,_=pick(z0)
    plan=[(0,.267),(-.017,.204),(-.036,.105),(-.016,.051),(-.014,0),(.014,0),(.017,.047),(.035,.108),(.017,.201)]
    vertices=[(x0+u,y0,z0+h) for u,h in plan]
    front=len(vertices)
    vertices.extend([(x0,y0-.018,z0+.104),(x0,y0+.018,z0+.104)])
    faces=[(i,(i+1)%len(plan),front) for i in range(len(plan))]
    faces += [((i+1)%len(plan),i,front+1) for i in range(len(plan))]
    blade=mesh_object('Faceted forged spearhead whose bevel follows the leaf edge',vertices,faces,m['brass'],parent)
    blade.data.materials.append(m['bronze'])
    for p in blade.data.polygons:
        if (p.index+1)%3==0:
            p.material_index=1


def boss(name,parent,place,m,r):
    rows=[]
    for k,d in ((1.18,.0055),(1.13,.012),(1.03,.018),(.88,.026),(.66,.040),(.38,.048),(.02,.050)):
        rows.append([place(cos(e)*r*k,sin(e)*r*k,d) for e in angle_span(0,tau,24)[:-1]])
    obj=volume(name,rows,m['bronze'],parent,True)
    obj.data.materials.append(m['brass'])
    for face in obj.data.polygons:
        if (face.index-1)//24 in (0,2):
            face.material_index=1


def sun_shield(a,m):
    parent=a.part('LeftForearm')
    held=a.hand_point('Left')
    center=Vector((held.x+.028,held.y-.057,held.z-.046))
    tilt=Euler((-.107,.087,-.335)).to_matrix()
    radius=.309
    inverse=tilt.transposed()
    clearance=[]
    for point in a.hands['Left']:
        x,y,z=inverse@(point-center)
        r=(x*x+z*z)/(radius*radius)
        if r<.95:
            clearance.append(y+.051*(1.-r))
    if clearance:
        center+=tilt@Vector((0.,min(0.,min(clearance)-.014),0.))
    def place(x,z,d):
        radial=(x*x+z*z)/(radius*radius)
        curved=-.051*(1.-min(1.1,radial))
        return tuple(center+tilt@Vector((x,curved-d,z)))
    rim=[(.012,-.044),(.62,-.042),(.947,-.038),(1.010,-.025),(1.025,-.007),
         (1.016,.006),(.975,.012),(.934,.009),(.903,.003),(.68,0.),(.34,0.),(.006,0.)]
    rows=[[place(r*radius*cos(t),r*radius*sin(t),d) for t in angle_span(0,tau,50)[:-1]] for r,d in rim]
    shield=volume('Single curved wooden aspis with a doubled cast bronze lip',rows,m['paint blue'],parent,True)
    for shade in (m['wood'],m['bronze'],m['brass'],m['gold dark']):
        shield.data.materials.append(shade)
    for face in shield.data.polygons:
        row=(face.index-1)//50
        face.material_index=1 if row<2 else 4 if row==2 else 2 if row in (3,4,6) else 3 if row in (5,7) else 0
    for n in range(8):
        phase=n*tau/8+.18
        ray=[(.054,-.116),(.102,-.10),(.149,-.147),(.205,-.113),(.271,-.002),(.230,-.054),
             (.182,.065),(.120,.085),(.074,.088)]
        outline=[(r*cos(phase+t),r*sin(phase+t)) for r,t in ray]
        relief('Hammered rays of Thekla’s sun seal',parent,outline,lambda x,z,d:place(x,z,d+.0025),
               m['brass'],m['bronze'],.0047,.052)
        line=[place(r*cos(phase+t),r*sin(phase+t),.006) for r,t in ((.077,-.006),(.136,-.043),(.196,-.023),(.24,-.006))]
        piping('Shallow engraved line on the curved ray',parent,line,.0015,m['bronze'],5)
    boss('Domed raised sun at the hub of the aspis',parent,place,m,.056)
    for q in angle_span(0,tau,18)[:-1]:
        p=place(.296*cos(q),.296*sin(q),.015)
        obj=stone('Heat-darkened bronze pin in the shield rim',p,(.0048,.0041,.0048),m['brass'],parent,1)
        for f in obj.data.polygons:
            f.use_smooth=True
    for x in (-.106,.09):
        path=[place(x,-.113,-.056),place(x,-.059,-.136),place(x,.040,-.141),place(x,.110,-.054)]
        tube('Fitted leather hand strap underneath the aspis',parent,path,[(.015,.008)]*4,m['hide'],8,across=(1,0,0))


def eagle(parent,place,m):
    def mark(name,outline,depth=.005):
        relief(name,parent,outline,lambda x,z,d:place(x,z,d+.004),m['brass'],m['bronze'],depth,.052)
    body=[(-.011,.096),(-.056,.158),(-.053,.201),(-.025,.235),(.025,.241),(.054,.225),(.053,.203),
          (.021,.212),(.003,.181),(.048,.135),(.071,.081),(.063,.018),(.044,-.068),(.075,-.145),
          (.030,-.128),(0.,-.166),(-.037,-.127),(-.071,-.145),(-.045,-.058),(-.066,-.010),(-.055,.066)]
    mark('Curved eagle body, hooked face and feathers on the scutum',body,.008)
    for side in (-1,1):
        shoulder=[(.027,.132),(.075,.165),(.121,.190),(.172,.235),(.208,.268),(.206,.218),(.181,.173),
                  (.153,.127),(.114,.071),(.072,.039),(.040,.048)]
        mark('Cast raised shoulder of the eagle wing',[(side*x,z) for x,z in shoulder],.0068)
        for i in range(6):
            startx=.041+.008*i
            startz=.087-.016*i
            tipx=.209-.012*i
            tipz=.179-.045*i
            wing=[(startx,startz-.007),(startx+.026,startz+.020),(tipx-.024,tipz-.004),
                  (tipx+.003,tipz+.013),(tipx-.009,tipz-.028),(tipx-.039,tipz-.043),(startx+.011,startz-.033)]
            mark('Separated brass flight feather in the eagle wing',[(side*x,z) for x,z in wing],.0063)
            piping('Engraved vane of a flight feather',parent,[place(side*(startx+.016),startz,.012),
                place(side*(tipx-.031),tipz-.006,.013)],.0013,m['gold dark'],5)
        for end in (-.022,0.,.027):
            claw=[place(side*.034,-.056,.010),place(side*.077,-.060,.012),
                  place(side*(.093+end),-.087,.009),place(side*(.081+end),-.096,.007)]
            piping('Clawed foot on the emblemed scutum face',parent,claw,.0035,m['brass'],6)
    for row in range(5):
        for col in (-1,0,1):
            x=col*.016+(row%2)*.003
            z=.103-.029*row
            line=[place(x-.007,z,.013),place(x,z-.010,.0145),place(x+.007,z,.013)]
            piping('Short scale seam cut into the metal eagle breast',parent,line,.0014,m['gold dark'],5)
    stone('Small dark eye on the emblemed eagle',place(.015,.221,.014),(.0031,.0016,.0031),m['gold dark'],parent,1)


def scutum(a,m):
    parent=a.part('LeftForearm')
    grip=a.hand_point('Left')
    top=grip.z+.003
    bottom=.018
    height=(top-bottom)*.5
    center=Vector((grip.x+.003,grip.y+.038,(top+bottom)*.5))
    tilt=Euler((-.087,.041,-.105)).to_matrix()
    width=.251
    def place(x,z,d):
        curve=.47*x*x
        return tuple(center+tilt@Vector((x,curve-d,z)))
    outline=[(-width+.041,-height),(width-.039,-height),(width-.012,-height+.015),
             (width,-height+.040),(width,height-.044),(width-.016,height-.019),(width-.042,height),
             (-width+.042,height),(-width+.014,height-.019),(-width,height-.045),
             (-width,-height+.041),(-width+.013,-height+.017)]
    rings=[[place(x*k,z*k,d) for x,z in outline] for k,d in ((.985,-.047),(1.,-.041),(1.009,-.011),(.992,.001))]
    base=volume('Steam formed timber core of Marcus’s long scutum',rings,m['wood'],parent,True)
    base.data.materials.append(m['gold dark'])
    for face in base.data.polygons:
        if (face.index-1)//len(outline) in (1,2):
            face.material_index=1
    def panels(u,t):
        z=height*(2*t-1)*.987
        x=width*.984*(2*u-1)*(1-.078*abs(2*t-1)**18)
        x+=.0013*sin(pi*t)*sin(23*u)
        return place(x,z,.0028)
    strips('Crimson painted hide fitted to the correctly curved wooden core',parent,[i/22 for i in range(23)],
           [i/30 for i in range(31)],panels,[m['paint red']],smooth=True)
    piping('Rolled brass frame following the tall round cornered face',parent,
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
    center_handle=[place(-.048,-.045,-.046),place(-.022,-.017,-.104),place(.040,.030,-.106),place(.072,.058,-.046)]
    tube('Fitted dark handle on the back of the scutum',parent,center_handle,[(.023,.009)]*4,m['hide'],8,across=(0,0,1))


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
