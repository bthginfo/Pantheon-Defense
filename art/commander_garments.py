"""Individual costume patterns, weighted cloth and articulated armour for the two heroes."""
from bisect import bisect_right
from math import atan2, cos, pi, sin, tau

from mathutils import Vector

from commander_forms import angle_span, piping, relief, stitched, strips, tube
from commander_paint import mantle_stamp
from geometry import stone, volume


class Torso:
    def __init__(self,a):
        self.greek=a.name=='thekla'
        self.bottom=a.joint('pelvis').z+.050
        self.top=a.joint('l-shoulder').z+(.058 if self.greek else .073)
        self.form=[(0.,.129,.095,-.014),(.19,.136,.095,-.014),(.48,.156,.114,-.008),
                   (.69,.172,.120,-.013),(.83,.183,.120,-.012),(.91,.185,.138,-.014),(1.,.085,.084,-.018)]
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
    color=m['linen'] if b.greek else m['red']
    neck=a.joint('neck')
    angles=[i/24 for i in range(25)]
    shoulder_width,shoulder_depth=(.183,.127) if b.greek else (.216,.139)
    shoulder_z=neck.z-(.008 if b.greek else .017)
    opening_width=.102 if b.greek else .112
    def bodice(u,t):
        q=tau*u+pi/2
        if t<=.90:
            return b.point(q,t,.003,.004)
        forward=max(0.,-sin(q))
        shoulder=Vector((shoulder_width*cos(q),neck.y-.014+shoulder_depth*sin(q),
                         shoulder_z-(.055 if b.greek else .044)*forward))
        if t<.95:
            return Vector(b.point(q,.90,.003,.004)).lerp(shoulder,(t-.90)/.05)
        rim=Vector((opening_width*cos(q),neck.y-.015+.101*sin(q),
                    neck.z-.007-(.045 if b.greek else .027)*forward**1.7))
        return shoulder.lerp(rim,(t-.95)/.05)
    strips('Bound neckline and fitted yoke' if b.greek else 'Wool yoke closed underneath the cloak',
           body,angles,[0,.10,.23,.38,.53,.66,.75,.83,.90,.95,.992,1.],bodice,
           [color,m['linen shadow'] if b.greek else m['red']],lambda u,t:int(t>.992),lining=.004)
    if b.greek:
        for index,(start,end,level) in enumerate((
            (-.124,.110,.235),(-.141,.129,.386),(-.150,.134,.548),(-.139,.125,.698),
        )):
            def fold(u,t):
                x=start+(end-start)*u
                center=level+.202*u+.025*sin(pi*u)
                width=(.106+.104*sin(pi*u))*(1.-.038*index)
                lift=(.002+.027*(1.-t)**1.4)*sin(pi*u)**.51
                return b.front(x,center+width*(t-.5),.009+lift)
            strips('Broad overlapping linen wrap across the cuirass',body,
                   [0,.12,.25,.43,.63,.82,.94,1.],[0,.15,.38,.82,1.],
                   fold,[m['linen'],m['linen light'],m['linen shadow']],
                   lambda u,v:2 if v<.10 else 1 if v<.26 and u<.84 else 0,lining=.004,smooth=False)
        harness=[(-.150,.094,.887,-.030,.026,.039),(.143,-.083,.914,-.033,.050,.051)]
        for start,end,high,low,width,lift in harness:
            def strap(u,t):
                x=start*(1.-u)+end*u+(t-.5)*width
                h=high*(1.-u)+low*u+.017*sin(pi*u)
                return b.front(x,h,.012+(lift-.012)*sin(pi*u)**.67)
            u=[i/14 for i in range(15)]
            strips('Leather harness cut and shaped to the linen folds',body,u,[0,.09,.91,1.],strap,
                   [m['hide'],m['hide edge']],lambda s,t:int(t<.09 or t>.91),lining=.004,smooth=False)
            stitched('Thread at the edge of the fitted leather strap',body,
                     [(x,y-.0017,z) for x,y,z in (strap(s,.15) for s in u)],.0016,m['hide edge'],17)


