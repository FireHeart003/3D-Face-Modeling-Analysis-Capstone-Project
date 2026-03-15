#pragma once
#include <string>
#include <vector>
#include <cstdint>

namespace face {

class Renderer {
public:
    Renderer(int width, int height);
    ~Renderer();

    // Load a GLB (gltf binary) from disk
    void load_model(const std::string& glb_path);

    // Render one frame; returns RGBA8 bytes width*height*4
    std::vector<uint8_t> render(float yaw_deg, float pitch_deg, float roll_deg);

    int width() const { return m_width; }
    int height() const { return m_height; }

private:
    void destroy();

    int m_width = 0;
    int m_height = 0;

    // Opaque pointers so header doesn't drag in Filament headers
    struct Impl;
    Impl* m = nullptr;
};

} // namespace face