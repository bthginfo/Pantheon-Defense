use bevy::{
    animation::{
        AnimationPlayer,
        graph::{AnimationGraph, AnimationGraphHandle, AnimationNodeIndex},
        transition::AnimationTransitions,
    },
    asset::{AssetMetaCheck, AssetPlugin},
    core_pipeline::tonemapping::Tonemapping,
    gltf::{Gltf, GltfAssetLabel},
    pbr::{CascadeShadowConfigBuilder, NotShadowCaster},
    prelude::*,
    render::camera::{CameraUpdateSystem, ScalingMode},
    scene::SceneInstanceReady,
    transform::TransformSystem,
    window::{PresentMode, WindowPlugin, WindowResolution},
};
use pantheon_simulation::{self as sim, Game, Point};
use serde::Serialize;
use std::{
    cell::RefCell,
    collections::{HashMap, HashSet},
    time::Duration,
};
use wasm_bindgen::prelude::*;

mod circuit_art;
mod combat_fx;
mod crowd;
mod predict;
mod scenery;
use combat_fx::{CombatFx, WeaponLook};
use scenery::{Palette, Scenery};

thread_local! {
    static MAIL: RefCell<Mailbox> = RefCell::new(Mailbox::default());
}

#[derive(Default)]
struct Mailbox {
    game: Option<(String, Game)>,
    focus: Option<(usize, f32)>,
    viewer: usize,
    viewing: bool,
    layout_dirty: bool,
}

#[derive(Resource)]
struct Graphics {
    mobile: bool,
}

#[wasm_bindgen]
pub fn play_arena(mobile: bool) {
    let mut app = App::new();
    app.insert_resource(Graphics { mobile })
        .insert_resource(ClearColor(Color::srgb_u8(25, 70, 77)))
        .insert_resource(AmbientLight {
            color: Color::srgb_u8(208, 225, 245),
            brightness: 315.,
            ..default()
        })
        .insert_resource(bevy::pbr::DirectionalLightShadowMap { size: 768 })
        .init_resource::<Arena>()
        .add_plugins(
            DefaultPlugins
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        canvas: Some("#arena".into()),
                        resolution: WindowResolution::new(1000., 700.)
                            .with_scale_factor_override(if mobile { 1.0 } else { 1.16 }),
                        fit_canvas_to_parent: true,
                        prevent_default_event_handling: false,
                        present_mode: PresentMode::AutoVsync,
                        ..default()
                    }),
                    ..default()
                })
                .set(AssetPlugin {
                    file_path: "assets".into(),
                    meta_check: AssetMetaCheck::Never,
                    ..default()
                }),
        )
        .add_systems(Startup, setup)
        .add_systems(
            Update,
            (
                pull_game,
                orient_camera,
                animate_figures,
                crowd::draw,
                animate_projectiles,
                combat_fx::animate,
                play_clips,
                focus_radius,
                mark_boss_zone,
                report_fps,
            )
                .chain(),
        )
        .add_systems(
            PostUpdate,
            project_slots
                .after(TransformSystem::TransformPropagate)
                .after(CameraUpdateSystem),
        );
    crowd::install(&mut app);
    app.run();
}

#[wasm_bindgen]
pub fn set_room_state(room: &str, state: &str) -> bool {
    let Ok(game) = serde_json::from_str(state) else {
        return false;
    };
    MAIL.with(|mail| {
        let mut mail = mail.borrow_mut();
        mail.game = Some((room.into(), game));
        mail.viewing = true;
    });
    true
}

#[wasm_bindgen]
pub fn close_board() {
    predict::reset();
    MAIL.with(|mail| {
        let mut mail = mail.borrow_mut();
        mail.game = None;
        mail.viewing = false;
        mail.layout_dirty = true;
    });
}

fn show_board() {
    MAIL.with(|mail| mail.borrow_mut().viewing = true);
}

#[wasm_bindgen]
pub fn set_board_focus(slot: i32, radius: f32) {
    MAIL.with(|mail| {
        mail.borrow_mut().focus = (slot >= 0
            && (slot as usize) < sim::tiles_for(sim::CIRCUIT_RULES).len())
        .then_some((slot as usize, radius.max(0.)));
    });
}

#[wasm_bindgen]
pub fn set_viewer(viewer: usize) {
    MAIL.with(|mail| mail.borrow_mut().viewer = viewer.min(1));
}

fn event(name: &str, text: &str) {
    let Some(window) = web_sys::window() else {
        return;
    };
    let init = web_sys::CustomEventInit::new();
    init.set_detail(&JsValue::from_str(text));
    if let Ok(event) = web_sys::CustomEvent::new_with_event_init_dict(name, &init) {
        let _ = window.dispatch_event(&event);
    }
}

#[derive(Component)]
struct ArenaCamera;

#[derive(Component)]
struct RangeRing;

#[derive(Component)]
struct FocusMarker;

#[derive(Component)]
struct BossMarker;

#[derive(Resource, Default)]
struct Arena {
    theme: String,
    room: String,
    rule_version: u8,
    viewer: usize,
    camera_configured: bool,
    pressure: usize,
    scenery: Vec<Entity>,
    figures: HashMap<u32, Entity>,
    shots: HashMap<u32, VisibleShot>,
    graph: HashMap<String, Clips>,
    assets: HashMap<String, Handle<Gltf>>,
    seen: HashSet<u32>,
    projected: Vec2,
    tick: u64,
    tick_arrived: f64,
    boss_cast: Option<sim::BossCast>,
    ready: bool,
}

#[derive(Clone)]
struct Clips {
    graph: Handle<AnimationGraph>,
    tracks: HashMap<&'static str, AnimationNodeIndex>,
}

