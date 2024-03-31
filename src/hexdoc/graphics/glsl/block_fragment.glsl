#version 330

uniform sampler2DArray texture0;
uniform float layer;
uniform float light;

in vec2 uv;

out vec4 fragColor;

void main() {
    vec4 texColor = texture(texture0, vec3(uv, layer));
    fragColor = vec4(light * texColor.rgb, texColor.a);
}
