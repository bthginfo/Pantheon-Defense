//! Short weapon accents and staged hero spells, drawn on the Bevy battle board.

use bevy::{
    asset::RenderAssetUsages,
    pbr::NotShadowCaster,
    prelude::*,
    render::{
        mesh::{Indices, PrimitiveTopology, VertexAttributeValues},
        view::NoFrustumCulling,
    },
};
use pantheon_simulation::Event;
use std::f32::consts::{PI, TAU};

use super::{Projectile, facing, p3};

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum WeaponLook {
    Bolt,
    Blade,
    Stone,
    Flame,
    Frost,
    Lightning,
    Gold,
}

impl WeaponLook {
    pub fn for_attack(attack: &str) -> Self {
        match attack {
            "arrow" | "pierce" | "bleed" | "shred" => Self::Bolt,
            "guard" => Self::Blade,
            "stone" => Self::Stone,
            "frost" => Self::Frost,
            "chain" => Self::Lightning,
            "rally" | "fortune" => Self::Gold,
            _ => Self::Flame,
        }
    }

    pub fn model(self) -> &'static str {
        match self {
            Self::Bolt => "fx_bolt",
            Self::Frost => "fx_frost",
            Self::Stone | Self::Blade => "fx_spark",
            _ => "fx_sun",
        }
    }

    pub fn arc(self) -> f32 {
        match self {
            Self::Stone => 1.20,
            Self::Flame => 0.59,
            Self::Lightning | Self::Bolt => 0.14,
            Self::Blade => 0.10,
            _ => 0.38,
        }
    }

    pub fn minimum_flight(self) -> f64 {
        match self {
            Self::Blade | Self::Lightning => 0.13,
            Self::Bolt | Self::Gold => 0.20,
            _ => 0.25,
        }
    }

    fn pigment(self) -> Hue {
        match self {
            Self::Blade | Self::Bolt => Hue::Ivory,
            Self::Stone | Self::Gold => Hue::Amber,
            Self::Flame => Hue::Ember,
            Self::Frost => Hue::Ice,
            Self::Lightning => Hue::Violet,
        }
    }
}

#[derive(Clone, Copy)]
enum Hue {
    Amber,
    Ivory,
    Ember,
    Ice,
    Violet,
    Jade,
}

#[derive(Clone, Copy)]
enum SpellLook {
    Flame,
    Frost,
    Lightning,
    Assault,
    Ward,
    Grove,
    Quake,
}

impl SpellLook {
    fn for_skill(skill: &str) -> Self {
        match skill {
            "meteor" | "comet" | "forge" | "brand" | "lantern" => Self::Flame,
            "mist" | "tide" | "crescent" => Self::Frost,
            "thunder" | "coil" => Self::Lightning,
            "phalanx" | "breach" | "salvo" | "volley" | "charge" | "windstep" => Self::Assault,
            "grove" | "bloom" => Self::Grove,
            "quarry" | "stonegate" => Self::Quake,
            _ => Self::Ward,
        }
    }

    fn pigment(self) -> Hue {
        match self {
            Self::Flame => Hue::Ember,
            Self::Frost => Hue::Ice,
            Self::Lightning => Hue::Violet,
            Self::Assault => Hue::Ivory,
            Self::Grove => Hue::Jade,
            Self::Ward | Self::Quake => Hue::Amber,
        }
    }
}

#[derive(Clone, Copy)]
enum Shape {
    Ring,
    Sweep,
    Shard,
    Flash,
    Tail,
}

struct Geometry {
    positions: Vec<[f32; 3]>,
    triangles: Vec<u32>,
}

struct ActiveEffect {
    shape: Shape,
    hue: Hue,
    bright: bool,
    motion: Transient,
}

#[derive(Component)]
pub(super) struct EffectCanvas;

#[derive(Resource)]
pub struct CombatFx {
    display: Handle<Mesh>,
    geometry: [Geometry; 5],
    batch: Vec<ActiveEffect>,
}

struct Transient {
    begins: f64,
    lasts: f32,
    position: Vec3,
    rotation: Quat,
    drift: Vec3,
    gravity: f32,
    spin: f32,
    start_scale: Vec3,
    end_scale: Vec3,
    taper: bool,
}

