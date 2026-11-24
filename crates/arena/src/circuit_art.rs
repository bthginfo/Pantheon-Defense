use super::{Shared, facing, p3};
use bevy::{
    asset::RenderAssetUsages,
    pbr::NotShadowCaster,
    prelude::*,
    render::mesh::{Indices, PrimitiveTopology, VertexAttributeValues},
};
use pantheon_simulation::{self as sim, CIRCUIT_RULES};

#[derive(Default)]
struct Geometry {
    positions: Vec<[f32; 3]>,
    normals: Vec<[f32; 3]>,
    colors: Vec<[f32; 4]>,
    indices: Vec<u32>,
}

impl Geometry {
    fn paint(&mut self, source: &Mesh, pos: Vec3, dimensions: Vec3, angle: f32, color: [u8; 3]) {
        let (
            Some(VertexAttributeValues::Float32x3(vertices)),
            Some(VertexAttributeValues::Float32x3(normals)),
            Some(indices),
        ) = (
            source.attribute(Mesh::ATTRIBUTE_POSITION),
            source.attribute(Mesh::ATTRIBUTE_NORMAL),
            source.indices(),
        )
        else {
            return;
        };
        let rotation = Quat::from_rotation_y(angle);
        let rgba = LinearRgba::from(Color::srgb_u8(color[0], color[1], color[2]));
        let start = self.positions.len() as u32;
        let sun = Vec3::new(-0.47, 0.83, -0.31);
        for (point, normal) in vertices.iter().zip(normals) {
            self.positions
                .push((pos + rotation * (Vec3::from(*point) * dimensions)).to_array());
            let normal = (rotation * (Vec3::from(*normal) / dimensions)).normalize_or_zero();
            self.normals.push(normal.to_array());
            let light = 0.49 + 0.69 * normal.dot(sun).max(0.);
            self.colors
                .push([rgba.red * light, rgba.green * light, rgba.blue * light, 1.]);
        }
        self.indices
            .extend(indices.iter().map(|i| start + i as u32));
    }

    fn build(self) -> Mesh {
        Mesh::new(
            PrimitiveTopology::TriangleList,
            RenderAssetUsages::RENDER_WORLD,
        )
        .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, self.positions)
        .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, self.normals)
        .with_inserted_attribute(Mesh::ATTRIBUTE_COLOR, self.colors)
        .with_inserted_indices(Indices::U32(self.indices))
    }
}

struct Landmarks {
    stone: [u8; 3],
    cliff: [u8; 3],
    paving: [u8; 3],
    pale: [u8; 3],
    soil: [u8; 3],
    groom: [u8; 3],
    pop: [u8; 3],
    tree: [u8; 3],
    tree_light: [u8; 3],
    roof: [u8; 3],
    water: [u8; 3],
}

impl Landmarks {
    fn themed(theme: &str) -> Self {
        match theme {
            "rome" => Self {
                stone: [157, 100, 81],
                cliff: [68, 59, 57],
                paving: [167, 116, 96],
                pale: [220, 182, 143],
                soil: [110, 119, 92],
                groom: [129, 93, 77],
                pop: [212, 131, 104],
                tree: [68, 97, 78],
                tree_light: [113, 133, 95],
                roof: [139, 61, 60],
                water: [38, 67, 75],
            },
            "japan" => Self {
                stone: [133, 142, 121],
                cliff: [54, 74, 75],
                paving: [156, 152, 130],
                pale: [201, 191, 160],
                soil: [92, 124, 100],
                groom: [104, 139, 120],
                pop: [197, 122, 101],
                tree: [50, 103, 84],
                tree_light: [122, 158, 122],
                roof: [48, 85, 102],
                water: [39, 78, 89],
            },
            _ => Self {
                stone: [182, 146, 110],
                cliff: [74, 85, 74],
                paving: [178, 143, 108],
                pale: [225, 197, 155],
                soil: [117, 147, 108],
                groom: [119, 152, 124],
                pop: [213, 161, 99],
                tree: [63, 111, 89],
                tree_light: [115, 158, 111],
                roof: [56, 112, 119],
                water: [43, 91, 104],
            },
        }
    }
}

