//! Baked Blender dioramas and the soft contact shadows that follow moving pieces.

use super::{Arena, ArenaCamera, Graphics, Shared, event};
use bevy::{
    asset::RenderAssetUsages,
    core_pipeline::tonemapping::Tonemapping,
    gltf::GltfAssetLabel,
    pbr::NotShadowCaster,
    prelude::*,
    render::{
        camera::CameraUpdateSystem,
        mesh::{Indices, PrimitiveTopology},
        render_resource::{Extent3d, TextureDimension, TextureFormat, TextureUsages},
        view::RenderLayers,
    },
    scene::SceneInstanceReady,
    transform::TransformSystem,
};

#[derive(Component)]
struct Diorama(String);

#[derive(Component)]
struct ReadyDiorama;

#[derive(Component)]
struct TerrainCamera;

#[derive(Component)]
struct TerrainBackdrop;

#[derive(Resource)]
struct TerrainCache {
    image: Handle<Image>,
    capture: Option<(Entity, usize, UVec2)>,
    frames: u8,
}

const TERRAIN_LAYER: usize = 1;
const CAPTURE_WARMUP_FRAMES: u8 = 3;

pub fn install_terrain_cache(app: &mut App) {
    app.add_systems(Startup, prepare_terrain_cache).add_systems(
        PostUpdate,
        update_terrain_cache
            .after(CameraUpdateSystem)
            .before(TransformSystem::TransformPropagate),
    );
}

pub fn live_layers() -> RenderLayers {
    RenderLayers::layer(0).with(TERRAIN_LAYER)
}

pub fn build(commands: &mut Commands, assets: &AssetServer, theme: &str) -> Vec<Entity> {
    let colors = match theme {
        "rome" => [24, 61, 75],
        "japan" => [20, 70, 85],
        _ => [12, 73, 89],
    };
    commands.insert_resource(ClearColor(Color::srgb_u8(colors[0], colors[1], colors[2])));
    let model = format!("models/arena_{theme}.glb");
    let scene = assets.load(GltfAssetLabel::Scene(0).from_asset(model));
    vec![
        commands
            .spawn((Diorama(theme.into()), SceneRoot(scene)))
            .observe(reveal)
            .id(),
    ]
}

fn reveal(
    trigger: Trigger<SceneInstanceReady>,
    mut commands: Commands,
    graphics: Res<Graphics>,
    boards: Query<&Diorama>,
    children: Query<&Children>,
    meshes: Query<(), With<Mesh3d>>,
) {
    if let Ok(board) = boards.get(trigger.target()) {
        for entity in children.iter_descendants(trigger.target()) {
            if meshes.contains(entity) {
                let mut mesh = commands.entity(entity);
                mesh.insert(NotShadowCaster);
                if graphics.mobile {
                    mesh.insert(RenderLayers::layer(TERRAIN_LAYER));
                }
            }
        }
        commands.entity(trigger.target()).insert(ReadyDiorama);
        event("pantheon-board-models", &board.0);
    }
}

fn prepare_terrain_cache(
    mut commands: Commands,
    graphics: Res<Graphics>,
    mut images: ResMut<Assets<Image>>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    if !graphics.mobile {
        return;
    }
    let mut image = Image::new_fill(
        Extent3d {
            width: 1,
            height: 1,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        &[0, 0, 0, 255],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    image.texture_descriptor.usage |= TextureUsages::RENDER_ATTACHMENT;
    let image = images.add(image);
    commands.spawn((
        TerrainCamera,
        Camera3d::default(),
        Camera {
            order: -1,
            is_active: false,
            target: image.clone().into(),
            ..default()
        },
        Projection::Orthographic(OrthographicProjection::default_3d()),
        Tonemapping::ReinhardLuminance,
        Msaa::Off,
        RenderLayers::layer(TERRAIN_LAYER),
    ));
    commands.spawn((
        TerrainBackdrop,
        Visibility::Hidden,
        Mesh3d(meshes.add(Rectangle::new(1., 1.))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color_texture: Some(image.clone()),
            unlit: true,
            ..default()
        })),
        NotShadowCaster,
    ));
    commands.insert_resource(TerrainCache {
        image,
        capture: None,
        frames: 0,
    });
}

