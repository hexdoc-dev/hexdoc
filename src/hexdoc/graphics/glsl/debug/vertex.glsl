#version 330

uniform mat4 m_proj;
uniform mat4 m_camera;
uniform mat4 m_model;

in vec3 in_position;

void main() {
	gl_Position = m_proj * m_camera * m_model * vec4(in_position, 1.0);
}