impl Transient {
    fn at(begins: f64, lasts: f32, position: Vec3) -> Self {
        Self {
            begins,
            lasts,
            position,
            rotation: Quat::IDENTITY,
            drift: Vec3::ZERO,
            gravity: 0.,
            spin: 0.,
            start_scale: Vec3::ONE,
            end_scale: Vec3::ONE,
            taper: true,
        }
    }

    fn shaped(mut self, start: Vec3, end: Vec3) -> Self {
        self.start_scale = start;
        self.end_scale = end;
        self
    }
}

impl CombatFx {
    pub fn new(
        commands: &mut Commands,
        meshes: &mut Assets<Mesh>,
        materials: &mut Assets<StandardMaterial>,
    ) -> Self {
        // WebGL still prepares this mesh before the first visible effect.
        let display = meshes.add(
            Mesh::new(
                PrimitiveTopology::TriangleList,
                RenderAssetUsages::default(),
            )
            .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, vec![[0., 0., 0.]; 3])
            .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0., 1., 0.]; 3])
            .with_inserted_attribute(Mesh::ATTRIBUTE_COLOR, vec![[0., 0., 0., 0.]; 3])
            .with_inserted_indices(Indices::U32(vec![0, 1, 2])),
        );
        commands.spawn((
            EffectCanvas,
            Mesh3d(display.clone()),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::WHITE,
                alpha_mode: AlphaMode::Add,
                cull_mode: None,
                unlit: true,
                ..default()
            })),
            Transform::default(),
            Visibility::Hidden,
            NoFrustumCulling,
            NotShadowCaster,
        ));
        let sphere = Sphere::new(1.).mesh().ico(0).unwrap();
        let Some(VertexAttributeValues::Float32x3(positions)) =
            sphere.attribute(Mesh::ATTRIBUTE_POSITION)
        else {
            unreachable!("icosphere positions are float triples")
        };
        let shard = Geometry {
            positions: positions.clone(),
            triangles: sphere
                .indices()
                .unwrap()
                .iter()
                .map(|index| index as u32)
                .collect(),
        };
        Self {
            display,
            geometry: [
                marking(TAU, true),
                marking(2.06, false),
                shard,
                star(),
                taper(),
            ],
            batch: Vec::new(),
        }
    }

    pub fn active(&self) -> usize {
        self.batch.len()
    }

    pub fn clear(&mut self) {
        self.batch.clear();
    }

    fn emit(
        &mut self,
        budget: &mut usize,
        shape: Shape,
        hue: Hue,
        bright: bool,
        motion: Transient,
    ) {
        if *budget == 0 {
            return;
        }
        *budget -= 1;
        self.batch.push(ActiveEffect {
            shape,
            hue,
            bright,
            motion,
        });
    }

    fn stamp(&mut self, budget: &mut usize, pos: Vec3, at: f64, radius: f32, hue: Hue, lasts: f32) {
        let mut motion =
            Transient::at(at, lasts, pos).shaped(Vec3::splat(radius * 0.19), Vec3::splat(radius));
        motion.spin = if radius > 1.4 { 0.52 } else { 0.24 };
        self.emit(budget, Shape::Ring, hue, false, motion);
    }

    fn flash(&mut self, budget: &mut usize, pos: Vec3, at: f64, hue: Hue, size: f32) {
        let motion =
            Transient::at(at, 0.22, pos).shaped(Vec3::splat(size), Vec3::splat(size * 0.62));
        self.emit(budget, Shape::Flash, hue, true, motion);
    }

    fn shards(
        &mut self,
        budget: &mut usize,
        pos: Vec3,
        at: f64,
        hue: Hue,
        size: f32,
        count: usize,
        angle: f32,
        spread: f32,
    ) {
        for i in 0..count {
            let heading = angle + spread * (i as f32 + 0.5) / count as f32;
            let speed = (1.6 + (i % 4) as f32 * 0.44) * size.sqrt();
            let mut motion = Transient::at(
                at + 0.018 * (i % 3) as f64,
                0.28 + 0.07 * (i % 3) as f32,
                pos,
            );
            motion.drift = Vec3::new(heading.sin() * speed, 1.4 + speed, heading.cos() * speed);
            motion.gravity = 4.5;
            motion.rotation = Quat::from_rotation_arc(Vec3::Y, motion.drift.normalize());
            motion.start_scale = Vec3::new(0.10, 0.26 + 0.06 * (i % 4) as f32, 0.11) * size;
            motion.end_scale = motion.start_scale * 0.28;
            self.emit(budget, Shape::Shard, hue, i % 3 != 0, motion);
        }
    }

    fn line(
        &mut self,
        budget: &mut usize,
        from: Vec3,
        to: Vec3,
        at: f64,
        width: f32,
        hue: Hue,
        lasts: f32,
    ) {
        let vector = from - to;
        let scale = Vec3::new(width, width, vector.length());
        if scale.z < 0.04 {
            return;
        }
        let mut motion = Transient::at(at, lasts, to).shaped(scale, Vec3::new(0.01, 0.01, scale.z));
        motion.rotation = Quat::from_rotation_arc(-Vec3::Z, vector.normalize());
        motion.taper = false;
        self.emit(budget, Shape::Tail, hue, true, motion);
    }

    fn bolt(
        &mut self,
        budget: &mut usize,
        from: Vec3,
        to: Vec3,
        at: f64,
        width: f32,
        segments: usize,
    ) {
        let side = (to - from)
            .cross(Vec3::Y)
            .try_normalize()
            .unwrap_or(Vec3::X);
        let mut previous = from;
        for i in 1..=segments {
            let t = i as f32 / segments as f32;
            let jag = if i % 2 == 0 { 0.34 } else { -0.31 };
            let next = from.lerp(to, t) + (side * jag + Vec3::Y * jag * 0.32) * (PI * t).sin();
            self.line(
                budget,
                previous,
                next,
                at + f64::from(t) * 0.045,
                width,
                Hue::Violet,
                0.19,
            );
            previous = next;
        }
    }

    pub fn impact(&mut self, budget: &mut usize, hit: &Event, at: f64, handheld: bool) {
        let kind = WeaponLook::for_attack(&hit.actor);
        let pigment = kind.pigment();
        let end = p3(hit.pos, 0.98);
        let ground = p3(hit.pos, 0.50);
        let direction = hit
            .origin
            .map_or(0., |origin| facing(end - p3(origin, 0.98)));
        let strength = (hit.power.max(0.) / 130.).min(1.0);
        self.flash(budget, end, at, pigment, 0.28 + strength * 0.39);
        match kind {
            WeaponLook::Flame | WeaponLook::Frost | WeaponLook::Stone => {
                let radius = match kind {
                    WeaponLook::Flame => 1.39,
                    WeaponLook::Frost => 1.04,
                    _ => 0.63,
                };
                self.stamp(budget, ground, at + 0.02, radius, pigment, 0.34);
                self.shards(
                    budget,
                    end,
                    at,
                    pigment,
                    radius,
                    if handheld { 4 } else { 7 },
                    direction,
                    TAU,
                );
            }
            WeaponLook::Lightning => {
                if let Some(origin) = hit.origin {
                    self.bolt(budget, p3(origin, 1.28), end, at, 0.16, 4);
                }
                for (index, link) in hit
                    .links
                    .iter()
                    .take(if handheld { 2 } else { 3 })
                    .enumerate()
                {
                    self.bolt(
                        budget,
                        end,
                        p3(*link, 0.93),
                        at + 0.035 * index as f64,
                        0.14,
                        3,
                    );
                }
            }
            WeaponLook::Blade => {
                let mut motion = Transient::at(at, 0.26, ground + Vec3::Y * 0.24)
                    .shaped(Vec3::splat(0.47), Vec3::splat(1.21));
                motion.rotation = Quat::from_rotation_y(direction);
                self.emit(budget, Shape::Sweep, pigment, true, motion);
                self.shards(budget, end, at, pigment, 0.64, 4, direction - 1.0, 2.0);
            }
            WeaponLook::Bolt | WeaponLook::Gold => {
                self.shards(
                    budget,
                    end,
                    at,
                    pigment,
                    0.61 + strength * 0.27,
                    if handheld { 2 } else { 4 },
                    direction - 1.3,
                    2.6,
                );
            }
        }
    }

    pub fn cast(&mut self, budget: &mut usize, spell: &Event, at: f64, handheld: bool) {
        let look = SpellLook::for_skill(&spell.actor);
        let pigment = look.pigment();
        let ground = p3(spell.pos, 0.59);
        let source = p3(spell.origin.unwrap_or(spell.pos), 0.55);
        let aim = p3(spell.pos, 1.0);
        let radius = spell.power.clamp(1.25, 4.75);
        let strike = at + 0.24;
        self.stamp(budget, source, at, 0.97, pigment, 0.42);
        self.stamp(budget, ground, at + 0.05, radius, pigment, 0.49);
        self.stamp(
            budget,
            ground + Vec3::Y * 0.025,
            strike,
            radius,
            pigment,
            0.72,
        );
        self.flash(budget, aim + Vec3::Y * 0.19, strike, pigment, 1.55);
        match look {
            SpellLook::Flame => {
                for i in 0..3 {
                    let offset = (i as f32 - 1.) * radius * 0.37;
                    let hit = aim + Vec3::new(offset, 0., 0.31 * offset);
                    let delay = 0.067 * i as f64;
                    let sky = hit + Vec3::new(-1.74, 6.2, -0.91);
                    let v = sky - hit;
                    let scale = Vec3::new(0.46, 0.46, 2.35);
                    let mut meteor =
                        Transient::at(at + delay, 0.22, sky).shaped(scale, scale * 1.38);
                    meteor.drift = -v / 0.22;
                    meteor.rotation = Quat::from_rotation_arc(-Vec3::Z, v.normalize());
                    meteor.taper = false;
                    self.emit(budget, Shape::Tail, pigment, true, meteor);
                    self.flash(budget, hit, strike + delay, pigment, 1.16);
                    self.stamp(
                        budget,
                        hit - Vec3::Y * 0.35,
                        strike + delay,
                        1.18,
                        pigment,
                        0.42,
                    );
                    self.shards(
                        budget,
                        hit,
                        strike + delay,
                        pigment,
                        1.46,
                        if handheld { 4 } else { 6 },
                        delay as f32,
                        TAU,
                    );
                }
            }
            SpellLook::Lightning => {
                self.bolt(
                    budget,
                    aim + Vec3::Y * 7.9 + Vec3::new(-0.72, 0., 0.42),
                    aim,
                    strike,
                    0.37,
                    7,
                );
                self.bolt(budget, source + Vec3::Y * 0.88, aim, strike, 0.22, 5);
                self.shards(budget, aim, strike, pigment, 1.3, 9, 0., TAU);
            }
            SpellLook::Assault => {
                let direction = (aim - source).try_normalize().unwrap_or(Vec3::Z);
                let side = direction.cross(Vec3::Y).try_normalize().unwrap_or(Vec3::X);
                for i in -2i32..=2 {
                    let offset = side * i as f32 * 0.45;
                    self.line(
                        budget,
                        source + Vec3::Y * 0.79 + offset,
                        aim + offset * 1.4,
                        strike + f64::from(i.abs()) * 0.034,
                        0.19,
                        pigment,
                        0.27,
                    );
                }
                let mut sweep = Transient::at(strike, 0.43, ground + Vec3::Y * 0.16)
                    .shaped(Vec3::splat(0.76), Vec3::splat(radius));
                sweep.rotation = Quat::from_rotation_y(facing(direction));
                self.emit(budget, Shape::Sweep, pigment, true, sweep);
                self.shards(
                    budget,
                    aim,
                    strike,
                    pigment,
                    1.18,
                    8,
                    facing(direction) - 1.3,
                    2.6,
                );
            }
            SpellLook::Ward => {
                let mut halo = Transient::at(strike, 0.85, ground)
                    .shaped(Vec3::splat(radius * 0.44), Vec3::splat(radius));
                halo.drift = Vec3::Y * 1.14;
                halo.spin = -1.12;
                self.emit(budget, Shape::Ring, pigment, true, halo);
                for i in 0..5 {
                    let angle = i as f32 * TAU / 5.;
                    let pillar = ground + Vec3::new(angle.sin(), 0., angle.cos()) * radius * 0.69;
                    self.line(
                        budget,
                        pillar,
                        pillar + Vec3::Y * 1.76,
                        strike + i as f64 * 0.033,
                        0.13,
                        pigment,
                        0.45,
                    );
                }
            }
            SpellLook::Grove => {
                for i in 0..if handheld { 8 } else { 13 } {
                    let angle = i as f32 * 2.399;
                    let direction = Vec3::new(angle.sin(), 0., angle.cos());
                    let from = ground + direction * radius * (0.42 + 0.14 * (i % 4) as f32);
                    let mut petal = Transient::at(strike + 0.023 * i as f64, 0.57, from)
                        .shaped(Vec3::new(0.14, 0.16, 0.47), Vec3::new(0.17, 0.27, 0.65));
                    petal.drift = direction.cross(Vec3::Y) * 2.54 + Vec3::Y * 2.1;
                    petal.rotation = Quat::from_rotation_arc(Vec3::Z, petal.drift.normalize());
                    petal.spin = -2.18;
                    self.emit(budget, Shape::Tail, pigment, i % 3 == 0, petal);
                }
                let mut swirl = Transient::at(strike, 0.69, ground + Vec3::Y * 0.18)
                    .shaped(Vec3::splat(radius * 0.42), Vec3::splat(radius));
                swirl.spin = 3.6;
                self.emit(budget, Shape::Sweep, pigment, true, swirl);
            }
            SpellLook::Frost | SpellLook::Quake => {
                let ice = matches!(look, SpellLook::Frost);
                let count = if handheld { 8 } else { 12 };
                for i in 0..count {
                    let angle = i as f32 * TAU / count as f32;
                    let rim = ground
                        + Vec3::new(angle.cos(), 0., angle.sin())
                            * radius
                            * (0.46 + 0.20 * (i % 3) as f32);
                    let height = 0.54 + 0.25 * (i % 4) as f32;
                    let mut pillar = Transient::at(strike + 0.03 * (i % 5) as f64, 0.54, rim);
                    pillar.start_scale = Vec3::new(0.14, 0.31, 0.13);
                    pillar.end_scale = if ice {
                        Vec3::new(0.29, 1.26 + height, 0.23)
                    } else {
                        Vec3::new(0.52, 0.66 + height, 0.46)
                    };
                    pillar.drift = Vec3::Y * height * if ice { 1.9 } else { 0.8 };
                    pillar.rotation = Quat::from_rotation_z((angle * 2.).sin() * 0.30);
                    self.emit(budget, Shape::Shard, pigment, i % 3 != 0, pillar);
                }
                self.shards(budget, aim, strike, pigment, 1.21, 7, 0., TAU);
            }
        }
    }

    pub fn accent(&mut self, budget: &mut usize, event: &Event, at: f64) {
        let (pigment, radius, count) = match event.kind.as_str() {
            "boss_impact" => (Hue::Ember, event.power, 12),
            "victory" => (Hue::Amber, 2.7, 16),
            "merge" | "ritual" => (Hue::Amber, 1.25, 9),
            "stack" | "upgrade" => (Hue::Jade, 0.89, 5),
            "death" | "leak" => (Hue::Ember, 0.55, 4),
            "boss" => (Hue::Violet, 1.06, 7),
            "draw" | "place" => (Hue::Ivory, 0.66, 3),
            _ => return,
        };
        let pos = p3(event.pos, 0.54);
        self.stamp(
            budget,
            pos,
            at,
            radius.max(0.4),
            pigment,
            0.39 + radius * 0.08,
        );
        self.shards(
            budget,
            pos + Vec3::Y * 0.39,
            at,
            pigment,
            radius.clamp(0.60, 1.7),
            count,
            0.,
            TAU,
        );
    }
}

