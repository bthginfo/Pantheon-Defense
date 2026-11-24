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
    for t in (0,.19,.43,.66,.86,.97,1.):
        row=[]
        for q in angle_span(0,tau,28)[:-1]:
            at_front=max(0.,-sin(q))
            low=height-(.068 if female else .045)+at_front*(.169 if female else .134)
            z=low+(height+.142-low)*sin(t*pi/2)
            factor=max(.013,cos(t*pi/2))
            row.append((cos(q)*(.089 if female else .094)*factor,
                        -.034+sin(q)*.100*factor,z))
        rows.append(row)
    volume('Hair cap beneath the crown and side locks',rows,m['hair'],head,True)
    if female:
        for level,(count,ring_height,radius) in enumerate(((13,-.014,.092),(11,-.043,.089),(10,-.064,.081))):
            for i in range(count):
                q=-.40+(pi+.78)*(i+.12*(level%2))/(count-1)
                radial=Vector((cos(q),sin(q),0.))
                tangential=Vector((-sin(q),cos(q),0.))
                width=radius+rng.uniform(-.005,.007)
                origin=Vector((0,-.037,height+ring_height+rng.uniform(-.010,.007)))+radial*width
                curl=1 if i%4!=0 else -1
                path=[origin+radial*r+tangential*(flow*curl)+Vector((0,0,z))
                      for r,flow,z in ((-.017,-.010,.027),(.006,-.015,.015),(.020,.000,-.003),
                                       (.013,.017,-.014),(-.004,.019,-.006),(-.008,.012,.001))]
                lock=tube('Hand-shaped faceted curl sweeping around the temple',head,path,
                          [(.005,.005),(.014,.012),(.017,.014),(.015,.010),(.008,.006),(.002,.002)],
                          m['hair warmth'] if (i+level)%5==0 else m['hair'],6,across=radial,smooth=False)
                for face in lock.data.polygons:
                    face.use_smooth=(face.index-1)//6 in (1,2,3)
        return
    for strand in range(14):
        theta=strand*tau/14
        facing=max(0.,-sin(theta))
        if facing>.44:
            continue
        radial=.081
        low=height-.028+rng.uniform(-.017,.013)
        depth=.085+rng.uniform(0,.008)
        path=[]
        for t in (0,.26,.54,.77,1.):
            tilt=theta+.31*t+.21*sin(t*pi*1.35)
            bulge=.009*sin(t*pi)
            x=cos(tilt)*(radial+bulge)
            y=-.033+sin(tilt)*(depth+.85*bulge)
            z=low+.038*(1.-t)+.010*sin(t*pi*1.7)
            path.append((x,y,z))
        shapes=[(.003,.002),(.009,.005),(.010,.005),(.006,.004),(.0017,.0015)]
        tube('Close-cropped side lock',head,path,shapes,
             m['hair warmth'] if strand%7==3 else m['hair'],6,across=(cos(theta),sin(theta),.23),smooth=False)


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
            z=eye.z-.067-.017*t**1.35+.003*sin(pi*t)
            depth=a.face_depth(x,z)
            if depth is not None:
                points.append((x,depth-.0027,z))
        if len(points)>4:
            tube('Combed grey edged moustache',head,points,
                 [(.0022+.0016*sin(i*pi/(len(points)-1)),.0023) for i in range(len(points))],
                 m['beard'],6,across=(0.,0.,1.))
    for i in range(19):
        u=(i+.5)/19
        path=[]
        start=.20+.06*(i%5)
        for row in (start,.51,.69,.859,.963):
            x,y,z=cover(u+.027*(u-.5)*row,row)
            path.append((x,y-.0012,z+.0013))
        tube('Short angular locks in the beard',head,path,
             [(.001,.0012),(.0026,.0015),(.0035,.0018),(.0027,.0016),(.0008,.0007)],
             m['grey hair'] if i%5 in (0,1) and .27<u<.73 else m['hair warmth'],5,across=(1,0,.1),smooth=False)


