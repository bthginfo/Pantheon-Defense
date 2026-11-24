//! Baked Blender dioramas and the soft contact shadows that follow moving pieces.

use super::{Shared, event};
use bevy::{
    asset::RenderAssetUsages,
    gltf::GltfAssetLabel,
    pbr::NotShadowCaster,
    prelude::*,
    render::mesh::{Indices, PrimitiveTopology},
    scene::SceneInstanceReady,
};

#[derive(Component)]
struct Diorama(String);

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
    boards: Query<&Diorama>,
    children: Query<&Children>,
    meshes: Query<(), With<Mesh3d>>,
) {
    if let Ok(board) = boards.get(trigger.target()) {
        for entity in children.iter_descendants(trigger.target()) {
            if meshes.contains(entity) {
                commands.entity(entity).insert(NotShadowCaster);
            }
        }
        event("pantheon-board-models", &board.0);
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