pub fn animate(
    time: Res<Time>,
    mut fx: ResMut<CombatFx>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut canvas: Query<&mut Visibility, With<EffectCanvas>>,
    missiles: Query<(&Projectile, &Transform)>,
) {
    let Ok(mut visible) = canvas.single_mut() else {
        return;
    };
    let now = time.elapsed_secs_f64();
    fx.batch
        .retain(|item| now < item.motion.begins + f64::from(item.motion.lasts));
    let mut positions = Vec::new();
    let mut colors = Vec::new();
    let mut indices = Vec::new();
    let mut draw = |shape: Shape, hue: Hue, bright, pose: Transform, opacity| {
        let model = &fx.geometry[shape as usize];
        let offset = positions.len() as u32;
        let color = palette(hue, bright, opacity);
        for &point in &model.positions {
            positions.push(pose.transform_point(Vec3::from_array(point)).to_array());
            colors.push(color);
        }
        indices.extend(model.triangles.iter().map(|index| index + offset));
    };
    for item in &fx.batch {
        let motion = &item.motion;
        let elapsed = (now - motion.begins) as f32;
        if elapsed < 0. {
            continue;
        }
        let t = elapsed / motion.lasts;
        let ease = 1. - (1. - t).powi(2);
        let scale = motion.start_scale.lerp(motion.end_scale, ease);
        let opacity = if motion.taper {
            (1. - t).powf(0.55)
        } else {
            1. - t * 0.45
        };
        draw(
            item.shape,
            item.hue,
            item.bright,
            Transform {
                translation: motion.position + motion.drift * elapsed
                    - Vec3::Y * motion.gravity * elapsed.powi(2),
                rotation: Quat::from_rotation_y(motion.spin * elapsed) * motion.rotation,
                scale,
            },
            opacity,
        );
    }
    for (missile, pose) in &missiles {
        if now < missile.began || now >= missile.ends {
            continue;
        }
        let (width, length) = match missile.look {
            WeaponLook::Bolt => (0.10, 0.92),
            WeaponLook::Flame => (0.25, 1.25),
            WeaponLook::Frost => (0.18, 0.81),
            WeaponLook::Lightning => (0.19, 1.05),
            WeaponLook::Stone => (0.13, 0.52),
            _ => (0.15, 0.51),
        };
        draw(
            Shape::Tail,
            missile.look.pigment(),
            matches!(missile.look, WeaponLook::Bolt | WeaponLook::Frost),
            pose.with_scale(Vec3::new(width, width, length)),
            0.88,
        );
    }
    if positions.is_empty() {
        *visible = Visibility::Hidden;
        return;
    }
    *visible = Visibility::Inherited;
    let Some(mesh) = meshes.get_mut(&fx.display) else {
        return;
    };
    mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0., 1., 0.]; positions.len()]);
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
    mesh.insert_attribute(Mesh::ATTRIBUTE_COLOR, colors);
    mesh.insert_indices(Indices::U32(indices));
}

