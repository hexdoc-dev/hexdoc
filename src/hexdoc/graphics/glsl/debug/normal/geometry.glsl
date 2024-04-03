#version 330

uniform mat4 m_proj;
uniform mat4 m_camera;
uniform mat4 m_model;
uniform float lineSize;

layout (triangles) in;
in vec3 normal[];

layout (line_strip, max_vertices = 5) out;
out vec3 color;

vec3 get_gl_in_position(int i) {
    return gl_in[i].gl_Position.xyz;
}

void emitTransformedVertex(mat4 transform, vec3 vertex) {
    gl_Position = transform * vec4(vertex, 1.0);
    EmitVertex();
}

void main() {
    vec3 midpoint = vec3(0.0);
    for (int i = 0; i < 3; i++) {
        midpoint += get_gl_in_position(i);
    }
    midpoint /= 3.0;

    vec3 avgNormal = vec3(0.0);
    for (int i = 0; i < 3; i++) {
        avgNormal += normal[i];
    }
    avgNormal = normalize(avgNormal);

    // make negative normals shorter
    vec3 offset = avgNormal * lineSize;
    if (avgNormal != abs(avgNormal)) offset /= 2;

    mat4 transform = m_proj * m_camera * m_model;

    // use abs to make sure negative normals still have the correct colour
    color = abs(avgNormal);

    emitTransformedVertex(transform, midpoint + offset);
    emitTransformedVertex(transform, midpoint);

    // make triangle lines darker to differentiate them from the normals
    color /= 2;

    for (int i = 0; i < 3; i++) {
        vec3 vertex = get_gl_in_position(i);
        emitTransformedVertex(transform, vertex + 0.2 * (midpoint - vertex));
    }

    EndPrimitive();
}
