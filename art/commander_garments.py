"""Individual costume patterns, weighted cloth and articulated armour for the two heroes."""
from math import atan2, cos, pi, sin, tau

from mathutils import Vector

from commander_forms import angle_span, piping, relief, stitched, strips, tube
from geometry import stone, volume


class Torso:
    def __init__(self,a):
        self.greek=a.name=='thekla'
        self.bottom=a.joint('pelvis').z+.050
        self.top=a.joint('l-shoulder').z+(.058 if self.greek else .073)
        self.form=[(0.,.129,.095,-.014),(.19,.136,.095,-.014),(.48,.156,.114,-.008),
                   (.69,.172,.119,-.013),(.83,.184,.101,-.009),(.91,.151,.093,-.009),(1.,.077,.071,-.018)]
        if not self.greek:
            self.form=[(0.,.187,.124,-.002),(.19,.191,.121,-.001),(.48,.205,.131,-.003),
                       (.69,.225,.140,-.010),(.83,.233,.137,-.013),(.91,.190,.111,-.011),(1.,.084,.088,-.020)]

    def z(self,t):
        return self.bottom+t*(self.top-self.bottom)

    def point(self,q,t,offset=0.,fold=0.):
        u=max(0.,min(1.,t))
        for low,high in zip(self.form,self.form[1:]):
            if low[0]<=u<=high[0]:
                w=(u-low[0])/(high[0]-low[0])
                rx,ry,cy=(a+(b-a)*w for a,b in zip(low[1:],high[1:]))
                break
        x=cos(q)
        y=sin(q)
        radius=offset+fold*sin(11*q+.28*t)*sin(pi*u)
        front=max(-y,0.)
        chest=(.015 if self.greek else .010)*front**3*sin(pi*max(0.,1-abs(t-.65)/.33))**2
        return ((rx+radius)*x,cy+(ry+radius)*y-chest,self.z(t))

    def front(self,x,t,lift=.005):
        rx=self.point(0,t)[0]
        proportion=max(-.985,min(.985,x/rx))
        angle=-pi/2+atan2(proportion,(1.-proportion*proportion)**.5)
        _,y,z=self.point(angle,t)
        return x,y-lift,z


def pin(name,parent,p,r,mat):
    obj=stone(name,p,(r,r*.42,r),mat,parent,1)
    for face in obj.data.polygons:
        face.use_smooth=True
    return obj


def fitted_tunic(a,b,m):
    body=a.part('Body')
    color=m['linen'] if b.greek else m['red lining']
    rings=[[b.point(q,t,.002,.006) for q in angle_span(-pi/2,3*pi/2,32)[:-1]]
           for t in (0,.075,.17,.26,.36,.46,.59,.66,.75,.83,.88,.94,1.)]
    volume('Fitted pleated linen bodice' if b.greek else 'Folded wool under the lorica',rings,color,body,True)
    neck=a.joint('neck')
    def collar(u,t):
        q=tau*u-pi/2
        width=(.091 if b.greek else .100)-.021*t
        depth=(.094 if b.greek else .107)-.020*t
        return width*cos(q),neck.y-.009+depth*sin(q),neck.z-.058+.065*t-.008*max(0.,-sin(q))
    strips('Rolled fabric neckline following the neck into the shoulder',body,[i/28 for i in range(29)],
           [0,.21,.53,.80,1.],collar,[color,m['linen light'] if b.greek else m['red']],
           lambda u,t:int(t>.76),lining=.003)
    if b.greek:
        for i in range(3):
            def fold(u,t):
                x=-.139+.270*u
                h=.47+.074*i+.17*u+.046*sin(pi*u)
                p=b.front(x,h+.014*(2*t-1),.008+(.0025+sin(pi*t)*.004)*sin(pi*u))
                return p
            strips('Diagonal linen folds laid over the bust',body,[i/12 for i in range(13)],[0,.22,.56,1],fold,
                    [m['linen'],m['linen light'],m['linen shadow']],lambda u,v:1 if .28<v<.55 else 2 if v>.82 else 0,
                    lining=.003)
        for start,end,thick in ((-.145,.111,.023),(.153,-.069,.018)):
            path=[b.front(start*(1-u)+end*u,.90-.64*u,.021+.005*sin(pi*u)) for u in [i/16 for i in range(17)]]
            tube('Leather harness following the shape of the tunic',body,path,[(thick/2,.0028)]*len(path),m['hide'],8,across=(1,0,.18))
            stitched('Visible stitched edge along the chest strap',body,[(x-.003,y-.003,z) for x,y,z in path],.0017,m['hide edge'],19)
        clasp=b.front(.028,.466,.032)
        pin('Cast button joining the cross-straps',body,clasp,.016,m['brass'])


