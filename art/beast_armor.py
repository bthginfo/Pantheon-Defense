"""Regional armour for the Rift forces, sculpted against the Blender turnaround."""
from math import cos, pi, sin

from commander_forms import relief, strips
from figures import cut, curve, emblem, pin
from forge import empty, material, span
from geometry import bevel_block as block, mesh_object, shell


COLOURS = {
    "aegean": ("ead0a4", "549a8e", "ba674e", "293c55", "b3f6db"),
    "rome": ("b1956d", "806253", "ac493e", "462c36", "ffd498"),
    "japan": ("e8d4ae", "56817b", "ab4944", "293a55", "ffbc76"),
}


def regional_paints(theme):
    out = {}
    bindings = ("ivory","glaze","madder","cloth","light")
    strokes = ("linen light","verdigris","faded madder","teal lining","")
    for key, rgb, brush in zip(bindings,COLOURS[theme],strokes):
        surface = material("Rift "+key,rgb,.23 if key=="glaze" else 0.)
        surface["Surface variation"] = .17 if key!="light" else .026
        if brush:
            surface["Brush pigment"] = brush
        out[key] = surface
    return out


def plate(name, parent, outline, pigment, rim, y, lift=.034, curve=.0):
    return relief(name,parent,outline,lambda x,z,d:(x,y+abs(x)*curve-d,z),pigment,rim,lift,.10)


def helmet_crest(head, m, across, width, height):
    """The wide Roman crest and the narrow Greek ridge share a faceted construction."""
    count = 10
    coords, faces = [], []
    for thickness in (-.049,.049):
        for step in range(count+1):
            a = (-1.27+2.54*step/count)
            for rise in (.55,1.):
                u = width*sin(a)*rise
                v = .290 + height*cos(a)*rise
                coords.append((u,thickness+.008,v) if across else (thickness,u+.040,v))
    stride = (count+1)*2
    for step in range(count):
        i = step*2
        faces.extend(((i,i+2,i+3,i+1),(i+1,i+3,stride+i+3,stride+i+1),
                      (stride+i,stride+i+1,stride+i+3,stride+i+2)))
    faces.extend(((0,1,stride+1,stride),(stride-2,2*stride-2,2*stride-1,stride-1)))
    crest = mesh_object("Painted crested helmet",coords,faces,None,head)
    for swatch in (m["madder"] if across else m["cloth"],m["accent"],m["old gold"]):
        crest.data.materials.append(swatch)
    for face in crest.data.polygons:
        face.material_index = 2 if face.index in (1,len(faces)-1) else int(face.index%6==3)
    crest.data.polygons[-1].material_index = 1


def eyes(head, m, wide, amber):
    for sign in (-1,1):
        outline = [(sign*x*wide,z) for x,z in ((.046,.245),(.143,.270),(.159,.238),(.071,.214))]
        plate("Dark seam under the brow",head,outline,m["ink"],None,-.247,.009,.28)
        inset = [(sign*x*wide,z) for x,z in ((.057,.243),(.132,.255),(.136,.240),(.069,.227))]
        plate("Luminous eye in the mask",head,inset,m["light"] if amber else m["ember"],None,-.261,.010,.28)


def aegean_mask(head, m, scale, crest):
    shell("Salt-etched Corinthian helmet",[(.252,.194*scale,.128,0,.022),(.344,.206*scale,.159,0,.017),
          (.397,.159*scale,.122,0,.035),(.428,.087*scale,.081,0,.051)],m["ink"],head,10,False)
    outer=[(-.169,.291),(-.108,.353),(0,.365),(.108,.353),(.169,.291),(.155,.132),
           (.114,.063),(.057,.089),(.049,.168),(0,.129),(-.049,.168),(-.057,.089),(-.114,.063),(-.155,.132)]
    plate("Rim of weathered bronze on the blue Greek mask",head,[(x*scale,z) for x,z in outer],m["glaze"],m["old gold"],-.231,.033,.30)
    plate("Nasal keel angled like a ship's bow",head,[(-.059,.296),(0,.342),(.060,.296),(.020,.178),(0,.152),(-.020,.178)],
          m["old gold"],m["ivory"],-.269,.042,.42)
    eyes(head,m,scale,True)
    if crest < 7:
        helmet_crest(head,m,False,.252+.02*max(0,crest),.248 if crest>=5 else .209)
    for side in (-1,1):
        curve("Salt-bright edge of the helmet",head,[(side*.148,-.166,.284),(side*.223,-.066,.32),
             (side*.209,.113,.382),(side*.127,.167,.402)],[.019,.026,.019,.007],m["old gold"],6)


