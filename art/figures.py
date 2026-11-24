"""Sculpted faction figures. Colours, garments and insignia are set by character."""
from math import cos, exp, pi, sin, sqrt, tau
from random import Random

from mathutils import Vector

from forge import empty, material, span, stone
from geometry import bevel_block as block, mesh_object, shell, silhouette, torus_mesh, volume

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
    _,_,fabric,trim,_=colors
    faction=item["theme"]
    rng=Random(item["id"]+" complexion")
    skin=rng.choice(("c99670","c88965","ae7857","e0ae8b","ad7559","d79e80"))
    if item["id"] in ("thekla","akari","marcus"):
        skin={"thekla":"ca9472","akari":"dfaa88","marcus":"b8805e"}[item["id"]]
    dark={"aegean":"333f41","rome":"463538","japan":"343749"}[faction]
    gold={"aegean":"c8a260","rome":"c39659","japan":"c9a971"}[faction]
    edge={"aegean":"eed79b","rome":"e3bc7d","japan":"e7ca8d"}[faction]
    hair=rng.choice(("382e2e","382e35","332f38","553933","443231"))
    return {name:material(name,color,metallic) for name,color,metallic in [
        ("fabric",fabric,0),("accent",trim,0),("body",skin,0),("blush","9e5f50",0),
        ("hair",hair,0),("hair edge","544349",0),("hem",dark,0),("belt","695247",0),
        ("leather","825d48",0),("boots","4a3b34",0),("gold",gold,.22),("fillet",edge,.17),
        ("steel","b5bab8",.35),("dark iron","656e70",.31),("antique white","e8dfc4",0),
        ("sclera","eee4d0",0),("iris","463e33",0),("pupil","242627",0),("wood","715041",0),
    ]}


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
    for a,b,r,s in zip(points,points[1:],radii,radii[1:]):
        span(name,a,b,r,mat,parent,sides,s)


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


def head_mesh(head,m,broad,masculine):
    profile=[
        (.005,.077,.092,.014),(.036,.125,.119,.006),(.075,.167,.142,.003),
        (.129,.190,.162,.002),(.183,.205,.174,.008),(.225,.203,.184,.014),
        (.259,.200,.184,.019),(.297,.202,.187,.024),(.345,.193,.181,.030),
        (.394,.164,.149,.041),(.435,.101,.107,.045),(.45,.039,.055,.045),
    ]
    rings=[]
    for z,rx,ry,cy in profile:
        row=[]
        for i in range(32):
            t=i*tau/32-pi/2
            x=broad*rx*cos(t)
            y=cy+ry*sin(t)
            if sin(t)<-.69:
                y-=exp(-(x/.043)**2)*exp(-((z-.187)/.055)**2)*.053
                y+=exp(-((abs(x)-.081)/.041)**2)*exp(-((z-.237)/.034)**2)*.011
                y-=exp(-((abs(x)-.135)/.054)**2)*exp(-((z-.158)/.047)**2)*.009
            row.append((x,y,z))
        rings.append(row)
    volume("Single sculpted face, nose, jaw and sockets",rings,m["body"],head,True)
    for side in (-1,1):
        x=side*.078*broad
        eye=cut("Dark eye socket",head,(x,-.153,.237),(.043,.016,.023),m["hair"],2,True)
        eye.rotation_euler.y=-side*.1
        cut("Warm off-white eyeball",head,(x,-.163,.236),(.031,.012,.0128),m["sclera"],2,True)
        cut("Coloured iris",head,(x+.004,-.173,.236),(.012,.006,.013),m["iris"],2,True)
        cut("Pupil",head,(x+.004,-.178,.236),(.0067,.0035,.0091),m["pupil"],2,True)
        cut("Eye catchlight",head,(x+.001,-.181,.241),(.0031,.0018,.0029),m["sclera"],1)
        curve("Upper lid at the brow line",head,[(x-side*.033,-.161,.236),(x,-.172,.248),
              (x+side*.034,-.150,.240)],[.005,.007,.0055],m["hair"],6)
        curve("Raised brow",head,[(x-side*.039,-.158,.269),(x,-.166,.280),(x+side*.043,-.139,.267)],
              [.010,.014,.006],m["hair"],6)
        cut("Outer ear",head,(side*.195*broad,.013,.169),(.049,.046,.073),m["body"],2,True)
        cut("Recess of ear",head,(side*.219*broad,-.013,.165),(.023,.025,.040),m["blush"],2,True)
    curve("Small carved half smile",head,[(-.052,-.134,.098),(-.022,-.147,.093),(.011,-.150,.094),(.050,-.136,.103)],
          [.004,.007,.007,.005],m["blush"])
    if masculine:
        for i in range(7):
            x=(i-3)*.035*broad
            y=-.143+(abs(x)*.23)
            b=cut("Faceted boxed beard",head,(x,y,.069+abs(x)*.21),(.055,.042,.078),m["hair"],1,True)
            b.rotation_euler.y=-x*2


