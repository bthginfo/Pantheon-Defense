"""Build the two lead characters in their own fitted stances and costume patterns."""
from commander_anatomy import Anatomy
from commander_equipment import equipment
from commander_forms import paints
from commander_garments import costume
from commander_portraits import portrait

COMMANDERS = frozenset(('thekla','marcus'))


def commander(item):
    name=item['id']
    art=Anatomy(name)
    pigments=paints()
    art.sculpt(pigments['skin '+name],pigments['lip'],pigments['flush'],pigments['beard'])
    portrait(art,pigments)
    costume(art,pigments)
    equipment(art,pigments)
    return art.bind(),item['model']['shape'],item['model']['weapon']
