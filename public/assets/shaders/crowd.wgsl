#import bevy_pbr::mesh_functions::{get_world_from_local, mesh_position_local_to_clip, mesh_normal_local_to_world, get_tag}
#import bevy_pbr::mesh_view_bindings::view

@group(2) @binding(0) var poses: texture_2d<f32>;
@group(2) @binding(1) var paint: texture_2d<f32>;
@group(2) @binding(2) var brush: sampler;

struct Vertex {
    @builtin(instance_index) instance: u32,
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) uv: vec2<f32>,
    @location(3) pigment: vec4<f32>,
    @location(4) joints: vec4<u32>,
    @location(5) weights: vec4<f32>,
};

struct Surface {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) pigment: vec3<f32>,
    @location(2) lighting: vec3<f32>,
};

fn pose_row(joint: i32, read: i32, mix_frame: f32) -> vec4<f32> {
    let first = textureLoad(poses,vec2<i32>(joint,read),0);
    if mix_frame < 0.003 { return first; }
    let next = min(read+1,i32(textureDimensions(poses).y)-1);
    return mix(first,textureLoad(poses,vec2<i32>(joint,next),0),mix_frame);
}

@vertex
fn vertex(input: Vertex) -> Surface {
    let tag = get_tag(input.instance);
    let row = i32(tag >> 8u);
    let mix_frame = f32(tag & 255u) / 256.0;
    let local = vec4<f32>(input.position,1.0);
    var position = vec3<f32>(0.0);
    var normal = vec3<f32>(0.0);
    for (var i = 0u; i < 4u; i++) {
        let weight = input.weights[i];
        if weight < 0.0001 { continue; }
        let column = i32(input.joints[i]) * 3;
        let x = pose_row(column,row,mix_frame);
        let y = pose_row(column+1,row,mix_frame);
        let z = pose_row(column+2,row,mix_frame);
        position += vec3<f32>(dot(x,local),dot(y,local),dot(z,local)) * weight;
        normal += vec3<f32>(dot(x.xyz,input.normal),dot(y.xyz,input.normal),dot(z.xyz,input.normal)) * weight;
    }

    let n = mesh_normal_local_to_world(normalize(normal),input.instance);
    let sun = max(0.0,dot(n,vec3<f32>(-0.40,0.74,0.54)));
    let fill = max(0.0,dot(n,vec3<f32>(0.67,0.57,-0.48)));
    let sky = clamp(n.y * 0.23 + 0.12,0.0,0.35);
    // A warm rim separates figures from the pale stone of the board.
    let toward_camera = normalize(view.world_from_view[2].xyz);
    let rim = pow(1.0 - clamp(dot(n,toward_camera),0.0,1.0),2.4);
    var result: Surface;
    result.clip = mesh_position_local_to_clip(get_world_from_local(input.instance),vec4<f32>(position,1.0));
    result.uv = input.uv;
    result.pigment = input.pigment.rgb;
    result.lighting = vec3<f32>(0.49,0.51,0.56) + vec3<f32>(1.0,0.84,0.62)*sun*0.93
        + vec3<f32>(0.33,0.50,0.67)*(fill*0.23+sky) + vec3<f32>(1.0,0.86,0.64)*rim*0.38;
    return result;
}

@fragment
fn fragment(input: Surface) -> @location(0) vec4<f32> {
    return vec4<f32>(textureSample(paint,brush,input.uv).rgb*input.pigment*input.lighting,1.0);
}