#[derive(Component)]
struct Figure {
    asset: String,
    target: Vec3,
    stride: Option<Stride>,
    stack: u8,
    members: Vec<Entity>,
    yaw: f32,
    enemy: bool,
    cached: bool,
    glide: Option<Glide>,
    clip_until: f64,
    clip: &'static str,
    fall: Option<Fall>,
    hit_at: Option<f64>,
    players: Vec<Entity>,
    active_clip: &'static str,
    clip_started: f64,
}

#[derive(Component)]
struct FormationMember(Entity);

struct Fall {
    begins: f64,
    ends: f64,
}

struct Glide {
    from: Vec3,
    began: f64,
    seconds: f64,
}

struct Stride {
    lane: usize,
    reported: f32,
    displayed: f32,
    correction: f32,
    speed: f32,
    time: f64,
}

impl Stride {
    fn new(lane: usize, progress: f32, speed: f32, time: f64) -> Self {
        Self {
            lane,
            reported: progress,
            displayed: progress,
            correction: 0.,
            speed,
            time,
        }
    }

    fn step(&mut self, now: f64) -> f32 {
        let elapsed = (now - self.time).max(0.) as f32;
        let target =
            self.reported + elapsed.min(2.6) * self.speed + self.correction * (-elapsed * 6.).exp();
        self.displayed = self.displayed.max(target);
        self.displayed
    }

    fn refresh(&mut self, lane: usize, progress: f32, speed: f32, now: f64) {
        let shown = self.step(now);
        if lane != self.lane || (shown - progress).abs() > 4. {
            *self = Self::new(lane, progress, speed, now);
        } else {
            self.reported = progress;
            self.correction = shown - progress;
            self.speed = speed;
            self.time = now;
        }
    }

    fn gait_phase(&self, family: &str, now: f64, seconds: f32) -> f32 {
        let cycle = match family {
            "moth" | "wisp" => return ((now as f32 + self.displayed * 0.16) / seconds).fract(),
            "hound" => 1.46,
            "titan" => 1.55,
            "golem" => 1.37,
            "brute" | "warden" => 1.18,
            _ => 1.02,
        };
        (self.displayed / cycle).rem_euclid(1.)
    }
}

#[derive(Default)]
struct FpsSample {
    first: f64,
    frames: u32,
}

#[derive(Component)]
struct Projectile {
    from: Vec3,
    to: Vec3,
    began: f64,
    ends: f64,
    arc: f32,
    look: WeaponLook,
}

#[derive(Component)]
struct BatchedProjectile;

struct VisibleShot {
    entity: Option<Entity>,
    arrives: f64,
}

#[derive(Resource)]
struct Shared {
    cube: Handle<Mesh>,
    crystal: Handle<Mesh>,
    disk: Handle<Mesh>,
    line: Handle<Mesh>,
    rays: [Handle<StandardMaterial>; 6],
    ring: Handle<StandardMaterial>,
    team: [Handle<StandardMaterial>; 2],
    shadow: circuit_art::ContactShadow,
}

fn p3(point: Point, y: f32) -> Vec3 {
    Vec3::new(point[0], y, point[1])
}

fn facing(vector: Vec3) -> f32 {
    vector.x.atan2(vector.z)
}

fn simple(color: Color, emissive: f32) -> StandardMaterial {
    StandardMaterial {
        base_color: color,
        emissive: LinearRgba::from(color) * emissive,
        perceptual_roughness: 0.76,
        ..default()
    }
}

fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut mats: ResMut<Assets<StandardMaterial>>,
    asset_server: Res<AssetServer>,
    mut arena: ResMut<Arena>,
    graphics: Res<Graphics>,
) {
    let shared = Shared {
        cube: meshes.add(Cuboid::new(1., 1., 1.)),
        crystal: meshes.add(Sphere::new(1.).mesh().ico(0).unwrap()),
        disk: meshes.add(Cylinder::new(1., 1.).mesh().resolution(12)),
        line: meshes.add(
            Torus::new(0.975, 1.0)
                .mesh()
                .major_resolution(52)
                .minor_resolution(5),
        ),
        rays: [0xf9b54c, 0x8bdeda, 0xf09276, 0xf8dd91, 0xb9a2f2, 0xff886b].map(|int| {
            mats.add(simple(
                Color::srgb_u8((int >> 16) as u8, (int >> 8) as u8, int as u8),
                1.0,
            ))
        }),
        ring: mats.add(StandardMaterial {
            base_color: Color::srgba(1., 0.78, 0.37, 0.55),
            emissive: LinearRgba::rgb(0.8, 0.42, 0.08),
            alpha_mode: AlphaMode::Blend,
            unlit: true,
            ..default()
        }),
        team: [Color::srgb(0.28, 0.86, 0.83), Color::srgb(0.96, 0.53, 0.39)]
            .map(|color| mats.add(simple(color, 0.28))),
        shadow: circuit_art::ContactShadow::new(&mut meshes, &mut mats),
    };

    commands.spawn((
        ArenaCamera,
        Camera3d::default(),
        Camera {
            is_active: false,
            ..default()
        },
        Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: 29.0,
                min_height: 18.25,
            },
            ..OrthographicProjection::default_3d()
        }),
        Transform::from_xyz(3.3, 26.7, 27.5).looking_at(Vec3::new(0.0, -0.12, 0.1), Vec3::Y),
        Tonemapping::ReinhardLuminance,
        Msaa::Off,
    ));
    commands.spawn((
        DirectionalLight {
            color: Color::srgb_u8(255, 237, 212),
            illuminance: 7_900.,
            shadows_enabled: !graphics.mobile,
            shadow_normal_bias: 0.37,
            ..default()
        },
        Transform::from_xyz(-6.8, 12., 8.2).looking_at(Vec3::ZERO, Vec3::Y),
        CascadeShadowConfigBuilder {
            num_cascades: 1,
            maximum_distance: 64.,
            ..default()
        }
        .build(),
    ));
    let ring = |mesh: Handle<Mesh>, material: Handle<StandardMaterial>| {
        (
            Mesh3d(mesh),
            MeshMaterial3d(material),
            Transform::default(),
            NotShadowCaster,
            Visibility::Hidden,
        )
    };
    commands.spawn((RangeRing, ring(shared.line.clone(), shared.ring.clone())));
    commands.spawn((
        FocusMarker,
        ring(shared.line.clone(), shared.rays[3].clone()),
    ));

    commands.spawn((
        BossMarker,
        ring(shared.line.clone(), shared.rays[5].clone()),
    ));

    if !graphics.mobile {
        for id in ["fx_bolt", "fx_sun", "fx_frost", "fx_spark"] {
            arena
                .assets
                .insert(id.into(), asset_server.load(format!("models/{id}.glb")));
        }
    }
    let combat_fx = CombatFx::new(&mut commands, &mut meshes, &mut mats);
    commands.insert_resource(combat_fx);
    commands.insert_resource(shared);
}

