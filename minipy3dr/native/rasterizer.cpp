#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <new>
#include <vector>

namespace {

struct ScreenVertex {
    double x;
    double y;
    double z;
};

struct Color {
    std::uint8_t r;
    std::uint8_t g;
    std::uint8_t b;
};

struct Vec3 {
    double x;
    double y;
    double z;
};

struct Matrix4 {
    double m[16];
};

struct NativeTriangle {
    ScreenVertex a;
    ScreenVertex b;
    ScreenVertex c;
    Color color;
};

struct MeshRange {
    int vertex_start;
    int vertex_count;
    int face_start;
    int face_count;
    int material_index;
};

struct MeshState {
    double position_x;
    double position_y;
    double position_z;
    double rotation_x;
    double rotation_y;
    double rotation_z;
    double scale_x;
    double scale_y;
    double scale_z;
    double local_radius;
};

struct MaterialData {
    double red;
    double green;
    double blue;
    double ambient;
};

struct LightData {
    double direction_x;
    double direction_y;
    double direction_z;
    double red;
    double green;
    double blue;
    double intensity;
};

struct PreparedLight {
    Vec3 incoming;
    double color_red;
    double color_green;
    double color_blue;
    double intensity;
};

struct ViewVertex {
    double x;
    double y;
    double z;
};

struct NativeFrameBuffer {
    PyObject_HEAD
    int width;
    int height;
    std::vector<std::uint8_t> color;
    std::vector<float> depth;
};

bool parse_screen_vertex(PyObject* value, ScreenVertex* out) {
    PyObject* sequence = PySequence_Fast(value, "screen vertex must be a 3-item sequence");
    if (sequence == nullptr) {
        return false;
    }
    if (PySequence_Fast_GET_SIZE(sequence) != 3) {
        Py_DECREF(sequence);
        PyErr_SetString(PyExc_ValueError, "screen vertex must be a 3-item sequence");
        return false;
    }

    PyObject** items = PySequence_Fast_ITEMS(sequence);
    out->x = PyFloat_AsDouble(items[0]);
    out->y = PyFloat_AsDouble(items[1]);
    out->z = PyFloat_AsDouble(items[2]);
    Py_DECREF(sequence);
    return !PyErr_Occurred();
}

bool parse_color(PyObject* value, Color* out) {
    PyObject* sequence = PySequence_Fast(value, "color must be a 3-item sequence");
    if (sequence == nullptr) {
        return false;
    }
    if (PySequence_Fast_GET_SIZE(sequence) != 3) {
        Py_DECREF(sequence);
        PyErr_SetString(PyExc_ValueError, "color must be a 3-item sequence");
        return false;
    }

    PyObject** items = PySequence_Fast_ITEMS(sequence);
    long components[3] = {
        PyLong_AsLong(items[0]),
        PyLong_AsLong(items[1]),
        PyLong_AsLong(items[2]),
    };
    Py_DECREF(sequence);
    if (PyErr_Occurred()) {
        return false;
    }

    for (long component : components) {
        if (component < 0 || component > 255) {
            PyErr_SetString(PyExc_ValueError, "color components must be in the range 0..255");
            return false;
        }
    }

    out->r = static_cast<std::uint8_t>(components[0]);
    out->g = static_cast<std::uint8_t>(components[1]);
    out->b = static_cast<std::uint8_t>(components[2]);
    return true;
}

struct BufferView {
    Py_buffer view{};
    bool acquired = false;

    ~BufferView() {
        if (acquired) {
            PyBuffer_Release(&view);
        }
    }

    template <typename T>
    const T* data() const {
        return static_cast<const T*>(view.buf);
    }

