#version 330

struct Light {
    vec3 direction;
    float diffuse;
};

#define NUM_LIGHTS 3

uniform Light lights[NUM_LIGHTS];
uniform sampler2DArray texture0;
uniform float layer;

in vec2 uv;
in vec3 normal;

out vec4 fragColor;

void main() {
    vec4 texColor = texture(texture0, vec3(uv, layer));

    float diffuse = 0.0;
    for (int i = 0; i < NUM_LIGHTS; i++) {
        Light light = lights[i];
        vec3 lightDir = normalize(-light.direction);
        diffuse += light.diffuse * max(dot(normal, lightDir), 0.0);
    }

    fragColor = vec4(min(diffuse, 1.0) * texColor.rgb, texColor.a);
}
