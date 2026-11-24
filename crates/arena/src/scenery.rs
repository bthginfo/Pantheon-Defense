use super::{Shared, simple};
use bevy::{gltf::GltfAssetLabel, pbr::NotShadowCaster, prelude::*, scene::SceneInstanceReady};
use pantheon_simulation::{self as sim, SLOTS};

pub struct Palette {
    sea: [u8; 3],
    foam: [u8; 3],
    foam_dark: [u8; 3],
    stone: [u8; 3],
    face: [u8; 3],
    grass: [u8; 3],
    path: [u8; 3],
    chalk: [u8; 3],
    tile: [u8; 3],
    earth: [u8; 3],
    leaf: [u8; 3],
    bright_leaf: [u8; 3],
    roof: [u8; 3],
    cloth: [u8; 3],
}

impl Palette {
    pub fn for_theme(id: &str) -> Self {
        match id {
            "rome" => Self {
                sea: [46, 82, 83],
                foam: [122, 152, 137],
                foam_dark: [66, 112, 111],
                stone: [172, 118, 95],
                face: [103, 75, 68],
                grass: [133, 120, 76],
                path: [184, 139, 112],
                chalk: [214, 179, 146],
                tile: [163, 121, 102],
                earth: [90, 62, 42],
                leaf: [89, 106, 65],
                bright_leaf: [135, 145, 69],
                roof: [154, 66, 54],
                cloth: [182, 73, 64],
            },
            "japan" => Self {
                sea: [44, 80, 88],
                foam: [111, 166, 161],
                foam_dark: [65, 117, 128],
                stone: [137, 145, 121],
                face: [74, 94, 86],
                grass: [108, 133, 101],
                path: [173, 159, 128],
                chalk: [192, 183, 150],
                tile: [151, 160, 133],
                earth: [90, 76, 60],
                leaf: [54, 107, 86],
                bright_leaf: [117, 159, 127],
                roof: [52, 81, 92],
                cloth: [157, 74, 64],
            },
            _ => Self {
                sea: [40, 96, 103],
                foam: [114, 172, 155],
                foam_dark: [61, 137, 138],
                stone: [192, 170, 123],
                face: [122, 119, 89],
                grass: [149, 162, 101],
                path: [211, 183, 137],
                chalk: [229, 208, 164],
                tile: [195, 176, 132],
                earth: [106, 78, 50],
                leaf: [87, 125, 87],
                bright_leaf: [131, 160, 98],
                roof: [50, 110, 119],
                cloth: [51, 122, 125],
            },
        }
    }
}

pub struct Scenery<'a, 'w, 's> {
    commands: &'a mut Commands<'w, 's>,
    all: Vec<Entity>,
    cube: Handle<Mesh>,
    rock: Handle<Mesh>,
    cylinder: Handle<Mesh>,
    colors: Vec<Handle<StandardMaterial>>,
}

const SEA: usize = 0;
const FOAM: usize = 1;
const DEEP: usize = 2;
const STONE: usize = 3;
const CLIFF: usize = 4;
const GRASS: usize = 5;
const TRAIL: usize = 6;
const IVORY: usize = 7;
const TILE: usize = 8;
const WOOD: usize = 9;
const LEAF: usize = 10;
const BUD: usize = 11;
const ROOF: usize = 12;
const FLAG: usize = 13;
const GLOW: usize = 14;

impl<'a, 'w, 's> Scenery<'a, 'w, 's> {
    pub fn new(
        commands: &'a mut Commands<'w, 's>,
        mesh: &mut Assets<Mesh>,
        material: &mut Assets<StandardMaterial>,
        shared: &Shared,
        palette: Palette,
    ) -> Self {
        let colors = [
            palette.sea,
            palette.foam,
            palette.foam_dark,
            palette.stone,
            palette.face,
            palette.grass,
            palette.path,
            palette.chalk,
            palette.tile,
            palette.earth,
            palette.leaf,
            palette.bright_leaf,
            palette.roof,
            palette.cloth,
            [255, 191, 102],
        ]
        .into_iter()
        .enumerate()
        .map(|(index, [r, g, b])| {
            material.add(simple(
                Color::srgb_u8(r, g, b),
                match index {
                    GLOW => 1.3,
                    SEA => 0.12,
                    _ => 0.02,
                },
            ))
        })
        .collect();
        Self {
            commands,
            all: Vec::new(),
            cube: shared.cube.clone(),
            rock: shared.crystal.clone(),
            cylinder: mesh.add(Cylinder::new(1., 1.).mesh().resolution(7)),
            colors,
        }
    }

