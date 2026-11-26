//! Shared meshes and Blender pose palettes for the handheld renderer.

use bevy::{
    asset::{AssetLoader, LoadContext, RenderAssetUsages, io::Reader},
    image::{CompressedImageFormats, ImageSampler, ImageType},
    pbr::{MaterialPipeline, MaterialPipelineKey, MaterialPlugin, NotShadowCaster},
    prelude::*,
    render::{
        mesh::{
            Indices, MeshTag, MeshVertexAttribute, MeshVertexBufferLayoutRef, PrimitiveTopology,
        },
        render_resource::{
            AsBindGroup, Extent3d, RenderPipelineDescriptor, ShaderRef,
            SpecializedMeshPipelineError, TextureDimension, TextureFormat, VertexFormat,
        },
    },
};
use std::{
    collections::{HashMap, VecDeque},
    io::{Error, ErrorKind, Read},
};

use super::{Figure, Graphics, desired_clip};

const CLIPS: [&str; 9] = [
    "Idle",
    "Walk",
    "Attack",
    "Cast",
    "Hit",
    "Death",
    "Spawn",
    "Ascend",
    "Celebrate",
];

// Bevy's stock joint attributes select its per-entity skinning pipeline.
const PALETTE_JOINT: MeshVertexAttribute =
    MeshVertexAttribute::new("PaletteJoint", 408_690_843, VertexFormat::Uint16x4);
const PALETTE_WEIGHT: MeshVertexAttribute =
    MeshVertexAttribute::new("PaletteWeight", 408_690_844, VertexFormat::Float32x4);

#[derive(Asset, TypePath, AsBindGroup, Debug, Clone)]
struct FigureMaterial {
    #[texture(0, sample_type = "float", filterable = false, visibility(vertex))]
    poses: Handle<Image>,
    #[texture(1)]
    #[sampler(2)]
    paint: Handle<Image>,
}

impl Material for FigureMaterial {
    fn vertex_shader() -> ShaderRef {
        "shaders/crowd.wgsl".into()
    }
    fn fragment_shader() -> ShaderRef {
        "shaders/crowd.wgsl".into()
    }

    fn specialize(
        _pipeline: &MaterialPipeline<Self>,
        descriptor: &mut RenderPipelineDescriptor,
        layout: &MeshVertexBufferLayoutRef,
        _key: MaterialPipelineKey<Self>,
    ) -> Result<(), SpecializedMeshPipelineError> {
        descriptor.vertex.buffers = vec![layout.0.get_layout(&[
            Mesh::ATTRIBUTE_POSITION.at_shader_location(0),
            Mesh::ATTRIBUTE_NORMAL.at_shader_location(1),
            Mesh::ATTRIBUTE_UV_0.at_shader_location(2),
            Mesh::ATTRIBUTE_COLOR.at_shader_location(3),
            PALETTE_JOINT.at_shader_location(4),
            PALETTE_WEIGHT.at_shader_location(5),
        ])?];
        descriptor.primitive.cull_mode = None;
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct Clip {
    row: u32,
    frames: u32,
    seconds: f32,
}

#[derive(Asset, TypePath)]
pub(super) struct CachedFigure {
    mesh: Handle<Mesh>,
    material: Handle<FigureMaterial>,
    clips: [Clip; 9],
}

#[derive(Default)]
struct FigureLoader;

fn broken() -> Error {
    Error::new(ErrorKind::InvalidData, "invalid Pantheon figure")
}

struct Payload<'a>(&'a [u8]);
impl<'a> Payload<'a> {
    fn take(&mut self, size: usize) -> Result<&'a [u8], Error> {
        let (head, tail) = self.0.split_at_checked(size).ok_or_else(broken)?;
        self.0 = tail;
        Ok(head)
    }
    fn number(&mut self) -> Result<u32, Error> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn floats<const N: usize>(&mut self, count: usize) -> Result<Vec<[f32; N]>, Error> {
        Ok(self
            .take(count * N * 4)?
            .chunks_exact(N * 4)
            .map(|bytes| {
                std::array::from_fn(|i| {
                    f32::from_le_bytes(bytes[i * 4..i * 4 + 4].try_into().unwrap())
                })
            })
            .collect())
    }
}

impl AssetLoader for FigureLoader {
    type Asset = CachedFigure;
    type Settings = ();
    type Error = Error;

