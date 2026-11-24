"""Sculpted faction figures. Colours, garments and insignia are set by character."""
from math import cos, pi, sin, tau
from random import Random

from mathutils import Vector

from forge import empty, material
from geometry import bevel_block as block, mesh_object, shell, silhouette, span, stone, torus_mesh, volume
from figure_detail import cape, harness, polished_sun_disc, scutum
from roster_portraits import sculpt_head
from commander_forms import relief, strips, tube

# Each entry selects a garment construction, headwear, textile colours, and personal crest.
WARDROBE = {
    "hoplite": ("linen","bronze","e9dcc2","276b70","sun"),
    "slinger": ("tunic","kerchief","daae83","976347","wave"),
    "toxotes": ("leather","braid","95a898","326b6f","leaf"),
    "agora": ("travel","cap","cd9b64","647c65","coin"),
    "oracle": ("robe","laurel","f0dfcc","706aa1","star"),
    "peltast": ("leather","bronze","e3ccb3","518086","wave"),
    "promachos": ("muscle","crest","b98560","863f35","torch"),
    "melanion": ("travel","hood","adad75","395944","leaf"),
    "keraunos": ("muscle","cap","ae7046","393d4b","bolt"),
    "selene_cult": ("robe","moon","ddd0df","535980","moon"),
    "bronze_giant": ("muscle","crest","c2a268","286462","sun"),
    "hippokamp": ("scale","crest","93aeaa","376969","wave"),
    "thekla": ("linen","corinthian","e8dfc5","30686f","sun"),
    "ilios": ("robe","solar","edc575","94524a","sun"),
    "melia": ("robe","braid","b6c6a7","3f725f","leaf"),
    "harmonia": ("travel","laurel","e6c6c1","9c607a","flower"),
    "astra": ("robe","moon","c8cad9","424b7f","star"),
    "nikandros": ("muscle","crest","cd945d","813c39","bolt"),
    "thalassa": ("scale","braid","adceca","306482","wave"),
    "daedalon": ("leather","cap","b6a28a","8c6045","wing"),
    "legionary": ("segments","galea","b6a49a","9c5045","wing"),
    "veles": ("tunic","hood","dbb592","7b4b4b","bolt"),
    "funditor": ("travel","kerchief","c9a587","7a584f","star"),
    "quaestor": ("robe","laurel","dec5aa","78465a","coin"),
    "signifer": ("segments","crest","b59270","812f39","wing"),
    "vesta": ("robe","veil","e6c6a0","864c57","torch"),
    "centurion": ("segments","crest","adb1aa","9a5242","wing"),
    "sagittarius": ("leather","galea","cdaf82","6a434c","star"),
    "fulgur": ("scale","galea","bd9c6c","7f4358","bolt"),
    "aquilifer": ("scale","solar","c8a86b","823744","wing"),
    "custos": ("segments","galea","969f9f","76363e","moon"),
    "ignifer": ("muscle","crest","c99e7c","813f3c","torch"),
    "marcus": ("segments","crest","ada7a0","8c3f42","wing"),
    "livia": ("robe","veil","eed9b7","8a5e76","torch"),
    "aurelia": ("scale","galea","c6b093","925847","sun"),
    "severus": ("segments","galea","a7a29e","573447","bolt"),
    "octavia": ("travel","braid","d1beac","6b4b68","star"),
    "cassia": ("scale","laurel","d3bf97","7d534b","leaf"),
    "remus": ("leather","hood","c0997f","6b4948","wing"),
    "vindex": ("muscle","crest","b7abad","632f44","moon"),
    "ashigaru": ("lamellar","hat","9aaea8","435d5a","leaf"),
    "yumi": ("kimono","braid","c4b697","48717c","moon"),
    "tessen": ("hakama","kerchief","c0a9b0","764f6c","wave"),
    "inari_servant": ("kimono","hood","e8d3ba","a26d57","flower"),
    "monk": ("robe","cap","c69f72","6b5548","coin"),
    "kitsune": ("kimono","fox","ded4bd","935548","torch"),
    "shinobi": ("leather","hood","a39cb1","4f475f","moon"),
    "yamabushi": ("robe","hat","c2b591","597468","leaf"),
    "miko": ("kimono","ribbon","e5d4bc","9e5564","flower"),
    "nobori": ("lamellar","kabuto","ae9a79","5a6b63","wing"),
    "komainu": ("scale","solar","c7b584","5d776d","sun"),
    "shiranui": ("lamellar","veil","b6a4bd","755166","torch"),
    "akari": ("lamellar","moon","a6aeba","665578","moon"),
    "raiden": ("lamellar","kabuto","b8aac8","515586","bolt"),
    "tomoe": ("hakama","ribbon","d8c1c8","634b6b","moon"),
    "sayo": ("kimono","veil","e3bca0","846052","torch"),
    "kaito": ("leather","hood","a4b5b1","385969","wave"),
    "hana": ("kimono","braid","e1b6bc","895b77","flower"),
    "orochi": ("lamellar","kabuto","9bac9c","47695d","wave"),
    "riku": ("scale","kabuto","bda484","615754","sun"),
}


def mat_set(item, colors):
    armor,_,fabric,trim,_=colors
    faction=item["theme"]
    rng=Random(item["id"]+" complexion")
    skin=rng.choice(("c99670","c88965","ae7857","e0ae8b","ad7559","d79e80"))
    if item["id"] in ("thekla","akari","marcus"):
        skin={"thekla":"ca9472","akari":"dfaa88","marcus":"b8805e"}[item["id"]]
    dark={"aegean":"333f41","rome":"463538","japan":"343749"}[faction]
    gold={"aegean":"c8a260","rome":"c39659","japan":"c9a971"}[faction]
    edge={"aegean":"eed79b","rome":"e3bc7d","japan":"e7ca8d"}[faction]
    hair=rng.choice(("382e2e","382e35","332f38","553933","443231"))
    materials={name:material(name,color,metallic) for name,color,metallic in [
        ("fabric",fabric,0),("accent",trim,0),("body",skin,0),("blush","9e5f50",0),
        ("hair",hair,0),("hair edge","544349",0),("hem",dark,0),("belt","695247",0),
        ("leather","825d48",0),("boots","4a3b34",0),("gold",gold,.22),("fillet",edge,.17),
        ("steel","c2c6c4",.43),("dark iron","717b84",.32),("antique white","e8dfc4",0),
        ("sclera","eee4d0",0),("iris","463e33",0),("pupil","242627",0),("wood","715041",0),
    ]}
    for key,value in (("fabric",.81),("accent",.77),("hair",.63),("body",.71),("belt",.69),
                      ("boots",.68),("gold",.39),("fillet",.29),("steel",.34),("dark iron",.43)):
        materials[key].node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=value
    if item["id"]=="akari":
        materials.update(silk=material("Pale folded sleeve silk","ead9c1"),
            lacquer=material("Akari's russet lacquer","684149",.10),
            stitching=material("Faded salmon stitching","c39384"))
    elif item["id"]=="marcus":
        materials["greave"]=material("Tanned leather gaiters","765346")
        iron=material("Marcus’s worn forged iron","989490",.44)
        iron.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=.43
        materials["steel"]=iron
    elif item["id"]=="bronze_giant":
        materials.update(body=material("Weathered bronze skin","a18456",.38),
                         patina=material("Verdigris on the guardian's brow","5b887e",.13))
    pigments={
        "fabric":"linen" if armor in ("linen","tunic","travel") else "teal",
        "accent":"teal","hem":"teal lining","belt":"hide dark",
        "leather":"hide","boots":"hide dark","gold":"bronze","fillet":"brass",
        "steel":"iron edge","dark iron":"iron","antique white":"linen light",
        "wood":"ash","silk":"linen","lacquer":"paint red","stitching":"hem red",
        "patina":"verdigris",
    }
    if item["id"]=="bronze_giant":
        pigments["body"]="bronze"
    for name,pigment in pigments.items():
        if name in materials:
            materials[name]["Brush pigment"]=pigment
    return materials


