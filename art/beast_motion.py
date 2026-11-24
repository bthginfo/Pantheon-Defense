"""Foot-planted walk cycles with articulated knees, ankles and paws."""
from math import acos, atan2, cos, hypot, pi, sin, tau


def limited_cos(value):
    return acos(max(-1.,min(1.,value)))


def step(phase, first, second, hip_height, width, lift, rise, front=1.):
    stance=.58
    if phase<stance:
        y=width*(phase/stance-.5)
        z=0.
        toe=.16*sin(pi*phase/stance)*max(0.,(phase/stance-.68)/.32)
    else:
        swing=(phase-stance)/(1.-stance)
        y=width*(.5-(3.*swing*swing-2.*swing*swing*swing))
        z=lift*sin(pi*swing)**1.32
        toe=-.20*sin(tau*swing)
    down=hip_height+rise-z
    reach=min(first+second-.006,hypot(down,y))
    thigh=atan2(y,down)-front*limited_cos((first**2+reach**2-second**2)/(2*first*reach))
    knee=front*(pi-limited_cos((first**2+second**2-reach**2)/(2*first*second)))
    return thigh,knee,toe-thigh-knee


def ground_walk(item, pose):
    family=item.get("archetype",item["id"])
    heavy=family in ("brute","warden","golem","titan")
    duration=41 if heavy else 33
    frames={}
    for frame in range(1,duration+1,2):
        t=(frame-1)/(duration-1)
        sway=sin(tau*t)
        rise=(.020 if heavy else .028)*(.5-.5*cos(2*tau*t))
        lean=.057 if heavy else .042
        frame_pose={
            "Figure":pose((0.,0.,rise)),
            "Body":pose((.020*sway,0.,0.),(lean,.046*sway,-.082*sway)),
            "Head":pose(rotation=(-lean*.6,-.035*sway,.064*sway)),
            "LeftArm":pose(rotation=(-.25*sway,.028,.105)),
            "RightArm":pose(rotation=(.23*sway,-.032,-.091)),
            "Mantle":pose(rotation=(.11+.061*sin(2*tau*t),-.031*sway,.072*sway)),
        }
        for label,cycle in (("Left",t%1.),("Right",(t+.5)%1.)):
            thigh,knee,toe=step(cycle,.357,.326,.601,.410 if heavy else .447,
                                .100 if heavy else .132,rise)
            frame_pose[label+"Leg"]=pose(rotation=(thigh,.035 if label=="Left" else -.035,0.))
            frame_pose[label+"Shin"]=pose(rotation=(knee,0,0))
            frame_pose[label+"Foot"]=pose(rotation=(toe,0,0))
        frames[frame]=frame_pose
    return duration,frames


def hound_trot(pose):
    frames={}
    duration=29
    for frame in range(1,duration+1,2):
        t=(frame-1)/(duration-1)
        sway=sin(tau*t)
        rise=.028*(.5-.5*cos(2*tau*t))
        body={
            "Figure":pose((0,0,rise)),
            "Body":pose((0,0,.015*sin(2*tau*t)),(.07*cos(2*tau*t),.052*sway,0)),
            "Head":pose(rotation=(-.062*cos(2*tau*t),.013,.036*sway)),
            "Mantle":pose(rotation=(.06*cos(tau*t),0,.22*sin(tau*t-.32))),
        }
        for label,offset,hip,forward in (("LeftArm",0.,.577,1.),("RightArm",.5,.577,1.),
                                        ("LeftLeg",.58,.486,-1.),("RightLeg",.08,.486,-1.)):
            upper=hip*.49
            lower=hip-.089-upper
            thigh,knee,toe=step((t+offset)%1.,upper,lower,hip-.151,.380,.099,rise,forward)
            body[label]=pose(rotation=(thigh,0.,0.))
            body[label+"Lower"]=pose(rotation=(knee,0.,0.))
            body[label+"Paw"]=pose(rotation=(toe,0.,0.))
        frames[frame]=body
    return duration,frames