fn palette(hue: Hue, bright: bool, opacity: f32) -> [f32; 4] {
    let [rim, core] = [
        [[228, 145, 55], [255, 237, 156]],
        [[255, 188, 106], [255, 248, 215]],
        [[249, 85, 34], [255, 224, 122]],
        [[77, 203, 236], [187, 252, 255]],
        [[135, 97, 246], [229, 217, 255]],
        [[62, 202, 160], [203, 255, 188]],
    ][hue as usize];
    let paint = if bright { core } else { rim };
    let intensity = if bright { 1.52 } else { 1.13 };
    let mut color = Color::srgb_u8(paint[0], paint[1], paint[2]).to_linear() * intensity;
    color.alpha = opacity * if bright { 0.88 } else { 0.69 };
    color.to_f32_array()
}

fn marking(angle: f32, rune: bool) -> Geometry {
    let mut points = Vec::new();
    let mut indices = Vec::new();
    let segments = if rune { 30 } else { 18 };
    let mut band = |from: f32, to: f32, inner: f32, outer: f32| {
        let first = points.len() as u32;
        for (a, r) in [(from, inner), (from, outer), (to, outer), (to, inner)] {
            points.push([a.sin() * r, 0., a.cos() * r]);
        }
        indices.extend([first, first + 1, first + 2, first, first + 2, first + 3]);
    };
    for i in 0..segments {
        let from = (i as f32 / segments as f32 - 0.5) * angle;
        let step = angle / segments as f32;
        band(
            from,
            from + step * if rune { 0.85 } else { 1. },
            if rune { 0.94 } else { 0.79 },
            1.0,
        );
        if rune && i % 3 == 0 {
            band(from + 0.045, from + step * 1.29, 0.69, 0.75);
            band(from + 0.048, from + step * 0.42, 0.74, 0.91);
        }
    }
    Geometry {
        positions: points,
        triangles: indices,
    }
}

fn star() -> Geometry {
    let mut points = vec![[0., 0., 0.]];
    let mut indices = Vec::new();
    for i in 0..16u32 {
        let angle = i as f32 * TAU / 16.;
        let radius = match i % 4 {
            0 => 1.0,
            2 => 0.62,
            _ => 0.22,
        };
        points.push([angle.sin() * radius * 1.15, 0., angle.cos() * radius]);
        indices.extend([0, i + 1, (i + 1) % 16 + 1]);
    }
    Geometry {
        positions: points,
        triangles: indices,
    }
}

fn taper() -> Geometry {
    Geometry {
        positions: vec![
            [0., 0., -1.],
            [-1., 0., -0.13],
            [0., 1., -0.09],
            [1., 0., -0.13],
            [0., -1., -0.09],
            [0., 0., 0.19],
        ],
        triangles: vec![
            0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 1, 5, 2, 1, 5, 3, 2, 5, 4, 3, 5, 1, 4,
        ],
    }
}