def hair_cap(head,m,style,broad):
    shell("Sculpted central hair mass",[
        (.247,.193*broad,.17,0,.034),(.304,.209*broad,.179,0,.033),(.389,.194*broad,.166,0,.039),
        (.449,.146*broad,.115,0,.036),(.481,.053,.050,.007,.025),
    ],m["hair"],head,16,True)
    for i in range(5):
        x=(-.143+.068*i)*broad
        top=.404+.033*sin(.6*i)
        lock=silhouette("Sculpted sweep of the fringe",[(x-.031,top-.016),(x+.028,top+.022),
            (x+.077,top-.024),(x+.017,top-.087),(x-.038,top-.110)],.045,
            m["hair"] if i%2 else m["hair edge"],head)
        lock.location.y=-.146+abs(x)*.18
        lock.rotation_euler.z=-x*.61
    if style in ("braid","moon","ribbon","corinthian"):
        for side in (-1,1):
            curve("Tied sculpted braid",head,[(side*.143,.046,.357),(side*.179,.117,.278),
                  (side*.196,.175,.229),(side*.151,.240,.193)], [.056,.051,.043,.031],m["hair"],8)
        cut("Knot of the bun",head,(0,.207,.318),(.130,.098,.125),m["hair"],2)
        for i in range(5):
            a=i*tau/5
            cut("Fold of the bun",head,(cos(a)*.075,.242,.315+sin(a)*.078),
              (.061,.048,.065),m["hair edge"] if i%2 else m["hair"],1,True)
    if style in ("ribbon","braid","veil"):
        for side in (-1,1):
            ribbon=empty("Knotted ribbon",(side*.055,.19,.275),head)
            ribbon.rotation_euler.y=.18*side
            fabric_panel("Dyed hanging hair tie",ribbon,.052,.08,.29,.055*side,.118,m)