fn pull_game(
    mut commands: Commands,
    mut arena: ResMut<Arena>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut mats: ResMut<Assets<StandardMaterial>>,
    mut figures: Query<(&mut Figure, &Transform)>,
    mut projectiles: Query<&mut Projectile>,
    mut combat_fx: ResMut<CombatFx>,
    mut crowd: ResMut<crowd::Crowd>,
    graphics: Res<Graphics>,
    asset_server: Res<AssetServer>,
    gltfs: Res<Assets<Gltf>>,
    shared: Res<Shared>,
    time: Res<Time<Real>>,
) {
    let Some((room, game)) = MAIL
        .with(|mail| mail.borrow_mut().game.take())
        .or_else(predict::frame)
    else {
        return;
    };
    let now = time.elapsed_secs_f64();
    let cached = graphics.mobile && game.on_circuit();
    let fresh_room = arena.room != room;
    if fresh_room {
        arena.camera_configured = false;
        arena.ready = false;
        for (_, entity) in arena.figures.drain() {
            commands.entity(entity).despawn();
        }
        for (_, shot) in arena.shots.drain() {
            if let Some(entity) = shot.entity {
                commands.entity(entity).despawn();
            }
        }
        combat_fx.clear();
        arena.room = room;
        arena.seen.clear();
    }
    if arena.theme != game.theme || arena.rule_version != game.rule_version {
        for ent in arena.scenery.drain(..) {
            commands.entity(ent).despawn();
        }
        arena.scenery = if game.on_circuit() {
            circuit_art::build(&mut commands, &asset_server, &game.theme, graphics.mobile)
        } else {
            commands.insert_resource(ClearColor(Color::srgb_u8(25, 70, 77)));
            Scenery::new(
                &mut commands,
                &mut meshes,
                &mut mats,
                &shared,
                Palette::for_theme(&game.theme),
            )
            .build(&game.theme, &asset_server)
        };
        arena
            .assets
            .retain(|id, _| sim::actor(id).is_none_or(|actor| actor.theme == game.theme));
        if cached {
            crowd.preload(&asset_server, &game.theme);
        } else {
            for actor in sim::catalog()
                .actors
                .iter()
                .filter(|a| a.theme == game.theme && a.kind == "troop" && a.rarity == 1)
            {
                arena
                    .assets
                    .entry(actor.id.clone())
                    .or_insert_with(|| asset_server.load(model_path(&actor.id, graphics.mobile)));
            }
        }
        arena.rule_version = game.rule_version;
        arena.camera_configured = false;
        arena.theme = game.theme.clone();
        arena.projected = Vec2::ZERO;
    }

    arena.pressure = game.enemies.len();
    if cached {
        for recruit in game.players.iter().flat_map(|p| &p.reserve) {
            crowd.request(&asset_server, &recruit.actor);
        }
    }
    let tiles = game.tiles();
    let recent = |effect: &&sim::Event| effect.tick + 22 >= game.tick;
    let deaths: HashSet<_> = game
        .events
        .iter()
        .filter(recent)
        .filter(|effect| effect.kind == "death")
        .map(|effect| effect.source)
        .collect();
    let current: HashSet<_> = game
        .pieces
        .iter()
        .map(|p| p.id)
        .chain(game.enemies.iter().map(|e| e.id))
        .collect();
    arena.figures.retain(|id, entity| {
        if current.contains(id)
            || deaths.contains(id)
            || figures
                .get(*entity)
                .is_ok_and(|(figure, _)| figure.fall.is_some())
        {
            return true;
        }
        commands.entity(*entity).despawn();
        false
    });

    for piece in &game.pieces {
        let position = p3(tiles[piece.slot], 0.42);
        if let Some(entity) = arena.figures.get(&piece.id) {
            if let Ok((mut figure, pose)) = figures.get_mut(*entity) {
                if figure.stack != piece.stack {
                    let scene = (!cached)
                        .then(|| figure_scene(&asset_server, &gltfs, &arena, &piece.actor));
                    set_formation(&mut commands, *entity, &mut figure, scene, piece.stack);
                }
                if figure.target.distance(position) > 0.3 {
                    figure.yaw = facing(position - pose.translation);
                    figure.glide = Some(Glide {
                        from: pose.translation,
                        began: now,
                        seconds: (0.20 + f64::from(pose.translation.distance(position)) * 0.031)
                            .min(0.48),
                    });
                    figure.target = position;
                }
            }
        } else {
            if cached {
                crowd.request(&asset_server, &piece.actor);
            } else {
                arena.assets.entry(piece.actor.clone()).or_insert_with(|| {
                    asset_server.load(model_path(&piece.actor, graphics.mobile))
                });
            }
            let entity = spawn_figure(
                &mut commands,
                &asset_server,
                &gltfs,
                &arena,
                &piece.actor,
                position,
                if piece.owner == 0 {
                    -0.32
                } else {
                    std::f32::consts::PI + 0.32
                },
                false,
                piece.stack,
                cached,
            );
            let appear = if piece.tier > 1 { "Ascend" } else { "Spawn" };
            commands
                .entity(entity)
                .queue(move |mut entity: EntityWorldMut| {
                    if let Some(mut figure) = entity.get_mut::<Figure>() {
                        figure.clip = appear;
                        figure.clip_until = now + 0.98;
                    }
                });
            if game.on_circuit() {
                circuit_art::footwork(
                    &mut commands,
                    &shared,
                    entity,
                    -0.019,
                    Vec2::new(0.64, 0.40),
                    Some(piece.owner),
                );
            } else {
                commands.entity(entity).with_children(|parent| {
                    parent.spawn((
                        Mesh3d(shared.disk.clone()),
                        MeshMaterial3d(shared.team[piece.owner].clone()),
                        Transform::from_xyz(0., -0.055, 0.).with_scale(Vec3::new(0.48, 0.03, 0.48)),
                    ));
                });
            }
            arena.figures.insert(piece.id, entity);
        }
    }
    for enemy in &game.enemies {
        let position = p3(enemy.pos, 0.36);
        let ahead = p3(
            sim::route_point(
                game.rule_version,
                &game.theme,
                enemy.lane,
                enemy.progress + 0.3,
            ),
            0.36,
        );
        let yaw = facing(ahead - position);
        let definition = sim::enemy_kind(&enemy.kind);
        let family = definition.family();
        let mut speed = definition.speed * game.enemy_speed_multiplier();
        if game.challenge == "rush" {
            speed *= 1.27;
        }
        if enemy.slow_until > game.tick {
            speed *= 1. - enemy.slow;
        }
        if enemy.haste_until > game.tick {
            speed *= 1.18;
        }
        if (family == "titan" && enemy.hp < enemy.max_hp * 0.43)
            || (family == "moth" && enemy.progress > 12.)
        {
            speed *= 1.33;
        }
        if game.phase != sim::Phase::Combat {
            speed = 0.;
        }
        if let Some(entity) = arena.figures.get(&enemy.id) {
            if let Ok((mut figure, _)) = figures.get_mut(*entity) {
                figure.target = position;
                if let Some(stride) = &mut figure.stride {
                    stride.refresh(enemy.lane, enemy.progress, speed, now);
                } else {
                    figure.stride = Some(Stride::new(enemy.lane, enemy.progress, speed, now));
                }
            }
        } else {
            if cached {
                crowd.request(&asset_server, &enemy.kind);
            } else {
                arena
                    .assets
                    .entry(enemy.kind.clone())
                    .or_insert_with(|| asset_server.load(model_path(&enemy.kind, graphics.mobile)));
            }
            let entity = spawn_figure(
                &mut commands,
                &asset_server,
                &gltfs,
                &arena,
                &enemy.kind,
                position,
                yaw,
                true,
                1,
                cached,
            );
            if game.on_circuit() {
                let size = if family == "hound" {
                    Vec2::new(0.44, 0.56)
                } else {
                    Vec2::new(0.46, 0.31)
                };
                circuit_art::footwork(&mut commands, &shared, entity, -0.010, size, None);
            }
            let stride = Stride::new(enemy.lane, enemy.progress, speed, now);
            commands
                .entity(entity)
                .queue(move |mut entity: EntityWorldMut| {
                    if let Some(mut figure) = entity.get_mut::<Figure>() {
                        figure.stride = Some(stride);
                    }
                });
            arena.figures.insert(enemy.id, entity);
        }
    }

    let missile_limit = if graphics.mobile { 54 } else { 94 };
    let mut missiles = arena
        .shots
        .values()
        .filter(|shot| shot.entity.is_some() && shot.arrives > now)
        .count();
    let mut stagger = 0;
    for shot in &game.shots {
        if shot.impact + 13 < game.tick {
            continue;
        }
        let start = p3(shot.from, 1.35);
        let target = p3(shot.to, 0.98);
        if let Some(cue) = arena.shots.get(&shot.id) {
            if let Some(entity) = cue.entity {
                if let Ok(mut missile) = projectiles.get_mut(entity) {
                    if missile.to.distance_squared(target) < 2.8 {
                        missile.to = target;
                    }
                }
            }
            continue;
        }

        if missiles >= missile_limit || (fresh_room && shot.impact < game.tick) {
            arena.shots.insert(
                shot.id,
                VisibleShot {
                    entity: None,
                    arrives: now,
                },
            );
            continue;
        }
        missiles += 1;
        if let Some(entity) = arena.figures.get(&shot.source) {
            if let Ok((mut figure, _)) = figures.get_mut(*entity) {
                if figure.glide.is_none()
                    && (!matches!(figure.clip, "Cast" | "Spawn" | "Ascend")
                        || figure.clip_until <= now)
                {
                    figure.yaw = facing(target - start);
                    figure.clip = "Attack";
                    figure.active_clip = "";
                    figure.clip_until = now + 0.42;
                }
            }
        }
        // Snapshots arrive in batches. Keep the flight readable and fire a short staggered volley.
        let look = WeaponLook::for_attack(&shot.attack);
        let remaining = shot.impact.saturating_sub(game.tick) as f64 * 0.05;
        let began = now + 0.025 * (stagger % 6) as f64;
        stagger += 1;
        let arrives = began + remaining.max(look.minimum_flight()).min(0.68);
        let mut projectile = commands.spawn((
            Transform::from_translation(start).with_scale(Vec3::splat(0.001)),
            NotShadowCaster,
            Projectile {
                from: start,
                to: target,
                began,
                ends: arrives,
                arc: look.arc(),
                look,
            },
        ));
        if !cached {
            let scene = figure_scene(&asset_server, &gltfs, &arena, look.model());
            projectile.insert(SceneRoot(scene));
        }
        let entity = projectile.id();
        if cached {
            projectile.insert(BatchedProjectile);
        }
        arena.shots.insert(
            shot.id,
            VisibleShot {
                entity: Some(entity),
                arrives,
            },
        );
    }
    let present: HashSet<_> = game
        .shots
        .iter()
        .filter(|shot| shot.impact + 13 >= game.tick)
        .map(|shot| shot.id)
        .collect();
    arena.shots.retain(|id, cue| {
        if present.contains(id) || now < cue.arrives + 0.09 {
            return true;
        }
        if let Some(entity) = cue.entity {
            commands.entity(entity).despawn();
        }
        false
    });

    let effect_limit: usize = if graphics.mobile { 155 } else { 272 };
    let mut budget = if fresh_room {
        effect_limit
    } else {
        effect_limit.saturating_sub(combat_fx.active())
    };
    let mut cast_hits = Vec::new();
    for effect in game.events.iter().filter(recent) {
        if !arena.seen.insert(effect.id) {
            continue;
        }
        if fresh_room && effect.tick + 5 < game.tick {
            continue;
        }
        match effect.kind.as_str() {
            "impact" => {
                let at = effect
                    .shot
                    .and_then(|id| arena.shots.get(&id))
                    .map_or(now, |flight| flight.arrives.max(now));
                if let Some(entity) = arena.figures.get(&effect.source) {
                    if let Ok((mut figure, _)) = figures.get_mut(*entity) {
                        figure.hit_at = Some(figure.hit_at.map_or(at, |first| first.min(at)));
                    }
                }
                let mut sparks = budget.saturating_sub(30);
                if sparks > 0 {
                    let carried = sparks;
                    combat_fx.impact(&mut sparks, effect, at, graphics.mobile);
                    budget -= carried - sparks;
                }
            }
            "cast" => {
                if let Some(entity) = arena.figures.get(&effect.source) {
                    if let Ok((mut figure, _)) = figures.get_mut(*entity) {
                        figure.clip = "Cast";
                        figure.active_clip = "";
                        figure.clip_until = now + 0.79;
                        if let Some(origin) = effect.origin {
                            if sim::distance(origin, effect.pos) > 0.12 {
                                figure.yaw = facing(p3(effect.pos, 0.) - p3(origin, 0.));
                            }
                        }
                    }
                }
                combat_fx.cast(&mut budget, effect, now, graphics.mobile);
                cast_hits.push((effect.tick, effect.pos, effect.power, now + 0.24));
            }
            "death" => {
                let at = cast_hits
                    .iter()
                    .filter(|(tick, pos, radius, _)| {
                        effect.tick == *tick && sim::distance(*pos, effect.pos) <= *radius
                    })
                    .map(|(_, _, _, at)| *at)
                    .fold(now, f64::max);
                let position = p3(effect.pos, 0.36);
                let fall = if let Some(entity) = arena.figures.get(&effect.source) {
                    if let Ok((mut figure, pose)) = figures.get_mut(*entity) {
                        let begins = at.max(figure.hit_at.unwrap_or(now));
                        figure.target = pose.translation;
                        figure.stride = None;
                        figure.fall = Some(Fall {
                            begins,
                            ends: begins + 1.14,
                        });
                        begins
                    } else {
                        at
                    }
                } else {
                    if cached {
                        crowd.request(&asset_server, &effect.actor);
                    } else {
                        arena.assets.entry(effect.actor.clone()).or_insert_with(|| {
                            asset_server.load(model_path(&effect.actor, graphics.mobile))
                        });
                    }
                    let entity = spawn_figure(
                        &mut commands,
                        &asset_server,
                        &gltfs,
                        &arena,
                        &effect.actor,
                        position,
                        0.,
                        true,
                        1,
                        cached,
                    );
                    commands
                        .entity(entity)
                        .queue(move |mut entity: EntityWorldMut| {
                            if let Some(mut figure) = entity.get_mut::<Figure>() {
                                figure.fall = Some(Fall {
                                    begins: at,
                                    ends: at + 1.14,
                                });
                            }
                        });
                    arena.figures.insert(effect.source, entity);
                    at
                };
                combat_fx.accent(&mut budget, effect, fall + 0.08);
            }
            _ => {
                if effect.kind == "victory" {
                    for piece in &game.pieces {
                        if let Some(entity) = arena.figures.get(&piece.id) {
                            if let Ok((mut figure, _)) = figures.get_mut(*entity) {
                                figure.clip = "Celebrate";
                                figure.clip_until = now + 1.48;
                            }
                        }
                    }
                }
                combat_fx.accent(&mut budget, effect, now);
            }
        }
    }
    if arena.seen.len() > 4000 {
        let first = game.events.first().map_or(0, |e| e.id);
        arena.seen.retain(|event| *event >= first);
    }
    arena.boss_cast = game.boss_cast;
    arena.tick = game.tick;
    arena.tick_arrived = now;
}

