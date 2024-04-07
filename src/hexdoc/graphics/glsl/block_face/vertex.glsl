#version 330

uniform mat4 m_proj;
uniform mat4 m_camera;
uniform mat4 m_model;
uniform mat4 m_normals;

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord_0;

out vec2 uv;
out vec3 normal;

void main() {
    gl_Position = m_proj * m_camera * m_model * vec4(in_position, 1);
    uv = in_texcoord_0;

    mat3 norm_matrix = transpose(inverse(mat3(m_normals)));
    normal = normalize(norm_matrix * in_normal);
}