    async fn load(
        &self,
        reader: &mut dyn Reader,
        _: &(),
        assets: &mut LoadContext<'_>,
    ) -> Result<CachedFigure, Error> {
        let mut data = Vec::new();
        reader.read_to_end(&mut data).await?;
        let mut unpacked = Vec::new();
        flate2::read::GzDecoder::new(data.as_slice())
            .take(24 * 1024 * 1024)
            .read_to_end(&mut unpacked)?;
        let mut reader = Payload(&unpacked);
        if reader.take(4)? != b"PDM1" {
            return Err(broken());
        }
        let vertices = reader.number()? as usize;
        let indices = reader.number()? as usize;
        let joints = reader.number()?;
        let rows = reader.number()?;
        let paint_len = reader.number()? as usize;
        if !(1..=65_535).contains(&vertices)
            || indices > 300_000
            || !(1..=128).contains(&joints)
            || !(1..=1024).contains(&rows)
        {
            return Err(broken());
        }

        let mut clips = [Clip {
            row: 0,
            frames: 1,
            seconds: 1.,
        }; 9];
        for clip in &mut clips {
            let row = reader.number()?;
            let frames = reader.number()?;
            let seconds = f32::from_bits(reader.number()?);
            if frames < 2
                || row >= rows
                || frames > rows - row
                || !seconds.is_finite()
                || seconds <= 0.
            {
                return Err(broken());
            }
            *clip = Clip {
                row,
                frames,
                seconds,
            };
        }
        let positions = reader.floats::<3>(vertices)?;
        let normals = reader.floats::<3>(vertices)?;
        let uv = reader.floats::<2>(vertices)?;
        let colour = reader.floats::<4>(vertices)?;
        let joint_index: Vec<[u16; 4]> = reader
            .take(vertices * 8)?
            .chunks_exact(8)
            .map(|bytes| {
                std::array::from_fn(|i| {
                    u16::from_le_bytes(bytes[i * 2..i * 2 + 2].try_into().unwrap())
                })
            })
            .collect();
        let weights = reader.floats::<4>(vertices)?;
        let indices = reader
            .take(indices * 4)?
            .chunks_exact(4)
            .map(|bytes| u32::from_le_bytes(bytes.try_into().unwrap()))
            .collect::<Vec<_>>();
        let raw_poses = reader.take((joints * 3 * rows * 16) as usize)?.to_vec();
        let paint = Image::from_buffer(
            reader.take(paint_len)?,
            ImageType::Extension("png"),
            CompressedImageFormats::NONE,
            true,
            ImageSampler::linear(),
            RenderAssetUsages::RENDER_WORLD,
        )
        .map_err(|error| Error::new(ErrorKind::InvalidData, error.to_string()))?;

        let mesh = Mesh::new(
            PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        )
        .with_inserted_attribute(Mesh::ATTRIBUTE_POSITION, positions)
        .with_inserted_attribute(Mesh::ATTRIBUTE_NORMAL, normals)
        .with_inserted_attribute(Mesh::ATTRIBUTE_UV_0, uv)
        .with_inserted_attribute(Mesh::ATTRIBUTE_COLOR, colour)
        .with_inserted_attribute(
            PALETTE_JOINT,
            bevy::render::mesh::VertexAttributeValues::Uint16x4(joint_index),
        )
        .with_inserted_attribute(PALETTE_WEIGHT, weights)
        .with_inserted_indices(Indices::U32(indices));
        let mut poses = Image::new(
            Extent3d {
                width: joints * 3,
                height: rows,
                depth_or_array_layers: 1,
            },
            TextureDimension::D2,
            raw_poses,
            TextureFormat::Rgba32Float,
            RenderAssetUsages::RENDER_WORLD,
        );
        poses.sampler = ImageSampler::nearest();
        let poses = assets.add_labeled_asset("poses".into(), poses);
        let paint = assets.add_labeled_asset("paint".into(), paint);
        let mesh = assets.add_labeled_asset("sculpt".into(), mesh);
        let material = assets.add_labeled_asset("material".into(), FigureMaterial { poses, paint });
        Ok(CachedFigure {
            mesh,
            material,
            clips,
        })
    }

    fn extensions(&self) -> &[&str] {
        &["figure"]
    }
}

#[derive(Resource, Default)]
pub(super) struct Crowd {
    models: HashMap<String, Handle<CachedFigure>>,
    queue: VecDeque<String>,
    next: f64,
    warm: Option<(Entity, f64)>,
    warmed: bool,
}

impl Crowd {
    pub(super) fn request(&mut self, assets: &AssetServer, id: &str) {
        self.models
            .entry(id.into())
            .or_insert_with(|| assets.load(format!("crowd/{id}.figure")));
    }