fn spawn_figure(
    commands: &mut Commands,
    assets: &AssetServer,
    gltfs: &Assets<Gltf>,
    arena: &Arena,
    id: &str,
    position: Vec3,
    yaw: f32,
    enemy: bool,
    stack: u8,
    cached: bool,
) -> Entity {
    let size = if arena.rule_version >= sim::CIRCUIT_RULES {
        match sim::actor(id).map(|actor| actor.kind.as_str()) {
            Some("building") => 1.12,
            Some("hero") => 1.72,
            _ if enemy => 1.42,
            _ => 1.55,
        }
    } else {
        1.0
    };
    let scene = (!cached).then(|| figure_scene(assets, gltfs, arena, id));
    let entity = commands
        .spawn((
            Transform::from_translation(position)
                .with_rotation(Quat::from_rotation_y(yaw))
                .with_scale(Vec3::splat(size)),
            Visibility::default(),
        ))
        .id();
    let mut figure = Figure {
        asset: id.into(),
        target: position,
        stride: None,
        stack: 0,
        members: Vec::new(),
        yaw,
        enemy,
        cached,
        glide: None,
        clip_until: 0.,
        clip: "Idle",
        fall: None,
        hit_at: None,
        players: Vec::new(),
        active_clip: "",
        clip_started: 0.,
    };
    set_formation(commands, entity, &mut figure, scene, stack);
    commands.entity(entity).insert(figure);
    entity
}

