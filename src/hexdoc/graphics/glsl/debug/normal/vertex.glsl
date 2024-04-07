#version 330

in vec3 in_position;
in vec3 in_normal;

out vec3 normal;

void main() {
    gl_Position = vec4(in_position, 1.0);
    normal = in_normal;
}
