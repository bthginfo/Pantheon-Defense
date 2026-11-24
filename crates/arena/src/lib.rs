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
    render::camera::ScalingMode,
    scene::SceneInstanceReady,
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
mod scenery;
use scenery::{Palette, Scenery};

thread_local! {
    static MAIL: RefCell<Mailbox> = RefCell::new(Mailbox::default());
}

#[derive(Default)]
struct Mailbox {
    game: Option<(String, Game)>,
    focus: Option<(usize, f32)>,
    viewer: usize,
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
            color: Color::srgb_u8(222, 232, 236),
            brightness: 210.,
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
                animate_projectiles,
                fade_fx,
                play_clips,
                focus_radius,
                mark_boss_zone,
                project_slots,
                report_fps,
            )
                .chain(),
        );
    app.run();
}

#[wasm_bindgen]
pub fn set_room_state(room: &str, state: &str) -> bool {
    let Ok(game) = serde_json::from_str(state) else {
        return false;
    };
    MAIL.with(|mail| mail.borrow_mut().game = Some((room.into(), game)));
    true
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
    shots: HashMap<u32, Entity>,
    graph: HashMap<String, Clips>,
    assets: HashMap<String, Handle<Gltf>>,
    seen: HashSet<u32>,
    projected: Vec2,
    projection_sent: f64,
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
    size: f32,
    yaw: f32,
    enemy: bool,
    traveling: bool,
    motion_until: f64,
    clip_until: f64,
    clip: &'static str,
    dying_until: Option<f64>,
    players: Vec<Entity>,
    active_clip: &'static str,
}

struct Stride {
    lane: usize,
    progress: f32,
    speed: f32,
    time: f64,
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
}

