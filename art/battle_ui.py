"""Paint the original stone panel, bronze plates and icons for the battle HUD."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "public" / "assets" / "ui"
INK = "#201c22"

def weather(image, seed, strength):
    rng = np.random.default_rng(seed)
    pixels = np.array(image)
    height, width = pixels.shape[:2]
    coarse = Image.fromarray(rng.integers(30, 226, size=(11, 22), dtype=np.uint8))
    broad = np.asarray(coarse.resize((width, height), Image.Resampling.BICUBIC), dtype=float) - 128
    y, x = np.indices((height, width))
    strokes = 2.1 * np.sin(x * .075 + y * .37) + 2.8 * np.sin(x * .037 - y * .19)
    grain = (broad * .105 + strokes + rng.normal(0, 1.65, (height, width))) * strength
    pixels[..., :3] = np.clip(pixels[..., :3].astype(float) + grain[..., None], 0, 255).astype("uint8")
    return Image.fromarray(pixels)

def plate():
    width, height = 768, 384
    pixels = np.empty((height, width, 3), dtype=np.uint8)
    yy, xx = np.indices((height, width))
    light = (1. - yy / height) * .65 + .35 * np.exp(-((xx - 320) / 390) ** 2)
    pixels[:] = np.stack([21 + light * 18, 29 + light * 25, 35 + light * 30], axis=-1)
    stone = Image.fromarray(pixels)
    brush = ImageDraw.Draw(stone)
    rock = "#263136"
    glint = "#42423e"
    brush.polygon([(0, 42), (13, 13), (104, 10), (121, 25), (338, 24), (357, 15),
                   (665, 13), (756, 31), (767, 66), (767, 0), (0, 0)], fill=rock)
    brush.line([(0, 41), (15, 15), (103, 13), (120, 26), (335, 27), (355, 16),
                (667, 14), (750, 30), (767, 64)], fill=glint, width=2)
    brush.polygon([(0, 352), (130, 367), (255, 363), (463, 354), (642, 364),
                   (767, 331), (767, 383), (0, 383)], fill="#141c22")
    brush.line([(0, 353), (129, 369), (246, 364), (454, 355), (643, 365), (767, 333)],
               fill="#373739", width=2)
    for side in (0, 1):
        for i in range(7):
            x = 15 + i * 15
            if side:
                x = width - x - 12
            y = 47 + i % 2 * 9
            brush.line([(x, y + 12), (x, y), (x + 11, y), (x + 11, y + 7), (x + 4, y + 7)],
                       fill="#533d36", width=3)
            brush.line([(x + 1, y + 11), (x + 1, y + 1), (x + 10, y + 1)], fill="#6a543e", width=2)
    return weather(stone, 7509, .87)

def brass():
    width, height = 448, 120
    y, x = np.indices((height, width))
    bloom = .22 * np.exp(-((x - 192) / 135) ** 2 - ((y - 7) / 88) ** 2)
    light = (1. - y / height) * .65 + bloom
    pixels = np.stack([165 + light * 98, 102 + light * 100, 50 + light * 95], axis=-1)
    bronze = Image.fromarray(np.clip(pixels, 0, 255).astype("uint8"))
    brush = ImageDraw.Draw(bronze)
    brush.line([(0, 19), (38, 16), (57, 11), (154, 13), (244, 8), (317, 11), (392, 9), (447, 18)],
               fill="#f5d495", width=2)
    brush.line([(0, 105), (101, 111), (220, 107), (276, 109), (339, 104), (447, 103)],
               fill="#a45d30", width=3)
    return weather(bronze, 9118, 1.12)

def artwork(mark, index):
    image = Image.new('RGBA', (128, 128))
    path = ImageDraw.Draw(image)
    def shape(points, color, edge=INK, width=4):
        path.polygon(points, fill=color)
        if edge:
            path.line([*points, points[0]], fill=edge, width=width, joint='curve')
    def stroke(points, color, width=3):
        path.line(points, fill=color, width=width, joint='curve')
    def disk(bounds, color, edge=INK, width=4):
        path.ellipse(bounds, fill=color, outline=edge, width=width)
    gold, sun, shadow = '#c58a48', '#f6d99a', '#704947'
    if mark == 'reserve':
        shape([(28,24),(65,14),(86,25),(83,61),(68,84),(42,91),(23,67)], shadow)
        shape([(45,37),(93,25),(112,45),(106,76),(87,105),(60,108),(42,86)], '#326a73')
        stroke([(47,41),(93,30),(105,44),(100,73),(86,96),(62,101),(46,84),(47,41)], sun, 6)
        shape([(77,47),(95,70),(78,87),(60,66)], gold, width=3)
        stroke([(62,66),(77,50),(84,61)], '#fff0bd', 3)
    elif mark == 'oracle' or mark == 'essence':
        if mark == 'oracle':
            disk((17, 20, 112, 110), '#54496b')
            path.arc((23,26,106,104),12,156,fill=sun,width=7)
            path.arc((24,26,105,105),197,330,fill=gold,width=5)
        shape([(64,14),(97,45),(89,82),(64,110),(38,83),(31,44)], '#9a71b9' if mark == 'oracle' else '#477eb4')
        shape([(64,17),(67,60),(91,46),(64,17)], '#f5d4ff' if mark == 'oracle' else '#c1f5ff', None)
        shape([(34,45),(67,60),(64,106),(41,81)], '#795d9d' if mark == 'oracle' else '#356691', None)
        stroke([(36,46),(67,60),(91,48)], '#e4b5f1' if mark == 'oracle' else '#b4eeff', 5)
    elif mark == 'hero':
        shape([(65,28),(70,15),(92,11),(108,26),(94,47),(80,55)], '#9d5653')
        shape([(25,82),(30,51),(54,32),(84,31),(102,51),(99,90),(88,103),(64,99),
               (57,75),(41,79),(40,103),(27,99)], '#5b7b86')
        shape([(33,51),(53,36),(82,34),(99,49),(97,62),(31,66)], gold)
        stroke([(38,51),(58,40),(80,39),(93,47)], sun, 6)
        shape([(31,66),(48,59),(58,71),(53,88),(47,102),(30,99)], '#9fa6a0', width=3)
        stroke([(66,76),(91,73)], '#233c48', 6)
        stroke([(68,70),(89,67)], sun, 3)
    elif mark == 'building':
        shape([(16,44),(66,14),(114,43),(105,58),(23,58)], '#779091')
        shape([(25,46),(66,22),(105,45)], '#b4afa0', None)
        for x, color in [(29, '#a49983'), (55, '#c0b395'), (81, '#a49983')]:
            shape([(x,51),(x+18,51),(x+16,94),(x+20,99),(x-2,99)], color, width=3)
            stroke([(x+6,57),(x+5,89)], '#e1cfaa', 4)
        shape([(20,97),(101,96),(110,108),(103,114),(16,113),(12,108)], shadow)
        stroke([(23,101),(97,100)], sun, 4)
    elif mark == 'smith':
        shape([(17,65),(60,65),(65,62),(112,59),(101,77),(83,82),(75,98),
               (88,104),(86,114),(27,114),(27,104),(44,97),(44,86),(25,83)], '#657779')
        stroke([(21,70),(62,70),(105,64)], '#c2d0c2', 5)
        shape([(66,43),(74,47),(52,84),(43,79)], '#9c6244')
        shape([(64,20),(89,27),(98,42),(83,55),(59,46),(52,36)], gold)
        stroke([(58,35),(67,25),(86,30),(92,41)], sun, 5)
    elif mark == 'recruit':
        shape([(29,103),(24,90),(42,71),(57,79),(44,98),(37,108)], '#785046')
        shape([(42,72),(78,23),(107,15),(107,39),(62,82)], '#9aafb2')
        shape([(47,75),(81,28),(101,21),(76,53),(59,76)], '#e1ebd3', None)
        stroke([(35,67),(63,88)], '#46352a', 15)
        stroke([(35,66),(63,86)], gold, 9)
        stroke([(40,68),(57,80)], sun, 3)
    else:
        shape([(63,13),(100,27),(115,62),(94,100),(60,113),(27,98),(14,64),(25,30)], gold)
        disk((26,25,102,101), '#d69a48', sun, 6)
        shape([(64,37),(74,57),(91,62),(73,73),(63,91),(53,72),(38,62),(54,54)], '#f3cc77', '#966237', 3)
        stroke([(52,56),(64,41),(70,54)], '#fff0ad', 3)
    return weather(image, 192 + index * 38, .63)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plate().save(OUT / "battle-stone.webp", quality=83, method=6)
    brass().save(OUT / "battle-bronze.webp", quality=85, method=6)
    icons = ('reserve', 'oracle', 'hero', 'building', 'smith', 'recruit', 'gold', 'essence')
    atlas = Image.new('RGBA', (128 * len(icons), 128))
    for index, name in enumerate(icons):
        atlas.paste(artwork(name, index), (128 * index, 0))
    atlas.save(OUT / "battle-icons.webp", quality=94, method=6)

if __name__ == "__main__":
    main()