fn formation_layout(stack: u8) -> &'static [Vec3] {
    static SINGLE: [Vec3; 1] = [Vec3::ZERO];
    static PAIR: [Vec3; 2] = [Vec3::new(-0.43, 0., -0.10), Vec3::new(0.43, 0., 0.10)];
    static TRIO: [Vec3; 3] = [
        Vec3::new(-0.47, 0., -0.10),
        Vec3::new(0.47, 0., -0.10),
        Vec3::new(0., 0., 0.36),
    ];
    match stack {
        2 => &PAIR,
        3 => &TRIO,
        _ => &SINGLE,
    }
}

fn set_formation(
    commands: &mut Commands,
    group: Entity,
    figure: &mut Figure,
    scene: Option<Handle<Scene>>,
    stack: u8,
) {
    figure.stack = stack.clamp(1, 3);
    let positions = formation_layout(figure.stack);
    if figure.members.len() > positions.len() {
        for member in figure.members.drain(positions.len()..) {
            commands.entity(member).despawn();
        }
        figure.active_clip = "";
    }
    for &position in &positions[figure.members.len()..] {
        let mut member = commands.spawn((
            ChildOf(group),
            FormationMember(group),
            Transform::from_translation(position).with_scale(Vec3::splat(if stack > 1 {
                0.78
            } else {
                1.
            })),
        ));
        if let Some(scene) = &scene {
            member.insert(SceneRoot(scene.clone())).observe(find_player);
        }
        figure.members.push(member.id());
    }
}

