"""Folded cloth, chased shield metal and role-specific regalia in the humanoid models."""
from math import cos, pi, sin, tau

from forge import empty, material
from geometry import bevel_block as block, mesh_object, shell, span, stone, torus_mesh

# This is the robe construction and cloth badge for each of the 24 hero silhouettes.
REGALIA = {
    "thekla": ("captain", "laurel"), "ilios": ("oracle", "sun"), "melia": ("oracle", "leaf"),
    "harmonia": ("standard", "flower"), "astra": ("oracle", "star"), "nikandros": ("veteran", "bolt"),
    "thalassa": ("guard", "wave"), "daedalon": ("smith", "wing"),
    "marcus": ("captain", "wing"), "livia": ("augur", "torch"), "aurelia": ("guard", "sun"),
    "severus": ("veteran", "bolt"), "octavia": ("standard", "star"), "cassia": ("augur", "leaf"),
    "remus": ("scout", "wing"), "vindex": ("guard", "moon"),
    "akari": ("shrine", "wave"), "raiden": ("guard", "bolt"), "tomoe": ("shrine", "moon"),
    "sayo": ("augur", "torch"), "kaito": ("scout", "wave"), "hana": ("oracle", "flower"),
    "orochi": ("guard", "wave"), "riku": ("veteran", "sun"),
}

