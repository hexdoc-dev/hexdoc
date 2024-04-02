#version 330

uniform mat4 m_proj;
uniform mat4 m_camera;
uniform mat4 m_model;

in vec3 in_position;
in vec2 in_texcoord_0;

out vec2 uv;

void main() {
    gl_Position = m_proj * m_camera * m_model * vec4(in_position, 1);
    uv = in_texcoord_0;
}