def belt_and_skirt(a,b,m):
    body=a.part('Body')
    split=not b.greek
    space=b.bottom-.006
    waist=b.form[0][1]
    girdle=[[(cos(q)*(waist+dx),sin(q)*(.102+dx)-.006,z) for q in angle_span(0,tau,32)[:-1]]
            for z,dx in ((space-.046,.002),(space-.042,.013),(space-.003,.018),(space+.010,.007),(space+.014,.001))]
    band=volume('Broad tapered stitched waist belt',girdle,m['hide'],body,True)
    band.data.materials.append(m['hide edge'])
    for face in band.data.polygons:
        if face.index//32 in (0,3):
            face.material_index=1
    def plaque(x,z,d):
        return x,-.127-d,z+space-.018
    outline=[(-.046,-.022),(.034,-.024),(.052,-.009),(.038,.020),(-.037,.022),(-.051,.008)]
    relief('Bronze waist buckle with bevelled corners',body,outline,plaque,m['bronze'],m['brass'],.010,.17)
    relief('Recessed leather through the buckle',body,[(-.022,-.010),(.020,-.010),(.027,.008),(-.023,.009)],
           lambda x,z,d:plaque(x,z,d+.012),m['hide dark'],m['gold dark'],.006,.08)
    for sign in (-1,1):
        pin('Worn buckle pin',body,plaque(sign*.037,0,.012),.0061,m['brass'])
    hidden_hem=.212 if b.greek else .259
    skirt=[]
    for r in (0,.14,.30,.53,.73,.91,1.):
        skirt.append([((waist+.006+.064*r)*cos(q)+.006*cos(q*12.),
                       -.006+(.099+.049*r)*sin(q)+.005*sin(q*12.)-
                       (.030*r*max(0.,-sin(q))**.62*(1+.33*cos(q)) if b.greek else 0),
                       space-.037-hidden_hem*r+.010*r*sin(q*7.)) for q in angle_span(0,tau,36)[:-1]])
    volume('Continuous underlayer closing the skirt between its split panels',skirt,m['linen shadow'] if b.greek else m['red lining'],body,True)
    layers=((9,.216,.141,.238,m['linen shadow'],.27),(8,.230,.167,.200,m['linen'],.16)) if not split else (
        (9,.238,.152,.281,m['linen shadow'],.00),(10,.253,.172,.241,m['red'],.28),(10,.265,.193,.180,m['dark iron'],.12))
    for row,(count,spread,depth,length,paint,shift) in enumerate(layers):
        for i in range(count):
            angle=(i+shift)*tau/count-pi/2
            def hanging(u,t):
                w=(u-.5)*(tau/count)*(1.14+.10*sin(t*pi))
                q=angle+w+.035*t*sin(i*2.11)
                inner=waist+.005+row*.016
                outward=inner+(spread-inner)*t**.83
                ripple=(.007 if split else .014)*cos((u-.42)*pi*1.65)*sin(pi*.62*t)
                x=(outward+ripple)*cos(q)
                initial=.106+row*.016
                y=(initial+(depth-initial)*t+ripple)*sin(q)-.006
                if not split:
                    y-=.025*t*max(0.,-sin(q))**.64
                hem=(.013 if split else .026)*sin(.51+i*1.93)+(u-.45)*(.015 if split else .042)
                return x,y,space-.037-(length+hem)*t
            pigment=[paint,m['bronze'] if split and row==2 else m['weft'],m['hide dark'] if split else m['linen shadow']]
            strips('Overlapping lappet of the split skirt',body,[0,.13,.36,.64,.88,1.],
                   [0,.18,.40,.71,.87,.933,.978,1.],hanging,pigment,
                   lambda u,v:1 if .935<v<.978 else 2 if v>.978 else 0,lining=.008 if split and row==2 else .004)
            if row==len(layers)-1:
                if split:
                    x,y,z=hanging(.5,.926)
                    pin('Small cast stud on leather pteruge',body,(x,y+.005*sin(angle),z),.0056,m['brass'])
                elif sin(angle)<.12:
                    route=[]
                    for u in [j/9 for j in range(10)]:
                        x,y,z=hanging(u,.929)
                        route.append((x+.002*cos(angle),y+.003*sin(angle),z))
                    stitched('Gold thread set into the layered skirt hem',body,route,.0019,m['weft'],10)