def cut(name, parent, center, dims, mat, subdivisions=2, smooth=False):
    obj=stone(name,center,dims,mat,parent,subdivisions)
    if smooth:
        for f in obj.data.polygons:
            f.use_smooth=True
    return obj


def limb(name,parent,start,end,limits,mat):
    a,b=Vector(start),Vector(end)
    length=(b-a).length
    rings=[(height*length,x,y,0,0) for height,x,y in limits]
    obj=shell(name,rings,mat,parent,10,True,pi/10)
    obj.location=a
    obj.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler()
    return obj


def curve(name,parent,points,radii,mat,sides=7):
    return tube(name,parent,points,[(radius,radius*.89) for radius in radii],mat,sides,smooth=False)


def pin(name,p,r,mat,parent):
    cut(name,parent,p,(r,r*.38,r),mat,1,True)


def emblem(style, parent, x,y,z, scale, m):
    def lines(name,pts,width=.012,paint=None):
        p=[(x+a*scale,y,z+b*scale) for a,b in pts]
        curve(name,parent,p,[width*scale]*len(p),paint or m["fillet"],5)
    if style in ("sun","star","flower","coin"):
        n=10 if style=="sun" else 6 if style=="flower" else 5
        torus_mesh("Engraved circular emblem",(x,y,z),.133*scale,.014*scale,m["fillet"],parent,16,6,True)
        for i in range(n):
            a=i*tau/n
            if style=="coin":
                break
            lines("Engraved radiating petal",[(cos(a)*.13,sin(a)*.13),(cos(a+.055)*.255,sin(a+.055)*.255)],.017)
        if style=="coin":
            lines("Coin stamp",[(-.069,-.009),(0,.083),(.072,0),(0,-.083),(-.069,-.009)])
        else:
            pin("Raised heart",(x,y-.011*scale,z),.048*scale,m["gold"],parent)
    elif style in ("leaf","wing","wave"):
        for side in (-1,1):
            lines("Curved crest stem",[(0,-.167),(side*.104,-.012),(side*.202,.159)],.014)
            for n in range(3):
                dx=.038+.042*n
                dz=-.095+.074*n
                lines("Small feather inlay",[(side*dx,dz),(side*(dx+.094),dz+.063)],.017)
    elif style=="moon":
        angles=[pi*(.15+i*.15) for i in range(11)]
        lines("Crescent inlay",[(cos(a)*.205,sin(a)*.205+.04) for a in angles],.019)
    else:
        lines("Hammered pointed inlay",[(-.015,.25),(.114,.036),(-.059,-.025),(.022,-.22)],.021)


def fabric_panel(name,parent,wtop,whem,height,shift,foot,m,center=(0,0,0),cascade=False):
    # A wavy grid makes folds and a continuous dyed hem from both sides.
    x,y,z=center
    verts=[]
    faces=[]
    cols=7
    for row in range(5):
        t=row/4
        for i in range(cols):
            u=(2*i/(cols-1)-1)
            width=wtop*(1-t)+whem*t
            crest=.020*sin(i*1.88+row*.2)+.035*t*cos(i*1.57+row*.44)
            verts.append((x+u*width+shift*t*t,y+foot*t**1.25+crest,
                          z-height*t+(.074*sin(i*1.44)+.024*u)*t*t))
    for row in range(4):
        for i in range(cols-1):
            a=row*cols+i
            b=a+cols
            faces.append((a,a+1,b+1,b))
    obj=mesh_object(name,verts,faces,None,parent)
    for paint in (m["accent"],m["hem"],m["fillet"],m["fabric"]):
        obj.data.materials.append(paint)
    for i,f in enumerate(obj.data.polygons):
        col=i%(cols-1)
        row=i//(cols-1)
        f.material_index=2 if col in (0,cols-2) and cascade else 1 if row==3 or col in (0,cols-2) else 0
    obj.modifiers.new("Two-sided fabric edge","SOLIDIFY").thickness=.021


def hair_cap(head,m,style,broad,theme,ident):
    shell("Carved hair volume",[
        (.247,.188*broad,.165,0,.040),(.304,.210*broad,.180,0,.032),(.389,.195*broad,.164,0,.033),
        (.449,.153*broad,.125,0,.035),(.481,.058,.059,.005,.027),
    ],m["hair"],head,20,True)
    face_shift=-1 if theme=="japan" else 1
    if style not in ("galea","bronze","crest","hat","kabuto"):
        for i in range(5):
            u=(-.155+.069*i)*broad
            base=.302+.014*sin(i*1.70)
            end=.421+.019*cos(i*.8)
            pts=[(u-.031,-.132+abs(u)*.17,base),
                 (u+.019,-.166+abs(u)*.21,base+.030),
                 (u+face_shift*.047,-.141,end-.012),
                 (u+face_shift*.01,-.082,end+.024),
                 (u-face_shift*.049,-.108,end-.017)]
            comb=mesh_object("Swept hair lock",pts,[(0,1,2,3,4)],m["hair edge"] if i%3==1 else m["hair"],head)
            comb.modifiers.new("Shaped outer hair strand","SOLIDIFY").thickness=.020
    if style in ("braid","moon","ribbon","corinthian"):
        for sign in (-1,1):
            curve("Shaped braid from temple to the back",head,[(sign*.141,.037,.371),
                 (sign*.173,.101,.284),(sign*.159,.191,.251),(sign*.111,.237,.212)],
                 [.043,.049,.040,.029],m["hair"],8)
        cut("Back hair gathered and tied",head,((.062 if ident=="akari" else 0),.193,.333),(.118,.094,.110),m["hair"],2)
        for i in range(6):
            a=i*tau/6
            x=cos(a)*.071
            cut("Carved loops of the tied hair",head,(x,.235,.332+sin(a)*.073),
                (.052,.038,.051),m["hair edge"] if i%3==0 else m["hair"],1,True)
    if ident=="thekla":
        for sign in (-1,1):
            for i in range(3):
                x=sign*(.150+.012*i)
                cut("Short sculpted curls against the temple",head,(x,.047+.011*i,.281-.044*i),
                    (.032,.038,.033),m["hair"],2,True)
    if style in ("ribbon","braid","veil") or ident=="akari":
        for side in (-1,1):
            ribbon=empty("Knotted ribbon",(side*.055,.191,.283),head)
            ribbon.rotation_euler.y=.18*side
            fabric_panel("Dyed silk from the back of the coiffure",ribbon,.049,.073,.31,.051*side,.091,m)


