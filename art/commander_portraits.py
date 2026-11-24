"""Two portraits with sculpted eyes, hair locks and separate fitted helmet patterns."""
from math import cos, pi, sin, tau
from random import Random

from mathutils import Vector

from commander_forms import angle_span, piping, relief, strips, tube
from geometry import mesh_object, stone, volume


def eyes(a,m):
    head=a.part('Head')
    for side in ('l','r'):
        eye=a.joint(side+'-eye')
        # The iris is a shallow dome at the front of the actual eyeball.
        radius=.0133 if a.name=='thekla' else .0128
        center=eye+Vector((0,-.0007,.0001))
        y=Vector((.092 if a.name=='thekla' else .052,-1,.019)).normalized()
        x=Vector((1.,0.,0.))
        z=y.cross(x).normalized()
        x=z.cross(y).normalized()
        ring=[(0.00,-radius),(.66,-radius*.75),(1.,0.),(.82,radius*.57),(.43,radius*.905),(.19,radius*.98),(.013,radius*1.01)]
        rows=[[(center+x*(radius*p*cos(q))+z*(radius*p*sin(q))+y*d) for q in (i*tau/20 for i in range(20))] for p,d in ring]
        obj=volume('Ivory eye with fitted iris and pupil',rows,m['white'],head,True)
        obj.data.materials.append(m['iris'])
        obj.data.materials.append(m['pupil'])
        for poly in obj.data.polygons:
            section=(poly.index-1)//20
            if section==4:
                poly.material_index=1
            elif section>=5:
                poly.material_index=2
        sign=1 if side=='l' else -1
        points=[]
        for i in range(8):
            t=i/7
            sx=sign*(.012+t*.051)
            sz=eye.z+.015+.009*sin(t*pi)+(.002 if a.name=='thekla' else -.003)*t
            depth=a.face_depth(sx,sz)
            if depth is not None:
                points.append((sx,depth-.0019,sz))
        if len(points)>2:
            radii=[(.0011+.00125*sin(pi*i/(len(points)-1)),.00104) for i in range(len(points))]
            tube('Swept brows, tapered at the temples',head,points,radii,m['hair'],7,across=(0,0,1))


def hair(a,m):
    head=a.part('Head')
    height=a.joint('head').z
    female=a.name=='thekla'
    rng=Random(a.name+' hair assembly')
    # Fitted cap underneath broad hand-directed locks.
    rows=[]
    for t in (0,.15,.32,.53,.72,.88,.96,1.):
        row=[]
        for q in angle_span(0,tau,28)[:-1]:
            at_front=max(0.,-sin(q))
            low=height-.061+at_front*.146
            z=low+(height+.142-low)*sin(t*pi/2)
            factor=max(.013,cos(t*pi/2))
            row.append((cos(q)*(.089 if female else .094)*factor,
                        -.034+sin(q)*.100*factor,z))
        rows.append(row)
    volume('Hair cap beneath the crown and side locks',rows,m['hair'],head,True)
    for strand in range(26 if female else 16):
        theta=(strand/(26 if female else 16))*tau
        facing=max(0.,-sin(theta))
        if facing>.44:
            continue
        radial=.081+(.004 if not female else rng.uniform(-.003,.009))
        low=height-.048+rng.uniform(-.017,.019)
        depth=.087+rng.uniform(0,.010)
        trail=.086 if female else .046
        path=[]
        for t in (0,.2,.47,.70,.88,1.):
            tilt=theta+.40*t+.16*sin(t*pi*1.4)
            x=cos(tilt)*(radial+.009*sin(t*pi))
            y=-.033+sin(tilt)*(depth+.006*sin(t*pi))
            z=low+trail*(1.-t)+.010*sin(t*pi*1.7)
            path.append((x,y,z))
        shapes=[(.003,.003),(.012,.009),(.016,.012),(.013,.011),(.011,.009),(.003,.002)] if female else [(.003,.002),(.010,.006),(.012,.006),(.011,.005),(.008,.004),(.002,.002)]
        tube('Sculpted dark curl' if female else 'Close-cropped side lock',head,path,shapes,
             m['hair warmth'] if strand%7==3 else m['hair'],7,across=(cos(theta),sin(theta),.23))
    if female:
        for sign in (-1,1):
            for i in range(4):
                x=sign*(.064+.006*i)
                y=-.094+.010*i
                z=height+.012-.006*i
                path=[(x-sign*.011,y+.016,z+.020),(x-sign*.010,y-.004,z+.009),(x-sign*.011,y-.011,z-.006),
                      (x-sign*.001,y-.010,z-.022),(x+sign*.002,y-.008,z-.010)]
                tube('Curl falling against temple',head,path,[(.005,.004),(.012,.008),(.012,.008),(.009,.007),(.002,.002)],
                     m['hair warmth'] if i==2 else m['hair'],8,across=(.52,.22,.54))