    fn object(&mut self, mesh: Handle<Mesh>, color: usize, pos: Vec3, size: Vec3, angle: f32) {
        let mut entity = self.commands.spawn((
            Mesh3d(mesh),
            MeshMaterial3d(self.colors[color].clone()),
            Transform::from_translation(pos)
                .with_scale(size)
                .with_rotation(Quat::from_rotation_y(angle)),
        ));
        if size.y < 0.16 {
            entity.insert(NotShadowCaster);
        }
        self.all.push(entity.id());
    }

    fn cube(&mut self, p: [f32; 3], s: [f32; 3], color: usize, angle: f32) {
        self.object(self.cube.clone(), color, p.into(), s.into(), angle);
    }
    fn rock(&mut self, p: [f32; 3], s: [f32; 3], color: usize, angle: f32) {
        self.object(self.rock.clone(), color, p.into(), s.into(), angle);
    }
    fn cylinder(&mut self, p: [f32; 3], s: [f32; 3], color: usize, angle: f32) {
        self.object(self.cylinder.clone(), color, p.into(), s.into(), angle);
    }

    pub fn build(mut self, theme: &str, assets: &AssetServer) -> Vec<Entity> {
        self.cube([0., -1.38, 0.], [88., 0.07, 75.], SEA, 0.);
        self.cube([0., -0.63, 0.1], [28., 1.32, 17.3], CLIFF, 0.);
        self.cube([0., 0.01, 0.0], [27.22, 0.33, 16.83], STONE, 0.);
        self.cube([0., 0.16, -1.0], [25.18, 0.13, 13.76], GRASS, 0.);
        self.cube([0., 0.20, 4.98], [23.8, 0.10, 3.70], STONE, 0.);
        self.cube([0., -0.19, 8.0], [9.0, 0.57, 2.84], CLIFF, 0.);
        self.cube([0., 0.08, 8.0], [8.66, 0.17, 2.55], STONE, 0.);
        self.cube([0., 0.10, 8.64], [4.89, 0.25, 0.44], IVORY, 0.);
        self.cube([0., 0.02, 9.05], [3.24, 0.21, 0.49], IVORY, 0.);
        for side in [-1., 1.] {
            self.cube([side * 13.55, 0.06, 0.15], [0.18, 0.17, 16.52], IVORY, 0.);
            self.cube([side * 12.17, 0.08, 8.08], [2.15, 0.29, 0.56], STONE, 0.);
            self.cube([side * 10.55, 0.08, 8.08], [0.64, 0.29, 0.56], IVORY, 0.);
            self.cube([side * 6.1, -0.15, 8.44], [1.68, 0.30, 1.42], CLIFF, 0.);
            self.cube([side * 6.08, -0.03, 8.51], [1.44, 0.13, 1.27], IVORY, 0.);
            self.cube([side * 12.62, 0.23, -4.75], [0.73, 0.20, 2.52], STONE, 0.);
            self.cube([side * 12.53, 0.22, 2.03], [0.73, 0.21, 3.43], STONE, 0.);
        }

        for side in [-1., 1.] {
            for n in 0..34 {
                let k = n as f32;
                let jitter = (k * 2.634).sin();
                let depth = (k * 0.386).cos().abs();
                let x = side * (13.4 + 0.85 * depth);
                let z = k * 0.48 - 7.8;
                self.rock(
                    [x, -0.52 - 0.25 * depth, z],
                    [
                        0.62 + 0.64 * depth,
                        0.45 + 0.43 * depth,
                        0.34 + 0.28 * depth,
                    ],
                    if n % 5 == 0 { STONE } else { CLIFF },
                    k * 1.118,
                );
                if n % 3 == 0 {
                    self.cube(
                        [side * (15.2 + 2.0 * depth), -1.32, z + jitter],
                        [0.76 + 1.1 * depth, 0.009, 0.047],
                        if n % 9 == 0 { FOAM } else { DEEP },
                        jitter * 0.26,
                    );
                }
            }
        }
        for n in 0..54 {
            let k = n as f32;
            let x = (k * 1.275).cos() * (15.5 + n as f32 % 11.);
            let z = (k * 2.598).sin() * (11.5 + n as f32 % 7.);
            if x.abs() < 14.8 && z.abs() < 9.4 {
                continue;
            }
            self.cube(
                [x, -1.319, z],
                [0.29 + (k * 1.75).sin().abs() * 1.25, 0.012, 0.049],
                if n % 5 == 2 { FOAM } else { DEEP },
                (k * 0.52).sin() * 0.24,
            );
        }

        for lane in 0..2 {
            let points = sim::path(theme, lane);
            for pair in points.windows(2) {
                let (x1, z1) = (pair[0][0], pair[0][1]);
                let (x2, z2) = (pair[1][0], pair[1][1]);
                let (w, h) = (x2 - x1, z2 - z1);
                let length = w.hypot(h);
                let angle = h.atan2(w);
                self.cube(
                    [(x1 + x2) * 0.5, 0.26, (z1 + z2) * 0.5],
                    [length + 0.52, 0.11, 1.86],
                    CLIFF,
                    -angle,
                );
                self.cube(
                    [(x1 + x2) * 0.5, 0.312, (z1 + z2) * 0.5],
                    [length + 0.48, 0.06, 1.62],
                    TRAIL,
                    -angle,
                );
                let pieces = (length / 0.73).ceil() as i32;
                for n in 0..pieces {
                    let t = (n as f32 + 0.5) / pieces as f32;
                    let j = (n as f32 * 2.618).sin() * 0.12;
                    self.cube(
                        [
                            x1 + w * t - j * h / length,
                            0.349,
                            z1 + h * t + j * w / length,
                        ],
                        [length / pieces as f32 - 0.034, 0.025, 1.36],
                        if n % 3 == 0 { IVORY } else { TRAIL },
                        -angle,
                    );
                }
            }
            let start = points[0];
            self.cylinder([start[0], 0.28, start[1]], [0.95, 0.31, 0.95], CLIFF, 0.);
            self.cylinder([start[0], 0.46, start[1]], [0.79, 0.14, 0.79], ROOF, 0.);
            self.rock([start[0], 0.58, start[1]], [0.44, 0.18, 0.44], GLOW, 0.);
        }

        for (index, point) in SLOTS.iter().copied().enumerate() {
            let owner = if index < 12 { FLAG } else { TILE };
            self.cube([point[0], 0.293, point[1]], [1.30, 0.13, 1.49], CLIFF, 0.);
            self.cube([point[0], 0.364, point[1]], [1.24, 0.081, 1.42], TILE, 0.);
            self.cube(
                [point[0], 0.412, point[1] - 0.59],
                [1.07, 0.024, 0.062],
                owner,
                0.,
            );
            for side in [-0.53, 0.53] {
                self.cube(
                    [point[0] + side, 0.411, point[1]],
                    [0.046, 0.018, 1.13],
                    IVORY,
                    0.,
                );
            }
        }

        self.cylinder([0., 0.26, 7.24], [1.10, 0.22, 1.10], TRAIL, 0.);
        self.cylinder([0., 0.44, 7.23], [0.79, 0.17, 0.79], ROOF, 0.);
        self.rock([0., 0.96, 7.29], [0.38, 0.57, 0.38], GLOW, 0.45);
        self.all.push(
            self.commands
                .spawn((
                    SceneRoot(assets.load(
                        GltfAssetLabel::Scene(0).from_asset(format!("models/gate_{theme}.glb")),
                    )),
                    Transform::from_xyz(0., 0.28, 8.52).with_scale(Vec3::splat(1.18)),
                ))
                .observe(|_: Trigger<SceneInstanceReady>| {
                    super::event("pantheon-board-models", "gate")
                })
                .id(),
        );

        for (index, (x, z)) in [
            (-11.65, -7.45),
            (-9.2, -7.57),
            (-4.65, -7.43),
            (-2.4, -7.35),
            (2.4, -7.3),
            (4.3, -6.63),
            (7.14, -7.43),
            (10.65, -7.6),
            (-11.75, 4.0),
            (-12.02, 5.7),
            (-9.06, 4.85),
            (-10.05, 6.36),
            (11.35, 4.42),
            (9.86, 5.29),
            (11.12, 6.57),
            (5.87, 7.39),
            (-5.8, 7.41),
            (-1.67, 2.58),
            (1.6, 2.64),
            (-1.49, -3.32),
            (1.64, -3.75),
            (-12.2, -1.02),
            (12.09, 0.54),
        ]
        .into_iter()
        .enumerate()
        {
            let size = 0.72 + (index as f32 * 1.9).cos().abs() * 0.54;
            self.tree(x, z, size, theme);
            if index % 3 == 0 {
                self.rock([x + 0.42, 0.38, z + 0.28], [0.25, 0.21, 0.28], CLIFF, 0.5);
                self.rock([x - 0.4, 0.42, z + 0.2], [0.15, 0.16, 0.22], IVORY, 0.25);
            }
        }

        for n in 0..5 {
            let x = n as f32 * 0.53 - 1.05;
            self.column(x, -6.33, if n % 2 == 0 { 1.7 } else { 1.41 });
        }
        self.cube([0., 1.86, -6.34], [3.04, 0.25, 0.76], ROOF, 0.);
        self.cube([0., 2.016, -6.34], [3.24, 0.10, 0.82], IVORY, 0.);
        for side in [-1., 1.] {
            self.column(side * 3.18, 3.08, 1.07);
            self.rock([side * 3.18, 1.66, 3.08], [0.16, 0.24, 0.17], GLOW, 0.3);
            for n in 0..5 {
                let x = side * (5.4 + n as f32 * 0.63);
                self.cube([x, 0.52, 7.95], [0.47, 0.65, 0.35], STONE, 0.);
                self.cube([x, 0.87, 7.95], [0.49, 0.08, 0.40], IVORY, 0.);
            }
        }

        for n in 0..22 {
            let x = (n as f32 * 2.56).sin() * 2.43;
            let z = (n as f32 * 1.31).cos() * 5.65;
            if z.abs() > 3.72 {
                continue;
            }
            let color = if n % 3 == 0 { BUD } else { LEAF };
            self.rock(
                [x, 0.25, z],
                [0.15 + 0.045 * (n % 4) as f32, 0.12, 0.24],
                color,
                n as f32,
            );
        }
        self.all
    }

