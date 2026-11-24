//! Baked Blender dioramas and the soft contact shadows that follow moving pieces.

use super::{Shared, event, model_path};
use bevy::{
    asset::RenderAssetUsages,
    gltf::GltfAssetLabel,
    pbr::NotShadowCaster,
    prelude::*,
    render::{
        mesh::{Indices, PrimitiveTopology},
        view::NoFrustumCulling,
    },
    scene::SceneInstanceReady,
};

#[derive(Component)]
struct Diorama(String);

pub fn build(
    commands: &mut Commands,
    assets: &AssetServer,
    theme: &str,
    mobile: bool,
) -> Vec<Entity> {
    let colors = match theme {
        "rome" => [24, 61, 75],
        "japan" => [20, 70, 85],
        _ => [12, 73, 89],
    };
    commands.insert_resource(ClearColor(Color::srgb_u8(colors[0], colors[1], colors[2])));
    let model = model_path(&format!("arena_{theme}"), mobile);
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

#[derive(Component)]
pub(super) struct Footprint {
    local: Transform,
}

#[derive(Component)]
pub(super) struct ShadowCanvas;

#[derive(Resource)]
pub struct ContactShadows {
    mesh: Handle<Mesh>,
    profile: Vec<Vec3>,
    colors: Vec<[f32; 4]>,
    indices: Vec<u32>,
}

impl ContactShadows {
    pub fn new(
        commands: &mut Commands,
        meshes: &mut Assets<Mesh>,
        materials: &mut Assets<StandardMaterial>,
    ) -> Self {
        let (profile, colors, indices) = shadow_profile();
        let mesh = meshes.add(
            Mesh::new(
                PrimitiveTopology::TriangleList,
                RenderAssetUsages::default(),
            )
            .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, vec![[0., 0., 0.]; 3])
            .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0., 1., 0.]; 3])
            .with_inserted_attribute(Mesh::ATTRIBUTE_COLOR, vec![[0., 0., 0., 0.]; 3])
            .with_inserted_indices(Indices::U32(vec![0, 1, 2])),
        );
        let material = materials.add(StandardMaterial {
            base_color: Color::WHITE,
            alpha_mode: AlphaMode::Blend,
            unlit: true,
            cull_mode: None,
            ..default()
        });
        commands.spawn((
            ShadowCanvas,
            Mesh3d(mesh.clone()),
            MeshMaterial3d(material),
            Visibility::Hidden,
            NoFrustumCulling,
            NotShadowCaster,
        ));
        Self {
            mesh,
            profile,
            colors,
            indices,
        }
    }
}

fn shadow_profile() -> (Vec<Vec3>, Vec<[f32; 4]>, Vec<u32>) {
    let steps = 18u32;
    let mut positions = vec![Vec3::ZERO];
    let mut colors = vec![[0.09, 0.125, 0.14, 0.37]];
    let mut indices = Vec::new();
    for (ring, (radius, alpha)) in [(0.39f32, 0.23f32), (1.0, 0.)].into_iter().enumerate() {
        for i in 0..steps {
            let theta = i as f32 * std::f32::consts::TAU / steps as f32;
            positions.push(Vec3::new(radius * theta.cos(), 0., radius * theta.sin()));
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
    (positions, colors, indices)
}

pub(super) fn update_contact_shadows(
    shadows: Res<ContactShadows>,
    mut meshes: ResMut<Assets<Mesh>>,
    feet: Query<(&Footprint, &Transform)>,
    mut canvas: Query<&mut Visibility, With<ShadowCanvas>>,
) {
    let Ok(mut visible) = canvas.single_mut() else {
        return;
    };
    if feet.is_empty() {
        visible.set_if_neq(Visibility::Hidden);
        return;
    }
    let Some(mesh) = meshes.get_mut(&shadows.mesh) else {
        return;
    };
    let vertices = feet.iter().len() * shadows.profile.len();
    let mut positions = Vec::with_capacity(vertices);
    let mut colors = Vec::with_capacity(vertices);
    let mut indices = Vec::with_capacity(feet.iter().len() * shadows.indices.len());
    for (foot, pose) in &feet {
        let transform = pose.mul_transform(foot.local);
        let offset = positions.len() as u32;
        positions.extend(
            shadows
                .profile
                .iter()
                .map(|&p| transform.transform_point(p).to_array()),
        );
        colors.extend_from_slice(&shadows.colors);
        indices.extend(shadows.indices.iter().map(|index| offset + index));
    }
    mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0., 1., 0.]; vertices]);
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
    mesh.insert_attribute(Mesh::ATTRIBUTE_COLOR, colors);
    mesh.insert_indices(Indices::U32(indices));
    visible.set_if_neq(Visibility::Inherited);
}

pub fn footwork(
    commands: &mut Commands,
    shared: &Shared,
    figure: Entity,
    height: f32,
    size: Vec2,
    camp: Option<usize>,
) {
    let local = Transform::from_xyz(0.091, height, 0.018).with_scale(Vec3::new(size.x, 1., size.y));
    commands.entity(figure).insert(Footprint { local });
    if let Some(camp) = camp {
        commands.entity(figure).with_children(|children| {
            children.spawn((
                Mesh3d(shared.line.clone()),
                MeshMaterial3d(shared.team[camp].clone()),
                Transform::from_xyz(0., height + 0.003, 0.)
                    .with_scale(Vec3::new(0.405, 0.021, 0.312)),
                NotShadowCaster,
            ));
        });
    }
}