def beard(a,m):
    head=a.part('Head')
    eye=a.joint('l-eye')
    jaw=a.joint('head').z-.099
    cols=[i/24 for i in range(25)]
    rows=[i/12 for i in range(13)]
    def cover(u,t):
        x=(2*u-1)*.086
        upper=eye.z-.094+.098*abs(2*u-1)**2.05-.003*sin(u*17)
        lower=jaw+.054*abs(2*u-1)**1.76-.013*cos((2*u-1)*pi/2)
        z=upper*(1-t)+lower*t
        depth=a.face_depth(x,min(upper,max(jaw+.004,z)))
        if depth is None:
            depth=-.066+.043*abs(2*u-1)**1.2
        lift=.0008+.0088*sin(t*pi*.78)*cos((2*u-1)*pi/2)
        ripple=.0022*sin(u*87+t*2.8)*sin(pi*t)
        return x,depth-lift+ripple,z
    strips('Full beard formed over cheeks, jaw and chin',head,cols,rows,cover,
           [m['beard'],m['hair'],m['hair warmth']],lambda u,t: 2 if .52<t<.85 and (int(20*u)%7 in (2,3)) else 0,
           lining=.004)
    for side in (-1,1):
        points=[]
        for i in range(10):
            t=i/9
            x=side*(.005+t*.033)
            z=eye.z-.063-.023*t**1.4+.004*sin(pi*t)
            depth=a.face_depth(x,z)
            if depth is not None:
                points.append((x,depth-.005,z))
        if len(points)>4:
            tube('Combed grey edged moustache',head,points,
                 [(.0031+.0017*sin(i*pi/(len(points)-1)),.0036) for i in range(len(points))],
                 m['beard'],8,across=(0.,0.,1.))
    for i in range(36):
        u=(i+.5)/36
        path=[]
        start=.20+.06*(i%5)
        for row in (start,.51,.69,.859,.963):
            x,y,z=cover(u+.027*(u-.5)*row,row)
            path.append((x,y-.0021,z+.0013))
        tube('Broken silver and dark beard locks under the chin',head,path,
             [(.001,.0012),(.002,.0015),(.0027,.0018),(.0021,.0016),(.0008,.0007)],
             m['grey hair'] if i%5 in (0,1) and .27<u<.73 else m['hair warmth'],5,across=(1,0,.1))