    fn column(&mut self, x: f32, z: f32, height: f32) {
        self.cube([x, 0.31, z], [0.57, 0.14, 0.56], STONE, 0.);
        self.cylinder(
            [x, 0.38 + height * 0.44, z],
            [0.171, height, 0.171],
            IVORY,
            0.,
        );
        self.cube([x, 0.42 + height, z], [0.45, 0.13, 0.43], STONE, 0.);
    }

    fn tree(&mut self, x: f32, z: f32, scale: f32, theme: &str) {
        self.cylinder(
            [x, 0.31 + 0.40 * scale, z],
            [0.12 * scale, 0.85 * scale, 0.12 * scale],
            WOOD,
            0.26,
        );
        if theme == "aegean" {
            for (i, [a, b, c]) in [
                [-0.19, 0.93, 0.08],
                [0.20, 1.0, 0.10],
                [0.04, 1.19, -0.12],
                [-0.13, 1.08, -0.22],
            ]
            .into_iter()
            .enumerate()
            {
                self.rock(
                    [x + a * scale, 0.25 + b * scale, z + c * scale],
                    [0.37 * scale, 0.32 * scale, 0.33 * scale],
                    if i % 3 == 0 { BUD } else { LEAF },
                    i as f32 * 0.83,
                );
            }
        } else {
            for i in 0..3 {
                let s = (0.53 - i as f32 * 0.11) * scale;
                self.rock(
                    [x, 0.62 + (i as f32 * 0.45 + 0.33) * scale, z],
                    [s, 0.54 * scale, s],
                    if i % 2 == 0 { LEAF } else { BUD },
                    i as f32 * 0.4,
                );
            }
        }
    }
}