    Py_ssize_t count(std::size_t item_size) const {
        return view.len / static_cast<Py_ssize_t>(item_size);
    }
};

bool get_contiguous_buffer(PyObject* object, BufferView* out, std::size_t item_size, const char* name) {
    if (PyObject_GetBuffer(object, &out->view, PyBUF_CONTIG_RO) != 0) {
        return false;
    }
    out->acquired = true;
    if (out->view.len % static_cast<Py_ssize_t>(item_size) != 0) {
        PyErr_Format(PyExc_ValueError, "%s has an invalid byte length", name);
        return false;
    }
    return true;
}

double clamp(double value, double low, double high) {
    return std::max(low, std::min(high, value));
}

std::uint8_t round_channel(double value) {
    return static_cast<std::uint8_t>(std::nearbyint(clamp(value, 0.0, 255.0)));
}

Vec3 subtract(Vec3 a, Vec3 b) {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}

Vec3 cross(Vec3 a, Vec3 b) {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}

double dot(Vec3 a, Vec3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

Vec3 normalize(Vec3 value) {
    const double length_sq = dot(value, value);
    if (length_sq == 0.0) {
        return {0.0, 0.0, 0.0};
    }
    const double scale = 1.0 / std::sqrt(length_sq);
    return {value.x * scale, value.y * scale, value.z * scale};
}

Vec3 transform_point(const Matrix4& matrix, Vec3 point) {
    const double x = matrix.m[0] * point.x + matrix.m[1] * point.y + matrix.m[2] * point.z + matrix.m[3];
    const double y = matrix.m[4] * point.x + matrix.m[5] * point.y + matrix.m[6] * point.z + matrix.m[7];
    const double z = matrix.m[8] * point.x + matrix.m[9] * point.y + matrix.m[10] * point.z + matrix.m[11];
    const double w = matrix.m[12] * point.x + matrix.m[13] * point.y + matrix.m[14] * point.z + matrix.m[15];
    if (w != 0.0 && w != 1.0) {
        const double inv_w = 1.0 / w;
        return {x * inv_w, y * inv_w, z * inv_w};
    }
    return {x, y, z};
}

ViewVertex transform_point_to_view(const Matrix4& matrix, Vec3 point) {
    return {
        matrix.m[0] * point.x + matrix.m[1] * point.y + matrix.m[2] * point.z + matrix.m[3],
        matrix.m[4] * point.x + matrix.m[5] * point.y + matrix.m[6] * point.z + matrix.m[7],
        matrix.m[8] * point.x + matrix.m[9] * point.y + matrix.m[10] * point.z + matrix.m[11],
    };
}

Matrix4 make_world_matrix(const MeshState& state) {
    const double cx = std::cos(state.rotation_x);
    const double sx = std::sin(state.rotation_x);
    const double cy = std::cos(state.rotation_y);
    const double sy = std::sin(state.rotation_y);
    const double cz = std::cos(state.rotation_z);
    const double sz = std::sin(state.rotation_z);

    return Matrix4{
        {
            cz * cy * state.scale_x,
            (cz * sy * sx - sz * cx) * state.scale_y,
            (cz * sy * cx + sz * sx) * state.scale_z,
            state.position_x,
            sz * cy * state.scale_x,
            (sz * sy * sx + cz * cx) * state.scale_y,
            (sz * sy * cx - cz * sx) * state.scale_z,
            state.position_y,
            -sy * state.scale_x,
            cy * sx * state.scale_y,
            cy * cx * state.scale_z,
            state.position_z,
            0.0,
            0.0,
            0.0,
            1.0,
        }
    };
}

bool should_cull_mesh(
    const MeshState& state,
    const Matrix4& view,
    double near,
    double cull_far,
    double vertical_tan,
    double horizontal_tan
) {
    const double scale = std::max({std::abs(state.scale_x), std::abs(state.scale_y), std::abs(state.scale_z)});
    const double radius = state.local_radius * scale;
    const ViewVertex center = transform_point_to_view(
        view,
        {state.position_x, state.position_y, state.position_z}
    );

    if (center.z - radius > -near) {
        return true;
    }
    if (center.z + radius < -cull_far) {
        return true;
    }

    const double depth = std::max(near, -center.z);
    if (std::abs(center.x) > depth * horizontal_tan + radius) {
        return true;
    }
    if (std::abs(center.y) > depth * vertical_tan + radius) {
        return true;
    }
    return false;
}

bool is_front_facing(ViewVertex a, ViewVertex b, ViewVertex c) {
    const Vec3 ab{b.x - a.x, b.y - a.y, b.z - a.z};
    const Vec3 ac{c.x - a.x, c.y - a.y, c.z - a.z};
    const Vec3 normal = cross(ab, ac);
    const Vec3 center{
        (a.x + b.x + c.x) / 3.0,
        (a.y + b.y + c.y) / 3.0,
        (a.z + b.z + c.z) / 3.0,
    };
    return normal.x * -center.x + normal.y * -center.y + normal.z * -center.z > 0.0;
}

Color shade_face(
    const MaterialData& material,
    const std::vector<PreparedLight>& lights,
    Vec3 a,
    Vec3 b,
    Vec3 c
) {
    const double material_red = material.red;
    const double material_green = material.green;
    const double material_blue = material.blue;
    if (lights.empty()) {
        return {
            round_channel(material_red),
            round_channel(material_green),
            round_channel(material_blue),
        };
    }

    const Vec3 normal = normalize(cross(subtract(b, a), subtract(c, a)));
    if (dot(normal, normal) == 0.0) {
        return {
            round_channel(material_red),
            round_channel(material_green),
            round_channel(material_blue),
        };
    }

    const double ambient = clamp(material.ambient, 0.0, 1.0);
    const double diffuse_scale = 1.0 - ambient;
    double red = material_red * ambient;
    double green = material_green * ambient;
    double blue = material_blue * ambient;

    for (const PreparedLight& light : lights) {
        const double strength = std::max(0.0, dot(normal, light.incoming)) * light.intensity;
        if (strength <= 0.0) {
            continue;
        }

        const double lit = diffuse_scale * strength;
        red += material_red * lit * light.color_red;
        green += material_green * lit * light.color_green;
        blue += material_blue * lit * light.color_blue;
    }

    return {
        round_channel(red),
        round_channel(green),
        round_channel(blue),
    };
}

bool project_vertex(
    ViewVertex view,
    const Matrix4& projection,
    int width,
    int height,
    ScreenVertex* out
) {
    const double clip_x = projection.m[0] * view.x + projection.m[1] * view.y + projection.m[2] * view.z + projection.m[3];
    const double clip_y = projection.m[4] * view.x + projection.m[5] * view.y + projection.m[6] * view.z + projection.m[7];
    const double clip_z = projection.m[8] * view.x + projection.m[9] * view.y + projection.m[10] * view.z + projection.m[11];
    const double clip_w = projection.m[12] * view.x + projection.m[13] * view.y + projection.m[14] * view.z + projection.m[15];
    if (clip_w == 0.0) {
        return false;
    }

    const double inv_w = 1.0 / clip_w;
    const double ndc_x = clip_x * inv_w;
    const double ndc_y = clip_y * inv_w;
    const double ndc_z = clip_z * inv_w;
    out->x = (ndc_x + 1.0) * 0.5 * static_cast<double>(width - 1);
    out->y = (1.0 - ndc_y) * 0.5 * static_cast<double>(height - 1);
    out->z = (ndc_z + 1.0) * 0.5;
    return true;
}

bool inside_z_plane(ViewVertex vertex, double plane_z, bool keep_less_equal) {
    if (keep_less_equal) {
        return vertex.z <= plane_z;
    }
    return vertex.z >= plane_z;
}

ViewVertex interpolate_view_vertex(ViewVertex a, ViewVertex b, double plane_z) {
    const double denominator = b.z - a.z;
    if (denominator == 0.0) {
        return a;
    }
    const double t = (plane_z - a.z) / denominator;
    return {
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        plane_z,
    };
}

void clip_against_z_plane(
    const std::vector<ViewVertex>& input,
    std::vector<ViewVertex>* output,
    double plane_z,
    bool keep_less_equal
) {
    output->clear();
    if (input.empty()) {
        return;
    }

    ViewVertex previous = input.back();
    bool previous_inside = inside_z_plane(previous, plane_z, keep_less_equal);
    for (ViewVertex current : input) {
        const bool current_inside = inside_z_plane(current, plane_z, keep_less_equal);
        if (current_inside != previous_inside) {
            output->push_back(interpolate_view_vertex(previous, current, plane_z));
        }
        if (current_inside) {
            output->push_back(current);
        }
        previous = current;
        previous_inside = current_inside;
    }
}

bool parse_triangle(PyObject* value, NativeTriangle* out) {
    PyObject* sequence = PySequence_Fast(value, "triangle must be a 4-item sequence");
    if (sequence == nullptr) {
        return false;
    }
    if (PySequence_Fast_GET_SIZE(sequence) != 4) {
        Py_DECREF(sequence);
        PyErr_SetString(PyExc_ValueError, "triangle must be a 4-item sequence");
        return false;
    }

    PyObject** items = PySequence_Fast_ITEMS(sequence);
    const bool parsed = parse_screen_vertex(items[0], &out->a) &&
                        parse_screen_vertex(items[1], &out->b) &&
                        parse_screen_vertex(items[2], &out->c) &&
                        parse_color(items[3], &out->color);
    Py_DECREF(sequence);
    return parsed;
}

void clear_buffer(NativeFrameBuffer* self, Color color) {
    std::fill(self->depth.begin(), self->depth.end(), std::numeric_limits<float>::infinity());
    for (std::size_t index = 0; index < self->color.size(); index += 3) {
        self->color[index] = color.r;
        self->color[index + 1] = color.g;
        self->color[index + 2] = color.b;
    }
}

void fill_triangle(NativeFrameBuffer* self, ScreenVertex a, ScreenVertex b, ScreenVertex c, Color color) {
    const int min_x = std::max(0, static_cast<int>(std::floor(std::min({a.x, b.x, c.x}))));
    const int max_x = std::min(self->width - 1, static_cast<int>(std::ceil(std::max({a.x, b.x, c.x}))));
    const int min_y = std::max(0, static_cast<int>(std::floor(std::min({a.y, b.y, c.y}))));
    const int max_y = std::min(self->height - 1, static_cast<int>(std::ceil(std::max({a.y, b.y, c.y}))));
    if (min_x > max_x || min_y > max_y) {
        return;
    }

    const double denominator = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
    if (denominator == 0.0) {
        return;
    }
    const double inv_denominator = 1.0 / denominator;

    for (int y = min_y; y <= max_y; ++y) {
        const double py = static_cast<double>(y) + 0.5;
        for (int x = min_x; x <= max_x; ++x) {
            const double px = static_cast<double>(x) + 0.5;
            const double weight_a = ((b.y - c.y) * (px - c.x) + (c.x - b.x) * (py - c.y)) * inv_denominator;
            const double weight_b = ((c.y - a.y) * (px - c.x) + (a.x - c.x) * (py - c.y)) * inv_denominator;
            const double weight_c = 1.0 - weight_a - weight_b;

            if (weight_a < -1e-6 || weight_b < -1e-6 || weight_c < -1e-6) {
                continue;
            }

            const double depth = weight_a * a.z + weight_b * b.z + weight_c * c.z;
            const std::size_t pixel_index = static_cast<std::size_t>(y) * self->width + static_cast<std::size_t>(x);
            if (depth < self->depth[pixel_index]) {
                self->depth[pixel_index] = static_cast<float>(depth);
                const std::size_t color_index = pixel_index * 3;
                self->color[color_index] = color.r;
                self->color[color_index + 1] = color.g;
                self->color[color_index + 2] = color.b;
            }
        }
    }
}

PyObject* NativeFrameBuffer_new(PyTypeObject* type, PyObject*, PyObject*) {
    auto* self = reinterpret_cast<NativeFrameBuffer*>(type->tp_alloc(type, 0));
    if (self != nullptr) {
        self->width = 0;
        self->height = 0;
        new (&self->color) std::vector<std::uint8_t>();
        new (&self->depth) std::vector<float>();
    }
    return reinterpret_cast<PyObject*>(self);
}

int NativeFrameBuffer_init(NativeFrameBuffer* self, PyObject* args, PyObject*) {
    int width = 0;
    int height = 0;
    PyObject* background_object = nullptr;
    if (!PyArg_ParseTuple(args, "iiO", &width, &height, &background_object)) {
        return -1;
    }
    if (width <= 0 || height <= 0) {
        PyErr_SetString(PyExc_ValueError, "frame buffer dimensions must be positive");
        return -1;
    }

    Color background{};
    if (!parse_color(background_object, &background)) {
        return -1;
    }

    const std::size_t pixel_count = static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
    if (pixel_count > static_cast<std::size_t>(PY_SSIZE_T_MAX) / 3) {
        PyErr_SetString(PyExc_OverflowError, "frame buffer is too large");
        return -1;
    }

    try {
        self->width = width;
        self->height = height;
        self->color.assign(pixel_count * 3, 0);
        self->depth.assign(pixel_count, std::numeric_limits<float>::infinity());
    } catch (const std::bad_alloc&) {
        PyErr_NoMemory();
        return -1;
    }

    clear_buffer(self, background);
    return 0;
}

void NativeFrameBuffer_dealloc(NativeFrameBuffer* self) {
    self->color.~vector<std::uint8_t>();
    self->depth.~vector<float>();
    Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
}

PyObject* NativeFrameBuffer_clear(NativeFrameBuffer* self, PyObject* args) {
    PyObject* color_object = nullptr;
    if (!PyArg_ParseTuple(args, "O", &color_object)) {
        return nullptr;
    }

    Color color{};
    if (!parse_color(color_object, &color)) {
        return nullptr;
    }

    Py_BEGIN_ALLOW_THREADS
    clear_buffer(self, color);
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

PyObject* NativeFrameBuffer_fill_triangle(NativeFrameBuffer* self, PyObject* args) {
    PyObject* a_object = nullptr;
    PyObject* b_object = nullptr;
    PyObject* c_object = nullptr;
    PyObject* color_object = nullptr;
    if (!PyArg_ParseTuple(args, "OOOO", &a_object, &b_object, &c_object, &color_object)) {
        return nullptr;
    }

    ScreenVertex a{};
    ScreenVertex b{};
    ScreenVertex c{};
    Color color{};
    if (!parse_screen_vertex(a_object, &a) || !parse_screen_vertex(b_object, &b) ||
        !parse_screen_vertex(c_object, &c) || !parse_color(color_object, &color)) {
        return nullptr;
    }

    Py_BEGIN_ALLOW_THREADS
    fill_triangle(self, a, b, c, color);
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

PyObject* NativeFrameBuffer_fill_triangles(NativeFrameBuffer* self, PyObject* args) {
    PyObject* triangles_object = nullptr;
    if (!PyArg_ParseTuple(args, "O", &triangles_object)) {
        return nullptr;
    }

    PyObject* sequence = PySequence_Fast(triangles_object, "triangles must be a sequence");
    if (sequence == nullptr) {
        return nullptr;
    }

    const Py_ssize_t count = PySequence_Fast_GET_SIZE(sequence);
    std::vector<NativeTriangle> triangles;
    try {
        triangles.reserve(static_cast<std::size_t>(count));
    } catch (const std::bad_alloc&) {
        Py_DECREF(sequence);
        PyErr_NoMemory();
        return nullptr;
    }

    PyObject** items = PySequence_Fast_ITEMS(sequence);
    for (Py_ssize_t index = 0; index < count; ++index) {
        NativeTriangle triangle{};
        if (!parse_triangle(items[index], &triangle)) {
            Py_DECREF(sequence);
            return nullptr;
        }
        triangles.push_back(triangle);
    }
    Py_DECREF(sequence);

    Py_BEGIN_ALLOW_THREADS
    for (const NativeTriangle& triangle : triangles) {
        fill_triangle(self, triangle.a, triangle.b, triangle.c, triangle.color);
    }
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

PyObject* NativeFrameBuffer_render_scene(NativeFrameBuffer* self, PyObject* args) {
    PyObject* vertices_object = nullptr;
    PyObject* faces_object = nullptr;
    PyObject* mesh_ranges_object = nullptr;
    PyObject* mesh_states_object = nullptr;
    PyObject* materials_object = nullptr;
    PyObject* lights_object = nullptr;
    PyObject* view_object = nullptr;
    PyObject* projection_object = nullptr;
    PyObject* background_object = nullptr;
    double near = 0.0;
    double far = 0.0;
    double cull_far = 0.0;
    double vertical_tan = 0.0;
    double horizontal_tan = 0.0;
    int enable_culling = 1;

    if (!PyArg_ParseTuple(
            args,
            "OOOOOOOOOdddddp",
            &vertices_object,
            &faces_object,
            &mesh_ranges_object,
            &mesh_states_object,
            &materials_object,
            &lights_object,
            &view_object,
            &projection_object,
            &background_object,
            &near,
            &far,
            &cull_far,
            &vertical_tan,
            &horizontal_tan,
            &enable_culling
        )) {
        return nullptr;
    }
    if (near <= 0.0 || far <= near || cull_far <= near) {
        PyErr_SetString(PyExc_ValueError, "invalid camera clipping distances");
        return nullptr;
    }

    Color background{};
    if (!parse_color(background_object, &background)) {
        return nullptr;
    }

    BufferView vertices;
    BufferView faces;
    BufferView mesh_ranges;
    BufferView mesh_states;
    BufferView materials;
    BufferView lights;
    BufferView view_buffer;
    BufferView projection_buffer;
    if (!get_contiguous_buffer(vertices_object, &vertices, sizeof(double), "vertices") ||
        !get_contiguous_buffer(faces_object, &faces, sizeof(std::int32_t), "faces") ||
        !get_contiguous_buffer(mesh_ranges_object, &mesh_ranges, sizeof(std::int32_t), "mesh_ranges") ||
        !get_contiguous_buffer(mesh_states_object, &mesh_states, sizeof(double), "mesh_states") ||
        !get_contiguous_buffer(materials_object, &materials, sizeof(double), "materials") ||
        !get_contiguous_buffer(lights_object, &lights, sizeof(double), "lights") ||
        !get_contiguous_buffer(view_object, &view_buffer, sizeof(double), "view_matrix") ||
        !get_contiguous_buffer(projection_object, &projection_buffer, sizeof(double), "projection_matrix")) {
        return nullptr;
    }

    const Py_ssize_t vertex_value_count = vertices.count(sizeof(double));
    const Py_ssize_t face_value_count = faces.count(sizeof(std::int32_t));
    const Py_ssize_t mesh_range_value_count = mesh_ranges.count(sizeof(std::int32_t));
    const Py_ssize_t mesh_state_value_count = mesh_states.count(sizeof(double));
    const Py_ssize_t material_value_count = materials.count(sizeof(double));
    const Py_ssize_t light_value_count = lights.count(sizeof(double));
    if (vertex_value_count % 3 != 0) {
        PyErr_SetString(PyExc_ValueError, "vertices must have shape (n, 3)");
        return nullptr;
    }
    if (face_value_count % 3 != 0) {
        PyErr_SetString(PyExc_ValueError, "faces must have shape (n, 3)");
        return nullptr;
    }
    if (mesh_range_value_count % 5 != 0) {
        PyErr_SetString(PyExc_ValueError, "mesh_ranges must have shape (n, 5)");
        return nullptr;
    }
    if (mesh_state_value_count % 10 != 0) {
        PyErr_SetString(PyExc_ValueError, "mesh_states must have shape (n, 10)");
        return nullptr;
    }
    if (material_value_count % 4 != 0) {
        PyErr_SetString(PyExc_ValueError, "materials must have shape (n, 4)");
        return nullptr;
    }
    if (light_value_count % 7 != 0) {
        PyErr_SetString(PyExc_ValueError, "lights must have shape (n, 7)");
        return nullptr;
    }
    if (view_buffer.count(sizeof(double)) != 16 || projection_buffer.count(sizeof(double)) != 16) {
        PyErr_SetString(PyExc_ValueError, "view and projection matrices must have 16 values");
        return nullptr;
    }

    const Py_ssize_t vertex_count = vertex_value_count / 3;
    const Py_ssize_t face_count = face_value_count / 3;
    const Py_ssize_t mesh_count = mesh_range_value_count / 5;
    const Py_ssize_t mesh_state_count = mesh_state_value_count / 10;
    const Py_ssize_t material_count = material_value_count / 4;
    const Py_ssize_t light_count = light_value_count / 7;
    if (mesh_state_count != mesh_count) {
        PyErr_SetString(PyExc_ValueError, "mesh_states count must match mesh_ranges count");
        return nullptr;
    }

    const auto* face_data = faces.data<std::int32_t>();
    const auto* range_data = mesh_ranges.data<std::int32_t>();
    for (Py_ssize_t mesh_index = 0; mesh_index < mesh_count; ++mesh_index) {
        const Py_ssize_t base = mesh_index * 5;
        const MeshRange range{
            range_data[base],
            range_data[base + 1],
            range_data[base + 2],
            range_data[base + 3],
            range_data[base + 4],
        };
        if (range.vertex_start < 0 || range.vertex_count < 0 ||
            static_cast<Py_ssize_t>(range.vertex_start) + range.vertex_count > vertex_count ||
            range.face_start < 0 || range.face_count < 0 ||
            static_cast<Py_ssize_t>(range.face_start) + range.face_count > face_count ||
            range.material_index < 0 || range.material_index >= material_count) {
            PyErr_SetString(PyExc_ValueError, "mesh range is out of bounds");
            return nullptr;
        }
        for (int face_offset = 0; face_offset < range.face_count; ++face_offset) {
            const Py_ssize_t face_index = static_cast<Py_ssize_t>(range.face_start) + face_offset;
            const std::int32_t ia = face_data[face_index * 3];
            const std::int32_t ib = face_data[face_index * 3 + 1];
            const std::int32_t ic = face_data[face_index * 3 + 2];
            if (ia < 0 || ib < 0 || ic < 0 ||
                ia >= range.vertex_count || ib >= range.vertex_count || ic >= range.vertex_count) {
                PyErr_SetString(PyExc_ValueError, "face index is out of bounds");
                return nullptr;
            }
        }
    }

    Matrix4 view{};
    Matrix4 projection{};
    std::copy(view_buffer.data<double>(), view_buffer.data<double>() + 16, view.m);
    std::copy(projection_buffer.data<double>(), projection_buffer.data<double>() + 16, projection.m);

    std::vector<PreparedLight> prepared_lights;
    try {
        prepared_lights.reserve(static_cast<std::size_t>(light_count));
    } catch (const std::bad_alloc&) {
        PyErr_NoMemory();
        return nullptr;
    }
    const double* light_data = lights.data<double>();
    for (Py_ssize_t index = 0; index < light_count; ++index) {
        const double* row = light_data + index * 7;
        const Vec3 direction{row[0], row[1], row[2]};
        const Vec3 normalized = normalize(direction);
        prepared_lights.push_back(
            PreparedLight{
                {-normalized.x, -normalized.y, -normalized.z},
                clamp(row[3] / 255.0, 0.0, 1.0),
                clamp(row[4] / 255.0, 0.0, 1.0),
                clamp(row[5] / 255.0, 0.0, 1.0),
                row[6],
            }
        );
    }

    std::vector<ViewVertex> clipped_a;
    std::vector<ViewVertex> clipped_b;
    clipped_a.reserve(8);
    clipped_b.reserve(8);

    const double* vertex_data = vertices.data<double>();
    const double* state_data = mesh_states.data<double>();
    const double* material_data = materials.data<double>();
    const bool culling_enabled = enable_culling != 0;

    Py_BEGIN_ALLOW_THREADS
    clear_buffer(self, background);

    for (Py_ssize_t mesh_index = 0; mesh_index < mesh_count; ++mesh_index) {
        const Py_ssize_t range_base = mesh_index * 5;
        const MeshRange range{
            range_data[range_base],
            range_data[range_base + 1],
            range_data[range_base + 2],
            range_data[range_base + 3],
            range_data[range_base + 4],
        };
        const double* state_row = state_data + mesh_index * 10;
        const MeshState state{
            state_row[0],
            state_row[1],
            state_row[2],
            state_row[3],
            state_row[4],
            state_row[5],
            state_row[6],
            state_row[7],
            state_row[8],
            state_row[9],
        };
        if (culling_enabled && should_cull_mesh(state, view, near, cull_far, vertical_tan, horizontal_tan)) {
            continue;
        }

        const Matrix4 world = make_world_matrix(state);
        const double* material_row = material_data + range.material_index * 4;
        const MaterialData material{
            material_row[0],
            material_row[1],
            material_row[2],
            material_row[3],
        };

        for (int face_offset = 0; face_offset < range.face_count; ++face_offset) {
            const Py_ssize_t face_index = static_cast<Py_ssize_t>(range.face_start) + face_offset;
            const int index_a = range.vertex_start + face_data[face_index * 3];
            const int index_b = range.vertex_start + face_data[face_index * 3 + 1];
            const int index_c = range.vertex_start + face_data[face_index * 3 + 2];

            const double* local_a_row = vertex_data + static_cast<Py_ssize_t>(index_a) * 3;
            const double* local_b_row = vertex_data + static_cast<Py_ssize_t>(index_b) * 3;
            const double* local_c_row = vertex_data + static_cast<Py_ssize_t>(index_c) * 3;
            const Vec3 world_a = transform_point(world, {local_a_row[0], local_a_row[1], local_a_row[2]});
            const Vec3 world_b = transform_point(world, {local_b_row[0], local_b_row[1], local_b_row[2]});
            const Vec3 world_c = transform_point(world, {local_c_row[0], local_c_row[1], local_c_row[2]});
            const ViewVertex view_a = transform_point_to_view(view, world_a);
            const ViewVertex view_b = transform_point_to_view(view, world_b);
            const ViewVertex view_c = transform_point_to_view(view, world_c);

            if (!is_front_facing(view_a, view_b, view_c)) {
                continue;
            }

            clipped_a.clear();
            clipped_a.push_back(view_a);
            clipped_a.push_back(view_b);
            clipped_a.push_back(view_c);
            clip_against_z_plane(clipped_a, &clipped_b, -near, true);
            clip_against_z_plane(clipped_b, &clipped_a, -far, false);
            if (clipped_a.size() < 3) {
                continue;
            }

            const Color color = shade_face(material, prepared_lights, world_a, world_b, world_c);
            ScreenVertex screen_origin{};
            if (!project_vertex(clipped_a[0], projection, self->width, self->height, &screen_origin)) {
                continue;
            }
            for (std::size_t vertex_index = 1; vertex_index + 1 < clipped_a.size(); ++vertex_index) {
                ScreenVertex screen_b{};
                ScreenVertex screen_c{};
                if (!project_vertex(clipped_a[vertex_index], projection, self->width, self->height, &screen_b) ||
                    !project_vertex(clipped_a[vertex_index + 1], projection, self->width, self->height, &screen_c)) {
                    continue;
                }
                fill_triangle(self, screen_origin, screen_b, screen_c, color);
            }
        }
    }
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

PyObject* NativeFrameBuffer_get_pixel(NativeFrameBuffer* self, PyObject* args) {
    int x = 0;
    int y = 0;
    if (!PyArg_ParseTuple(args, "ii", &x, &y)) {
        return nullptr;
    }
    if (x < 0 || y < 0 || x >= self->width || y >= self->height) {
        PyErr_SetString(PyExc_IndexError, "pixel coordinates are out of range");
        return nullptr;
    }

    const std::size_t color_index =
        (static_cast<std::size_t>(y) * self->width + static_cast<std::size_t>(x)) * 3;
    return Py_BuildValue(
        "(iii)",
        static_cast<int>(self->color[color_index]),
        static_cast<int>(self->color[color_index + 1]),
        static_cast<int>(self->color[color_index + 2])
    );
}

int NativeFrameBuffer_getbuffer(PyObject* exporter, Py_buffer* view, int flags) {
    auto* self = reinterpret_cast<NativeFrameBuffer*>(exporter);
    return PyBuffer_FillInfo(
        view,
        exporter,
        self->color.data(),
        static_cast<Py_ssize_t>(self->color.size()),
        1,
        flags
    );
}

PyMethodDef NativeFrameBuffer_methods[] = {
    {"clear", reinterpret_cast<PyCFunction>(NativeFrameBuffer_clear), METH_VARARGS, "Clear color and depth buffers."},
    {
        "fill_triangle",
        reinterpret_cast<PyCFunction>(NativeFrameBuffer_fill_triangle),
        METH_VARARGS,
        "Rasterize one flat-shaded triangle with depth testing.",
    },
    {
        "fill_triangles",
        reinterpret_cast<PyCFunction>(NativeFrameBuffer_fill_triangles),
        METH_VARARGS,
        "Rasterize flat-shaded triangles with depth testing.",
    },
    {
        "render_scene",
        reinterpret_cast<PyCFunction>(NativeFrameBuffer_render_scene),
        METH_VARARGS,
        "Render one scene from packed mesh arrays.",
    },
    {"get_pixel", reinterpret_cast<PyCFunction>(NativeFrameBuffer_get_pixel), METH_VARARGS, "Return one RGB pixel."},
    {nullptr, nullptr, 0, nullptr},
};

PyBufferProcs NativeFrameBuffer_buffer_procs = {
    NativeFrameBuffer_getbuffer,
    nullptr,
};

PyTypeObject NativeFrameBufferType = {
    PyVarObject_HEAD_INIT(nullptr, 0)
};

PyModuleDef module_definition = {
    PyModuleDef_HEAD_INIT,
    "minipy3dr._native",
    "Native software rasterizer backend for MiniPy3DR.",
    -1,
    nullptr,
};

}  // namespace

PyMODINIT_FUNC PyInit__native() {
    NativeFrameBufferType.tp_name = "minipy3dr._native.NativeFrameBuffer";
    NativeFrameBufferType.tp_basicsize = sizeof(NativeFrameBuffer);
    NativeFrameBufferType.tp_itemsize = 0;
    NativeFrameBufferType.tp_dealloc = reinterpret_cast<destructor>(NativeFrameBuffer_dealloc);
    NativeFrameBufferType.tp_flags = Py_TPFLAGS_DEFAULT;
    NativeFrameBufferType.tp_doc = "Native RGB framebuffer with a z-buffer.";
    NativeFrameBufferType.tp_methods = NativeFrameBuffer_methods;
    NativeFrameBufferType.tp_init = reinterpret_cast<initproc>(NativeFrameBuffer_init);
    NativeFrameBufferType.tp_new = NativeFrameBuffer_new;
    NativeFrameBufferType.tp_as_buffer = &NativeFrameBuffer_buffer_procs;

    if (PyType_Ready(&NativeFrameBufferType) < 0) {
        return nullptr;
    }

    PyObject* module = PyModule_Create(&module_definition);
    if (module == nullptr) {
        return nullptr;
    }

    Py_INCREF(&NativeFrameBufferType);
    if (PyModule_AddObject(module, "NativeFrameBuffer", reinterpret_cast<PyObject*>(&NativeFrameBufferType)) < 0) {
        Py_DECREF(&NativeFrameBufferType);
        Py_DECREF(module);
        return nullptr;
    }

    return module;
}
