#!BPY

# Copyright (c) 2020 SuperTuxKart author(s)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import bpy
import mathutils
import numpy as np
from . import stk_utils

object_geo_detail_level = {
    'off': -1,
    'always': 0,
    'medium': 1,
    'high': 2,
}

object_interaction = {
    'static': 0x00,
    'movable': 0x01,
    'ghost': 0x02,
    'physics': 0x03,
    'reset': 0x04,
    'knock': 0x05,
    'flatten': 0x06,
}

object_physics_shape = {
    'box': 0x00,
    'sphere': 0x01,
    'cylinder_x': 0x02,
    'cylinder_y': 0x03,
    'cylinder_z': 0x04,
    'cone_x': 0x05,
    'cone_y': 0x05,
    'cone_z': 0x06,
    'exact': 0x07,
}

object_flags = {
    'driveable': 0x00,
    'soccer_ball': 0x01,
    'glow': 0x02,
    'shadows': 0x04,
}

eggs_visibility = {
    'none': 0x00,
    'easy': 0x01,
    'intermediate': 0x02,
    'hard': 0x04,
}

camera_type = {
    'none': 0x00,
    'end_fixed': 0x01,
    'end_kart': 0x02,
    'cutscene': 0x03,
}

track_object = np.dtype([
    ('id', 'U127'),                 # ID
    ('lod', 'O'),                   # LOD collection reference
    ('lod_distance', np.float32),   # LOD standalone distance (<0 for instances)
    ('lod_modifiers', np.float32),  # LOD modifiers distance (<0 for instances or disabled)
    ('uv_animated', 'O'),           # Material reference for UV animation
    ('uv_speed_u', np.float32),     # UV aniamtion speed U
    ('uv_speed_v', np.float32),     # UV aniamtion speed V
    ('uv_speed_dt', np.float32),    # UV step aniamtion speed (<0 if disabled)
    ('visibility', np.int8),        # Geometry level visibility (object_geo_detail_level)
    ('interaction', np.int8),       # Interaction type (object_interaction)
    ('shape', np.int8),             # Physics shape (object_physics_shape)
    ('flags', np.int8),             # Object flags (object_flags)
    ('glow', stk_utils.vec3),       # Glow color (if glow flag set)
    ('visible_if', 'U127'),         # Scripting: only enabled if (poll function)
    ('on_collision', 'U127'),       # Scripting: on collision scripting callback
    ('custom_xml', 'U127'),         # Additional custom XML
])

track_placeables = np.dtype([
    ('id', 'U127'),
    ('start_index', np.int32),
    ('snap_ground', np.int32),
    ('ctf_only', np.int32),
])

track_eggs = np.dtype([
    ('id', 'U127'),
    ('visibility', np.int8),
])

track_billboard = np.dtype([
    ('id', 'U127'),
    ('fadeout_start', np.float32),
    ('fadeout_end', np.float32),
])

track_particles = np.dtype([
    ('id', 'U127'),
    ('file', 'U127'),
    ('distance', np.float32),
    ('emit', np.bool_),
])

track_godrays = np.dtype([
    ('id', 'U127'),
    ('opacity', np.float32),
    ('color', stk_utils.vec3),
])

track_audio = np.dtype([
    ('id', 'U127'),
    ('file', 'U127'),
    ('volume', np.float32),
    ('rolloff', np.float32),
    ('distance', np.float32),
])

track_action = np.dtype([
    ('id', 'U127'),
    ('action', 'U127'),
    ('distance', np.float32),
    ('timeout', np.float32),
    ('cylindrical', np.bool_),
])

track_driveline = np.dtype([
    ('id', 'U127'),
    ('lower', np.float32),
    ('higher', np.float32),
    ('invisible', np.bool_),
    ('ignore', np.bool_),
    ('direction', np.bool_),
])

track_checkline = np.dtype([
    ('id', 'U127'),
    ('end', 'O'),
    ('path', 'O'),
    ('speed', np.float32),
])

track_goal = np.dtype([
    ('id', 'U127'),
    ('team', np.bool_),
])

track_light = np.dtype([
    ('id', 'U127'),
    ('distance', np.float32),
    ('visible_if', 'U127'),
])

track_camera = np.dtype([
    ('id', 'U127'),
    ('type', np.int8),
    ('distance', np.float32),
])


def write_scene(context: bpy.context):
    lod_groups = None
    lod_
    for obj in context.scene.objects:
        pass


def assign_test():
    demo = []
    demo.append((
        "Hellooo1",
        None,
        -1.0,
        -1.0,
        None,
        0.0,
        0.0,
        -1.0,
        object_geo_detail_level['off'],
        object_interaction['static'],
        object_physics_shape['box'],
        0x04,
        (0.0, 0.0, 0.0),
        "",
        "",
        "",
    ))
    demo.append((
        "Hellooo2",
        None,
        -1.0,
        -1.0,
        None,
        0.0,
        0.0,
        -1.0,
        object_geo_detail_level['off'],
        object_interaction['static'],
        object_physics_shape['box'],
        0x04,
        (0.0, 0.0, 0.0),
        "",
        "",
        "",
    ))
    print(track_object)
    arr = np.array(demo, dtype=track_object)
    print(arr)