def hood(head,m,style,broad):
    angles=[-.19*pi+1.38*pi*i/14 for i in range(15)]
    points=[(rx*broad*cos(a),y+.026*abs(cos(a)),z+rz*sin(a))
            for y,z,rx,rz in ((-.139,.268,.230,.250),(-.084,.270,.258,.270),
                              (.068,.250,.269,.277),(.191,.234,.235,.260),
                              (.223,.222,.144,.164)) for a in angles]
    n=len(angles)
    faces=[(a,a+1,a+n+1,a+n) for row in range(4) for i in range(n-1) for a in (row*n+i,)]
    faces.append(tuple(range(4*n,5*n)))
    paint=m["antique white"] if style=="veil" else m["accent"]
    panel=mesh_object("Tailored canopy and crown folds of the head cloth",points,faces,paint,head)
    panel.modifiers.new("Cloth fold thickness","SOLIDIFY").thickness=.022
    curve("Stitched front seam of the head cloth",head,points[:n],[.013]*n,
          m["accent"] if style=="veil" else m["belt"],6)


def guardian_mask(head,m,ident):
    if ident=="bronze_giant":
        visor=silhouette("Weathered bronze faceguard with cheek cuts",
            [(-.222,.361),(-.098,.352),(0,.398),(.104,.352),(.224,.37),(.196,.153),
             (.091,.085),(.052,.166),(0,.129),(-.060,.169),(-.085,.090),(-.190,.167)],
            .051,m["gold"],head)
        visor.location.y=-.175
        for side in (-1,1):
            span("Patina recessed around the mask's eye",(side*.036,-.204,.241),(side*.155,-.207,.256),
                 .018,m["patina"],head,6,.013)
        pin("Bronze brow rivet",(0,-.208,.326),.035,m["fillet"],head)
    if ident=="komainu":
        mask=silhouette("Lion guardian mask with broad jaw",
            [(-.213,.305),(-.238,.402),(-.142,.463),(0,.402),(.144,.464),(.239,.398),
             (.213,.304),(.228,.155),(.106,.089),(0,.138),(-.108,.088),(-.228,.155)],
            .051,m["fabric"],head)
        mask.location.y=-.174
        for side in (-1,1):
            for i in range(4):
                theta=pi*(.27+i*.19)
                x=side*(.157+.069*sin(theta))
                cut("Curl in the carved lion mane",head,(x,-.171,.244+.166*cos(theta)),
                    (.058,.054,.062),m["gold"],1,True)
            pin("Carved lacquer lion eye",(side*.088,-.208,.279),.037,m["hem"],head)
            cut("Lion's sculpted muzzle",head,(side*.053,-.220,.181),
                (.077,.047,.048),m["gold"],2,True)
        pin("Dark centre of the lion nose",(0,-.268,.222),.033,m["hair"],head)


def headpiece(head,m,style,theme,broad,medal,hero,ident):
    if style in ("bronze","corinthian","galea","crest","kabuto"):
        helmet=m["dark iron"] if style=="galea" else m["gold"] if theme!="japan" else m["hem"]
        shell("Hammered open-faced helmet",[
            (.298,.218*broad,.198,0,.039),(.334,.234*broad,.202,0,.042),
            (.404,.206*broad,.183,0,.051),(.468,.150*broad,.136,0,.043),
            (.506,.079*broad,.072,0,.041),(.519,.037,.045,0,.046)
        ],helmet,head,14)
        shell("Folded lip of the helmet crown",[(.286,.207*broad,.191,0,.032),
              (.299,.224*broad,.201,0,.032),(.328,.231*broad,.204,0,.040),
              (.338,.225*broad,.199,0,.042)],m["fillet"],head,14)
        for side in (-1,1):
            if theme=="japan":
                for row in range(3):
                    plate=block("Layered lacquered helmet shikoro",(side*(.168+.016*row),.067,.328-.053*row),
                         (.105,.273,.057),m["dark iron"],head,.014)
                    plate.rotation_euler.y=side*.26
                    span("Red shikoro lacing",(side*(.215+.015*row),-.065,.324-.053*row),
                         (side*(.215+.015*row),.192,.324-.053*row),.012,m["accent"],head,6)
            else:
                def faceguard(x,z,d):
                    return side*x*broad,-.109+1.03*(x-.146)-d,z
                outline=[(.128,.306),(.208,.329),(.229,.281),(.224,.213),(.171,.131),
                         (.133,.161),(.153,.220)]
                relief("Stamped and bevelled cheek wing",head,outline,faceguard,helmet,m["fillet"],
                       .026 if hero else .019,.14)
                pin("Faceguard boss",(side*.174,-.112,.230),.022,m["fillet"],head)
        if style=="corinthian":
            mount=silhouette("Cast saddle under the sweeping helmet spine",
                [(-.143,.436),(.125,.443),(.106,.490),(0,.551),(-.074,.520)],.072,m["gold"],head)
            mount.rotation_euler.z=pi/2
            mount.location.y=.052
            for side in (-1,1):
                path=[(side*.051,.045+.29*cos(a),.414+.152*sin(a)) for a in [pi*(.14+.09*i) for i in range(9)]]
                curve("Raised contour of the cast helmet crest",head,path,[.008,.012,.021,.023,.023,.023,.019,.012,.007],m["fillet"],7)
            path=[(0,.043+.245*cos(a),.459+.152*sin(a)) for a in [pi*(.16+.092*i) for i in range(9)]]
            curve("Swept inlaid spine of the helmet",head,path,[.012,.029,.041,.045,.047,.042,.034,.023,.011],m["accent"],9)
        elif style=="crest":
            if theme=="rome":
                comb=silhouette("Curved saddle connecting the crest to the galea",
                    [(-.185,.439),(-.119,.471),(0,.509),(.121,.469),(.185,.439),
                     (.184,.503),(.082,.553),(0,.566),(-.082,.553),(-.184,.503)],
                    .082,m["gold"],head)
                comb.location.y=.044
            for i in range(9):
                angle=(i-4)*.116
                if theme=="rome":
                    p=(sin(angle)*.33,.041,.486+cos(angle)*.136)
                    obj=block("Dyed transverse Roman crest bristles",p,(.055,.102,.150),m["accent"],head,.018)
                    obj.rotation_euler.y=angle
                else:
                    obj=block("Sculpted ridge horsehair",(.011,.035+sin(angle)*.32,.486+cos(angle)*.124),
                         (.083,.057,.113),m["accent"] if i>2 else m["fillet"],head,.014)
                    obj.rotation_euler.x=-angle
        if style=="kabuto":
            for side in (-1,1):
                horn=silhouette("Swept brass maedate",[(.035,.338),(.142,.387),(.223,.593),(.190,.591),(.106,.462),(.03,.431)],.022,m["fillet"],head)
                horn.scale.x=side
                horn.location.y=-.148
    elif style in ("hat","cap","kerchief"):
        wide=.278 if style=="hat" else .204
        shell("Folded field headwear",[(.296,wide,wide*.90,0,.04),(.333,wide,wide*.89,0,.032),
            (.417,.17,.151,0,.035),(.467,.098,.074,0,.03)],m["accent"],head,14)
        if style=="hat":
            torus_mesh("Braided hat brim",(0,.039,.313),.265,.018,m["fillet"],head,20)
        else:
            span("Tied brow binding",(-.171,-.093,.326),(.173,-.092,.328),.026,m["fabric"],head,9)
    elif style in ("hood","veil"):
        hood(head,m,style,broad)
        for side in (-1,1):
            fabric_panel("Folded covering beside face",head,.114,.105,.43,side*.037,.12,m,
                         center=(side*.134,-.052,.414))
    elif style in ("moon","solar","laurel","ribbon"):
        if style=="moon":
            angles=[pi*(.89+i*.13) for i in range(11)]
            outline=[(.148*cos(a),.539+.134*sin(a)) for a in angles]
            outline.extend((.129*cos(a),.552+.113*sin(a)) for a in reversed(angles))
            crescent=silhouette("Cut and polished crescent crest",outline,.033,m["fillet"],head)
            crescent.location.y=-.143
            if ident=="akari":
                span("Brass stand between crescent and hair comb",(0,-.143,.413),
                     (0,-.145,.456),.027,m["gold"],head,7,.021)
        else:
            for side in (-1,1):
                for i in range(4):
                    p=(side*(.076+.029*i),-.142+.019*i,.379+.025*i)
                    leaf=cut("Hammered laurels or comb",head,p,(.032,.020,.065),m["fillet"],1)
                    leaf.rotation_euler.y=side*(.43-.05*i)
        pin("Foredge crest setting",(0,-.149,.382),.046,m["gold"],head)
        emblem(medal,head,0,-.175,.387,.29,m)
    if style=="fox":
        for side in (-1,1):
            face=silhouette("Carved kitsune ear",[(.109,.351),(.259,.39),(.210,.597)],.092,m["fabric"],head)
            face.scale.x=side
            face.location.y=.039
    guardian_mask(head,m,ident)