const MOBILE_MODELS: &str = include_str!("../../../public/assets/mobile/models.txt");

fn model_path(id: &str, mobile: bool) -> String {
    let directory = if mobile && MOBILE_MODELS.lines().any(|name| name == id) {
        "mobile"
    } else {
        "models"
    };
    format!("{directory}/{id}.glb")
}

fn figure_scene(
    assets: &AssetServer,
    gltfs: &Assets<Gltf>,
    arena: &Arena,
    id: &str,
) -> Handle<Scene> {
    let handle = arena.assets.get(id);
    handle
        .and_then(|handle| gltfs.get(handle))
        .and_then(|asset| asset.default_scene.clone())
        .unwrap_or_else(|| {
            let path = handle
                .and_then(Handle::path)
                .cloned()
                .unwrap_or_else(|| model_path(id, false).into());
            assets.load(GltfAssetLabel::Scene(0).from_asset(path))
        })
}

fn find_player(
    ready: Trigger<SceneInstanceReady>,
    mut commands: Commands,
    mut figures: Query<&mut Figure>,
    members: Query<&FormationMember>,
    children: Query<&Children>,
    animation: Query<&AnimationPlayer>,
) {
    let Ok(member) = members.get(ready.target()) else {
        return;
    };
    let Ok(mut figure) = figures.get_mut(member.0) else {
        return;
    };
    figure.players.retain(|player| animation.contains(*player));
    for player in children
        .iter_descendants(ready.target())
        .filter(|child| animation.contains(*child))
    {
        figure.players.push(player);
        commands.entity(player).insert(AnimationTransitions::new());
    }
    figure.active_clip = "";
}

fn desired_clip(figure: &Figure, now: f64) -> &'static str {
    if figure.fall.as_ref().is_some_and(|fall| now >= fall.begins) {
        "Death"
    } else if figure.glide.is_some() && figure.clip != "Cast" {
        "Walk"
    } else if figure.clip_until > now {
        figure.clip
    } else if figure.enemy || figure.glide.is_some() {
        "Walk"
    } else {
        "Idle"
    }
}