def headpiece(head,m,style,theme,broad,medal,hero):
    if style in ("bronze","corinthian","galea","crest","kabuto"):
        helmet=m["dark iron"] if style=="galea" else m["gold"] if theme!="japan" else m["hem"]
        shell("Hammered open-faced helmet",[
            (.298,.218*broad,.198,0,.039),(.334,.234*broad,.202,0,.042),
            (.404,.206*broad,.183,0,.051),(.468,.150*broad,.136,0,.043),
            (.506,.079*broad,.072,0,.041),(.519,.037,.045,0,.046)
        ],helmet,head,16,True)
        trim_height=.322
        torus_mesh("Helmet circlet seam",(0,.032,trim_height),.208,.016,m["fillet"],head,18)
        for side in (-1,1):
            if theme=="japan":
                for row in range(3):
                    plate=block("Layered lacquered helmet shikoro",(side*(.168+.016*row),.067,.328-.053*row),
                         (.105,.273,.057),m["dark iron"],head,.014)
                    plate.rotation_euler.y=side*.26
                    span("Red shikoro lacing",(side*(.215+.015*row),-.065,.324-.053*row),
                         (side*(.215+.015*row),.192,.324-.053*row),.012,m["accent"],head,6)
            else:
                cheek=silhouette("Sculpted hammered cheek wing",[(.116,.298),(.221,.322),(.226,.200),
                      (.173,.139),(.126,.177),(.146,.227)],.046 if hero else .025,helmet,head)
                if side<0:
                    cheek.scale.x=-1
                cheek.location.y=-.083
                pin("Faceguard boss",(side*.174,-.112,.230),.022,m["fillet"],head)
        if style=="corinthian":
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
        for side in (-1,1):
            fabric_panel("Folded covering beside face",head,.114,.105,.43,side*.037,.12,m,
                         center=(side*.134,-.052,.414))
    elif style in ("moon","solar","laurel","ribbon"):
        if style=="moon":
            pts=[(.148*cos(a),-.148,.486+.115*sin(a)) for a in [pi*(.92+i*.145) for i in range(9)]]
            curve("Open crescent crest",head,pts,[.024]+[.027]*7+[.010],m["fillet"],8)
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
        ],m["gold"] if armor=="muscle" else m["antique white"],body,16,True)
        for side in (-1,1):
            curve("Diagonal linen shoulder binding",body,[(side*.152,-.193,.382),(side*.109,-.212,.278),
                  (-side*.194,-.194,.077)],[.027,.030,.029],m["belt"],7)
    elif armor in ("scale","segments","lamellar"):
        for row in range(5):
            h=.066+row*.073
            rad=(.247+.012*row)*wide
            if armor=="segments":
                shell("Overlapping curved iron segment",[(h-.042,rad,.189,0,.011),(h,rad+.013,.204,0,.008),
                    (h+.035,rad-.004,.194,0,.011)], m["dark iron"] if row%2 else m["steel"],body,14)
            else:
                for index in range(8):
                    angle=(index-3.5)*.41
                    plate=block("Hand-laced lamellar panel",(sin(angle)*rad,-cos(angle)*.186,h),(.083*wide,.049,.086),
                          m["hem"] if armor=="lamellar" and row%2 else m["dark iron"] if armor=="lamellar" else m["gold"],body,.014,angle)
                    pin("Lamellar silk knot",(sin(angle)*rad,-cos(angle)*.208,h+.015),.013,m["accent"],body)
    else:
        for sign in (-1,1):
            curve("Folded edge of layered tunic",body,[(sign*.176,-.132,.403),(sign*.143,-.174,.295),
                  (-sign*.133,-.193,.113),(-sign*.196,-.154,-.035)],[.035,.031,.028,.024],
                  m["antique white"] if armor in ("robe","kimono","hakama") else m["accent"],7)
    shell("Heavy stitched crossbelt",[
        (-.120,.233*wide,.164,0,0),(-.095,.259*wide,.179,0,0),
        (-.031,.249*wide,.172,0,0),(-.017,.231*wide,.166,0,0)],m["belt"],body,16,True)
    block("Inlaid fibula at the centre sash",(0,-.182,-.066),(.145,.058,.102),m["gold"],body,.025)
    emblem(crest,body,0,-.215,-.064,.23,m)
    if ident=="akari":
        for side in (-1,1):
            shell("Pleated indigo hakama with split stride",[
                (-.632,.151,.201,side*.147,.018),(-.597,.173,.213,side*.158,.028),
                (-.392,.159,.194,side*.144,.022),(-.121,.111,.162,side*.087,0)
            ],m["hem"],body,9,False,pi/9)
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
                p=(sin(a)*(.236+row*.038)*wide,-cos(a)*(.166+row*.036),-.186-row*.137)
                t=block("Fanned hanging leather lappet",p,(.107*wide,.071,.221),
                      m["leather"] if row==0 else m["belt"],body,.023,a)
                t.rotation_euler.x=-.19 if armor!="lamellar" else -.11
                pin("Bright metal lappet pin",(p[0],p[1]-.032,p[2]-.063),.018,m["fillet"],body)
    if hero or plated:
        p=cut("Medallion with chased edge",body,(0,-.212,.291),(.079,.031,.077),m["gold"],2)
        emblem(crest,body,0,-.249,.289,.24,m)
    return plated


def armor_arm(arm,side,m,plated,japan,hero):
    limb("Upper arm with sculpted seam",arm,(0,-.009,-.018),(side*.054,-.025,-.249),
        [(0,.097,.093),(.20,.119,.110),(.57,.095,.087),(.87,.078,.077),(1,.072,.070)],
        m["fabric"] if japan or not plated else m["body"])
    if plated or hero:
        for row in range(3 if japan else 2):
            p=(side*(.045+.014*row),.005,-.008-.071*row)
            if japan:
                pad=block("Lacquered shoulder lamella",(p[0]+side*.029,-.004,p[2]),(.223,.266-.026*row,.061),
                          m["dark iron"],arm,.026)
                pad.rotation_euler.y=side*.36
                span("Dyed silk shoulder lacing",(p[0]-.068,-.111+row*.008,p[2]+.012),
                     (p[0]+.079,-.112+row*.008,p[2]-.015),.015,m["accent"],arm,7)
            else:
                pad=cut("Layered bevelled pauldron",arm,p,(.134-.002*row,.137-.009*row,.077),
                        m["gold"] if row==0 else m["dark iron"],2)
                pad.rotation_euler.y=side*.19
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