def torso(body,m,armor,wide,crest,hero,ident):
    shell("Tailored overlapping body undercloth",[
        (-.27,wide*.254,.181,0,.025),(-.198,wide*.273,.180,0,.020),
        (-.095,wide*.237,.158,0,.008),(.027,wide*.220,.151,0,.001),
        (.192,wide*.258,.169,0,.001),(.320,wide*.305,.174,0,.010),
        (.398,wide*.262,.161,0,.012),(.457,wide*.134,.105,0,.012),
    ],m["fabric"],body,16,True)
    plated=armor in ("muscle","scale","segments","linen","lamellar")
    if armor=="linen" or armor=="muscle":
        shell("Curved bronze thorax" if armor=="muscle" else "Bound linen breastplate",[
            (.047,.222*wide,.087,0,-.113),(.105,.245*wide,.108,0,-.119),
            (.271,.285*wide,.117,0,-.088),(.367,.264*wide,.106,0,-.074),
            (.407,.196*wide,.074,0,-.072)
        ],m["gold"] if armor=="muscle" else m["antique white"],body,14)
        if armor=="linen":
            for level in (.125,.202,.284):
                def wrap(u,t):
                    x=(2*u-1)*(.206+.022*sin(pi*u))*wide
                    y=-.234+.078*(2*u-1)**2-.015*(1.-t)
                    z=level+.067*u+.017*sin(pi*u)+(.078+.014*sin(pi*u))*(t-.5)
                    return x,y,z
                strips("Cut diagonal linen dam with woven edge",body,[0,.12,.32,.51,.73,.89,1.],[0,.14,.74,1.],
                       wrap,[m["fabric"],m["antique white"],m["hem"]],
                       lambda u,t:1 if t<.12 else 0,lining=.009,smooth=False)
        else:
            def breastplate(x,z,d):
                return x*wide,-.227+.15*abs(x)-d,z
            relief("Sculpted central rib of the bronze cuirass",body,
                   [(-.121,.334),(.004,.361),(.133,.332),(.146,.271),(.010,.136),(-.149,.274)],
                   breastplate,m["gold"],m["fillet"],.025,.13)
        for side in (-1,1):
            curve("Diagonal linen shoulder binding",body,[(side*.152,-.193,.382),(side*.109,-.212,.278),
                  (-side*.194,-.194,.077)],[.027,.030,.029],m["belt"],7)
    elif armor in ("scale","segments","lamellar"):
        for row in range(5):
            h=.066+row*.073
            rad=(.247+.012*row)*wide
            if armor=="segments":
                shell("Overlapping curved iron segment",[(h-.042,rad,.189,0,.011),(h,rad+.013,.204,0,.008),
                    (h+.035,rad-.004,.194,0,.011)],m["dark iron"],body,14)
                for x in (-.068,.068):
                    block("Small bronze lorica hinge",(x,-.199+.023*row/5,h-.007),(.061,.026,.024),m["gold"],body,.007)
                if ident=="marcus":
                    for side in (-1,1):
                        span("Bronze edge of the lorica band",(side*.038,-.205,h-.014),
                             (side*.197,-.158,h-.012),.010,m["gold"],body,6,.009)
            else:
                for index in range(8):
                    angle=(index-3.5)*.41
                    plate_color=m["gold"] if armor=="scale" else m["hem"] if row%2 else m["dark iron"]
                    if ident=="akari" and row>=3:
                        plate_color=m["lacquer"]
                    block("Hand-laced lamellar panel",(sin(angle)*rad,-cos(angle)*.186,h),
                          (.083*wide,.049,.086),plate_color,body,.014,angle)
                    pin("Lamellar silk knot",(sin(angle)*rad,-cos(angle)*.208,h+.015),.013,m["accent"],body)
    else:
        for sign in (-1,1):
            def wrap(u,t):
                width=(.114 if sign>0 else .083)*(1.-.41*u)
                x=sign*(.180*(1.-u)-.201*u)+width*(t-.5)
                y=-.161-.050*sin(pi*u)-.010*sin(t*pi)-(.013 if sign>0 else 0)
                z=.412-.454*u+.023*sin(pi*u)+.021*t
                return x,y,z
            strips("Wide cut lapel folded across the jacket",body,[0,.17,.38,.60,.79,1.],[0,.17,.73,1.],wrap,
                   [m["antique white"] if armor in ("robe","kimono","hakama") else m["accent"],m["hem"]],
                   lambda u,t:1 if t<.11 else 0,lining=.008,smooth=False)
    shell("Heavy stitched crossbelt",[
        (-.120,.233*wide,.164,0,0),(-.095,.259*wide,.179,0,0),
        (-.031,.249*wide,.172,0,0),(-.017,.231*wide,.166,0,0)],m["belt"],body,16,True)
    block("Inlaid fibula at the centre sash",(0,-.182,-.066),(.145,.058,.102),m["gold"],body,.025)
    emblem(crest,body,0,-.215,-.064,.23,m)
    if ident=="akari":
        for side in (-1,1):
            hakama=shell("Pleated indigo hakama with split stride",[
                (-.632,.151,.201,side*.147,.018),(-.597,.173,.213,side*.158,.028),
                (-.392,.159,.194,side*.144,.022),(-.121,.111,.162,side*.087,0)
            ],m["hem"],body,9,False,pi/9)
            hakama.data.materials.append(m["accent"])
            for row in range(3):
                for column in (0,3,6):
                    hakama.data.polygons[1+row*9+column].material_index=1
            for rear in (-1,1):
                for i in (-1,0,1):
                    cx=side*.158+i*.091
                    for radius in (.028,.044):
                        arc=[(cx+radius*cos(a),rear*(.192-.016*abs(i))+.018,
                              -.590+radius*sin(a)) for a in [pi*k/5 for k in range(6)]]
                        curve("Woven seigaiha on the split hem",body,arc,[.0065]*6,m["stitching"],5)
            for row in range(2):
                for i in range(4):
                    x=side*(.066+i*.061)
                    obj=block("Laced blue plates on the hip guards",(x,-.189+abs(x)*.18,-.182-.059*row),
                        (.078,.047,.093),m["dark iron"] if row%2 else m["accent"],body,.019,side*.094*i)
                    pin("Bronze tie point on skirt plate",(x,-.217+abs(x)*.18,-.168-.059*row),.014,m["fillet"],body)
        obi=empty("Coral silk knot and tied sash",(0,-.193,-.069),body)
        accent=material("Akari’s salmon-toned waist silk","ba6d5e")
        for side in (-1,1):
            side_knot=cut("Silk bow with sculpted folds",obi,(side*.074,-.033,.006),(.080,.043,.041),accent,2)
            side_knot.rotation_euler.y=side*.28
            cloth={**m,"accent":accent,"hem":m["accent"]}
            fabric_panel("Two folded front ribbons",obi,.057,.065,.47+.05*side,.08*side,-.065,cloth,
                         center=(side*.050,-.055,-.026))
        pin("Knot centre",(0,-.071,.003),.041,accent,obi)
    elif armor in ("robe","kimono","hakama","travel"):
        length=.54 if armor in ("robe","kimono","hakama") else .34
        shell("Flaring lower fabric",[
            (-length-.13,.284*wide,.209,0,0),(-length-.105,.307*wide,.222,0,.024),
            (-.302,.253*wide,.183,0,.011),(-.114,.216*wide,.169,0,.0)
        ],m["hem"] if armor=="hakama" else m["fabric"],body,14)
        for side in (-1,1):
            tied=empty("Hanging split sash",(side*.104,-.17,-.117),body)
            tied.rotation_euler.y=side*.213
            fabric_panel("Finished sash panel",tied,.105,.130,length,side*.045,-.057,m)
    else:
        for row in range(2):
            for i in range(8):
                a=(i-3.5)*.443
                def tasset(u,t):
                    q=a+(u-.5)*(.49-.055*t)+.061*t
                    ridge=.020*max(0.,1.-2.7*abs(u-.43))*sin(pi*t*.82)
                    x=sin(q)*(.235+.018*row+.047*t+ridge)*wide
                    y=-cos(q)*(.172+row*.023+.035*t+ridge)
                    z=-.119-row*.099-(.218+.039*(u-.5)+.024*sin(i*.85))*t
                    return x,y,z
                face=m["fabric"] if armor=="linen" else m["dark iron"] if armor=="lamellar" and row==0 else m["leather"]
                strips("Pointed, overlapping tasset",body,[0,.14,.43,.83,1.],[0,.32,.73,.915,1.],tasset,
                       [face,m["belt"]],lambda u,t:1 if t>.90 else 0,lining=.014,smooth=False,reverse=True)
                if row==0:
                    x,y,z=tasset(.53,.839)
                    pin("Rivet catching the light on the tasset",(x,y-.010,z),.016,m["fillet"],body)
    if hero or plated:
        p=cut("Medallion with chased edge",body,(0,-.212,.291),(.079,.031,.077),m["gold"],2)
        emblem(crest,body,0,-.249,.289,.24,m)
    return plated