fn play_clips(
    mut commands: Commands,
    mut arena: ResMut<Arena>,
    mut figures: Query<&mut Figure>,
    gltf: Res<Assets<Gltf>>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
    mut players: Query<(&mut AnimationPlayer, &mut AnimationTransitions)>,
    time: Res<Time<Real>>,
) {
    let time = time.elapsed_secs_f64();
    for mut figure in &mut figures {
        if figure.players.is_empty() {
            continue;
        }
        let desired = desired_clip(&figure, time);
        if desired == figure.active_clip {
            continue;
        }
        figure.players.retain(|player| players.contains(*player));
        if !arena.graph.contains_key(&figure.asset) {
            let Some(source) = arena
                .assets
                .get(&figure.asset)
                .and_then(|handle| gltf.get(handle))
            else {
                continue;
            };
            let tracks: Vec<_> = [
                "Idle",
                "Walk",
                "Attack",
                "Cast",
                "Hit",
                "Death",
                "Spawn",
                "Ascend",
                "Celebrate",
            ]
            .into_iter()
            .filter_map(|name| {
                source
                    .named_animations
                    .get(name)
                    .cloned()
                    .map(|clip| (name, clip))
            })
            .collect();
            if tracks.is_empty() {
                continue;
            }
            let (graph, indices) =
                AnimationGraph::from_clips(tracks.iter().map(|(_, clip)| clip.clone()));
            arena.graph.insert(
                figure.asset.clone(),
                Clips {
                    graph: graphs.add(graph),
                    tracks: tracks
                        .into_iter()
                        .zip(indices)
                        .map(|((name, _), index)| (name, index))
                        .collect(),
                },
            );
        }
        let clips = &arena.graph[&figure.asset];
        if let Some(index) = clips
            .tracks
            .get(desired)
            .or_else(|| clips.tracks.get("Idle"))
        {
            for entity in &figure.players {
                if let Ok((mut player, mut transitions)) = players.get_mut(*entity) {
                    commands
                        .entity(*entity)
                        .insert(AnimationGraphHandle(clips.graph.clone()));
                    let motion = transitions.play(
                        &mut player,
                        *index,
                        Duration::from_millis(match desired {
                            "Attack" | "Hit" => 78,
                            "Death" => 115,
                            _ => 142,
                        }),
                    );
                    match desired {
                        "Attack" => {
                            motion.set_speed(1.52);
                        }
                        "Cast" => {
                            motion.set_speed(1.27);
                        }
                        "Hit" => {
                            motion.set_speed(1.8);
                        }
                        "Death" | "Spawn" | "Ascend" | "Celebrate" => {}
                        "Walk" => {
                            motion
                                .set_speed(if figure.enemy { 1.14 } else { 1.33 })
                                .repeat();
                        }
                        _ => {
                            motion.repeat();
                        }
                    }
                }
            }
        }
        figure.active_clip = desired;
    }
}

fn animate_figures(
    mut commands: Commands,
    mut arena: ResMut<Arena>,
    mut figures: Query<(&mut Figure, &mut Transform)>,
    mut members: Query<&mut Transform, (With<FormationMember>, Without<Figure>)>,
    time: Res<Time<Real>>,
) {
    let now = time.elapsed_secs_f64();
    let delta = time.delta_secs().min(0.25);
    let theme = arena.theme.clone();
    let rules = arena.rule_version;
    arena.figures.retain(|_, entity| {
        if let Ok((mut figure, mut trans)) = figures.get_mut(*entity) {
            if figure.fall.as_ref().is_some_and(|fall| now >= fall.ends) {
                commands.entity(*entity).despawn();
                return false;
            }
            if figure.hit_at.is_some_and(|at| now >= at) {
                figure.hit_at = None;
                if figure.fall.is_none() && figure.clip_until <= now {
                    figure.clip = "Hit";
                    figure.clip_until = now + 0.21;
                }
            }
            let blend = 1. - (-delta * if figure.enemy { 16. } else { 13. }).exp();
            let translation = if let Some(track) = &mut figure.stride {
                let progress = track.step(now);
                let route =
                    |distance| p3(sim::route_point(rules, &theme, track.lane, distance), 0.36);
                let center = route(progress);
                let before = route((progress - 0.30).max(0.));
                let after = route(progress + 0.30);
                if (after - before).length_squared() > 0.004 {
                    figure.yaw = facing(after - before);
                }
                (center * 4. + before + after) / 6.
            } else if let Some(glide) = &figure.glide {
                let t = ((now - glide.began) / glide.seconds).clamp(0., 1.) as f32;
                let position = glide.from.lerp(figure.target, 1. - (1. - t).powi(2));
                if t >= 1. {
                    figure.glide = None;
                }
                position
            } else {
                figure.target
            };
            if trans.translation != translation {
                trans.translation = translation;
            }
            for (&entity, &position) in figure.members.iter().zip(formation_layout(figure.stack)) {
                let Ok(mut pose) = members.get_mut(entity) else {
                    continue;
                };
                if pose.translation.distance_squared(position) > 0.000001 {
                    pose.translation = pose.translation.lerp(position, blend);
                }
                let scale = Vec3::splat(if figure.stack > 1 { 0.78 } else { 1. });
                if pose.scale.distance_squared(scale) > 0.000001 {
                    pose.scale = pose.scale.lerp(scale, blend);
                }
            }
            let target = Quat::from_rotation_y(figure.yaw);
            if trans.rotation.dot(target).abs() < 0.999_999 {
                trans.rotation = trans.rotation.slerp(target, 1. - (-delta * 10.).exp());
            }
        }
        true
    });
}

fn animate_projectiles(time: Res<Time<Real>>, mut query: Query<(&Projectile, &mut Transform)>) {
    let now = time.elapsed_secs_f64();
    for (shot, mut transform) in &mut query {
        if now < shot.began || now >= shot.ends {
            transform.scale = Vec3::splat(0.001);
            continue;
        }
        let t = ((now - shot.began) / (shot.ends - shot.began)) as f32;
        let arc = std::f32::consts::PI * t;
        transform.translation = shot.from.lerp(shot.to, t) + Vec3::Y * arc.sin() * shot.arc;
        let tangent = shot.to - shot.from + Vec3::Y * (arc.cos() * shot.arc * std::f32::consts::PI);
        transform.rotation =
            Quat::from_rotation_arc(Vec3::Z, tangent.try_normalize().unwrap_or(Vec3::Z));
        transform.scale = Vec3::splat(0.94);
    }
}