def weight_linen_hem(obj,waist):
    """Let each half of the linen wrap follow its thigh as the hips move."""
    body=obj.vertex_groups.new(name='Body')
    left=obj.vertex_groups.new(name='LeftLeg')
    right=obj.vertex_groups.new(name='RightLeg')
    for v in obj.data.vertices:
        x,_,z=v.co
        hanging=min(.40,max(0.,(waist-.065-z)*1.32))
        bias=min(1.,max(0.,.5+4.*x))
        body.add([v.index],1.-hanging,'REPLACE')
        left.add([v.index],hanging*bias,'REPLACE')
        right.add([v.index],hanging*(1.-bias),'REPLACE')


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
        if b.greek:
            return .012+x+.22*z,-.128-d,z+space-.015-.25*x
        return x,-.127-d,z+space-.018
    outline=[(-.047,-.029),(.035,-.028),(.053,-.008),(.041,.025),(-.033,.030),(-.052,.009)] if b.greek else [
             (-.046,-.022),(.034,-.024),(.052,-.009),(.038,.020),(-.037,.022),(-.051,.008)]
    relief('Bronze waist buckle with bevelled corners',body,outline,plaque,m['bronze'],m['brass'],.012,.19)
    relief('Recessed leather through the buckle',body,[(-.022,-.010),(.020,-.010),(.027,.008),(-.023,.009)],
           lambda x,z,d:plaque(x,z,d+.012),m['hide dark'],m['gold dark'],.006,.08)
    for sign in (-1,1):
        pin('Worn buckle pin',body,plaque(sign*.037,0,.012),.0061,m['brass'])
    hidden_hem=.257 if b.greek else .259
    skirt=[]
    for r in (0,.14,.30,.53,.73,.91,1.):
        spread=.092*r**.64+.030*sin(pi*r)**.76 if b.greek else .064*r
        depth=(.065*r**.68 if b.greek else .049*r)
        skirt.append([((waist+.006+spread)*cos(q)+.006*cos(q*12.),
                       -.006+(.101+depth)*sin(q)+.005*sin(q*12.)-
                       (.053*r**.80*max(0.,-sin(q))**.62*(1+.32*cos(q)) if b.greek else 0),
                       space-.037-hidden_hem*r+.010*r*sin(q*7.)) for q in angle_span(0,tau,36)[:-1]])
    underlayer=volume('Continuous underlayer closing the skirt between its split panels',skirt,
                      m['linen shadow'] if b.greek else m['red lining'],body,True)
    if b.greek:
        weight_linen_hem(underlayer,space)
    layers=((7,.239,.172,.310,m['linen shadow'],.34),(6,.258,.188,.266,m['linen'],.19)) if not split else (
        (9,.240,.154,.277,m['red lining'],.00),(10,.258,.179,.235,m['red'],.28),(10,.268,.195,.199,m['hide dark'],.12))
    for row,(count,spread,depth,length,paint,shift) in enumerate(layers):
        for i in range(count):
            angle=(i+shift)*tau/count-pi/2
            def hanging(u,t):
                w=(u-.5)*(tau/count)*(1.14+.10*sin(t*pi))
                sweep=(.112+.060*sin(i*2.11)) if not split else .035*sin(i*2.11)
                q=angle+w+sweep*t
                inner=waist+.005+row*.016
                growth=t**(.65 if b.greek else .83)
                outward=inner+(spread-inner)*growth
                if b.greek:
                    outward+=.017*sin(pi*t)**.84
                crest=max(0.,1.-1.9*abs(u-.38))
                ripple=(.013 if split else .023)*crest*sin(pi*.62*t)
                x=(outward+ripple)*cos(q)
                initial=.106+row*.016
                y=(initial+(depth-initial)*growth+ripple)*sin(q)-.006
                if not split:
                    y-=.058*t**.77*max(0.,-sin(q))**.64
                hem=(.012 if split else .018)*sin(.51+i*1.93)+(u-.45)*(.022 if split else .095)
                if not split:
                    hem+=.055*max(0.,-cos(q))-.041*max(0.,cos(q))
                return x,y,space-.037-(length+hem)*t
            edge=m['hide edge'] if split else m['weft']
            pigment=[paint,edge,m['hide dark'] if split else m['linen shadow']]
            lappet=strips('Cut and bevelled lappet of the split skirt',body,[0,.12,.38,.63,.89,1.],
                          [0,.23,.54,.82,.936,.975,1.],hanging,pigment,
                          lambda u,v:1 if .94<v<.975 else 2 if v>.975 else 0,
                          lining=.008 if split and row==2 else .004,smooth=False,reverse=True)
            if b.greek:
                weight_linen_hem(lappet,space)
            if row==len(layers)-1:
                if split:
                    x,y,z=hanging(.5,.926)
                    pin('Small cast stud on leather pteruge',body,(x,y+.005*sin(angle),z),.0056,m['brass'])
                elif sin(angle)<.12:
                    route=[]
                    for u in [j/9 for j in range(10)]:
                        x,y,z=hanging(u,.929)
                        route.append((x+.002*cos(angle),y+.003*sin(angle),z))
                    thread=stitched('Gold thread set into the layered skirt hem',body,route,.0019,m['weft'],10)
                    weight_linen_hem(thread,space)