fn update_terrain_cache(
    cache: Option<ResMut<TerrainCache>>,
    arena: Res<Arena>,
    mut images: ResMut<Assets<Image>>,
    boards: Query<(Entity, &Diorama), With<ReadyDiorama>>,
    mut main: Query<(&Camera, &Transform, &Projection, &mut RenderLayers), With<ArenaCamera>>,
    mut capture: Query<
        (&mut Camera, &mut Transform, &mut Projection),
        (With<TerrainCamera>, Without<ArenaCamera>),
    >,
    mut backdrop: Query<
        (&mut Transform, &mut Visibility),
        (
            With<TerrainBackdrop>,
            Without<ArenaCamera>,
            Without<TerrainCamera>,
        ),
    >,
) {
    let (
        Some(mut cache),
        Ok((camera, view, projection, mut layers)),
        Ok((mut capture, mut pose, mut optics)),
        Ok((mut quad, mut show)),
    ) = (
        cache,
        main.single_mut(),
        capture.single_mut(),
        backdrop.single_mut(),
    )
    else {
        return;
    };
    let board = boards
        .iter()
        .find(|(entity, board)| arena.theme == board.0 && arena.scenery.contains(entity));
    let size = camera
        .physical_viewport_size()
        .filter(|size| size.min_element() > 0);
    let (Some((board, _)), Some(size), Projection::Orthographic(projection)) =
        (board, size, projection)
    else {
        cache.capture = None;
        capture.is_active = false;
        *show = Visibility::Hidden;
        *layers = live_layers();
        return;
    };
    let key = (board, arena.viewer, size);
    if cache.capture != Some(key) {
        if let Some(image) = images.get_mut(&cache.image) {
            image.resize(Extent3d {
                width: size.x,
                height: size.y,
                depth_or_array_layers: 1,
            });
        }
        *pose = *view;
        *optics = Projection::Orthographic(projection.clone());
        let center = projection.area.center();
        *quad = Transform::from_translation(
            view.translation
                + view.forward() * 120.
                + view.right() * center.x
                + view.up() * center.y,
        )
        .with_rotation(view.rotation)
        .with_scale(Vec3::new(
            projection.area.width(),
            projection.area.height(),
            1.,
        ));
        cache.capture = Some(key);
        // Keep the mesh visible until the target resize and render pipelines have settled.
        cache.frames = CAPTURE_WARMUP_FRAMES;
        capture.is_active = true;
        *show = Visibility::Hidden;
        *layers = live_layers();
    } else if cache.frames > 0 {
        cache.frames -= 1;
        if cache.frames == 0 {
            capture.is_active = false;
            *show = Visibility::Visible;
            *layers = RenderLayers::layer(0);
        }
    }
}

pub fn soft_shadow() -> Mesh {
    let steps = 18u32;
    let mut positions = vec![[0., 0., 0.]];
    let mut colors = vec![[0.09, 0.125, 0.14, 0.37]];
    let mut indices = Vec::new();
    for (ring, (radius, alpha)) in [(0.39f32, 0.23f32), (1.0, 0.)].into_iter().enumerate() {
        for i in 0..steps {
            let theta = i as f32 * std::f32::consts::TAU / steps as f32;
            positions.push([radius * theta.cos(), 0., radius * theta.sin()]);
            colors.push([0.09, 0.125, 0.14, alpha]);
            let current = i + 1;
            let next = (i + 1) % steps + 1;
            if ring == 0 {
                indices.extend([0, next, current]);
            } else {
                indices.extend([
                    current,
                    next,
                    current + steps,
                    next,
                    next + steps,
                    current + steps,
                ]);
            }
        }
    }
    let normals = vec![[0., 1., 0.]; positions.len()];
    Mesh::new(
        PrimitiveTopology::TriangleList,
        RenderAssetUsages::RENDER_WORLD,
    )
    .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, positions)
    .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, normals)
    .with_inserted_attribute(Mesh::ATTRIBUTE_COLOR, colors)
    .with_inserted_indices(Indices::U32(indices))
}

pub fn footwork(
    commands: &mut Commands,
    shared: &Shared,
    figure: Entity,
    height: f32,
    size: Vec2,
    camp: Option<usize>,
) {
    commands.entity(figure).with_children(|children| {
        children.spawn((
            Mesh3d(shared.footprint.clone()),
            MeshMaterial3d(shared.contact.clone()),
            Transform::from_xyz(0.091, height, 0.018).with_scale(Vec3::new(size.x, 1., size.y)),
            NotShadowCaster,
        ));
        if let Some(camp) = camp {
            // The slim inlay identifies each camp without putting a pedestal under the figures.
            children.spawn((
                Mesh3d(shared.line.clone()),
                MeshMaterial3d(shared.team[camp].clone()),
                Transform::from_xyz(0., height + 0.003, 0.)
                    .with_scale(Vec3::new(0.405, 0.021, 0.312)),
                NotShadowCaster,
            ));
        }
    });
}
