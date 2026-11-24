"""Prepare the CC0 anatomy used by the two commanders. Normal Blender builds are offline."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from gzip import GzipFile
from json import dumps, loads
from pathlib import Path
from urllib.request import urlopen

REVISION = 'a8bc2d54ff0ac92e78ff71431b1023eda42bf482'
ORIGIN = f'https://raw.githubusercontent.com/makehumancommunity/makehuman/{REVISION}'
DESTINATION = Path(__file__).with_name('reference-data')

SHAPES = {
    'thekla': {
        'macrodetails/caucasian-female-young': .81,
        'macrodetails/african-female-young': .19,
        'macrodetails/universal-female-young-maxmuscle-averageweight': .26,
        'head/head-diamond': .26,
        'nose/nose-greek-incr': .46,
        'nose/nose-width2-decr': .22,
        'chin/chin-prominent-incr': .26,
        'cheek/l-cheek-bones-incr': .52,
        'cheek/r-cheek-bones-incr': .52,
        'mouth/mouth-angles-down': .19,
    },
    'marcus': {
        'macrodetails/caucasian-male-young': .56,
        'macrodetails/caucasian-male-old': .44,
        'macrodetails/universal-male-young-maxmuscle-averageweight': .47,
        'macrodetails/universal-male-young-averagemuscle-maxweight': .32,
        'head/head-rectangular': .47,
        'nose/nose-curve-convex': .44,
        'nose/nose-width2-incr': .20,
        'chin/chin-width-incr': .61,
        'cheek/l-cheek-inner-decr': .30,
        'cheek/r-cheek-inner-decr': .30,
        'mouth/mouth-angles-down': .34,
    },
}
SOURCE = {
    'mesh': 'makehuman/data/3dobjs/base.obj',
    'weights': 'makehuman/data/rigs/default_weights.mhw',
    'license': 'LICENSE.ASSETS.md',
}
LIPS = ['mouth/mouth-upperlip-volume-incr', 'mouth/mouth-lowerlip-volume-incr']


def download(path):
    with urlopen(f'{ORIGIN}/{path}', timeout=35) as response:
        return response.read().decode('utf-8')


def target(text):
    return [(int(parts[0]), tuple(map(float, parts[1:4]))) for line in text.splitlines()
            if (parts := line.split()) and not line.startswith('#')]


def parse_obj(text):
    vertices, groups = [], defaultdict(list)
    for line in text.splitlines():
        if line.startswith('v '):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith('g '):
            group = line[2:]
        elif line.startswith('f '):
            groups[group].append(tuple(int(item.split('/')[0])-1 for item in line.split()[1:]))
    return vertices, groups


def rig_group(bone):
    name, _, side = bone.partition('.')
    side = {'L':'Left','R':'Right'}.get(side, '')
    if name.startswith('upperarm'):
        return side+'Arm'
    if name.startswith('lowerarm'):
        return side+'Forearm'
    if name.startswith(('wrist', 'metacarpal', 'finger')):
        return side+'Hand'
    if name.startswith('upperleg'):
        return side+'Leg'
    if name.startswith('lowerleg'):
        return side+'Shin'
    if name.startswith(('foot', 'toe')):
        return side+'Foot'
    if name.startswith(('neck', 'head', 'jaw', 'levator', 'oculi', 'orbicularis', 'oris',
                        'risorius', 'special', 'temporalis', 'tongue', 'eye')):
        return 'Head'
    return 'Body'


def body_weights(source):
    result=defaultdict(lambda: defaultdict(float))
    for bone, weights in source.items():
        name = rig_group(bone)
        for index, weight in weights:
            result[index][name] += weight
    return result


def prepare(name, base, groups, targets, all_weights, lip_vertices):
    position = [list(point) for point in base]
    for topic, amount in SHAPES[name].items():
        for index, delta in targets[topic]:
            for axis in range(3):
                position[index][axis] += delta[axis]*amount
    body = sorted({index for face in groups['body'] for index in face})
    low = min(position[index][1] for index in body)
    high = max(position[index][1] for index in body)
    height = 1.741 if name == 'thekla' else 1.806
    scale = height/(high-low)
    width = 1.015 if name == 'thekla' else 1.151
    coordinates = [(x*scale*width, -z*scale, (y-low)*scale+.009) for x,y,z in position]
    joint_names = ('shoulder','elbow','hand','finger-2-1','finger-3-1','finger-5-1','upper-leg','knee',
                   'ankle','foot-1','foot-2','eye','eye-target')
    guide_names = {'l-'+j for j in joint_names}|{'r-'+j for j in joint_names}|{'head','neck','pelvis','spine-1'}
    joints = {}
    for joint in guide_names:
        samples = {i for face in groups['joint-'+joint] for i in face}
        joints[joint] = [round(sum(coordinates[i][axis] for i in samples)/len(samples),6) for axis in range(3)]
    if len(joints) != len(guide_names):
        raise ValueError('A MakeHuman landmark is missing')
    def uncovered(face):
        x,_,z=(sum(coordinates[index][axis] for index in face)/len(face) for axis in range(3))
        neck=z-joints['neck'][2]
        if neck>-.071 and abs(x)<min(.143,.071+1.70*max(0,neck+.019)):
            return True
        if abs(x)>joints['l-shoulder'][0]+.026 and z>.83:
            return True
        low_cut=.314 if name=='marcus' else 0
        top_cut=.769 if name=='thekla' else .798
        return low_cut<z<top_cut and abs(x)>.008
    selected = [face for face in groups['body'] if uncovered(face)]
    indexes = sorted({i for face in selected for i in face})
    vertex_map = {original:local for local,original in enumerate(indexes)}
    return {
        'positions': [[round(v,6) for v in coordinates[i]] for i in indexes],
        'faces': [[vertex_map[i] for i in face] for face in selected],
        'weights': [[(key,round(value,4)) for key,value in sorted(all_weights[i].items(),key=lambda pair:-pair[1])[:4]
                    if value > .015] for i in indexes],
        'lip_vertices': [vertex_map[i] for i in indexes if i in lip_vertices],
        'joints': joints,
        'revision': REVISION,
    }


def main():
    topics = sorted(set(LIPS).union(*SHAPES.values()))
    inputs = list(SOURCE.values())+[f'makehuman/data/targets/{topic}.target' for topic in topics]
    with ThreadPoolExecutor(max_workers=10) as executor:
        contents = dict(zip(inputs,executor.map(download,inputs)))
    base, groups = parse_obj(contents[SOURCE['mesh']])
    weights = body_weights(loads(contents[SOURCE['weights']])['weights'])
    targets = {topic:target(contents[f'makehuman/data/targets/{topic}.target']) for topic in topics}
    lips = {index for expression in LIPS for index,delta in targets[expression] if sum(v*v for v in delta)>.00002}
    DESTINATION.mkdir(parents=True,exist_ok=True)
    (DESTINATION/'MakeHuman-CC0.md').write_text(contents[SOURCE['license']],encoding='utf-8')
    for name in SHAPES:
        data = prepare(name, base, groups, targets, weights, lips)
        with GzipFile(DESTINATION/f'{name}-anatomy.json.gz','wb',mtime=0) as output:
            output.write(dumps(data,separators=(',',':'),sort_keys=True).encode('utf-8'))
        print(f'{name}: {len(data["positions"])} points, {len(data["faces"])} faces')


if __name__=='__main__':
    main()
