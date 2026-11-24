"""Creatures of the Rift. Their rigs share actions, with different silhouettes and motion."""
from math import cos, pi, sin, tau
from random import Random

from forge import empty, material, span
from figures import cut, curve, emblem, fabric_panel, limb, pin
from geometry import bevel_block as block, mesh_object, shell, silhouette, torus_mesh

TINTS = {
    "reaver": ("584052","997072","b57a61","e5a476","6b4862"),
    "hound": ("3b3948","69616a","8b5664","eaa16c","4f394c"),
    "brute": ("574853","887179","99726b","d8a474","654252"),
    "wisp": ("4e496e","806f98","a38ba7","eab0b4","695774"),
    "herald": ("55414d","987370","ba8785","efb785","774353"),
    "warden": ("46535d","697e83","81a2a0","d4dcbd","516a7d"),
    "moth": ("514463","886d99","a18ba9","e6b877","447e7b"),
    "golem": ("4f484b","756870","a17962","ecab72","714853"),
    "titan": ("4b454e","726779","b58a61","f9b07d","785065"),
}


def palette(item):
    ink,rock,metal,flare,trim=TINTS[item["id"]]
    return {k:material(k,v, r) for k,v,r in [
        ("ink",ink,0),("rock",rock,0),("old gold",metal,.19),("ember",flare,0),("accent",trim,0),
        ("hem",ink,0),("fabric",rock,0),("fillet",metal,.2),("gold",flare,0),("claw","bca58e",0)
    ]}


def spikes(parent,points,m,rng):
    for i,(x,y,z,w,l) in enumerate(points):
        profile=[
            (0.,w,w*.85,0,0),(.36*l,w*.73,w*.70,.032,-.008),
            (l,w*.035,w*.024,.082,.028),
        ]
        shard=shell("Layered chipped obsidian blade",profile,m["rock"] if i%2 else m["accent"],parent,6,False,rng.random()*.98)
        shard.location=(x,y,z)
        shard.rotation_euler.x=rng.uniform(-.25,.45)
        shard.rotation_euler.y=rng.uniform(-.28,.30)+.91*x


def gems(parent,origin,m,spread):
    x,y,z=origin
    for i in range(3):
        shift=(i-1)*spread
        cut("Subsurface amber fracture",parent,(x+shift,y,z+abs(i-1)*.046),
            (.034,.019,.056),m["ember"],1)


def hound(item,m):
    root=empty("Figure")
    root.scale=(.92,)*3
    body=empty("Body",(0,.10,.61),root)
    head=empty("Head",(0,-.50,.119),body)
    tail=empty("Mantle",(0,.54,.047),body)
    rng=Random(item["id"])
    body_parts=[
        ("Rising shoulders",(.0,-.203,.032),(.40,.343,.386),"rock"),
        ("Tapered haunches",(.0,.34,-.043),(.311,.407,.285),"ink"),
        ("Underlapping shale chest",(.0,-.219,-.127),(.302,.354,.230),"accent"),
    ]
    for name,p,size,paint in body_parts:
        cut(name,body,p,size,m[paint],2)
    for side in (-1,1):
        for n in range(4):
            piece=cut("Overlapping volcanic side plate",body,
                 (side*(.255-.034*n),-.22+.192*n,.096+.012*n),
                 (.191,.206,.205-.019*n),m["rock"] if n%2 else m["ink"],1)
            piece.rotation_euler.y=side*.52
        curve("Ember seam on ribs",body,[(side*.351,-.283,.052),(side*.40,-.131,-.044),
            (side*.332,.113,-.033),(side*.291,.233,.055)],[.027,.023,.019,.01],m["ember"],6)
    spikes(body,[(0,-.321+n*.209,.318-.022*n,.16-.012*n,.33-.029*n) for n in range(5)],m,rng)
    cut("Tapered mask of the hound",head,(0,-.088,-.007),(.305,.281,.233),m["rock"],2)
    cut("Forepart of tapered snout",head,(0,-.286,-.137),(.211,.237,.126),m["ink"],2)
    cut("Black nose wedge",head,(0,-.454,-.105),(.111,.095,.074),m["accent"],1)
    for side in (-1,1):
        cut("Slanted ember eye",head,(side*.14,-.293,.014),(.058,.035,.036),m["ember"],2)
        brow=cut("Obsidian ridge over eye",head,(side*.173,-.253,.063),(.104,.092,.045),m["ink"],1)
        brow.rotation_euler.y=side*.34
        curve("Carved sweeping ear",head,[(side*.129,.124,.142),(side*.229,.217,.327),
            (side*.219,.205,.462)],[.113,.084,.008],m["accent"],6)
        for front in (-1,1):
            x=side*(.259 if front<0 else .226)
            z=.577 if front<0 else .486
            y=-.235 if front<0 else .44
            label=("Left" if side<0 else "Right")+("Arm" if front<0 else "Leg")
            leg=empty(label,(x,y,z),root)
            ball=cut("Slanted heavy canine foreleg",leg,(side*.024,0,-.079),(.146,.169,.229),m["rock"],2)
            ball.rotation_euler.x=.30*front
            limb("Shale leg below the joint",leg,(side*.04,.028,-.127),(side*.081,.009,-z+.11),
                 [(0,.114,.104),(.39,.132,.105),(.76,.086,.081),(1,.082,.087)],m["ink"])
            cut("Heavy four-legged paw",leg,(side*.082,-.057,-z+.087),(.141,.161,.095),m["rock"],2)
            for n in range(3):
                t=side*.081+(n-1)*.063
                span("Sharp stone toe",(t,-.12,-z+.081),(t,-.232,-z+.053),.040,m["claw"],leg,6,.012)
    curve("Raised segmented hound tail",tail,[(0,0,0),(.018,.211,.12),(.063,.391,.348),(.132,.419,.52),
          (.212,.305,.596)],[.123,.11,.084,.049,.014],m["accent"],7)
    return root,"hound","fang"