def rome_mask(head, m, scale, crest):
    shell("Blackened iron legion helmet",[(.254,.203*scale,.163,0,.015),(.336,.202*scale,.184,0,.019),
          (.397,.166*scale,.156,0,.030),(.428,.099*scale,.085,0,.030)],m["rock"],head,12,False)
    outline=[(-.181,.291),(-.145,.341),(.145,.341),(.181,.291),(.16,.093),(.093,.079),(0,.130),(-.093,.079),(-.16,.093)]
    plate("Cast bronze hypocentre mask",head,[(x*scale,z) for x,z in outline],m["ink"],m["old gold"],-.236,.031,.19)
    plate("Copper bridge down to the chin",head,[(-.077,.171),(.001,.237),(.08,.172),(.084,.098),(0,.059),(-.084,.098)],
          m["rock"],m["glaze"],-.254,.035,.27)
    eyes(head,m,scale,True)
    block("Scorched brow band", (0.,-.190,.313),(.365*scale,.088,.047),m["old gold"],head,.012)
    helmet_crest(head,m,True,.368 if crest>=5 else .317,.272 if crest>=5 else .218)
    for sign in (-1,1):
        pin("Copper pin at the temple",(sign*.179*scale,-.159,.27),.040,m["ivory"],head)


def oni_mask(head, m, scale, crest):
    jaw=[(-.189,.304),(-.115,.355),(0,.326),(.115,.355),(.189,.304),(.175,.180),(.119,.075),
         (.071,.082),(.047,.057),(0,.051),(-.047,.057),(-.071,.082),(-.119,.075),(-.175,.180)]
    plate("Carved ivory oni mask",head,[(x*scale,z) for x,z in jaw],m["ivory"],m["old gold"],-.233,.052,.40)
    plate("Sleeping mouth beneath the mask",head,[(-.112,.131),(-.058,.159),(0,.125),(.052,.151),(.119,.134),(.071,.084),(-.071,.084)],
          m["ink"],m["madder"],-.284,.012,.21)
    eyes(head,m,scale,True)
    plate("Red brush mark across the helmet",head,[(-.092,.301),(-.043,.328),(0,.288),(.043,.328),(.093,.299),(0,.256)],
          m["madder"],None,-.285,.012,.26)
    for sign in (-1,1):
        curve("Tusk tracing the cheek of the shrine guard",head,[(sign*.079,-.276,.100),(sign*.135,-.296,.109),
              (sign*.174,-.277,.173),(sign*.161,-.237,.218)],[.031,.037,.023,.004],m["ivory"],6)
        curve("Heavy forked oni horn",head,[(sign*.145,-.037,.274),(sign*.243,.028,.365),
              (sign*.315,.121,.470),(sign*.283,.184,.583+.04*(crest>=5))],
              [.110,.084,.058,.004],m["ink"],6)
        for row in range(3):
            fan=cut("Carved ivory mane tips",head,(sign*(.175+.036*row),.077+.094*row,.275-.074*row),
                    (.120,.154,.099),m["ivory"] if row else m["edge"],1)
            fan.rotation_euler.y=sign*(.52-.14*row)