def armor_arm(arm,side,m,plated,japan,hero,ident):
    limb("Upper arm with sculpted seam",arm,(0,-.009,-.018),(side*.054,-.025,-.249),
        [(0,.097,.093),(.20,.119,.110),(.57,.095,.087),(.87,.078,.077),(1,.072,.070)],
        m["fabric"] if japan or not plated else m["body"])
    if ident=="akari":
        limb("Pleated ivory sleeve under the articulated armour",arm,
             (side*.012,-.006,-.031),(side*.052,-.038,-.253),
             [(0,.102,.099),(.29,.125,.112),(.66,.135,.126),(.85,.117,.111),(1,.106,.093)],m["silk"])
    if plated or hero:
        for row in range(3 if japan and ident!="akari" else 2):
            p=(side*(.045+.014*row),.005,-.008-.071*row)
            if japan:
                pad=block("Lacquered shoulder lamella",(p[0]+side*.029,-.004,p[2]),(.223,.266-.026*row,.061),
                          m["lacquer"] if ident=="akari" and row==0 else m["dark iron"],arm,.026)
                pad.rotation_euler.y=side*.36
                span("Dyed silk shoulder lacing",(p[0]-.068,-.111+row*.008,p[2]+.012),
                     (p[0]+.079,-.112+row*.008,p[2]-.015),.015,m["accent"],arm,7)
            else:
                def plate(u,t):
                    q=-.21+3.62*u
                    peak=max(0.,1.-2.6*abs(u-.60))
                    radius=.125-.012*row+.018*(1.-t)+.020*peak
                    x=side*(.027+sin(q)*radius)
                    y=cos(q)*(radius+.013)-.008
                    z=.042-.082*row-.095*t+.033*peak*(1.-.30*t)
                    return x,y,z
                strips("Hammered pauldron with a peaked lip",arm,[0,.13,.29,.47,.65,.82,1.],[0,.25,.78,.91,1.],
                       plate,[m["gold"] if row==0 else m["dark iron"],m["fillet"]],
                       lambda u,t:int(t>.83),lining=.013,smooth=False,reverse=side<0)
                pin("Rivet at shoulder edge",(p[0],-.123+row*.009,p[2]),.023,m["fillet"],arm)
    fore=empty("LeftForearm" if side<0 else "RightForearm",(side*.050,-.029,-.219),arm)
    limb("Fitted forearm profile",fore,(0,0,0),(side*.025,-.119,-.184),
        [(0,.080,.078),(.21,.087,.082),(.65,.076,.062),(.82,.059,.057),(1,.057,.053)],m["body"])
    limb("Raised cuff and strapped bracer",fore,(side*.012,-.051,-.052),(side*.026,-.103,-.164),
        [(0,.078,.071),(.13,.082,.076),(.82,.073,.066),(1,.067,.062)], m["dark iron"] if japan else m["gold"] if plated else m["belt"])
    hand=empty("LeftHand" if side<0 else "RightHand",(side*.031,-.129,-.181),fore)
    cut("Palm carved round the handle",hand,(0,0,-.027),(.070,.060,.070),m["body"],2,True)
    for k in range(3):
        cut("Curled finger",hand,((k-1)*.035,-.031,-.047),(.022,.035,.038),m["body"],2,True)
    cut("Thumb next to guard",hand,(-side*.049,-.008,-.005),(.033,.042,.057),m["body"],2,True)
    return hand