def helmet(a,m):
    head=a.part('Head')
    eye=a.joint('l-eye')
    greek=a.name=='thekla'
    rx,ry=(.093,.113) if greek else (.109,.135)
    cy=-.037 if greek else -.060
    top=eye.z+(.127 if greek else .144)
    cols=angle_span(0,tau,40)[:-1]
    levels=(0.,.066,.16,.29,.47,.66,.84,.95,.994)
    def crown(q,t):
        facing=-sin(q)
        lower=eye.z+.029+.027*facing-.018*abs(cos(q))
        rise=sin(t*pi/2)
        width=cos(t*pi/2)*(1+.046*sin(3*pi*t))
        return (rx*width*cos(q),cy+ry*width*sin(q),lower+(top-lower)*rise)
    rows=[[crown(q,t) for q in cols] for t in levels]
    shell=volume('Raised curved helmet bowl, forged from one form',rows,m['bronze'] if greek else m['dark iron'],head,True)
    shell.data.materials.append(m['gold dark'])
    for face in list(shell.data.polygons)[1:len(cols)+1]:
        face.material_index=1
    piping('Rolled and hammered rim of the open face helmet',head,[crown(q,0) for q in [*cols,0]],.0042,m['brass'],8)
    band_cols=[i/24 for i in range(25)]
    def brow(u,v):
        q=pi+pi*u
        x,y,z=crown(q,0.)
        return x*1.011,y-.003,z+.011*v+.005*sin(pi*u)
    strips('Raised forehead band with engraved outer lip',head,band_cols,[0,.20,.80,1.],brow,
           [m['bronze'],m['brass'],m['gold dark']],lambda u,v:1 if v<.19 or v>.83 else 0,lining=.0025)
    for side in (-1,1):
        def placing(x,z,depth):
            y=-.068-.73*(.088-abs(x))
            return side*x,y-depth,eye.z+z
        if greek:
            outline=[(.065,.046),(.088,.048),(.096,.013),(.092,-.031),(.079,-.048),(.069,-.031),(.073,-.013)]
        else:
            outline=[(.069,.044),(.105,.042),(.110,.011),(.107,-.038),(.090,-.068),(.082,-.058),(.083,-.032),(.073,-.007)]
        relief('Shaped cheek guard with a rolled lower fold',head,outline,placing,m['bronze'],m['gold dark'],.006,.09)
        for dx,dz in ((.087,.027),(.089,-.010),(.087,-.027)):
            rivet=stone('Small forged temple fitting',placing(dx,dz,.008),(.0047,.0025,.0047),m['brass'],head,2)
            for face in rivet.data.polygons:
                face.use_smooth=True
    if greek:
        low=[(-.127,top-.019),(-.090,top+.004),(-.034,top+.010),(.025,top+.000),(.072,top-.028)]
        high=[(-.114,top+.033),(-.054,top+.076),(-.001,top+.075),(.068,top+.041),(.130,top+.009)]
        crest(head,low,high,.024,m['teal'],m['teal light'],m['bronze'],False)
    else:
        low=[(-.109,top-.023),(-.061,top+.001),(0.,top+.004),(.061,top+.000),(.109,top-.025)]
        high=[(-.156,top+.031),(-.091,top+.083),(-.012,top+.106),(.069,top+.101),(.149,top+.050)]
        crest(head,low,high,.034,m['red'],m['red fold'],m['bronze'],True)


def crest(head,low,high,width,dark,light,metal,across):
    def axis(u,controls):
        pos=u*(len(controls)-1)
        index=min(len(controls)-2,int(pos))
        a,b=controls[index],controls[index+1]
        t=pos-index
        p=controls[max(0,index-1)]
        q=controls[min(len(controls)-1,index+2)]
        return tuple(.5*((2*A)+(-P+B)*t+(2*P-5*A+4*B-Q)*t*t+(-P+3*A-3*B+Q)*t*t*t)
                     for A,B,P,Q in zip(a,b,p,q))
    def sample(u,t,side):
        x0,z0=axis(u,low)
        x1,z1=axis(u,high)
        x=x0+(x1-x0)*t
        z=z0+(z1-z0)*t
        thick=side*width*(.69+.31*sin(t*pi))*(.85+.15*sin(u*pi))
        ridged=.0016*sin(85*u+3*t)
        if across:
            return x,-.055+thick+ridged,z
        return thick+ridged,x,z
    u=[i/32 for i in range(33)]
    rows=[0,.18,.37,.61,.83,1.]
    for side in (-1,1):
        strips('Dyed horsehair, broad sweeps and narrow ridges',head,u,rows,lambda x,z:sample(x,z,side),
                [dark,light],lambda x,z:int((int(32*x)+3)%11 in (0,1) and z>.22), lining=.001)
    for v in (0,1):
        strips('Thick edge of the fitted horsehair crest',head,u,[0,1],lambda x,t:sample(x,v,2*t-1),[dark],lining=.001)
        strips('Finished ends of the horsehair crest',head,[0,1],rows,lambda x,t:sample(v,t,2*x-1),[dark],lining=.001)
    piping('Metal saddle joining the crest to the helmet bowl',head,[sample(t,.009,0.) for t in u],.011 if across else .008,metal,8)


def portrait(a,m):
    eyes(a,m)
    hair(a,m)
    if a.name=='marcus':
        beard(a,m)
    helmet(a,m)