def lorica(a,b,m):
    body=a.part('Body')
    colors=[m['iron'],m['iron edge'],m['dark iron']]
    angles=[i/36 for i in range(37)]
    for row in range(5):
        lower=.034+row*.154
        def bend(u,v):
            q=tau*u-pi/2
            profile=lower+.185*v
            z=b.z(profile)+.013*(1-abs(sin(q)))**1.3 + .004*cos(q*2.)
            x,y,_=b.point(q,profile,.017+.013*(1-v)+.004*sin(pi*v))
            return x,y,z
        strips('Overlapping curved hand-forged lorica band',body,angles,[0,.075,.17,.41,.78,.94,1.],
               bend,colors,lambda u,v:1 if .056<v<.15 else 2 if v>.9 else 0,lining=.008)
        for side in (-1,1):
            x,y,z=b.front(side*(.055+.011*row),lower+.086,.041)
            def setting(dx,dz,raise_by):
                return x+dx,y-raise_by,z+dz
            relief('Copper band clasp rolled around its rivets',body,[(-.029,-.007),(.026,-.009),(.033,.004),(.024,.012),(-.030,.010)],
                   setting,m['bronze'],m['gold dark'],.007,.12)
            for short in (-.020,.021):
                pin('Round copper rivet set into the clasp',body,setting(short,0,.008),.0053,m['brass'])


def cloak(a,b,m):
    parent=a.part('Mantle')
    greek=b.greek
    z0=b.top-.013
    main=m['teal'] if greek else m['red']
    edge=m['hem red'] if greek else m['bronze']
    lighter=m['teal light'] if greek else m['red fold']
    interior=m['teal lining'] if greek else m['red lining']
    side=1 if greek else -1
    def cape(u,t):
        w=2*u-1
        width=(.139+.183*t+.062*t*t) if greek else (.211+.161*t+.031*t*t)
        x=w*width+side*(.086+.024*t+.059*t*t)
        ridge=(.014+.044*t)*(sin(w*9.6+.7+t*1.4)+.36*cos(w*18.-.7+t*.9))
        y=.138+.044*t+.059*t*t+.052*t*(1-abs(w))+ridge
        y+=(.016 if greek else .046)*(1-.48*t)
        z=z0-(.936 if greek else 1.074)*t+(.012+.064*t)*w-.077*w*w*t+.073*cos(3*w)*t*t
        return x,y,z
    columns=[0,.028,.058,.115,.18,.27,.35,.42,.50,.59,.66,.74,.83,.883,.942,.972,1.]
    rows=[0,.07,.17,.29,.44,.59,.71,.82,.902,.929,.95,.979,1.]
    pattern=lambda u,t: 1 if .92<t<.979 or u<.028 or u>.972 else 2 if .56<t<.83 and .24<u<.36 else 0
    strips('Long shaped mantle with deep weighted folds and inset border',parent,columns,rows,
           cape,[main,edge,lighter,interior],pattern,lining=.007)
    path=[]
    for u in [i/34 for i in range(35)]:
        x,y,z=cape(u,.954)
        path.append((x,y+.004,z))
    stitched('Repeated colored thread in the large hem',parent,path,.003,m['hem blue'] if greek else m['red lining'],33)
    if greek:
        for index in range(17):
            left=.039+index*.054
            steps=((0,.943),(.038,.943),(.038,.965),(.014,.965),(.014,.952),(.028,.952))
            decor=[]
            for offset,level in steps:
                x,y,z=cape(left+offset,level)
                decor.append((x,y+.0039,z))
            piping('Dark meander woven into Thekla’s terracotta hem',parent,decor,.0018,m['hem blue'],5)
    def shawl(u,t):
        across=(u-.5)*(.146+.018*t)
        if greek:
            center=.118+.107*t**1.4
            z=z0-.009-.721*t+(u-.5)*.043
            y=-.128-.048*sin(pi*t)+.221*t*t+.014*cos(3*pi*u+t)
            x=center+across
        else:
            x=-.191+.402*u+.028*(t-.2)*sin(pi*u)
            z=z0-.021+.039*(2*u-1)**2-.044*u-(.084+.108*u)*t-.031*sin(pi*u)*sin(pi*t*.95)
            y=-.160-.026*sin(pi*u)-.025*sin(t*3*pi+.34*u)-.019*t
        return x,y,z
    shawl_columns=[0,.05,.14,.24,.36,.48,.60,.73,.86,.95,1.]
    face_pattern=pattern if greek else lambda u,t: 2 if .32<t<.47 else 0
    strips('Inscribed fold sweeping over the shoulder and across the cloak clasp',parent,
           shawl_columns,rows,shawl,[main,edge,lighter,interior],face_pattern,lining=.009)
    def bridge(u,t):
        if greek:
            p,q=Vector(shawl(u,0)),Vector(cape(.37+.46*u,0))
        else:
            p,q=Vector(shawl(.71+.29*u,0.)),Vector(cape(.69+.31*u,0.))
        loc=p.lerp(q,t)
        loc.z+=(.032 if greek else .039)*sin(pi*t)
        return tuple(loc)
    strips('Wool gathered over the shoulder in heavy folds',parent,shawl_columns,[0,.16,.34,.58,.81,1.],bridge,
           [main],lining=.008)
    x,y,z=shawl(.39 if greek else .092,.065)
    pin('Oversize cast fibula pinning the cloak at the front',a.part('Body'),(x,y-.012,z),.026,m['bronze'])
    pin('Scuffed bronze on the fibula face',a.part('Body'),(x,y-.023,z),.018,m['brass'])