def boots(root,wide,m,armor,theme):
    for side,label in ((-1,"LeftLeg"),(1,"RightLeg")):
        leg=empty(label,(side*.158*wide,.02,.795),root)
        booted=theme=="japan" or armor in ("leather","tunic","travel")
        limb("Tapered trousers" if booted else "Tailored leg",leg,(0,0,.024),(side*.027,.014,-.463),
            [(0,.115,.106),(.23,.117,.11),(.61,.091,.087),(.88,.081,.077),(1,.079,.074)],
            m["hem"] if booted else m["body"])
        guard=side*.031
        limb("Strapped greave",leg,(guard,-.005,-.373),(guard*1.4,-.016,-.691),
            [(0,.082,.076),(.26,.098,.083),(.74,.079,.072),(1,.064,.066)],
            m["dark iron"] if theme=="japan" else m["gold"])
        foot=cut("Deliberately shaped sandal or boot",leg,(guard*1.4,-.091,-.720),(.103,.174,.083),m["boots"],2,True)
        sole=block("Stitched sole",(guard*1.4,-.084,-.783),(.202,.292,.047),m["belt"],leg,.029)
        for step in range(3):
            belt=block("Criss-cross sandal straps",(guard*1.4,-.145+.053*step,-.655-.011*step),
                  (.181,.035,.026),m["leather"],leg,.012,side*.07)
        pin("Bronze boot clasp",(guard*1.4,-.088,-.61),.028,m["fillet"],leg)


def shield(hand,m,theme,crest,size=1.0):
    parent=empty("Shield fixed to forearm",(0,-.102,-.101),hand)
    parent.scale=(size,)*3
    if theme=="rome":
        for thickness,col in ((.093,m["belt"]),(.063,m["accent"])):
            shell("Curved double scutum shell",[
                (-.465,.207,.061,0,-.004),(-.418,.268,.082,0,-.008),(.381,.270,.091,0,-.014),(.431,.220,.071,0,-.013)
            ],col,parent,12,True)
        for side in (-1,1):
            curve("Rolled scutum border",parent,[(side*.216,-.061,-.435),(side*.257,-.071,-.371),
                  (side*.258,-.073,.363),(side*.212,-.069,.413)],[.031,.022,.024,.023],m["fillet"],9)
        for height in (-.429,.414):
            span("Hammered short edge",( -.205,-.066,height),(.205,-.067,height),.024,m["gold"],parent,8)
        emblem(crest,parent,0,-.113,.03,.91,m)
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
        emblem(crest,parent,0,-.078,0,1.00,m)
    cut("Metal shield boss",parent,(0,-.132,0),(.064,.049,.070),m["fillet"],2)
    for sign in (-1,1):
        span("Rear leather handle",(sign*.16,.051,-.18),(sign*.08,.093,.13),.028,m["belt"],parent,7)


