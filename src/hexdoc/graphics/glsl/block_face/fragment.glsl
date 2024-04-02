#version 330

struct Light {
    vec3 direction;
    float diffuse;
};

#define NUM_LIGHTS 3

uniform Light lights[NUM_LIGHTS];
uniform sampler2DArray texture0;
uniform float layer;
uniform float flatLighting;

in vec2 uv;
in vec3 normal;

out vec4 fragColor;

float getDiffuse(Light light) {
    vec3 lightDir = normalize(-light.direction);

    // for debugging, light back faces with half the intensity
    float dotProduct = dot(normal, lightDir);
    if (dotProduct < 0) dotProduct = -dotProduct / 2;

    return light.diffuse * dotProduct;
}

void main() {
    vec4 texColor = texture(texture0, vec3(uv, layer));

    float diffuse = 0.0;
    if (flatLighting != 0) {
        diffuse = flatLighting;
    } else {
        for (int i = 0; i < NUM_LIGHTS; i++) {
            diffuse += getDiffuse(lights[i]);
        }
    }

    fragColor = vec4(min(diffuse, 1.0) * texColor.rgb, texColor.a);
}
