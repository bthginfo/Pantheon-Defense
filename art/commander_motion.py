"""Motion keyed from the fitted spear grip and the planted scutum stance."""
from math import sin, tau


def commander_clips(item,pose):
    greek=item['id']=='thekla'
    clips={}
    walk={}
    for frame in (1,5,9,13,17,21,25,29,33):
        cycle=sin(tau*(frame-1)/32)
        lead=sin(tau*(frame-3)/32)
        walk[frame]={
            'Body':pose((0,0,abs(lead)*.021),(.022,.020*cycle,.029*cycle)),
            'LeftLeg':pose((0,0,max(0.,cycle)*.044),(.29*cycle,0,.017)),
            'RightLeg':pose((0,0,max(0.,-cycle)*.044),(-.29*cycle,0,-.017)),
            'LeftShin':pose(rotation=(.33*max(0.,cycle),0,0)),
            'RightShin':pose(rotation=(.33*max(0.,-cycle),0,0)),
            'LeftFoot':pose(rotation=(-.17*cycle,0,0)),
            'RightFoot':pose(rotation=(.17*cycle,0,0)),
            'LeftArm':pose(rotation=(-.072*cycle,0,0)),
            'RightArm':pose(rotation=(.116*cycle,.021*cycle,0)),
            'RightHand':pose(rotation=((.22 if greek else .02)-.092*cycle,0,0)),
            'Mantle':pose(rotation=(.095+abs(cycle)*.062,0,.083*cycle)),
        }
    clips['Walk']=(33,walk)
    clips['Idle']=(61,{
        15:{'Body':pose((0,0,.008),(.005,0,.010)),'Mantle':pose(rotation=(.024,.005,.017))},
        30:{'Body':pose((0,0,.015),(.006,.005,-.006)),'Head':pose(rotation=(-.010,.011,.064)),
            'RightForearm':pose(rotation=(.020,0,.006)),'Mantle':pose(rotation=(.043,0,-.017))},
        45:{'Body':pose((0,0,.008),(.001,-.005,0)), 'Head':pose(rotation=(.010,.012,.022))},
    })
    if greek:
        draw={'Body':pose((0,.025,.012),(-.061,-.031,.18)),
              'RightArm':pose(rotation=(.31,-.039,-.051)),
              'RightForearm':pose(rotation=(.275,.047,.11)),
              'RightHand':pose(rotation=(.102,.036,-.071)),
              'LeftArm':pose(rotation=(.045,0,.127)), 'Mantle':pose(rotation=(.19,-.018,.068))}
        thrust={'Body':pose((0,-.081,.023),(.087,.012,-.127)),
                'RightArm':pose(rotation=(-.39,.095,-.072)),
                'RightForearm':pose(rotation=(.668,-.020,.069)),
                'RightHand':pose(rotation=(1.055,.084,-.068)),
                'LeftArm':pose(rotation=(.089,-.067,.005)),
                'LeftLeg':pose((0,-.042,.007),(-.117,0,0)),
                'LeftShin':pose(rotation=(.164,0,0)), 'Mantle':pose(rotation=(.173,-.052,-.064))}
        clips['Attack']=(28,{7:draw,12:thrust,15:thrust,
            22:{'Body':pose((0,-.026,.007),(.030,.005,-.035)), 'RightHand':pose(rotation=(.45,.025,0))}})
        clips['Cast']=(47,{9:draw,
            17:{**thrust,'RightArm':pose(rotation=(-.58,.10,-.070)),
                'RightHand':pose(rotation=(.92,-.032,.03)), 'LeftForearm':pose(rotation=(.21,0,.09))},
            27:{'Body':pose((0,-.045,.020),(.049,0,-.08)), 'LeftArm':pose(rotation=(.17,-.16,.067)),
                'RightHand':pose(rotation=(.49,0,-.038)), 'Mantle':pose(rotation=(.24,-.026,-.11))}})
    else:
        prepare={'Body':pose((0,.021,-.016),(-.046,.024,.162)),
                 'RightArm':pose(rotation=(-.76,-.08,.15)), 'RightForearm':pose(rotation=(-.24,.17,-.12)),
                 'LeftArm':pose(rotation=(.028,0,.053)), 'Head':pose(rotation=(.028,0,-.083))}
        signal={'Body':pose((0,-.036,.017),(.068,-.014,-.18)),
                'RightArm':pose(rotation=(-1.30,.15,.060)),'RightForearm':pose(rotation=(-.21,.079,.031)),
                'RightHand':pose(rotation=(.27,.07,.059)), 'LeftArm':pose(rotation=(-.069,.037,.042)),
                'Mantle':pose(rotation=(.17,-.035,-.105))}
        clips['Attack']=(28,{7:prepare,12:signal,16:signal,
            22:{'RightArm':pose(rotation=(-.51,.048,.026)), 'Body':pose((0,-.021,.014),(.028,0,-.026))}})
        clips['Cast']=(47,{9:prepare,
            16:{**signal,'RightArm':pose(rotation=(-1.73,.21,.13)), 'RightForearm':pose(rotation=(.16,.034,-.053))},
            25:{**signal,'RightArm':pose(rotation=(-1.09,.035,.08)), 'Mantle':pose(rotation=(.224,-.126,-.12))},
            33:{'RightArm':pose(rotation=(-.31,0,.03))}})
    clips['Hit']=(18,{4:{'Body':pose((0,.049,-.018),(-.15,.038,.070)), 'Head':pose(rotation=(.050,-.019,.046)),
        'LeftForearm':pose(rotation=(.13,.06,.01)), 'Mantle':pose(rotation=(-.101,0,.072))},
        9:{'Body':pose((0,.021,-.011),(-.047,.021,.019))}})
    clips['Death']=(39,{6:{'Figure':pose((0,.041,.055),(-.16,.008,.085))},
        19:{'Figure':pose((0,.21,.187),(-.86,-.08,-.156)), 'RightArm':pose(rotation=(-.34,0,-.24)),
            'RightHand':pose(rotation=(.19,0,.17)), 'LeftArm':pose(rotation=(-.197,-.13,-.28))},
        39:{'Figure':pose((0,.51,.016),(-1.505,-.063,-.21),.93),
            'RightArm':pose(rotation=(.240,-.12,-.24)), 'Mantle':pose(rotation=(.052,0,-.099))}})
    clips['Spawn']=(25,{1:{'Figure':pose((0,0,-.17),(0,0,-.068),.88)},
        8:{'Figure':pose((0,0,.094),(0,0,.034),1.018),'Mantle':pose(rotation=(.098,0,.043))},
        16:{'Figure':pose((0,0,-.022),(0,0,-.012),.984)}})
    clips['Ascend']=(37,{10:{'Figure':pose((0,0,.14),(0,0,-.20),1.018),'Mantle':pose(rotation=(.25,0,.209))},
        20:{'Figure':pose((0,0,.205),(0,0,.25),1.043), 'RightArm':pose(rotation=(-.196 if greek else -1.05,.062,.124)),
            'LeftArm':pose(rotation=(-.124,.010,-.032))}})
    clips['Celebrate']=(54,{13:{'RightArm':pose(rotation=(-.30 if greek else -1.24,.067,.075)),
                                 'Figure':pose((0,0,.055),(0,0,.122))},
        26:{'RightArm':pose(rotation=(-.184 if greek else -.96,.16,-.102)),
            'Figure':pose((0,0,.086),(0,0,-.091)), 'Mantle':pose(rotation=(.124,0,.199))},
        39:{'Figure':pose((0,0,.024))}})
    return clips