def lorica(a,b,m):
    body=a.part('Body')
    colors=[m['iron'],m['iron edge'],m['dark iron']]
    angles=[0,.026,.113,.188,.25,.35,.43,.5,.57,.65,.75,.812,.887,.974,1.]
    for row in range(5):
        lower=.034+row*.154
        def bend(u,v):
            q=tau*u-pi/2
            centre=max(0.,1.-5.2*abs(cos(q)))
            profile=lower+.181*v
            z=b.z(profile)+.022*(1-abs(sin(q)))+.012*cos(q*2.)-.007*centre
            lip=(.009 if v==0. else .017)*(1.-v)
            x,y,_=b.point(q,profile,.017+lip+.006*centre)
            return x,y,z
        strips('Forged lorica plate with a bevel and raised chest ridge',body,angles,[0,.12,.24,.73,1.],
               bend,colors,lambda u,v:1 if v<.09 else 2 if v>.8 or .19<u<.34 or .70<u<.81 else 0,
               lining=.009,smooth=False)
        for side in (-1,1):
            x,y,z=b.front(side*(.054+.010*row),lower+.079,.039)
            def setting(dx,dz,raise_by):
                return x+dx,y-raise_by,z+dz
            relief('Bronze hinge with bevelled corners',body,[(-.026,-.008),(.024,-.009),(.031,.003),(.020,.012),(-.027,.010)],
                   setting,m['bronze'],m['gold dark'],.008,.15)
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
    columns=[0,.027,.10,.20,.29,.38,.50,.61,.70,.80,.90,.972,1.]
    rows=[0,.12,.29,.49,.67,.81,.902,.922,.951,.976,1.]
    folds=(0.,.16,.49,-.32,.78,.30,-.64,-.12,1.,-.26,.33,.49,.4)
    def cape(u,t):
        w=2*u-1
        width=(.122+.216*t+.076*t*t) if greek else (.211+.179*t+.039*t*t)
        turn=.028*sin(pi*t)*(1.-w*w)+.043*sin(t*pi*.86)*sin(tau*u)
        centre=(.139-.439*t**1.22) if greek else (-.091-.056*t-.076*t*t)
        x=w*width+centre+turn
        section=next(i for i,end in enumerate(columns[1:]) if u<=end)
        low,high=columns[section:section+2]
        blend=(u-low)/(high-low)
        opening=.017+.070*t+.014*sin(pi*t)*sin(tau*u)
        ridge=opening*(folds[section]*(1.-blend)+folds[section+1]*blend)
        y=.138+.057*t+.061*t*t+.052*t*(1-abs(w))+ridge
        y+=(.016 if greek else .046)*(1-.48*t)
        z=z0-(1.113 if greek else 1.093)*t+(.013+.094*t)*w-.070*w*w*t+(.048*cos(3*w)+ridge*.52)*t*t
        if greek:
            z+=.330*max(0.,-w)**2.2*t*t
        return x,y,z
    def pattern(u,t):
        band=(.904<t<.923 or .951<t<.976) if greek else .921<t<.976
        if band or u<.027 or u>.972:
            return 1
        return 2 if .61<u<.70 and .29<t<.82 else 0
    cloak_mesh=strips('Long mantle with four weighted folds and a woven border',parent,columns,rows,
                      cape,[main,edge,lighter,interior],pattern,lining=.007,smooth=False)
    mantle_stamp(cloak_mesh,columns,rows,greek)
    def fitted_hem(u,t):
        # Interpolate the actual broad cloth faces before placing the stitched pattern.
        i=min(len(columns)-2,bisect_right(columns,u)-1)
        j=min(len(rows)-2,bisect_right(rows,t)-1)
        left,right=columns[i:i+2]
        upper,lower=rows[j:j+2]
        across=(u-left)/(right-left)
        start=Vector(cape(left,upper)).lerp(Vector(cape(right,upper)),across)
        end=Vector(cape(left,lower)).lerp(Vector(cape(right,lower)),across)
        return start.lerp(end,(t-upper)/(lower-upper))
    path=[]
    for u in [i/34 for i in range(35)]:
        x,y,z=fitted_hem(u,.954)
        path.append((x,y+.006,z))
    stitched('Repeated colored thread in the large hem',parent,path,.003,m['weft'] if greek else m['red lining'],33)
    if greek:
        for index in range(13):
            left=.044+index*.071
            steps=((0,.928),(.052,.928),(.052,.950),(.017,.950),(.017,.936),(.034,.936))
            decor=[fitted_hem(left+offset,level) for offset,level in steps]
            for depth in (-.010,.0055):
                piping('Terracotta meander woven into the jade hem',parent,
                       [(x,y+depth,z) for x,y,z in decor],.0026,m['hem red'],5)
    def shawl(u,t):
        if greek:
            center=.126+.125*t**1.3
            width=.173+.021*t-.066*t*t
            z=z0-.007-.335*t+(u-.5)*(.108-.066*t)
            fold=(.014+.018*t)*max(0.,1.-3.6*abs(u-.36))
            y=-.139-.048*sin(pi*t)+.251*t*t-fold
            x=center+(u-.5)*width
        else:
            x=-.197+.406*u+.041*(t-.2)*sin(pi*u)
            z=z0-.027+.038*(2*u-1)**2-.034*u-(.089+.111*u)*t-.029*sin(pi*u)*sin(pi*t)
            fold=.050*max(0.,1.-3.8*abs(t-.27-.13*u))+.034*max(0.,1.-5.1*abs(t-.77+.08*u))
            y=-.168-.024*sin(pi*u)-fold-.005*t
        return x,y,z
    shawl_columns=[0,.028,.16,.31,.42,.60,.78,.938,.972,1.]
    shawl_rows=[0,.13,.28,.43,.56,.70,.81,.91,.943,.978,1.]
    shawl_mesh=strips('Broad diagonal folds gathered at the cloak clasp',parent,
                      shawl_columns,shawl_rows,shawl,[main,edge,lighter,interior],
                      pattern if greek else None,lining=.009,smooth=False,reverse=True)
    mantle_stamp(shawl_mesh,shawl_columns,shawl_rows,greek)
    pinned=shawl_mesh.vertex_groups.new(name='Body')
    pinned.add(list(range(len(shawl_mesh.data.vertices))),1.,'REPLACE')
    def bridge(u,t):
        if greek:
            p,q=Vector(shawl(u,0)),Vector(cape(.37+.46*u,0))
        else:
            p,q=Vector(shawl(.71+.29*u,0.)),Vector(cape(.69+.31*u,0.))
        loc=p.lerp(q,t)
        loc.z+=(.047 if greek else .038)*sin(pi*t)
        return tuple(loc)
    bridge_rows=[0,.23,.51,.77,1.]
    shoulder=strips('Wool gathered over the shoulder in heavy folds',parent,shawl_columns,bridge_rows,bridge,
                    [main],lining=.008,smooth=False)
    bound=shoulder.vertex_groups.new(name='Body')
    trailing=shoulder.vertex_groups.new(name='Mantle')
    for row,t in enumerate(bridge_rows):
        first=row*len(shawl_columns)
        vertices=list(range(first,first+len(shawl_columns)))
        bound.add(vertices,1.-t,'REPLACE')
        trailing.add(vertices,t,'REPLACE')
    x,y,z=shawl(.39 if greek else .092,.065)
    radius=.029 if greek else .025
    parent=a.part('Body')
    disk=[(radius*cos(q),radius*sin(q)) for q in angle_span(0,tau,10)[:-1]]
    relief('Cast bronze fibula pinning the cloak',parent,disk,lambda u,v,d:(x+u,y-.007-d,z+v),
           m['bronze'],m['brass'],.011,.18)
    pin('Hammered centre of the fibula',parent,(x,y-.021,z),radius*.42,m['brass'])


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
        broad=.074 if b.greek else .092
        ranks=[(-.030,broad*.58),(-.009,broad*.78),(.043,broad),(.083,broad*.92),(.111,broad*.83)]
        tube('Linen sleeve with a shaped hem' if b.greek else 'Wool sleeve showing below the armour',parent,
             [shoulder+axis*height for height,_ in ranks],[(r,r*.94) for _,r in ranks],
             m['linen'] if b.greek else m['red lining'],14,across=(0,1,0))
        piping('Visible folded edge of the sleeve',parent,[band(q,.105,broad*.845) for q in angle_span(0,tau,14)],.005,m['linen light'],6)
        rows=0 if b.greek and sign>0 else 3
        for i in range(rows):
            def plates(u,t):
                q=-3.49+3.96*u
                rib=max(0.,1.-2.1*abs(u-.50))
                size=(.042-.011*i) if b.greek else (.019-.003*i)
                radius=broad+size+.015*(1.-t)+.019*rib
                drift=-.051+i*.049
                along=drift+t*.069+.043*abs(2*u-1)**1.7+.030*t*rib
                return band(q,along,radius+(.009 if .13<t<.84 else 0.))
            strips('Tiered shoulder plate with a raised keel and bronze fasteners',parent,
                   [0,.10,.21,.38,.54,.71,.89,1.],[0,.144,.68,.851,.934,1.],plates,
                   [m['bronze'],m['brass'],m['gold dark']] if b.greek else [m['iron'],m['iron edge'],m['dark iron']],
                   lambda u,t:1 if .85<t<.94 else 2 if t<.12 or u>.895 else 0,
                   lining=.010 if b.greek else .012,smooth=False,reverse=sign<0)
            for u in (.24,.83):
                x,y,z=plates(u,.66)
                pin('Shoulder guard fastener',parent,(x+sign*.003,y+(.004 if u<.50 else -.004),z+.002),.0055,m['brass'])
            if b.greek:
                lip=[]
                for u in (.15,.27,.43,.60,.76,.88):
                    x,y,z=plates(u,.910)
                    lip.append((x-.002,y-.002,z+.002))
                piping('Bright struck lip along each bronze shoulder plate',parent,lip,.0029,m['brass'],5)