def boots(root,wide,m,armor,theme,ident,height):
    for side,label in ((-1,"LeftLeg"),(1,"RightLeg")):
        stride=.036 if ident=="marcus" else .048 if ident=="akari" else .027
        leg=empty(label,(side*.136*wide,.02+side*stride,height),root)
        leg.scale=(.85,.88,height/.795)
        leg.rotation_euler.z=-side*.096
        booted=theme=="japan" or armor in ("leather","tunic","travel")
        limb("Tapered trousers" if booted else "Tailored leg",leg,(0,0,.024),(side*.027,.014,-.463),
            [(0,.115,.106),(.23,.117,.11),(.61,.091,.087),(.88,.081,.077),(1,.079,.074)],
            m["hem"] if booted else m["body"])
        guard=side*.031
        limb("Strapped greave",leg,(guard,-.005,-.373),(guard*1.4,-.016,-.691),
            [(0,.082,.076),(.26,.098,.083),(.74,.079,.072),(1,.064,.066)],
            m.get("greave",m["dark iron"] if theme=="japan" else m["gold"]))
        shell("Bevelled boot or skin fitted to a sandal",[
            (-.770,.093,.164,guard*1.4,-.091),(-.746,.101,.169,guard*1.4,-.092),
            (-.715,.089,.139,guard*1.4,-.078),(-.674,.075,.085,guard*1.4,-.035),
        ],m["boots"] if booted else m["body"],leg,10,False)
        block("Stitched sole",(guard*1.4,-.084,-.783),(.202,.292,.047),m["belt"],leg,.029)
        for step in range(3):
            block("Criss-cross sandal straps",(guard*1.4,-.145+.053*step,-.655-.011*step),
                  (.181,.035,.026),m["leather"],leg,.012,side*.07)
        pin("Bronze boot clasp",(guard*1.4,-.088,-.61),.028,m["fillet"],leg)


def shield(hand,m,theme,crest,size=1.0,hero=False):
    parent=empty("Shield fixed to forearm",(0,-.102,-.101),hand)
    parent.scale=(size,)*3
    if theme=="rome":
        scutum(parent,m,hero,crest)
        if crest!="wing":
            emblem(crest,parent,0,-.129,.03,.91,m)
    else:
        model=shell("Convex round shield with timber backing",[
            (-.070,.332,.332,0,0),(-.048,.365,.365,0,0),(.012,.356,.356,0,0),
            (.052,.242,.242,0,0),(.078,.074,.074,0,0)
        ],m["accent"],parent,22,True)
        model.rotation_euler.x=pi/2
        torus_mesh("Raised shield rim",(0,-.011,0),.348,.031,m["gold"],parent,24,6,True)
        torus_mesh("Bevelled inner shield lip",(0,-.046,0),.296,.014,m["fillet"],parent,24,6,True)
        for i in range(12):
            a=tau*i/12
            pin("Rivets around embossed shield",(cos(a)*.314,-.050,sin(a)*.314),.021,m["fillet"],parent)
        if crest=="sun":
            polished_sun_disc(parent,m,hero)
        else:
            emblem(crest,parent,0,-.078,0,1.0,m)
    cut("Metal shield boss",parent,(0,-.132,0),(.064,.049,.070),m["fillet"],2)
    for sign in (-1,1):
        span("Rear leather handle",(sign*.16,.051,-.18),(sign*.08,.093,.13),.028,m["belt"],parent,7)