def silk_hem(name, parent, wide, length, side, cloth, rim, back, fold=.24):
    """Shape drapery in a single seam so the cloth follows its bone from every view."""
    xs=(-1.,-.928,-.76,-.54,-.275,-.02,.26,.539,.755,.928,1.)
    ys=(0,.09,.22,.40,.60,.77,.89,.956,1.0)
    def sample(u,t):
        pleat=sin(8.31*u+1.63*t)+.53*sin(16.82*u-1.6*t)
        tube=(.015+.076*t)*(1-.42*abs(u))*pleat
        width=wide*(.735+.27*t+.136*t*t)
        return (side*.081+u*width+side*.156*t*t,
                .069+fold*t**1.66+tube+.097*t*abs(u)**2,
                -length*t+ (.067*cos(u*4.7)+side*.052*u)*t*t)
    points=[sample(u,t) for t in ys for u in xs]
    faces=[]
    for row in range(len(ys)-1):
        for col in range(len(xs)-1):
            a=row*len(xs)+col
            b=a+len(xs)
            if row in (0,7) or col in (0,9):
                faces.append((a,a+1,b+1,b))
            else:
                faces.extend(((a,a+1,b),(a+1,b+1,b)) if (row+col)%2 else ((a,a+1,b+1),(a,b+1,b)))
    cloth_obj=mesh_object(name,points,faces,None,parent)
    for paint in (cloth,rim,back):
        cloth_obj.data.materials.append(paint)
    for poly in cloth_obj.data.polygons:
        min_u=min(xs[i%len(xs)] for i in poly.vertices)
        max_u=max(xs[i%len(xs)] for i in poly.vertices)
        min_t=min(ys[i//len(xs)] for i in poly.vertices)
        poly.material_index=1 if min_u>=.928 or max_u<=-.928 or min_t>=.956 else 0
    lining=cloth_obj.modifiers.new("Tailored lining and wool edge","SOLIDIFY")
    lining.thickness=.022
    lining.material_offset=2
    return sample


def embroidery(parent,sample,style,metal,offset):
    if style in ("wing","leaf","laurel","wave"):
        for side in (-1,1):
            for i in range(5):
                center=side*(.125+.166*i)
                a=.709+.021*(i%2)
                uvd=[(-.065,-.018),(.001,-.048),(.060,-.015),(.071,.035),(.01,.043),(-.042,.011)]
                point=[]
                for u,t in uvd:
                    x,y,z=sample(center+side*u,a+t+u*.49)
                    point.append((x,y+offset,z))
                mesh_object("Chased leaf embroidered into the cloak",point,[(0,1,2,3,4,5)],metal,parent)
    else:
        for side in (-1,1):
            center=side*.52
            points=[]
            for i in range(12):
                a=i*tau/12
                reach=1.0 if i%2==0 else .49
                x,y,z=sample(center+.153*reach*cos(a),.745+.088*reach*sin(a))
                points.append((x,y+offset,z))
            mesh_object("Woven six-petal cloak badge",points,[tuple(range(12))],metal,parent)


def cape(actor, parent, width, materials):
    ident=actor["id"]
    cut,picture=REGALIA.get(ident,("field","leaf"))
    length={
        "captain":.886,"veteran":.773,"guard":.692,"shrine":.684,
        "scout":.462,"oracle":.861,"augur":.794,"smith":.469,"standard":.705,"field":.551,
    }[cut]
    side = -1 if actor["theme"]=="japan" or ident=="marcus" else 1
    split = cut in ("scout","shrine","oracle")
    contrast=materials["gold"] if actor["theme"]!="japan" else materials["fabric"]
    if split:
        for i in (-1,1):
            strip=empty("Split back textile",(i*width*.265,0,.007),parent)
            strip.rotation_euler.y=i*.125
            sample=silk_hem("Independent folded back ribbon",strip,width*.57,length*(.97+i*.04),
                            i,materials["accent"],contrast,materials["hem"],.31)
            if actor["kind"]=="hero":
                embroidery(strip,sample,picture,contrast,.027)
    else:
        factor=1.05 if cut=="captain" else .92
        rim=material("Muted cinnabar within the gold hem","a46151",0) if ident=="thekla" else contrast
        sample=silk_hem("Broad layered mantle on the shoulders",parent,width*factor,length,
                        side,materials["accent"],rim,materials["hem"],.226)
        if actor["kind"]=="hero":
            embroidery(parent,sample,picture,contrast,.027)


def scutum(parent, m, hero, crest):
    height=.465 if hero else .443
    width=.275 if hero else .250
    outline=[(-width+.046,-height),(width-.046,-height),(width,-height+.06),
             (width,height-.055),(width-.05,height+.009),(-width+.05,height+.009),
             (-width,height-.054),(-width,-height+.06)]
    curve=lambda x: -.117+.57*x*x
    rings=[[(x*factor,curve(x*factor)+y,z*factor) for x,z in outline]
          for y,factor in ((.088,.966),(.053,1.02),(.019,1.015),(0.,.988))]
    # The section is in the X/Z plane. The same outline gives a real curved shield edge.
    points=[v for row in rings for v in row]
    n=len(outline)
    faces=[tuple(range(n-1,-1,-1))]
    for i in range(3):
        for k in range(n):
            j=(k+1)%n
            faces.append((i*n+k,i*n+j,(i+1)*n+j,(i+1)*n+k))
    center=len(points)
    points.append((0.,curve(0.),0.))
    for i in range(n):
        faces.append((3*n+i,3*n+(i+1)%n,center))
    mesh=mesh_object("Cupped leather-and-wood scutum",points,faces,None,parent)
    for mat in (m["belt"],m["gold"],m["accent"]):
        mesh.data.materials.append(mat)
    for poly in mesh.data.polygons:
        poly.material_index=2 if poly.index>3*n else 1 if (poly.index>n) else 0
    for a,b in zip(outline,outline[1:]+outline[:1]):
        span("Raised polished scutum edging",(a[0],curve(a[0])-.005,a[1]),
             (b[0],curve(b[0])-.005,b[1]),.018 if hero else .014,m["fillet"],parent,6)
    for side in (-1,1):
        for z in (-height+.064,height-.064):
            x=side*(width-.042)
            stone("Corner fastener", (x,curve(x)-.021,z),(.018,.012,.019),m["fillet"],parent,1)
    if crest=="wing":
        def brass_badge(name,outline):
            mesh=mesh_object(name,[(x,curve(x)-.026,z) for x,z in outline],
                             [tuple(range(len(outline)))],m["fillet"],parent)
            mesh.modifiers.new("Embossed brass thickness","SOLIDIFY").thickness=.012

        wing=[(.035,.035),(.079,.082),(.109,.176),(.108,.250),(.147,.327),(.188,.363),
              (.172,.300),(.228,.331),(.202,.248),(.244,.276),(.223,.188),(.241,.209),
              (.224,.136),(.190,.094),(.159,.072),(.108,.038),(.077,.020)]
        tail=[(-.062,-.062),(.062,-.062),(.104,-.143),(.100,-.224),(.041,-.206),
              (0,-.259),(-.039,-.202),(-.103,-.226),(-.104,-.147)]
        eagle=[(-.028,.027),(-.037,.109),(-.028,.159),(.008,.190),(.055,.181),
               (.069,.143),(.039,.148),(.020,.127),(.031,.044)]
        scale=1.0 if hero else .76
        for side in (-1,1):
            brass_badge("Raised serrated wing on the eagle badge",[(side*x*scale,z*scale) for x,z in wing])
            if hero:
                for i in range(3):
                    x=side*(.141+.023*i)
                    z=.244-.056*i
                    span("Incised feather shaft",(x*.77,curve(x*.77)-.037,z-.079),
                         (x,curve(x)-.040,z),.007,m["gold"],parent,5,.003)
        for label,outline in (("Beaked head of the eagle badge",eagle),("Split tail of the eagle badge",tail)):
            brass_badge(label,[(x*scale,z*scale) for x,z in outline])
    return curve(0)


def polished_sun_disc(parent,m,hero):
    reach=.284 if hero else .245
    n=14 if hero else 9
    for i in range(n):
        a=i*tau/n
        verts=[(.111*cos(a-.088),-.084,.111*sin(a-.088)),
               (.184*cos(a-.078),-.081,.184*sin(a-.078)),
               (reach*cos(a+.055),-.055,reach*sin(a+.055)),
               (.190*cos(a+.138),-.078,.190*sin(a+.138)),
               (.114*cos(a+.087),-.084,.114*sin(a+.087))]
        piece=mesh_object("Hammered bronze rays on curved shield",verts,[(0,1,2,3,4)],m["fillet"],parent)
        piece.modifiers.new("Raised hammered thickness","SOLIDIFY").thickness=.012
        if hero:
            offset=a+.138
            stone("Pin on the sun-disc rim",(.313*cos(offset),-.048,.313*sin(offset)),
                  (.011,.009,.011),m["gold"],parent,1)
    torus_mesh("Braided brass center border",(0,-.083,0),.136,.012,m["gold"],parent,18,5,True)


def harness(actor,body,m,width):
    """Silhouette cues identify heavy guards, scouts, support, and elite gear from above."""
    kind=actor["model"]["weapon"]
    hero=actor["kind"]=="hero"
    motion=actor["model"]["shape"]
    race=actor["theme"]
    if kind in ("bow","javelin"):
        span("Visible cross-back harness",(-.182*width,-.134,.402),(.138*width,-.213,.066),
             .019,m["belt"],body,7,.025)
        span("Rawhide seam on quiver strap",(-.188*width,-.154,.396),(.13*width,-.231,.063),
             .009,m["fillet"],body,6,.009)
        small_bins=3 if hero else 2
    elif kind in ("staff","fan","banner"):
        small_bins=2
        for i in range(3 if hero else 2):
            x=(i-1)*.069
            z=.290-.042*abs(i-1)
            span("Laced pendant seed",(x,-.215,z+.049),(x,-.232,z-.093),.012,m["gold"],body,6,.007)
            stone("Jewel on the casting harness",(x,-.234,z-.078),(.025,.019,.032),m["accent"],body,1)
    elif kind in ("hammer","sword","glaive","spear"):
        small_bins=1
        for side in (-1,1):
            for i in range(3 if hero else 2):
                z=.107+.072*i
                x=side*.169*width
                stone("Chest-band bronze rivet",(x,-.198+abs(x)*.08,z),
                      (.016,.012,.015),m["fillet"],body,1)
        if motion in ("titan","bulwark","regent"):
            padding=empty("Overlapping battle plate on one hip",(width*.230,.024,-.144),body)
            padding.rotation_euler.z=.594
            for i in range(2 if hero else 1):
                plate=block("Visible shaped tasset",(.024,-.02,-.05-i*.091),(.163,.078,.17),
                            m["dark iron"] if race!="aegean" else m["gold"],padding,.022)
                plate.rotation_euler.x=-.31
    else:
        small_bins=3
    for i in range(small_bins):
        x=width*(-.22+.105*(i%2))
        y=.147 if i<2 else .192
        z=-.178+.051*i
        shell("Tied belt bag or scroll case",[(z-.093,.048,.042,x,y),(z-.066,.071,.060,x,y),
                (z+.032,.065,.055,x,y),(z+.073,.045,.043,x,y)],
              m["leather"] if i%2==0 else m["accent"],body,8,True)
        torus_mesh("Laced strap on belt pouch",(x,y,z+.037),.051,.013,m["belt"],body,12,5)