def helmet(a,m):
    head=a.part('Head')
    eye=a.joint('l-eye')
    greek=a.name=='thekla'
    rx,ry=(.103,.121) if greek else (.112,.135)
    cy=-.037 if greek else -.060
    top=eye.z+(.127 if greek else .144)
    cols=angle_span(-pi/2,3*pi/2,16)[:-1]
    levels=(0.,.11,.38,.65,.86,1.)
    def crown(q,t):
        facing=-sin(q)
        lower=eye.z+.030+.025*facing-.022*abs(cos(q))
        rise=(sin(t*pi/2))**(1.17 if greek else 1.03)
        width=max(.035,cos(t*pi/2))*(1+.043*sin(3*pi*t))
        ridge=max(0.,1.-3.0*abs(cos(q)))*max(0.,facing)
        prow=(.018 if greek else .007)*ridge*(1.-t)
        return rx*width*cos(q),cy+ry*width*sin(q)-prow,lower+(top-lower)*rise
    rows=[[crown(q,t) for q in cols] for t in levels]
    shell=volume('Forged helmet crown with hand-set planes',rows,m['bronze'] if greek else m['dark iron'],head)
    shell.data.materials.append(m['gold dark'] if greek else m['iron'])
    for face in list(shell.data.polygons)[1:-1]:
        row,sector=divmod(face.index-1,len(cols))
        if row==0 or (not greek and sector in (15,0) and 1<=row<=3):
            face.material_index=1
    rim=[crown(q,0.) for q in [*cols,cols[0]+tau]]
    tube('Narrow folded edge around the helmet',head,rim,[(.0037,.0037)]*len(rim),m['bronze'],6,
         across=(0,0,1),smooth=False)
    band_cols=[i/8 for i in range(9)]
    def brow(u,v):
        q=pi+pi*u
        x,y,z=crown(q,0.)
        beak=max(0.,1.-3.2*abs(2*u-1))
        lip=.021+.017*beak if greek else .020
        return x*1.025,y-.0043-.007*sin(pi*u)+.005*v,z+lip*v-(.032 if greek else .006)*beak
    strips('Angular brow with a central peak and a bevel',head,band_cols,[0,.25,.80,1.],brow,
               [m['bronze'],m['brass'],m['gold dark']],lambda u,v:1 if v<.20 else 2 if v>.85 else 0,
           lining=.003,smooth=False)
    for side in (-1,1):
        def placing(x,z,depth):
            y=-.073-.77*(.088-abs(x))
            return side*x,y-depth,eye.z+z
        if greek:
            outline=[(.067,.060),(.100,.050),(.111,.010),(.103,-.047),(.074,-.062),(.066,-.040),(.079,-.009)]
        else:
            outline=[(.075,.049),(.110,.050),(.120,.017),(.114,-.044),(.094,-.075),(.078,-.052),(.089,-.025),(.075,-.004)]
        relief('Bevelled metal cheek guard',head,outline,placing,m['bronze'] if greek else m['iron'],
               m['gold dark'] if greek else m['bronze'],.008,.15)
        inset=[(.083,.035),(.094,.036),(.100,.006),(.095,-.035),(.079,-.047),(.086,-.005)] if greek else [
               (.085,.036),(.105,.039),(.108,.011),(.101,-.044),(.093,-.054),(.090,-.009)]
        relief('Folded ridge descending to the tip of the cheek guard',head,inset,
               lambda x,z,d:placing(x,z,d+.007),m['brass'] if greek else m['iron edge'],m['bronze'],.0026,.11)
        for dx,dz in ((.087,.026),(.091,-.019)):
            stone('Forged temple rivet',placing(dx,dz,.012),(.0045,.0025,.0045),m['brass'],head,1)
    if greek:
        low=[(-.135,top-.029),(-.080,top-.001),(-.029,top+.006),(.024,top-.003),(.108,top-.046)]
        high=[(-.108,top+.036),(-.058,top+.081),(.011,top+.113),(.088,top+.121),(.180,top+.080)]
        crest(head,low,high,.025,m['teal'],m['teal light'],m['bronze'],False)
    else:
        low=[(-.119,top-.032),(-.065,top-.005),(0.,top+.004),(.065,top-.002),(.117,top-.024)]
        high=[(-.184,top+.030),(-.102,top+.087),(-.021,top+.109),(.077,top+.103),(.175,top+.053)]
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
        thick=side*width*(.53+.47*sin(t*pi))*(.79+.21*sin(u*pi))
        ridged=.0047*sin(47*u+1.5*t)
        if across:
            return x,-.055+thick+ridged,z
        return thick+ridged,x,z
    u=[0,.068,.143,.226,.31,.395,.49,.58,.672,.762,.85,.927,1.]
    rows=[0,.29,.69,1.]
    front_side=-1 if across else 1
    for side in (-1,1):
        strips('Dyed horsehair in thick swept planes',head,u,rows,lambda x,z:sample(x,z,side),
                [dark,light],lambda x,z:int((.27<x<.36 or .60<x<.75) and z>.42),
                lining=.001,smooth=False,reverse=side!=front_side)
    for v in (0,1):
        reverse=bool(v)!=across
        strips('Thick edge of the fitted horsehair crest',head,u,[0,1],lambda x,t:sample(x,v,2*t-1),
               [dark],smooth=False,reverse=reverse)
        strips('Cut end of the horsehair crest',head,[0,1],rows,lambda x,t:sample(v,t,2*x-1),
               [dark],smooth=False,reverse=reverse)
    piping('Metal saddle joining the crest to the helmet bowl',head,
           [sample(t,0.,0.) for t in u],.009 if across else .005,metal,6)


def portrait(a,m):
    eyes(a,m)
    hair(a,m)
    if a.name=='marcus':
        beard(a,m)
    helmet(a,m)