def weapon(hand,hips,kind,m,crest,hero,ident):
    h=1.14 if hero else .92
    if kind in ("spear","glaive","javelin","staff","banner","hammer","sword"):
        top=h if kind!="sword" else .55
        lb=-.46 if kind in ("spear","glaive","javelin","banner","staff") else -.23
        if kind in ("staff","banner"): top=h*1.01
        if kind=="hammer": top=.62 if hero else .51
        if kind!="sword":
            span("Tapered engraved shaft",(0,0,lb),(0,0,top),.040 if hero else .032,
                  m["wood"] if kind!="staff" else m["dark iron"],hand,9,.029)
        for z in (-.187,-.133,-.079,-.025,.029,.083):
            span("Rolled grip leather",(-.001,0,z-.017),(.001,0,z+.018),.042,m["belt"],hand,8,.038)
        if kind in ("spear","glaive","javelin","sword"):
            start=top-.098 if kind!="sword" else .106
            peak=start+(.48 if kind=="glaive" else .60 if kind=="sword" else .365 if hero else .26)
            arc=.160 if kind=="glaive" else .018
            if kind=="glaive":
                silhouette("Drawn curved naginata with honed edge",[(0,start),(-.049,start+.127),
                    (-.012,start+.285),(.067,peak-.065),(arc,peak),(.137,peak-.111),
                    (.084,start+.210),(.058,start+.071)],.039,m["steel"],hand)
                curve("Visible darker spine of the curved blade",hand,[(.016,-.023,start+.025),
                     (.022,-.031,start+.168),(.066,-.028,start+.306),(.125,-.013,peak-.048)],
                     [.012,.016,.012,.002],m["dark iron"],6)
                shell("Rounded brass naginata guard",[(start-.004,.099,.052,0,0),
                      (start+.015,.115,.062,0,0),(start+.030,.092,.053,0,0)],m["gold"],hand,12)
            else:
                silhouette("Planar honed leaf blade",[(0,start),(-.074,start+.091),(arc-.041,peak-.102),
                           (arc,peak),(arc+.067,peak-.096),(.083,start+.11)],.047,m["steel"],hand)
                curve("Raised bronze fuller",hand,[(0,-.027,start+.044),(.025,-.034,start+.183),
                     (arc,-.023,peak-.033)],[.014,.012,.003],m["fillet"],6)
                block("Fitted weapon guard",(0,0,start+.006),(.21,.089,.056),m["gold"],hand,.015)
        elif kind=="hammer":
            hammer=block("Weighted bevelled bronze hammer head",(0,0,top),(.49,.29,.31),m["dark iron"],hand,.079)
            for side in (-1,1):
                block("Tapered brass hammer cheek",(side*.208,-.01,top),(.146,.295,.273),m["gold"],hand,.05)
            emblem(crest,hand,0,-.153,top,.46,m)
        elif kind=="staff":
            focus=empty("Crafted channel at the staff tip",(0,0,top+.121),hand)
            focus.rotation_euler.z=.12
            if crest in ("sun","moon","star"):
                size=.141 if hero else .112
                torus_mesh("Circular brass setting for a polished stone",(0,-.008,0),size,.026,m["fillet"],focus,16,6,True)
                rays=11 if crest=="sun" else 5 if crest=="star" else 3
                for i in range(rays):
                    a=i*tau/rays
                    reach=size*1.7
                    span("Outward tip of the carved setting",(size*cos(a),0,size*sin(a)),
                         (reach*cos(a),0,reach*sin(a)),.025,m["gold"],focus,5,.003)
                cut("Polished enamel at the centre of the setting",focus,(0,-.022,0),
                    (size*.69,.067,size*.73),m["accent"],2,True)
            else:
                fill=m["accent"]
                cut("Glazed stone cut to a flame or leaf",focus,(0,-.008,.012),(.083,.069,.135),fill,1)
                for side in (-1,1):
                    curve("Forged branches curving over the crystal",focus,
                        [(0,0,-.171),(side*.118,0,-.065),(side*.14,0,.087),(side*.080,0,.149)],
                        [.039,.031,.021,.006],m["gold"],7)
        elif kind=="banner":
            span("Silk standard crosspiece",(-.243,0,top-.059),(.243,0,top-.059),.036,m["gold"],hand,8)
            pennant=empty("Banner sail",(0,0,top-.064),hand)
            fabric_panel("Split company standard",pennant,.226,.195,.55,.09,.024,m,center=(0,-.011,0),cascade=True)
            emblem(crest,pennant,0,-.058,-.22,.52,m)
            if ident=="aquilifer":
                bird=silhouette("Roman eagle finial above the standard",
                    [(-.317,.158),(-.207,.192),(-.087,.120),(-.039,.173),(-.036,.237),
                     (.075,.256),(.111,.217),(.045,.189),(.068,.125),(.202,.196),(.318,.159),
                     (.278,.060),(.166,.017),(.074,.030),(0,-.027),(-.081,.030),(-.192,.021),(-.283,.069)],
                    .047,m["fillet"],hand)
                bird.location.z=top+.054
            else:
                cut("Hammered banner finial",hand,(0,0,top+.073),(.079,.050,.077),m["fillet"],1)
    elif kind=="bow":
        bow=empty("Laminate bow turned towards the draw hand",(0,0,0),hand)
        bow.rotation_euler.z=1.37
        length=1.27 if ident=="yumi" else 1.01
        points=[(0,-.367+sin(pi*i/8)*.367,-.435+i*length/8) for i in range(9)]
        curve("Sculpted recurved laminated bow",bow,points,[.023,.030,.035,.042,.045,.043,.035,.029,.022],m["wood"],9)
        span("Bowstring",points[0],points[-1],.010,m["antique white"],bow,5,.010)
        for i in (2,6):
            a,b=Vector(points[i]),Vector(points[i+1])
            span("Dyed fiber marking on the upper and lower limb",a.lerp(b,.12),a.lerp(b,.61),.045,m["accent"],bow,7)
        quiver=empty("Cross-back quiver",(.152,.196,.035),hips)
        quiver.rotation_euler.y=-.52
        shell("Quiver leather basket",[(0,.115,.099,0,0),(.47,.112,.107,0,0),(.55,.123,.108,0,0)],m["belt"],quiver,9)
        for i in range(4):
            x=(i-1.5)*.041
            span("Prepared reed arrow",(x,0,.40),(x,.006,.65+.035*i),.011,m["wood"],quiver,6)
            pin("Archer feather",(x,.007,.661+.035*i),.034,m["fabric"],quiver)
    elif kind=="fan":
        p=[(0,-.07,-.035)]
        for i in range(9):
            a=.21+i*(pi-.42)/8
            p.append((cos(a)*.281,-.09,.03+sin(a)*.334))
        obj=mesh_object("Painted open folding fan",p,[(0,i+1,i+2) for i in range(8)],None,hand)
        for paint in (m["fabric"],m["accent"],m["gold"]):
            obj.data.materials.append(paint)
        for i,face in enumerate(obj.data.polygons):
            face.material_index=[0,1,1,2,2,1,1,0][i]
        obj.modifiers.new("Weight of fan paper","SOLIDIFY").thickness=.025
        for q in p[1:]:
            span("Fan rib",(0,-.099,-.038),q,.012,m["gold"],hand,5,.009)
    else:
        curve("Braided leather sling",hand,[(-.095,0,.139),(-.075,-.093,-.048),(.014,-.207,-.352),
              (.135,-.178,-.173)],[.025,.016,.023,.016],m["belt"],7)
        cut("Polished sling shot",hand,(.013,-.199,-.308),(.081,.068,.071),m["steel"],2)