#[derive(Component)]
struct Particle {
    begins: f64,
    lasts: f64,
    velocity: Vec3,
    spin: Vec3,
    start: Vec3,
    scale: Vec3,
    ring: bool,
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
    };

    commands.spawn((
        ArenaCamera,
        Camera3d::default(),
        Camera {
            is_active: true,
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
            color: Color::srgb_u8(255, 231, 190),
            illuminance: 8_600.,
            shadows_enabled: !graphics.mobile,
            shadow_normal_bias: 0.37,
            ..default()
        },
        Transform::from_xyz(-4., 12., 5.).looking_at(Vec3::ZERO, Vec3::Y),
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

    for enemy in sim::catalog().enemies.iter().take(3) {
        arena.assets.insert(
            enemy.id.clone(),
            asset_server.load(format!("models/{}.glb", enemy.id)),
        );
    }
    for id in ["fx_bolt", "fx_sun", "fx_frost", "fx_spark"] {
        arena
            .assets
            .insert(id.into(), asset_server.load(format!("models/{id}.glb")));
    }
    commands.insert_resource(shared);
}

fn pull_game(
    mut commands: Commands,
    mut arena: ResMut<Arena>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut mats: ResMut<Assets<StandardMaterial>>,
    mut figures: Query<&mut Figure>,
    mut projectiles: Query<&mut Projectile>,
    asset_server: Res<AssetServer>,
    gltfs: Res<Assets<Gltf>>,
    shared: Res<Shared>,
    time: Res<Time>,
) {
    let Some((room, game)) = MAIL.with(|mail| mail.borrow_mut().game.take()) else {
        return;
    };
    let now = time.elapsed_secs_f64();
    if arena.room != room {
        arena.camera_configured = false;
        arena.ready = false;
        for (_, entity) in arena.figures.drain() {
            commands.entity(entity).despawn();
        }
        for (_, entity) in arena.shots.drain() {
            commands.entity(entity).despawn();
        }
        arena.room = room;
        arena.seen.clear();
    }
    if arena.theme != game.theme || arena.rule_version != game.rule_version {
        for ent in arena.scenery.drain(..) {
            commands.entity(ent).despawn();
        }
        arena.scenery = if game.on_circuit() {
            circuit_art::build(&mut commands, &mut meshes, &mut mats, &shared, &game.theme)
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
        for actor in sim::catalog()
            .actors
            .iter()
            .filter(|a| a.theme == game.theme && a.kind == "troop" && a.rarity == 1)
        {
            arena
                .assets
                .entry(actor.id.clone())
                .or_insert_with(|| asset_server.load(format!("models/{}.glb", actor.id)));
        }
        arena.rule_version = game.rule_version;
        arena.camera_configured = false;
        arena.theme = game.theme.clone();
        arena.projected = Vec2::ZERO;
    }

    arena.pressure = game.enemies.len();
    let tiles = game.tiles();
    let death: HashMap<_, _> = game
        .events
        .iter()
        .filter(|e| e.kind == "death")
        .map(|e| (e.source, e))
        .collect();
    let current_pieces: HashSet<_> = game
        .pieces
        .iter()
        .map(|p| p.id)
        .chain(game.enemies.iter().map(|e| e.id))
        .collect();
    let gone: Vec<_> = arena
        .figures
        .iter()
        .filter(|(id, _)| !current_pieces.contains(id))
        .map(|(id, entity)| (*id, *entity))
        .collect();
    for (id, entity) in gone {
        let Ok(mut figure) = figures.get_mut(entity) else {
            continue;
        };
        if figure.dying_until.is_some() {
            continue;
        }
        if let Some(e) = death.get(&id) {
            figure.target = p3(e.pos, 0.36);
            figure.stride = None;
            figure.clip = "Death";
            figure.dying_until = Some(now + 1.23);
        } else {
            commands.entity(entity).despawn();
            arena.figures.remove(&id);
        }
    }

    for piece in &game.pieces {
        let position = p3(tiles[piece.slot], 0.42);
        if let Some(entity) = arena.figures.get(&piece.id) {
            if let Ok(mut figure) = figures.get_mut(*entity) {
                figure.stack = piece.stack;
                if figure.target.distance(position) > 0.3 {
                    figure.yaw = facing(position - figure.target);
                    figure.target = position;
                    figure.motion_until = now + 0.45;
                }
            }
        } else {
            arena
                .assets
                .entry(piece.actor.clone())
                .or_insert_with(|| asset_server.load(format!("models/{}.glb", piece.actor)));
            let entity = spawn_figure(
                &mut commands,
                &asset_server,
                &gltfs,
                &arena,
                &piece.actor,
                position,
                if piece.owner == 0 { -0.3 } else { 0.32 },
                false,
            );
            let stack = piece.stack;
            let appear = if piece.tier > 1 { "Ascend" } else { "Spawn" };
            commands
                .entity(entity)
                .queue(move |mut entity: EntityWorldMut| {
                    if let Some(mut figure) = entity.get_mut::<Figure>() {
                        figure.stack = stack;
                        figure.clip = appear;
                        figure.clip_until = now + 0.98;
                    }
                });
            commands.entity(entity).with_children(|parent| {
                parent.spawn((
                    Mesh3d(shared.disk.clone()),
                    MeshMaterial3d(shared.team[piece.owner].clone()),
                    Transform::from_xyz(0., -0.055, 0.).with_scale(Vec3::new(0.48, 0.03, 0.48)),
                ));
            });
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
        let mut speed = sim::enemy_kind(&enemy.kind).speed;
        if game.challenge == "rush" {
            speed *= 1.27;
        }
        if enemy.slow_until > game.tick {
            speed *= 1. - enemy.slow;
        }
        if enemy.haste_until > game.tick {
            speed *= 1.18;
        }
        if (enemy.kind == "titan" && enemy.hp < enemy.max_hp * 0.43)
            || (enemy.kind == "moth" && enemy.progress > 12.)
        {
            speed *= 1.33;
        }
        let stride = Stride {
            lane: enemy.lane,
            progress: enemy.progress,
            speed,
            time: now,
        };
        if let Some(entity) = arena.figures.get(&enemy.id) {
            if let Ok(mut figure) = figures.get_mut(*entity) {
                figure.target = position;
                figure.yaw = yaw;
                figure.stride = Some(stride);
                figure.traveling = true;
            }
        } else {
            arena
                .assets
                .entry(enemy.kind.clone())
                .or_insert_with(|| asset_server.load(format!("models/{}.glb", enemy.kind)));
            let entity = spawn_figure(
                &mut commands,
                &asset_server,
                &gltfs,
                &arena,
                &enemy.kind,
                position,
                yaw,
                true,
            );
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

    for shot in &game.shots {
        if shot.impact + 13 < game.tick {
            continue;
        }
        let start = p3(shot.from, 1.35);
        let target = p3(shot.to, 0.98);
        if let Some(entity) = arena.shots.get(&shot.id) {
            if let Ok(mut missile) = projectiles.get_mut(*entity) {
                missile.to = target;
            }
            continue;
        }

        if let Some(entity) = arena.figures.get(&shot.source) {
            if let Ok(mut figure) = figures.get_mut(*entity) {
                figure.yaw = facing(target - start);
                if !matches!(figure.clip, "Cast" | "Spawn" | "Ascend") || figure.clip_until <= now {
                    figure.clip = "Attack";
                    figure.active_clip = "";
                    figure.clip_until = now + 0.47;
                }
            }
        }
        let asset = match shot.attack.as_str() {
            "stone" | "guard" => "fx_spark",
            "pierce" | "arrow" | "shred" | "bleed" => "fx_bolt",
            "frost" => "fx_frost",
            _ => "fx_sun",
        };
        let lifetime = (shot.impact.saturating_sub(shot.started) as f64) * 0.05;
        let remaining = ((shot.impact.saturating_sub(game.tick) as f64) * 0.05).max(0.16);
        let entity = spawn_figure(
            &mut commands,
            &asset_server,
            &gltfs,
            &arena,
            asset,
            start,
            facing(target - start),
            false,
        );
        commands.entity(entity).remove::<Figure>().insert((
            NotShadowCaster,
            Projectile {
                from: start,
                to: target,
                began: now - (lifetime - remaining).max(0.) * 0.8,
                ends: now + remaining,
                arc: if shot.attack == "guard" { 0.18 } else { 0.76 },
            },
        ));
        // Projectiles already have their Blender mesh as a SceneRoot. Their travel is driven by the hit tick.
        arena.shots.insert(shot.id, entity);
    }
    let present: HashSet<_> = game
        .shots
        .iter()
        .filter(|s| s.impact + 13 >= game.tick)
        .map(|s| s.id)
        .collect();
    arena.shots.retain(|id, entity| {
        if present.contains(id) {
            return true;
        }
        if projectiles
            .get(*entity)
            .is_ok_and(|missile| now < missile.ends + 0.07)
        {
            return true;
        }
        commands.entity(*entity).despawn();
        false
    });

    for effect in &game.events {
        if !arena.seen.insert(effect.id) || effect.tick + 26 < game.tick {
            continue;
        }
        let (color, radius, duration, count) = match effect.kind.as_str() {
            "impact" => {
                if let Some(entity) = arena.figures.get(&effect.source) {
                    if let Ok(mut figure) = figures.get_mut(*entity) {
                        if figure.dying_until.is_none() {
                            if figure.clip_until <= now || figure.clip == "Idle" {
                                figure.clip = "Hit";
                                figure.clip_until = now + 0.24;
                            }
                        }
                    }
                }
                (
                    match effect.actor.as_str() {
                        "frost" => 1,
                        "sun" => 0,
                        "pierce" | "arrow" => 3,
                        _ => 2,
                    },
                    if effect.actor == "sun" { 1.13 } else { 0.41 },
                    0.28,
                    if effect.actor == "sun" { 7 } else { 3 },
                )
            }
            "death" => {
                if !arena.figures.contains_key(&effect.source) {
                    arena.assets.entry(effect.actor.clone()).or_insert_with(|| {
                        asset_server.load(format!("models/{}.glb", effect.actor))
                    });
                    let id = spawn_figure(
                        &mut commands,
                        &asset_server,
                        &gltfs,
                        &arena,
                        &effect.actor,
                        p3(effect.pos, 0.34),
                        0.,
                        true,
                    );
                    commands
                        .entity(id)
                        .queue(move |mut entity: EntityWorldMut| {
                            if let Some(mut f) = entity.get_mut::<Figure>() {
                                f.dying_until = Some(now + 1.0);
                                f.clip = "Death";
                            }
                        });
                    arena.figures.insert(effect.source, id);
                }
                (5, 0.68, 0.46, 6)
            }
            "cast" => {
                if let Some(entity) = arena.figures.get(&effect.source) {
                    if let Ok(mut figure) = figures.get_mut(*entity) {
                        figure.clip = "Cast";
                        figure.active_clip = "";
                        figure.clip_until = now + 0.92;
                    }
                }
                (
                    match effect.actor.as_str() {
                        "mist" => 1,
                        "thunder" => 4,
                        "meteor" => 5,
                        _ => 3,
                    },
                    effect.power,
                    0.98,
                    15,
                )
            }
            "merge" => (0, 1.18, 0.74, 12),
            "upgrade" => (1, 0.77, 0.5, 8),
            "place" => (3, 0.64, 0.4, 5),
            "leak" => (5, 1.48, 0.61, 10),
            "boss" => (4, 1.48, 0.75, 9),
            "stack" => (1, 0.6, 0.45, 6),
            "ritual" => (4, 1.48, 1.07, 13),
            "draw" => (3, 0.58, 0.36, 4),
            "victory" => {
                for piece in &game.pieces {
                    if let Some(entity) = arena.figures.get(&piece.id) {
                        if let Ok(mut figure) = figures.get_mut(*entity) {
                            figure.clip = "Celebrate";
                            figure.clip_until = now + 1.48;
                        }
                    }
                }
                (3, 2.25, 1.2, 19)
            }
            "boss_impact" => (5, effect.power, 0.78, 15),
            _ => continue,
        };
        if arena.pressure > 34
            && matches!(effect.kind.as_str(), "impact" | "death")
            && effect.id % 2 != 0
        {
            continue;
        }
        burst(
            &mut commands,
            &shared,
            p3(effect.pos, 0.55),
            now,
            color,
            radius,
            duration,
            count,
        );
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
) -> Entity {
    let size = if arena.rule_version >= sim::CIRCUIT_RULES {
        match sim::actor(id).map(|actor| actor.kind.as_str()) {
            Some("building") => 1.0,
            Some("hero") => 1.27,
            _ => 1.21,
        }
    } else {
        1.0
    };
    let gltf = arena.assets.get(id).and_then(|handle| gltfs.get(handle));
    let scene = gltf
        .and_then(|asset| asset.default_scene.clone())
        .unwrap_or_else(|| {
            assets.load(GltfAssetLabel::Scene(0).from_asset(format!("models/{id}.glb")))
        });
    commands
        .spawn((
            SceneRoot(scene),
            Transform::from_translation(position)
                .with_rotation(Quat::from_rotation_y(yaw))
                .with_scale(Vec3::splat(size)),
            Figure {
                asset: id.into(),
                target: position,
                stride: None,
                stack: 1,
                size,
                yaw,
                enemy,
                traveling: enemy,
                motion_until: 0.,
                clip_until: 0.,
                clip: "Idle",
                dying_until: None,
                players: Vec::new(),
                active_clip: "",
            },
        ))
        .observe(find_player)
        .id()
}

fn find_player(
    ready: Trigger<SceneInstanceReady>,
    mut commands: Commands,
    mut figures: Query<&mut Figure>,
    children: Query<&Children>,
    animation: Query<&AnimationPlayer>,
) {
    let Ok(mut figure) = figures.get_mut(ready.target()) else {
        return;
    };
    figure.players = children
        .iter_descendants(ready.target())
        .filter(|child| animation.get(*child).is_ok())
        .collect();
    for player in &figure.players {
        commands.entity(*player).insert(AnimationTransitions::new());
    }
}

fn play_clips(
    mut commands: Commands,
    mut arena: ResMut<Arena>,
    mut figures: Query<&mut Figure>,
    gltf: Res<Assets<Gltf>>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
    mut players: Query<(&mut AnimationPlayer, &mut AnimationTransitions)>,
    time: Res<Time>,
) {
    let time = time.elapsed_secs_f64();
    for mut figure in &mut figures {
        if figure.players.is_empty() {
            continue;
        }
        let desired = if figure.dying_until.is_some() {
            "Death"
        } else if figure.clip_until > time {
            figure.clip
        } else if figure.enemy || figure.traveling || figure.motion_until > time {
            "Walk"
        } else {
            "Idle"
        };
        if desired == figure.active_clip {
            continue;
        }
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
    time: Res<Time>,
) {
    let now = time.elapsed_secs_f64();
    let delta = time.delta_secs().min(0.08);
    let theme = arena.theme.clone();
    let rules = arena.rule_version;
    arena.figures.retain(|_, entity| {
        if let Ok((mut figure, mut trans)) = figures.get_mut(*entity) {
            if figure.dying_until.is_some_and(|last| now >= last) {
                commands.entity(*entity).despawn();
                return false;
            }
            let blend = 1. - (-delta * if figure.enemy { 16. } else { 13. }).exp();
            let previous = trans.translation;
            let destination = if let Some(track) = &figure.stride {
                let offset = ((now - track.time) as f32).clamp(0., 0.78) * track.speed;
                let progress = track.progress + offset;
                let pos = p3(sim::route_point(rules, &theme, track.lane, progress), 0.36);
                let ahead = p3(
                    sim::route_point(rules, &theme, track.lane, progress + 0.24),
                    0.36,
                );
                if (ahead - pos).length_squared() > 0.004 {
                    figure.yaw = facing(ahead - pos);
                }
                pos
            } else {
                figure.target
            };
            trans.translation = previous.lerp(destination, blend);
            let scale = figure.size + f32::from(figure.stack.saturating_sub(1)) * 0.055;
            trans.scale = trans.scale.lerp(Vec3::splat(scale), (delta * 9.).min(1.));
            trans.rotation = trans
                .rotation
                .slerp(Quat::from_rotation_y(figure.yaw), (delta * 11.).min(1.0));
            if !figure.enemy {
                figure.traveling = previous.distance(figure.target) > 0.085;
            }
        }
        true
    });
}

fn animate_projectiles(time: Res<Time>, mut query: Query<(&Projectile, &mut Transform)>) {
    let now = time.elapsed_secs_f64();
    for (shot, mut transform) in &mut query {
        let t = ((now - shot.began) / (shot.ends - shot.began)).clamp(0., 1.) as f32;
        let next = shot.from.lerp(shot.to, t);
        let v = shot.to - shot.from;
        transform.translation = next + Vec3::Y * (std::f32::consts::PI * t).sin() * shot.arc;
        transform.rotation =
            Quat::from_rotation_y(facing(v)) * Quat::from_rotation_x((0.5 - t) * shot.arc);
        transform.scale = Vec3::splat(if t >= 1. {
            0.001
        } else {
            0.83 + (t * 7.0).sin() * 0.12
        });
    }
}

fn burst(
    commands: &mut Commands,
    shared: &Shared,
    pos: Vec3,
    now: f64,
    color: usize,
    radius: f32,
    duration: f64,
    count: usize,
) {
    let material = shared.rays[color].clone();
    commands.spawn((
        Mesh3d(shared.line.clone()),
        MeshMaterial3d(material.clone()),
        Transform::from_translation(pos),
        Particle {
            begins: now,
            lasts: duration,
            velocity: Vec3::new(radius, 0., 0.),
            spin: Vec3::ZERO,
            start: pos - Vec3::Y * 0.16,
            scale: Vec3::splat(0.48),
            ring: true,
        },
    ));
    for i in 0..count {
        let angle = i as f32 * 2.399;
        let power = 1. + (i % 4) as f32 * 0.55;
        let velocity = Vec3::new(
            angle.cos() * power,
            1.25 + power * 0.68,
            angle.sin() * power,
        );
        let scale =
            Vec3::new(0.08, 0.12 + 0.02 * power, 0.06) * if radius > 1.4 { 1.46 } else { 1. };
        commands.spawn((
            Mesh3d(shared.crystal.clone()),
            MeshMaterial3d(material.clone()),
            Transform::from_translation(pos).with_scale(scale),
            Particle {
                begins: now,
                lasts: duration * (0.7 + 0.1 * (i % 4) as f64),
                velocity: velocity * radius.sqrt(),
                spin: Vec3::new(angle, 2., power),
                start: pos,
                scale,
                ring: false,
            },
        ));
    }
}

fn fade_fx(
    mut commands: Commands,
    time: Res<Time>,
    mut particles: Query<(Entity, &Particle, &mut Transform)>,
) {
    let now = time.elapsed_secs_f64();
    for (entity, particle, mut transform) in &mut particles {
        let elapsed = (now - particle.begins) as f32;
        let t = elapsed / particle.lasts as f32;
        if t > 1. {
            commands.entity(entity).despawn();
        } else if particle.ring {
            transform.translation = particle.start;
            let size = 0.26 + particle.velocity.x * (1. - (1. - t).powi(2));
            transform.scale = Vec3::new(size, (1. - t).max(0.01) * 0.22, size);
        } else {
            transform.translation =
                particle.start + particle.velocity * elapsed - Vec3::Y * 4.4 * elapsed.powi(2);
            transform.scale = particle.scale * (1. - t).max(0.01);
            transform.rotation = Quat::from_euler(
                EulerRot::XYZ,
                particle.spin.x * elapsed,
                particle.spin.y * elapsed,
                particle.spin.z * elapsed,
            );
        }
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
    time: Res<Time>,
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
    mut query: Query<(&mut Transform, &mut Projection), With<ArenaCamera>>,
) {
    let viewer = MAIL.with(|mail| mail.borrow().viewer);
    if arena.camera_configured && arena.viewer == viewer {
        return;
    }
    if arena.theme.is_empty() {
        return;
    }
    let Ok((mut transform, mut projection)) = query.single_mut() else {
        return;
    };
    if arena.rule_version >= sim::CIRCUIT_RULES {
        let side = if viewer == 0 { 1. } else { -1. };
        *transform =
            Transform::from_xyz(0.32 * side, 26.8, 19.1 * side).looking_at(Vec3::ZERO, Vec3::Y);
        *projection = Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: 15.9,
                min_height: 17.6,
            },
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
    time: Res<Time>,
) {
    let Ok((camera, transform)) = camera.single() else {
        return;
    };
    let Some(size) = camera.logical_viewport_size() else {
        return;
    };
    if size.x < 4. || size.y < 4. || arena.theme.is_empty() {
        return;
    }
    let now = time.elapsed_secs_f64();
    if size == arena.projected && now - arena.projection_sent < 1.0 {
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
    arena.projection_sent = now;
    if !arena.ready {
        arena.ready = true;
        event("pantheon-ready", "");
    }
}