def limb_gear(a,b,m):
    for side,source,sign in (('Left','l',1),('Right','r',-1)):
        parent=a.part(side+'Forearm')
        elbow=a.joint(source+'-elbow')
        wrist=a.joint(source+'-hand')
        center=elbow.lerp(wrist,.79)
        direction=(wrist-elbow).normalized()
        width=.040 if b.greek else .050
        bracer=tube('Bevelled forearm cuff over leather',parent,
                    [center+direction*k for k in (-.072,-.063,-.036,.010,.024,.030)],
                    [(width*r,width*r*.94) for r in (1.02,1.18,1.10,.91,.87,.77)],m['hide'],9,across=(0,0,1),
                    smooth=False)
        bracer.data.materials.append(m['bronze'] if sign<0 or not b.greek else m['hide edge'])
        for face in bracer.data.polygons:
            if (face.index-1)//9 in (0,3):
                face.material_index=1
        start=a.joint(source+'-knee')
        foot=a.joint(source+'-ankle')
        parent=a.part(side+'Shin')
        lower=a.part(side+'Foot')
        if b.greek:
            def shin(u,t):
                q=(u-.5)*1.81
                p=foot.lerp(start,.078+t*.81)
                radius=(.043+.035*t+.006*sin(pi*t))
                p.x+=radius*sin(q)
                p.y-=(radius+.008)*cos(q)+.027*(1-abs(2*u-1))
                p.z+=.052*t**3*cos(q)**6-.018*(1-t)*cos(q)
                return tuple(p)
            cols=[0,.09,.28,.46,.53,.73,.91,1.]
            rows=[0,.055,.21,.51,.74,.898,.963,1.]
            strips('Bronze greave struck into a sharp central keel',parent,cols,rows,shin,
                   [m['bronze'],m['brass'],m['gold dark']],
                   lambda u,t:1 if .46<u<.53 or t>.96 else 2 if u<.10 or u>.91 else 0,lining=.009,smooth=False)
            def knee_plate(u,t,d):
                x,y,z=shin(u,t)
                return x,y-.003-d,z
            relief('Bevelled bronze panel below the knee',parent,
                   [(.51,.997),(.79,.891),(.75,.790),(.53,.687),(.28,.773),(.25,.884)],
                   knee_plate,m['bronze'],m['brass'],.008,.18)
            for t in (.18,.74):
                center=foot.lerp(start,.080+t*.807)
                rr=.049+.030*t
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
                       [(r,r*.92) for r in width],m['hide dark'],10,across=(1,0,0),smooth=False)
            shaft.data.materials.append(m['hide edge'])
            for face in shaft.data.polygons:
                if (face.index-1)//10 in (0,4):
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
    amounts=[(.008,.96),(.015,1.0),(.023,.98),(.029,.94)] if sandal else [(.005,.94),(.016,1.),(.032,1.),(.054,.90),(.079,.72),(.110,.52)]
    rings=[]
    for z,k in amounts:
        rings.append([tuple(Vector((rear.x,rear.y,z))+width*(w*k*(1 if sandal else 1.13))+
                            tangent*(length*((t-.35)*k+.35))) for w,t in sole])
    shoe=volume('Stitched calfskin sandal sole' if sandal else 'Bevelled boot toe joined to the shaft',
                rings,m['hide'] if sandal else m['hide dark'],parent,sandal)
    if not sandal:
        shoe.data.materials.append(m['hide'])
        for face in list(shoe.data.polygons)[1:len(sole)+1]:
            face.material_index=1
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