def armour(parts, theme, m, crest, wide):
    body, mantle = parts["Body"], parts["Mantle"]
    colours = {
        "aegean": (m["glaze"],m["accent"],m["old gold"]),
        "rome": (m["rock"],m["madder"],m["old gold"]),
        "japan": (m["cloth"],m["glaze"],m["madder"]),
    }[theme]
    for level in range(3):
        z=.339-level*.109
        size=(.30-.020*level)*wide
        crestline = [(-size,z),(-size*.72,z-.097),(0,z-.129),(size*.72,z-.097),
                     (size,z),(size*.47,z+.063),(-size*.47,z+.063)]
        plate("Overlapping regional breastplate",body,crestline,colours[level%2],colours[2],
              -.258+level*.008,.053,.21)
    closure = plate("Metal and carnelian belt clasp",body,[(-.079,-.095),(0,-.068),(.079,-.095),(.051,-.150),(-.051,-.150)],
                    m["old gold"],m["ivory"],-.254,.031)
    cut("Small light sunk in the belt clasp",body,(.0,-.288,-.112),(.030,.021,.032),m["light"],1)
    for side,label in ((-1,"Left"),(1,"Right")):
        guard=parts[label+"Arm"]
        for level in range(3):
            length=(.285-.022*level)*wide
            width=.129+.012*(crest>=5)
            z=.200-.105*level
            def shoulder(u,t):
                a=(u*2.-1)*1.31
                return side*(.032+length*t), width*sin(a)+.029*t,z-.20*t+cos(a)*(.068-.014*t)
            strips("Layered carved shoulder armour",guard,[0,.22,.51,.79,1.],[0,.14,.82,1.],shoulder,
                   [colours[level%2],m["ivory"] if theme=="aegean" else colours[2]],
                   lambda u,t:int(t>.79 or u>.76),lining=.044,smooth=False,reverse=side<0)
        accent= m["ivory"] if theme=="aegean" else m["old gold"]
        if theme=="aegean":
            curve("Hooked shell ridge on the shoulder",guard,[(side*.05,-.119,.216),(side*.138,-.103,.287),
                  (side*.256,-.028,.313),(side*.337,.093,.255)],[.092,.081,.058,.007],m["ivory"],7)
            curve("Coral tucked into the lower armour",guard,[(side*.089,.020,.207),(side*.141,.014,.296),
                  (side*.11,-.049,.379)],[.039,.031,.006],m["madder"],6)
        elif theme=="japan":
            curve("Vermilion rope holding the shoulder plates",guard,[(side*.066,-.143,.198),(side*.117,-.157,.075),
                  (side*.118,-.168,-.022)],[.035,.031,.025],m["madder"],6)
        else:
            block("Broad red cast top to the segmented shoulder", (side*.102,.0,.183),
                  (.221,.360,.104),m["madder"],guard,.034,side*.23)
        pin("Large bronze buckle", (side*.234*wide,-.259,.314), .052, accent,body)
        trim_outline=[(side*x,z) for x,z in ((.051,-.136),(.173,-.145),(.245,-.226),(.194,-.459),(.105,-.506),(.061,-.379))]
        plate("Jointed thigh plate over painted cloth",body,trim_outline,colours[0],colours[2],-.197,.032,.32)
        greave=parts.get(label+"Shin",parts[label+"Leg"])
        outline=[(-.073,-.071),(.066,-.066),(.073,-.245),(0,-.282),(-.079,-.229)]
        plate("Painted bevel along the shin",greave,outline,m["glaze"] if theme=="aegean" else colours[0],
              m["old gold"],-.103,.023,.18)
    def cloak(u,t):
        axis=u*2.0-1.0
        return axis*(.337+.114*t)*wide,.059+.207*t-.098*axis*axis,-.035-t*.547+.067*cos(u*12.)*t
    strips("Scalloped coloured fabric down the back",mantle,[0,.12,.29,.5,.71,.88,1.],[0,.20,.79,.91,1.],
           cloak,[m["cloth"] if theme=="aegean" else m["madder"],colours[2],m["hem"]],
           lambda u,t: 1 if t>.80 else 2 if u<.11 or u>.89 else 0,lining=.019,smooth=False)
    clasp=empty("Back insignia",(0,.174,-.220),mantle)
    clasp.rotation_euler.z=pi
    emblem({"aegean":"wave","rome":"wing","japan":"moon"}[theme],clasp,0,-.029,.00,.41,m)


def finish_guards(root, theme, family, crest, m):
    parts={part.name:part for part in root.children_recursive if part.type=="EMPTY"}
    boss = crest>=5
    wide = 1.26 if boss else 1.09
    head = parts["Head"]
    if theme=="aegean":
        aegean_mask(head,m,wide,crest)
    elif theme=="rome":
        rome_mask(head,m,wide,crest)
    else:
        oni_mask(head,m,wide,crest)
    armour(parts,theme,m,crest,wide)
    if boss:
        for level in range(2):
            y=.15+.084*level
            cut("Incandescent prism at the back of the crown",head,(0,y,.54+.13*level),
                (.119-.019*level,.086,.157),m["light"] if level else m["glaze"],1)
        if crest>=8:
            for side in (-1,1):
                curve("Swept crest blade of the end boss",head,[(side*.22,.05,.31),(side*.282,.124,.491),
                      (side*.383,.189,.635),(side*.315,.192,.820)],
                      [.084,.088,.057,.006],m["old gold"] if theme!="japan" else m["ink"],7)
                span("Incandescent fracture on the engraved crest",(side*.24,-.029,.369),
                     (side*.296,.006,.545),.017,m["light"],head,5,.003)