def hero_regalia(item,body,head,mantle,m,wide,crest):
    theme=item["theme"]
    shape=item["model"]["shape"]
    if shape in ("seer","spirit","robe","banner"):
        for side in (-1,1):
            fabric_panel("Long layered ceremonial sash",body,.102,.141,.62 if side<0 else .46,
                         side*.103,-.054,m,center=(side*.115,-.184,.103),cascade=True)
            clasp=cut("Hammered clasp fastening the sash",body,(side*.126,-.235,.113),
                       (.063,.034,.07),m["fillet"],2)
            clasp.rotation_euler.y=side*.31
        if theme=="aegean":
            crest_mount=empty("Ceremonial shoulder diadem",(-.168,.084,.262),head)
            for i in range(5):
                x=-.048-.036*i
                leaf=cut("Punched bronze laurel leaf",crest_mount,(x,-.017,.010+i*.039),
                         (.037,.019,.083),m["fillet"],1)
                leaf.rotation_euler.y=-.53+i*.19
        elif theme=="japan":
            for i in range(3):
                x=(i-1)*.056
                curve("Knotted ribbons behind the collar",mantle,[(x,0,.053),(x+.023,.087,-.118),
                      (x+.085,.155,-.282-.069*i)],[.032,.029,.011],m["accent"],6)
        else:
            for i in range(4):
                pin("Small gold phalera across the shoulder",(-.148-.032*i,-.158+.020*i,.339-.022*i),
                    .032,m["gold"],body)
    else:
        side=-1
        def guardian_plate(x,z,d):
            return side*x*wide,-.183+.21*x-d,z
        outline=[(.200,.406),(.307,.462),(.409,.426),(.454,.332),(.392,.253),(.261,.272)]
        relief("Swept commander's pauldron bearing a chased border",body,outline,guardian_plate,
               m["dark iron"] if theme=="japan" else m["gold"],m["fillet"],.028,.105)
        emblem(crest,body,-.319*wide,-.181,.363,.36,m)
        if theme=="rome":
            for i in range(3):
                curve("Hanging links of the bronze officer's harness",body,
                      [(-.238,-.204,.336-.036*i),(-.083,-.226,.285-.046*i),
                       (.084,-.226,.293-.045*i),(.205,-.172,.356-.034*i)],
                      [.013,.015,.012,.010],m["fillet"],7)
        elif theme=="japan":
            for i in range(3):
                x=.126+.055*i
                block("Lacquer plates at the left hip",(-x,-.155+.038*i,-.236-.043*i),
                      (.135,.085,.289),m["accent"],body,.023,-.13-.098*i)
        else:
            for i in range(3):
                x=-.098-.062*i
                tapered=block("Embossed bronze tongues at the hip",(x,-.198+.024*i,-.233-.033*i),
                              (.125,.068,.249),m["gold"],body,.032,-.135*i)
                pin("Burnished bronze tongue rivet",(x,-.231+.024*i,-.181-.034*i),.017,m["fillet"],body)


def humanoid(item):
    ident=item["id"]
    theme=item["theme"]
    colors=WARDROBE[ident]
    armor,style,_,_,crest=colors
    hero=item["kind"]=="hero"
    info=item["model"]
    shape,tool=info["shape"],info["weapon"]
    m=mat_set(item,colors)
    rng=Random(ident+" silhouette")
    wide={"titan":1.31,"bulwark":1.22,"regent":1.06,"smith":1.19,"runner":.857,
          "seer":.88,"spirit":.92,"banner":1.00}.get(shape,1.)
    wide*=rng.uniform(.972,1.04)
    if ident=="marcus":
        wide *= 1.186
    if ident=="akari":
        wide *= .931
    if ident=="thekla":
        wide *= .961
    root=empty("Figure")
    root.scale=(1.0 if hero else .91,)*3
    body_height=.945 if shape!="titan" else .987
    body=empty("Body",(0,.009,body_height),root)
    body.scale=(.86,.87,1.)
    shoulder=.266*wide
    head=empty("Head",(0,-.018,.457),body)
    head.scale=((.603 if hero else .586)+rng.uniform(-.016,.014),)*3
    shell("Soft neck above the collar",[(.400,.081,.070,0,.001),(.457,.062,.063,0,-.010),
          (.493,.063,.058,0,-.014)],m["body"],body,10,True)
    mantle=empty("Mantle",(0,.149,.391),body)
    plated=torso(body,m,armor,wide,crest,hero,ident)
    if hero or armor in ("robe","travel","hakama"):
        cape(item,mantle,.297*wide,m)
        for side in (-1,1):
            pin("Cloak clasp",(side*.17,-.135,.367),.038,m["gold"],body)
    if ident in ("thekla","marcus"):
        s=1 if ident=="thekla" else -1
        points=[(s*x,y,z) for x,y,z in [
            (-.199,.036,.359),(-.178,-.102,.405),(.208,-.132,.411),(.299,-.017,.353),
            (.231,.163,.325),(-.147,.165,.386),(-.121,-.199,.282),(.089,-.221,.303),(.277,-.167,.248),
        ]]
        faces=[(0,1,6),(1,2,7,6),(2,3,8,7),(3,4,8),(4,5,2,3),(5,0,1,2)]
        scarf=mesh_object("Cross-body draped wool clasp",points,faces,m["accent"],body)
        scarf.modifiers.new("Folded wool edge","SOLIDIFY").thickness=.030
        curve("Contrasting border of the mantle",body,[points[i] for i in (6,7,8,4)],
              [.013,.019,.015,.010],m["fillet"],7)
        pin("Hammered fibula by the mantle fold",(s*.149,-.227,.316),.056,m["fillet"],body)
    boots(root,wide,m,armor,theme,ident,body_height-.035)
    beard=ident in ("marcus","nikandros","daedalon","vindex","severus","keraunos","centurion","yamabushi","riku","promachos")
    face=(1.069 if beard else .973)+rng.uniform(-.042,.036)
    sculpt_head(head,m,ident,face,beard)
    hair_cap(head,m,style,face,theme,ident)
    headpiece(head,m,style,theme,face,crest,hero,ident)
    if hero and ident not in ("thekla","marcus","akari"):
        hero_regalia(item,body,head,mantle,m,wide,crest)
    hands=[]
    for side,label in ((-1,"LeftArm"),(1,"RightArm")):
        arm=empty(label,(side*shoulder,-.005,.310),body)
        arm.scale=(.89,.91,1.07)
        arm.rotation_euler.y=-.08*side
        hands.append(armor_arm(arm,side,m,plated,theme=="japan",hero,ident))
    weapon(hands[1],body,tool,m,crest,hero,ident)
    if tool in ("spear","sword","javelin") and (plated or hero) and theme!="japan":
        shield(hands[0],m,theme,crest,1.13 if hero else .89,hero)
    elif hero or armor in ("travel","tunic","robe"):
        pouch=empty("Fastened personal kit",(-.237,.041,-.145),body)
        cut("Lacquered small kit",pouch,(0,0,0),(.091,.096,.143),m["leather"],2)
        for dz in (-.047,.04):
            block("Textile keeper straps",(0,-.094,dz),(.125,.032,.027),m["gold"],pouch,.008)
    harness(item,body,m,wide)
    if style=="fox":
        for side in (-1,1):
            points=[(side*.053,.177,-.24),(side*.177,.295,-.12),(side*.30,.387,.077),(side*.32,.434,.235)]
            curve("Foxtail with angled tufts",mantle,points,[.082,.110,.081,.023],m["fabric"],8)
    return root,shape,tool