def shoulder_armor(a,b,m):
    for side,source,sign in (('Left','l',1),('Right','r',-1)):
        parent=a.part(side+'Arm')
        shoulder=a.joint(source+'-shoulder')
        elbow=a.joint(source+'-elbow')
        axis=(elbow-shoulder).normalized()
        neck_edge=Vector((sign*.054,-.010,b.top-.031))
        shoulder_edge=shoulder+axis*.034
        middle=neck_edge.lerp(shoulder_edge,.66)+Vector((0,0,.006))
        tube('Sewn shoulder gusset filling the join below the arm guard',a.part('Body'),
             [neck_edge,middle,shoulder_edge],[(.045,.028),(.060,.041),(.055,.040)],
             m['linen'] if b.greek else m['red lining'],12,across=(0,1,0))
        across=Vector((0,-1,0))
        radial=(across-axis*axis.dot(across)).normalized()
        cross=axis.cross(radial).normalized()*sign
        def band(q,along,radius):
            return tuple(shoulder+axis*along+radial*(cos(q)*radius)+cross*(sin(q)*radius*.87))
        broad=.074 if b.greek else .090
        ranks=[(-.030,broad*.58),(-.009,broad*.78),(.043,broad),(.083,broad*.92),(.111,broad*.83)]
        tube('Linen sleeve with a shaped hem' if b.greek else 'Wool sleeve showing below the armour',parent,
             [shoulder+axis*height for height,_ in ranks],[(r,r*.94) for _,r in ranks],
             m['linen'] if b.greek else m['red lining'],14,across=(0,1,0))
        piping('Visible folded edge of the sleeve',parent,[band(q,.105,broad*.845) for q in angle_span(0,tau,14)],.005,m['linen light'],6)
        rows=2 if b.greek and sign<0 else 0 if b.greek else 3
        for i in range(rows):
            def plates(u,t):
                q=-.66+3.16*u
                radius=broad+.011+.005*(1-t)
                drift=-.042+i*.045
                z=drift+t*.059+.043*(1.-sin(pi*u))
                return band(q,z,radius+.007*sin(pi*t)*sin(pi*u))
            strips('Sculpted overlapping shoulder guard',parent,[i/14 for i in range(15)],[0,.07,.21,.52,.86,1.],plates,
                   [m['bronze'] if b.greek else m['dark iron'],m['brass'] if b.greek else m['iron edge'],m['gold dark']],
                   lambda u,t:1 if t>.86 else 0,lining=.010)
            for u in (.13,.72):
                x,y,z=plates(u,.66)
                pin('Shoulder guard fastener',parent,(x+sign*.003,y-.004,z+.001),.006,m['brass'])