    pub(super) fn preload(&mut self, assets: &AssetServer, theme: &str) {
        let catalog = pantheon_simulation::catalog();
        let region = catalog.themes.iter().find(|entry| entry.id == theme);
        self.models.retain(|id, _| {
            pantheon_simulation::actor(id).is_some_and(|entry| entry.theme == theme)
                || region
                    .is_some_and(|map| map.wave_pack.contains(id) || map.boss_pack.contains(id))
        });
        self.queue.clear();
        self.queue.extend(
            catalog
                .actors
                .iter()
                .filter(|actor| actor.theme == theme && actor.kind == "troop" && actor.rarity <= 2)
                .map(|actor| actor.id.clone()),
        );
        if let Some(theme) = region {
            self.queue.extend(theme.wave_pack.iter().cloned());
        }
        if let Some(id) = self.queue.pop_front() {
            self.request(assets, &id);
        }
    }
}

pub(super) fn install(app: &mut App) {
    app.add_plugins(MaterialPlugin::<FigureMaterial> {
        shadows_enabled: false,
        prepass_enabled: false,
        ..default()
    })
    .init_asset::<CachedFigure>()
    .init_asset_loader::<FigureLoader>()
    .init_resource::<Crowd>();
}

pub(super) fn draw(
    mut commands: Commands,
    mut crowd: ResMut<Crowd>,
    models: Res<Assets<CachedFigure>>,
    server: Res<AssetServer>,
    graphics: Res<Graphics>,
    mut figures: Query<&mut Figure>,
    mut tags: Query<&mut MeshTag>,
    time: Res<Time<Real>>,
) {
    if !graphics.mobile {
        return;
    }
    let now = time.elapsed_secs_f64();
    if now >= crowd.next {
        if let Some(id) = crowd.queue.pop_front() {
            crowd.request(&server, &id);
        }
        crowd.next = now + 0.26;
    }
    // Prepare the shared vertex pipeline while the player is still in the lobby.
    if !crowd.warmed {
        if let Some(model) = crowd.models.values().find_map(|handle| models.get(handle)) {
            let marker = commands
                .spawn((
                    Mesh3d(model.mesh.clone()),
                    MeshMaterial3d(model.material.clone()),
                    MeshTag(0),
                    Transform::from_xyz(0., -2.4, 0.).with_scale(Vec3::splat(0.05)),
                    NotShadowCaster,
                ))
                .id();
            crowd.warmed = true;
            crowd.warm = Some((marker, now + 1.8));
        }
    }
    if let Some((marker, _)) = crowd.warm.filter(|(_, until)| now >= *until) {
        commands.entity(marker).despawn();
        crowd.warm = None;
    }
    for mut figure in &mut figures {
        if !figure.cached {
            continue;
        }
        let Some(model) = crowd
            .models
            .get(&figure.asset)
            .and_then(|handle| models.get(handle))
        else {
            continue;
        };
        let desired = desired_clip(&figure, now);
        if figure.active_clip != desired {
            figure.active_clip = desired;
            figure.clip_started = now;
        }
        let index = CLIPS.iter().position(|clip| *clip == desired).unwrap_or(0);
        let clip = model.clips[index];
        let elapsed = (now - figure.clip_started).max(0.) as f32;
        let speed = match desired {
            "Attack" => 1.5,
            "Hit" => 1.8,
            "Cast" => 1.25,
            _ => 1.,
        };
        for (member, &entity) in figure.members.iter().enumerate() {
            let phase = match desired {
                "Walk" => figure.stride.as_ref().map_or_else(
                    || (elapsed / clip.seconds).fract(),
                    |stride| {
                        stride.gait_phase(
                            pantheon_simulation::enemy_kind(&figure.asset).family(),
                            now,
                            clip.seconds,
                        )
                    },
                ),
                "Idle" => ((now as f32 + member as f32 * 0.16) / clip.seconds).fract(),
                _ => (elapsed * speed / clip.seconds).min(1.),
            };
            let frame =
                ((clip.row as f32 + phase * (clip.frames - 1) as f32) * 256.).round() as u32;
            if let Ok(mut tag) = tags.get_mut(entity) {
                if tag.0 != frame {
                    tag.0 = frame;
                }
            } else {
                commands.entity(entity).insert((
                    Mesh3d(model.mesh.clone()),
                    MeshMaterial3d(model.material.clone()),
                    MeshTag(frame),
                    NotShadowCaster,
                ));
            }
        }
    }
}