def weapon(hand,hips,kind,m,crest,hero):
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
            blade=silhouette("Planar honed leaf blade",[(0,start),(-.074,start+.091),(arc-.041,peak-.102),
                   (arc,peak),(arc+.067,peak-.096),(.083,start+.11)],.047,m["steel"],hand)
            curve("Raised bronze fuller",hand,[(0,-.027,start+.044),(.025,-.034,start+.183),
                 (arc,-.023,peak-.033)],[.014,.012,.003],m["fillet"],6)
            block("Machined fitted weapon guard",(0,0,start+.006),(.21,.089,.056),m["gold"],hand,.015)
        elif kind=="hammer":
            hammer=block("Weighted bevelled bronze hammer head",(0,0,top),(.49,.29,.31),m["dark iron"],hand,.079)
            for side in (-1,1):
                block("Tapered brass hammer cheek",(side*.208,-.01,top),(.146,.295,.273),m["gold"],hand,.05)
            emblem(crest,hand,0,-.153,top,.46,m)
        elif kind=="staff":
            torus_mesh("Prismatic staff cradle",(0,-.008,top+.12),.139,.034,m["fillet"],hand,16,6,True)
            cut("Polished glass counterweight",hand,(0,-.007,top+.125),(.096,.069,.126),m["accent"],1)
            for side in (-1,1):
                span("Staff prong",(side*.069,0,top-.069),(side*.129,0,top+.125),.028,m["gold"],hand,7,.016)
        elif kind=="banner":
            span("Silk standard crosspiece",(-.243,0,top-.059),(.243,0,top-.059),.036,m["gold"],hand,8)
            pennant=empty("Banner sail",(0,0,top-.064),hand)
            fabric_panel("Split company standard",pennant,.226,.195,.55,.09,.024,m,center=(0,-.011,0),cascade=True)
            emblem(crest,pennant,0,-.058,-.22,.52,m)
            cut("Hammered banner finial",hand,(0,0,top+.073),(.079,.050,.077),m["fillet"],1)
    elif kind=="bow":
        points=[(0,-.157+(sin(pi*i/8)*.26),-.43+i*.123) for i in range(9)]
        curve("Sculpted recurved laminated bow",hand,points,[.023,.030,.035,.042,.045,.043,.035,.029,.022],m["wood"],9)
        span("Bowstring",points[0],points[-1],.010,m["antique white"],hand,5,.010)
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


def humanoid(item):
    ident=item["id"]
    theme=item["theme"]
    colors=WARDROBE[ident]
    armor,style,_,_,crest=colors
    hero=item["kind"]=="hero"
    info=item["model"]
    shape,tool=info["shape"],info["weapon"]
    m=mat_set(item,colors)
    wide={"titan":1.27,"bulwark":1.18,"regent":1.04,"smith":1.15,"runner":.90,"seer":.92,"spirit":.95}.get(shape,1)
    if ident=="marcus":
        wide *= 1.156
    if ident=="akari":
        wide *= .943
    root=empty("Figure")
    root.scale=(.99 if hero else .88,)*3
    body=empty("Body",(0,.009,.83),root)
    shoulder=.274*wide
    head=empty("Head",(0,-.016,.468),body)
    mantle=empty("Mantle",(0,.135,.38),body)
    plated=torso(body,m,armor,wide,crest,hero,ident)
    if hero or armor in ("robe","travel","hakama"):
        fabric_panel("Hand-shaped trailing mantle",mantle,.241*wide,.293*wide,
                     .80 if hero else .61,.10 if theme!="japan" else -.09,.29,m,cascade=True)
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
    boots(root,wide,m,armor,theme)
    masculine=ident in ("marcus","nikandros","daedalon","vindex","severus","keraunos","centurion","yamabushi","riku","promachos")
    head_mesh(head,m,1.09 if masculine else .96,masculine)
    hair_cap(head,m,style,1.09 if masculine else .96)
    headpiece(head,m,style,theme,1.07 if masculine else 1,crest,hero)
    hands=[]
    for side,label in ((-1,"LeftArm"),(1,"RightArm")):
        arm=empty(label,(side*shoulder,-.005,.310),body)
        arm.rotation_euler.y=-.08*side
        hands.append(armor_arm(arm,side,m,plated,theme=="japan",hero))
    weapon(hands[1],body,tool,m,crest,hero)
    if tool in ("spear","sword","javelin") and (plated or hero) and theme!="japan":
        shield(hands[0],m,theme,crest,1.05 if hero else .86)
    elif hero or armor in ("travel","tunic","robe"):
        pouch=empty("Fastened personal kit",(-.237,.041,-.145),body)
        cut("Lacquered small kit",pouch,(0,0,0),(.091,.096,.143),m["leather"],2)
        for dz in (-.047,.04):
            block("Textile keeper straps",(0,-.094,dz),(.125,.032,.027),m["gold"],pouch,.008)
    if style=="fox":
        for side in (-1,1):
            points=[(side*.053,.177,-.24),(side*.177,.295,-.12),(side*.30,.387,.077),(side*.32,.434,.235)]
            curve("Foxtail with angled tufts",mantle,points,[.082,.110,.081,.023],m["fabric"],8)
    return root,shape,tool