def limb_gear(a,b,m):
    for side,source,sign in (('Left','l',1),('Right','r',-1)):
        parent=a.part(side+'Forearm')
        elbow=a.joint(source+'-elbow')
        wrist=a.joint(source+'-hand')
        center=elbow.lerp(wrist,.79)
        direction=(wrist-elbow).normalized()
        width=.040 if b.greek else .050
        bracer= tube('Shaped and wrapped wrist leather',parent,[center+direction*k for k in (-.049,-.043,-.023,.011,.026,.031)],
                    [(width*r,width*r*.94) for r in (1.02,1.15,1.07,.89,.88,.76)],m['hide'],13,across=(0,0,1))
        bracer.data.materials.append(m['bronze'] if sign<0 or not b.greek else m['hide edge'])
        for face in bracer.data.polygons:
            if (face.index-1)//13 in (0,3):
                face.material_index=1
        start=a.joint(source+'-knee')
        foot=a.joint(source+'-ankle')
        parent=a.part(side+'Shin')
        lower=a.part(side+'Foot')
        if b.greek:
            def shin(u,t):
                q=(u-.5)*1.81
                p=foot.lerp(start,.13+t*.69)
                radius=(.040+.025*t+.006*sin(pi*t))
                p.x+=radius*sin(q)
                p.y-=(radius+.009)*cos(q)+.009*(1-abs(2*u-1))
                p.z+=.035*t**3*cos(q)**4-.011*(1-t)*cos(q)
                return tuple(p)
            cols=[0,.09,.18,.29,.42,.50,.59,.72,.82,.91,1.]
            rows=[0,.043,.16,.34,.56,.75,.89,.96,1.]
            strips('Hand formed greave with the central bronze ridge',parent,cols,rows,shin,
                   [m['bronze'],m['brass'],m['gold dark']],lambda u,t:1 if .43<u<.58 or t>.96 else 2 if u<.10 or u>.91 else 0,
                   lining=.009)
            for t in (.18,.74):
                center=foot.lerp(start,.13+t*.68)
                rr=.048+.021*t
                for dz in (-.007,.008):
                    piping('Leather strap following the back of the greave',parent,
                           [(center.x+rr*cos(q),center.y+rr*sin(q),center.z+dz) for q in angle_span(0,pi,12)],.004,m['hide edge'],6)
            footwear(a,source,lower,m,True)
        else:
            footwear(a,source,lower,m,False)
            axis=(start-foot).normalized()
            heights=[.014,.038,.106,.189,.268,.294]
            width=[.046,.050,.054,.062,.066,.063]
            shaft=tube('Worn soft leather boot shaft with ankle crease',parent,[foot+axis*t for t in heights],
                       [(r,r*.92) for r in width],m['hide dark'],17,across=(1,0,0))
            shaft.data.materials.append(m['hide edge'])
            for face in shaft.data.polygons:
                if (face.index-1)//17 in (0,4):
                    face.material_index=1
            path=[]
            for i in range(12):
                p=foot+axis*(.017+i*.017)
                p.x+=(-1 if i%2 else 1)*.025
                p.y-=.054+i*.0009
                path.append(p)
                pin('Bronzed eyelet on boot leather',parent,p,.0047,m['bronze'])
            piping('Drawn crossed boot lacing',parent,path,.0024,m['hide edge'],6)


def footwear(a,source,parent,m,sandal):
    heel=a.joint(source+'-ankle')
    toes=a.joint(source+'-foot-2')
    tangent=Vector((toes.x-heel.x,toes.y-heel.y,0.)).normalized()
    width=Vector((-tangent.y,tangent.x,0.))
    front=Vector((toes.x,toes.y,.020))
    rear=Vector((heel.x,heel.y,.020))-tangent*.043
    length=(front-rear).length+.031
    sole=[(-.036,0.),(.035,.012),(.049,.169),(.045,.563),(.053,.777),(.039,.960),
          (.013,1.),(-.027,.989),(-.047,.893),(-.053,.745),(-.038,.50),(-.040,.188)]
    amounts=[(.008,.96),(.015,1.0),(.023,.98),(.029,.94)] if sandal else [(.005,.94),(.016,1.),(.029,1.),(.044,.93),(.078,.71),(.111,.50)]
    rings=[]
    for z,k in amounts:
        rings.append([tuple(Vector((rear.x,rear.y,z))+width*(w*k*(1 if sandal else 1.13))+
                            tangent*(length*((t-.35)*k+.35))) for w,t in sole])
    volume('Stitched calfskin sandal sole' if sandal else 'Rounded leather boot toe joined to the shaft',rings,m['hide'] if sandal else m['hide dark'],parent,True)
    if sandal:
        for center in (.37,.62,.82):
            path=[]
            for j in range(10):
                t=j/9
                p=rear+tangent*(length*(center+.12*(t-.5)))+width*((t-.5)*.100)
                p.z=.027+(.033+.020*(1-center))*sin(pi*t)**.44
                path.append(p)
            tube('Thin leather wrapping naturally across the foot',parent,path,[(.0072,.0034)]*len(path),m['hide edge'],7,across=tangent)


def costume(a,m):
    body=Torso(a)
    fitted_tunic(a,body,m)
    belt_and_skirt(a,body,m)
    if not body.greek:
        lorica(a,body,m)
    shoulder_armor(a,body,m)
    limb_gear(a,body,m)
    cloak(a,body,m)
