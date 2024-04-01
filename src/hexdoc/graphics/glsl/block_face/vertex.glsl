#version 330

uniform mat4 m_proj;
uniform mat4 m_camera;
uniform mat4 m_model;
uniform mat4 m_texture;

in vec3 in_position;
in vec2 in_texcoord_0;

out vec2 uv;

void main() {
    gl_Position = m_proj * m_camera * m_model * vec4(in_position, 1);

    vec4 rotCoord = m_texture * vec4(in_texcoord_0, 0.0, 1.0);
    uv = rotCoord.st;
}