def moth(item,m):
    root=empty("Figure")
    root.scale=(.83,)*3
    body=empty("Body",(0,.04,.85),root)
    head=empty("Head",(0,-.17,.186),body)
    tail=empty("Mantle",(0,.065,-.254),body)
    shell("Chitin abdomen with carved edges",[(-.58,.031,.043,0,.12),(-.462,.101,.122,0,.078),
        (-.211,.149,.153,0,.043),(.061,.173,.167,0,0),(.242,.121,.116,0,-.043)],m["ink"],body,10)
    for i in range(5):
        cut("Tapered and overlapping abdomen scale",body,(0,-.052+.032*i,.042-.115*i),
            (.141-.016*i,.072,.122),m["accent"] if i%2 else m["rock"],1)
    for side in (-1,1):
        cut("Large opal compound eye",head,(side*.091,-.085,.046),(.073,.048,.092),m["ember"],2)
        group=empty("LeftArm" if side<0 else "RightArm",(side*.117,0,.126),body)
        for z,w in ((.0,1.0),(-.212,.69)):
            sl=1 if z==0 else -1
            verts=[(0,0,z),(.27*side,.061,z+.116*sl),(.54*side,.111,z+.255*sl),
                (.89*side,.132,z+.351*sl),(.990*side,.164,z+.284*sl),(.87*side,.194,z+.076*sl),
                (.575*side,.232,z-.083*sl),(.308*side,.165,z-.117*sl)]
            verts=[(x*w,y,z0) for x,y,z0 in verts]
            faces=[(0,1,7),(1,2,6),(1,6,7),(2,3,4),(2,4,5),(2,5,6)]
            if side*sl>0: faces=[tuple(reversed(face)) for face in faces]
            wing=mesh_object("Folded translucent-looking wing facets",verts,faces,None,group)
            for chroma in (m["rock"],m["accent"],m["ink"],m["old gold"]):
                wing.data.materials.append(chroma)
            for f,c in zip(wing.data.polygons,(0,1,0,3,1,2)):
                f.material_index=c
            wing.modifiers.new("Folded wing thickness","SOLIDIFY").thickness=.019
            curve("Tapered wing piping",group,verts[1:],[.020,.014,.012,.013,.013,.018,.011],m["rock"],6)
        curve("Long swept metallic antenna",head,[(side*.052,-.031,.098),(side*.150,-.019,.209),
             (side*.242,.044,.363),(side*.408,.088,.451)],[.021,.019,.015,.007],m["old gold"],7)
        pin("Antenna cap",(side*.408,.085,.450),.023,m["ember"],head)
        for i in range(3):
            curve("Thin moth legs",body,[(side*.09,-.075,-.08-i*.072),(side*.17,-.207,-.17-i*.082),
                (side*.228,-.22,-.239-i*.073)],[.019,.015,.009],m["rock"],6)
    cut("Angular head and proboscis",head,(0,.008,.067),(.167,.117,.149),m["rock"],2)
    return root,"moth","fan"