fn focus_radius(
    arena: Res<Arena>,
    mut rings: Query<(&mut Transform, &mut Visibility), (With<RangeRing>, Without<FocusMarker>)>,
    mut markers: Query<(&mut Transform, &mut Visibility), (With<FocusMarker>, Without<RangeRing>)>,
) {
    let Ok((mut ring, mut ring_vis)) = rings.single_mut() else {
        return;
    };
    let Ok((mut marker, mut marker_vis)) = markers.single_mut() else {
        return;
    };
    let tiles = sim::tiles_for(arena.rule_version);
    if let Some((slot, radius)) = MAIL
        .with(|mail| mail.borrow().focus)
        .filter(|(slot, _)| *slot < tiles.len())
    {
        ring.translation = p3(tiles[slot], 0.47);
        ring.scale = Vec3::new(radius, 0.28, radius);
        marker.translation = p3(tiles[slot], 0.50);
        marker.scale = Vec3::new(0.70, 0.40, 0.70);
        *marker_vis = Visibility::Visible;
        *ring_vis = if radius > 0. {
            Visibility::Visible
        } else {
            Visibility::Hidden
        };
    } else {
        *ring_vis = Visibility::Hidden;
        *marker_vis = Visibility::Hidden;
    }
}

fn mark_boss_zone(
    arena: Res<Arena>,
    time: Res<Time<Real>>,
    mut query: Query<(&mut Transform, &mut Visibility), With<BossMarker>>,
) {
    let Ok((mut transform, mut visible)) = query.single_mut() else {
        return;
    };
    if let Some(cast) = &arena.boss_cast {
        let pulse = (time.elapsed_secs() * 12.).sin() * 0.10;
        transform.translation = p3(cast.pos, 0.55);
        let radius = cast.radius + pulse;
        transform.scale = Vec3::new(radius, 0.66 + pulse, radius);
        *visible = Visibility::Visible;
    } else {
        *visible = Visibility::Hidden;
    }
}

fn orient_camera(
    mut arena: ResMut<Arena>,
    graphics: Res<Graphics>,
    mut query: Query<(&mut Camera, &mut Transform, &mut Projection), With<ArenaCamera>>,
) {
    let (viewer, viewing, layout_dirty) = MAIL.with(|mail| {
        let mut mail = mail.borrow_mut();
        (
            mail.viewer,
            mail.viewing,
            std::mem::take(&mut mail.layout_dirty),
        )
    });
    if layout_dirty {
        arena.ready = false;
        arena.projected = Vec2::ZERO;
    }
    let Ok((mut camera, mut transform, mut projection)) = query.single_mut() else {
        return;
    };
    if camera.is_active != viewing {
        camera.is_active = viewing;
    }
    if !viewing || arena.theme.is_empty() || (arena.camera_configured && arena.viewer == viewer) {
        return;
    }
    if arena.rule_version >= sim::CIRCUIT_RULES {
        // A steeper view frames the portrait board edge to edge on a phone.
        let side = if viewer == 0 { 1. } else { -1. };
        *transform = Transform::from_xyz(1.35 * side, 27.0, 17.5 * side)
            .looking_at(Vec3::new(0., 0.04, 0.35 * side), Vec3::Y);
        *projection = Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: if graphics.mobile { 14.7 } else { 15.6 },
                min_height: 18.3,
            },
            viewport_origin: Vec2::new(0.5, if graphics.mobile { 0.47 } else { 0.5 }),
            ..OrthographicProjection::default_3d()
        });
    } else {
        *transform =
            Transform::from_xyz(3.3, 26.7, 27.5).looking_at(Vec3::new(0., -0.12, 0.1), Vec3::Y);
        *projection = Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: 29.,
                min_height: 18.25,
            },
            ..OrthographicProjection::default_3d()
        });
    }
    arena.camera_configured = true;
    arena.viewer = viewer;
    arena.projected = Vec2::ZERO;
}

fn report_fps(time: Res<Time<Real>>, mut sample: Local<FpsSample>) {
    let now = time.elapsed_secs_f64();
    if !MAIL.with(|mail| mail.borrow().viewing) {
        sample.first = now;
        sample.frames = 0;
        return;
    }
    sample.frames += 1;
    let time_passed = now - sample.first;
    if time_passed >= 1.5 {
        event(
            "pantheon-frame-rate",
            &format!("{:.1}", f64::from(sample.frames) / time_passed),
        );
        sample.frames = 0;
        sample.first = now;
    }
}

#[derive(Serialize)]
struct ProjectionData {
    width: f32,
    height: f32,
    slots: Vec<[f32; 2]>,
}

fn project_slots(
    mut arena: ResMut<Arena>,
    camera: Query<(&Camera, &GlobalTransform), With<ArenaCamera>>,
) {
    let Ok((camera, transform)) = camera.single() else {
        return;
    };
    if !camera.is_active {
        return;
    }
    let Some(size) = camera.logical_viewport_size() else {
        return;
    };
    if size.x < 4. || size.y < 4. || arena.theme.is_empty() {
        return;
    }
    if size == arena.projected && arena.ready {
        return;
    }
    let tiles = sim::tiles_for(arena.rule_version);
    let positions: Vec<_> = tiles
        .iter()
        .filter_map(|&point| camera.world_to_viewport(transform, p3(point, 0.57)).ok())
        .map(|pos| [pos.x, pos.y])
        .collect();
    if positions.len() != tiles.len() {
        return;
    }
    if let Ok(text) = serde_json::to_string(&ProjectionData {
        width: size.x,
        height: size.y,
        slots: positions,
    }) {
        event("pantheon-slots", &text);
    }
    arena.projected = size;
    if !arena.ready {
        arena.ready = true;
        event("pantheon-ready", "");
    }
}