pub fn build(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    shared: &Shared,
    theme: &str,
) -> Vec<Entity> {
    let land = Landmarks::themed(theme);
    let box_mesh = Mesh::from(Cuboid::new(1., 1., 1.));
    let boulder = Sphere::new(1.).mesh().ico(0).unwrap();
    let column = Mesh::from(Cylinder::new(1., 1.).mesh().resolution(8));
    let mut geometry = Geometry::default();

    commands.insert_resource(ClearColor(Color::srgb_u8(
        land.water[0],
        land.water[1],
        land.water[2],
    )));
    // Terraced seawalls, shore diagonals and worn pale paving.
    geometry.paint(
        &box_mesh,
        Vec3::new(0., -0.47, 0.),
        Vec3::new(13.4, 1.00, 16.75),
        0.,
        land.cliff,
    );
    geometry.paint(
        &box_mesh,
        Vec3::new(0., -0.38, 0.),
        Vec3::new(11.4, 1.0, 19.57),
        0.,
        land.cliff,
    );
    geometry.paint(
        &box_mesh,
        Vec3::new(0., 0.07, 0.),
        Vec3::new(13.65, 0.27, 16.7),
        0.,
        land.stone,
    );
    geometry.paint(
        &box_mesh,
        Vec3::new(0., 0.09, 0.),
        Vec3::new(11.65, 0.26, 19.75),
        0.,
        land.stone,
    );
    geometry.paint(
        &box_mesh,
        Vec3::new(0., 0.216, 0.),
        Vec3::new(11.64, 0.07, 17.0),
        0.,
        land.soil,
    );
    for (i, point) in sim::circuit_route(theme, 0).windows(2).enumerate() {
        let a = p3(point[0], 0.25);
        let b = p3(point[1], 0.25);
        let direction = b - a;
        let angle = direction.x.atan2(direction.z);
        let length = direction.length();
        let midpoint = (a + b) * 0.5;
        geometry.paint(
            &box_mesh,
            midpoint,
            Vec3::new(1.52, 0.095, length + 0.87),
            angle,
            land.cliff,
        );
        geometry.paint(
            &box_mesh,
            midpoint + Vec3::Y * 0.069,
            Vec3::new(1.35, 0.05, length + 0.80),
            angle,
            land.paving,
        );
        let panels = (length / 0.72).ceil() as u32;
        for j in 0..panels {
            let t = (j as f32 + 0.5) / panels as f32;
            let stone = a.lerp(b, t) + Vec3::Y * 0.097;
            let shade = if (j + i as u32) % 4 == 0 {
                land.pale
            } else {
                land.paving
            };
            geometry.paint(
                &box_mesh,
                stone,
                Vec3::new(1.21, 0.019, length / panels as f32 - 0.029),
                angle,
                shade,
            );
            if j % 2 == 0 {
                let stride = direction.normalize();
                geometry.paint(
                    &box_mesh,
                    stone + 0.26 * Vec3::new(stride.z, 0.04, -stride.x),
                    Vec3::new(0.025, 0.023, length / panels as f32 - 0.04),
                    angle,
                    land.paving,
                );
            }
        }
    }

    for (index, &point) in sim::tiles_for(CIRCUIT_RULES).iter().enumerate() {
        let p = p3(point, 0.294);
        geometry.paint(&box_mesh, p, Vec3::new(2.24, 0.14, 1.35), 0., land.cliff);
        let top = if index < 16 { land.stone } else { land.groom };
        geometry.paint(
            &box_mesh,
            p + Vec3::Y * 0.081,
            Vec3::new(2.19, 0.060, 1.31),
            0.,
            top,
        );
        let rim = if index < 16 {
            land.pop
        } else {
            [108, 167, 148]
        };
        for side in [-1., 1.] {
            geometry.paint(
                &box_mesh,
                p + Vec3::new(side * 1.049, 0.12, 0.),
                Vec3::new(0.046, 0.021, 1.17),
                0.,
                rim,
            );
        }
        for z in [-0.603, 0.603] {
            geometry.paint(
                &box_mesh,
                p + Vec3::new(0., 0.12, z),
                Vec3::new(2.05, 0.022, 0.041),
                0.,
                rim,
            );
        }
        for side in [-1., 1.] {
            geometry.paint(
                &box_mesh,
                p + Vec3::new(side * 0.86, 0.121, 0.42),
                Vec3::new(0.13, 0.027, 0.13),
                0.785,
                rim,
            );
        }
    }

    // The central shrine joins the two terraces and leaves both long approaches visible.
    geometry.paint(
        &box_mesh,
        Vec3::new(0., 0.284, 0.),
        Vec3::new(8.75, 0.16, 1.36),
        0.,
        land.stone,
    );
    geometry.paint(
        &box_mesh,
        Vec3::new(0., 0.38, 0.),
        Vec3::new(8.2, 0.10, 1.18),
        0.,
        land.pale,
    );
    for x in [-4.56, -2.86, 2.86, 4.56] {
        geometry.paint(
            &column,
            Vec3::new(x, 0.57, 0.),
            Vec3::new(0.168, 0.43, 0.168),
            0.,
            land.cliff,
        );
        geometry.paint(
            &boulder,
            Vec3::new(x, 0.87, 0.),
            Vec3::new(0.138, 0.184, 0.138),
            0.4,
            land.pop,
        );
    }
    for x in [-2.1, 2.1] {
        let height = if theme == "japan" { 1.25 } else { 1.04 };
        for offset in [-0.72, 0.72] {
            geometry.paint(
                &column,
                Vec3::new(x + offset, 0.43 + height * 0.32, 0.08),
                Vec3::new(0.091, height * 0.66, 0.091),
                0.0,
                if theme == "japan" {
                    land.pop
                } else {
                    land.pale
                },
            );
        }
        let roof = Vec3::new(x, 0.43 + height * 0.69, 0.08);
        geometry.paint(&box_mesh, roof, Vec3::new(1.77, 0.15, 0.42), 0., land.roof);
        geometry.paint(
            &box_mesh,
            roof + Vec3::Y * 0.11,
            Vec3::new(1.61, 0.075, 0.33),
            0.,
            land.pale,
        );
    }
    geometry.paint(
        &column,
        Vec3::new(0., 0.42, 0.),
        Vec3::new(1.12, 0.20, 1.12),
        0.39,
        land.roof,
    );
    geometry.paint(
        &column,
        Vec3::new(0., 0.54, 0.),
        Vec3::new(0.75, 0.14, 0.75),
        0.39,
        land.stone,
    );
    geometry.paint(
        &boulder,
        Vec3::new(0., 0.91, 0.),
        Vec3::new(0.43, 0.39, 0.43),
        0.39,
        land.pop,
    );

    for side in [-1., 1.] {
        for i in 0..16 {
            let z = (i as f32 - 7.5) * 1.19;
            let noise = (i as f32 * 2.413).sin();
            let x = side * (7.06 + noise * 0.22);
            geometry.paint(
                &boulder,
                Vec3::new(x, -0.53, z),
                Vec3::new(0.57 + 0.22 * noise.abs(), 0.46, 0.51),
                noise,
                if i % 3 == 0 { land.stone } else { land.cliff },
            );
            if i % 2 == 0 {
                for fan in 0..3 {
                    let f = fan as f32;
                    geometry.paint(
                        &box_mesh,
                        Vec3::new(
                            x + side * (0.73 + f * 1.28),
                            -1.13,
                            z + noise * 0.43 + f * 0.28,
                        ),
                        Vec3::new(0.93 + f * 0.26, 0.017, 0.036),
                        noise * 0.33 - f * 0.13,
                        if fan == 0 {
                            [101, 155, 157]
                        } else {
                            [62, 114, 123]
                        },
                    );
                }
            }
        }
        for (i, (x, z)) in [(5.44, 7.70), (-5.44, 7.70), (6.05, 1.63), (-5.60, -0.79)]
            .into_iter()
            .enumerate()
        {
            let x = side * x;
            let z = side * z;
            let scale = 0.88 + ((i + 1) as f32 * 1.1).cos() * 0.22;
            geometry.paint(
                &column,
                Vec3::new(x, 0.58, z),
                Vec3::new(0.080, 0.65, 0.080),
                0.13,
                land.cliff,
            );
            for layer in 0..4 {
                let theta = layer as f32 * 2.39 + side;
                let colour = if theme == "japan" && i == 2 {
                    if layer == 1 {
                        [227, 176, 169]
                    } else {
                        [169, 113, 131]
                    }
                } else if layer == 1 {
                    land.tree_light
                } else {
                    land.tree
                };
                geometry.paint(
                    &boulder,
                    Vec3::new(
                        x + 0.17 * theta.sin(),
                        0.80 + 0.16 * layer as f32,
                        z + 0.19 * theta.cos(),
                    ),
                    Vec3::new(0.37, 0.34, 0.37) * scale,
                    theta,
                    colour,
                );
            }
        }
    }

    let board = commands
        .spawn((
            Mesh3d(meshes.add(geometry.build())),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::WHITE,
                unlit: true,
                ..default()
            })),
            Transform::default(),
            NotShadowCaster,
        ))
        .id();
    let mut entities = vec![board];
    for lane in 0..2 {
        let points = sim::circuit_route(theme, lane);
        let center = p3(points[0], 0.44);
        let angle = facing(p3(points[1], 0.) - p3(points[0], 0.));
        entities.push(
            commands
                .spawn((
                    Mesh3d(shared.disk.clone()),
                    MeshMaterial3d(shared.rays[4].clone()),
                    NotShadowCaster,
                    Transform::from_translation(center).with_scale(Vec3::new(0.44, 0.028, 0.44)),
                ))
                .id(),
        );
        entities.push(
            commands
                .spawn((
                    Mesh3d(shared.line.clone()),
                    MeshMaterial3d(shared.rays[5].clone()),
                    NotShadowCaster,
                    Transform::from_translation(center + Vec3::Y * 0.052)
                        .with_scale(Vec3::new(0.83, 0.46, 0.83))
                        .with_rotation(Quat::from_rotation_y(angle)),
                ))
                .id(),
        );
    }
    super::event("pantheon-board-models", "circuit");
    entities
}