def wisp(item,m):
    root=empty("Figure")
    body=empty("Body",(0,0,.81),root)
    rings=empty("Mantle",(0,0,.075),body)
    core=empty("Head",(0,0,.06),body)
    cut("Flickering heart of the ash ghost",core,(0,0,0),(.189,.159,.274),m["ember"],1)
    cut("Outer smoky-hued shard",body,(0,.083,-.06),(.207,.194,.281),m["rock"],2)
    for angle,rad in ((.32,.279),(.95,.34),(1.45,.390)):
        holder=empty("Free orbit of the spirit",(0,0,0),rings)
        holder.rotation_euler=(angle,angle*.7,angle*.88)
        torus_mesh("Tapered hoops of folded brass",(0,0,0),rad,.027,m["old gold"],holder,16,5)
        for n in range(3):
            a=angle+n*tau/3
            spark=cut("Streak at the rim of orbit",holder,(cos(a)*rad,sin(a)*rad,0),
                 (.048,.034,.076),m["ember"],1)
    for side in (-1,1):
        attachment=empty("LeftArm" if side<0 else "RightArm",(side*.15,.031,-.107),body)
        fabric_panel("Trailing remnant of cloth",attachment,.117,.068,.58,side*.142,.196,m,cascade=True)
    return root,"wisp","staff"


def humanoid_foe(item,m):
    ident=item["id"]
    boss=ident in ("golem","titan")
    heavy=boss or ident in ("brute","warden")
    herald=ident=="herald"
    width=1.31 if boss else 1.20 if heavy else .88 if herald else .95
    rng=Random(ident)
    root=empty("Figure")
    root.scale=({"golem":1.25,"titan":1.46,"brute":1.03,"warden":.97}.get(ident,.89),)*3
    body=empty("Body",(0,.015,.81),root)
    head=empty("Head",(0,-.024,.453),body)
    mantle=empty("Mantle",(0,.217,.289),body)
    if herald:
        fabric_panel("Hand-torn ritual mantle",mantle,.254,.384,.89,-.102,.22,m,cascade=True)
    shell("Joined core stones",[
        (-.251,.236*width,.169,0,.055),(-.144,.265*width,.165,0,.04),
        (.008,.232*width,.181,0,.024),(.153,.263*width,.208,0,.011),
        (.355,.326*width,.211,0,.011),(.417,.228*width,.146,0,.008)
    ],m["ink"],body,12)
    cut("Broken breast plate",body,(0,-.154,.228),(.323*width,.117,.209),m["rock"] if not herald else m["accent"],2)
    for side in (-1,1):
        curve("Seam of light in broken chest armour",body,[(side*.199,-.236,.346),(side*.082,-.264,.243),
             (side*.125,-.258,.170),(side*.046,-.23,.108)],[.018,.026,.014,.006],m["ember"],6)
        cut("Split cuirass facet",body,(side*.219,-.14,.283),(.122,.128,.146),m["accent"],1)
        for n in range(3):
            y=-.138+.02*n
            block("Belt tab from an ancient suit",(side*(.059+.084*n),y,-.249),(.084,.060,.232),
                  m["old gold"] if boss else m["accent"],body,.018,side*.21*n)
    if ident=="titan":
        block("Hammered bronze girdle",(0,-.16,.040),(.515,.065,.074),m["old gold"],body,.024)
        emblem("sun",body,0,-.217,.206,.59,m)
    if ident=="golem":
        for n in range(3):
            x=(n-1)*.191
            cut("Open furnace embers",(mantle),(x,.014,.081+abs(n-1)*.067),(.077,.082,.191),m["ember"],1)
    if herald:
        shell("Weathered wrapped cloth lower half",[
            (-.62,.339,.221,0,.058),(-.589,.345,.236,0,.074),
            (-.286,.265,.179,0,.011),(-.125,.223,.179,0,0)],m["accent"],body,10)
    for side,label in ((-1,"Left"),(1,"Right")):
        arm=empty(label+"Arm",(side*.304*width,.017,.307),body)
        cut("Carved shoulder block",arm,(side*.073,.051,.013),(.165*width,.163,.155),m["rock"],2)
        biceps=cut("Forged biceps of layered rock",arm,(side*.046,.020,-.142),(.126*width,.120,.184),m["ink"],1)
        lower=empty(label+"Forearm",(side*.048,-.027,-.244),arm)
        cut("Fractured forearm gauntlet",lower,(side*.034,-.035,-.132),(.126*width,.122,.178),m["rock"],2)
        cut("Heavy angular fist",lower,(side*.081,-.064,-.278),(.112*width,.101,.116),m["old gold"] if boss else m["ink"],1)
        if heavy:
            for n in range(3):
                p=(side*(.034+.064*n),-.043,-.015+(.018 if n==0 else -.011*n))
                pin("Hammered shoulder pin",p,.034,m["old gold"],arm)
            spikes(arm,[(side*.072,.06,.105,.108,.211), (side*.137,.059,.063,.076,.186)],m,rng)
            gems(lower,(side*.04,-.142,-.14),m,.061)
        elif ident=="reaver":
            for n in range(3):
                x=side*.053+(n-1)*.043
                span("Jagged claw of the rift scout",(x,-.072,-.232),(x,-.150,-.395),.025,m["claw"],lower,6,.007)
        leg=empty(label+"Leg",(side*.152*width,.032,.772),root)
        limb("Leg of layered basalt",leg,(0,0,-.031),(side*.039,.008,-.609),
            [(0,.122*width,.117),(.37,.114*width,.121),(.70,.105,.094),(1,.081,.094)],m["ink"])
        cut("Angular knee guard",leg,(side*.02,-.068,-.377),(.115*width,.091,.132),m["rock"],2)
        cut("Carved stony foot",leg,(side*.055,-.078,-.678),(.133*width,.194,.104),m["rock"],2)
        if boss:
            block("Gold-washed foot plate",(side*.049,-.14,-.699),(.265,.142,.091),m["old gold"],leg,.036)
        if ident=="warden" and side<0:
            mirror=empty("Mirror shield mount",(side*.089,-.159,-.179),lower)
            obj=silhouette("Obsidian mirror shield with cut corners",[(0,-.455),(.269,-.266),(.305,.226),(.205,.368),
                 (0,.411),(-.21,.360),(-.306,.240),(-.268,-.278)],.098,m["rock"],mirror)
            torus_mesh("Silvered bevel",(0,-.054,-.006),.236,.034,m["old gold"],mirror,14,5,True)
            cut("Celadon mirror core",mirror,(0,-.067,0),(.200,.067,.214),m["accent"],2)
            emblem("moon",mirror,0,-.144,0,.794,m)
        if (boss or herald) and side>0:
            grip=empty("Clasped weapon",(side*.086,-.073,-.281),lower)
            span("Wear-scarred weapon grip",(0,0,-.39),(0,0,.808 if herald else .51),.065,m["accent"],grip,8,.038)
            if herald:
                torus_mesh("Bell of the Rift",(.045,-.026,.861),.165,.039,m["old gold"],grip,14,6,True)
                cut("Flickering fire within the herald relic",grip,(.046,-.033,.871),(.111,.115,.135),m["ember"],1)
            else:
                block("Precision-cut giant stone hammer",(.012,0,.58),(.511,.302,.311),m["rock"],grip,.080)
                for s in (-1,1):
                    block("Riveted heavy weapon collar",(s*.214,0,.582),(.165,.313,.264),m["old gold"],grip,.063)
                emblem("bolt",grip,.012,-.160,.583,.68,m)
    cut("Angled obsidian skull",head,(0,.013,.188),(.220*width,.169,.195),m["ink"],2)
    cut("Engraved faceted faceplate",head,(0,-.112,.197),(.155*width,.099,.155),m["rock"],2)
    for side in (-1,1):
        eye=cut("Slit of ember colour",head,(side*.087*width,-.196,.201),(.046,.017,.029),m["ember"],2)
        eye.rotation_euler.y=side*.37
        if not boss:
            curve("Rift helmet fin or horn",head,[(side*.149,.041,.291),
                 (side*.224,.093,.419),(side*.257,.127,.518)],[.080,.064,.009],m["accent"],6)
    if ident=="titan":
        for i in range(5):
            x=(i-2)*.094
            h=.542 if i==2 else .465-.022*abs(i-2)
            p=block("Asymmetrical gilded crown pylon",(x,.032,h),(.103,.094,.224 if i==2 else .173),
                m["old gold"],head,.034)
            p.rotation_euler.y=x*.68
            pin("Crown prism",(x,-.030,h-.028),.035,m["ember"],head)
    elif ident=="golem":
        spikes(head,[(-.134,0,.346,.114,.207),(.024,.033,.346,.11,.291),(.144,.057,.318,.081,.208)],m,rng)
    return root, "titan" if boss else "spirit" if herald else "bulwark", "staff" if herald else "hammer" if heavy else "sword"


def enemy_model(item):
    m=palette(item)
    builder={"moth":moth,"hound":hound,"wisp":wisp}.get(item["id"],humanoid_foe)
    return builder(item,m)
