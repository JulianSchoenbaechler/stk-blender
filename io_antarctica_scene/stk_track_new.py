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
import collections
import numpy as np
from . import stk_utils

SceneCollection = collections.namedtuple('SceneCollection', [
    'lod_groups',
    'static_objects',
    'dynamic_objects',
    'placeables',
    'billboards',
    'particles',
    'godrays',
    'audio_sources',
    'action_triggers',
    'drivelines',
    'checklines',
    'goals',
    'lights',
    'cameras',
])

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
    'none': 0x00,
    'driveable': 0x01,
    'soccer_ball': 0x02,
    'glow': 0x04,
    'shadows': 0x08,
}

placeable_type = {
    'item_gift': 0x00,
    'item_banana': 0x01,
    'item_easteregg': 0x02,
    'item_nitro_small': 0x03,
    'item_nitro_big': 0x04,
    'item_flag_red': 0x05,
    'item_flag_blue': 0x06,
    'start_position': 0x07,
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

track_placeable = np.dtype([
    ('id', 'U127'),
    ('type', np.int8),
    ('start_index', np.int32),
    ('snap_ground', np.bool_),
    ('ctf_only', np.bool_),
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


def write_scene(context: bpy.context, report):
    used_identifiers = []
    lod_groups = set()
    static_objects = []
    dynamic_objects = []
    placeables = []
    billboards = []
    particles = []
    godrays = []
    audio_sources = []
    action_triggers = []
    drivelines = []
    checklines = []
    goals = []
    lights = []
    cameras = []

    # Gather and categorize all objects that need to get exported
    for obj in context.scene.objects:
        # Ignore disabled
        if obj.hide_viewport or obj.hide_render:
            continue

        if (obj.type == 'MESH' or obj.type == 'EMPTY') and hasattr(obj, 'stk_track'):
            # Categorize objects
            props = obj.stk_track
            t = props.type

            # Unassigned model (defaults to static track scenery)
            if obj.type != 'EMPTY' and t == 'none':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                static_objects.append((
                    obj.name,                           # ID
                    None, -1.0, -1.0,                   # LOD: collection, distance, modifiers distance
                    None, 0.0, 0.0, -1.0,               # Animated UV: material, speed U, speed V, step
                    object_geo_detail_level['off'],     # Geometry level detail
                    object_interaction['static'],       # Object interaction
                    object_physics_shape['box'],        # Physics shape
                    object_flags['none'],               # Object specific flags
                    (0.0, 0.0, 0.0),                    # Glow color (if glow enabled)
                    "",                                 # Scripting: poll function (if)
                    "",                                 # Scripting: collision callback
                    "",                                 # Custom XML
                ))
                used_identifiers.append(obj.name)

            # Object (including LOD) with specified properties
            elif obj.type != 'EMPTY' and (t == 'object' or t == 'lod_instance' or t == 'lod_standalone'):
                # Name identifier
                staged = [props.name if len(props.name) > 0 else obj.name]

                # Skip if already an object with this identifier
                if staged[0] in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                is_static = props.interaction == 'static' or props.interaction == 'physics'

                # LOD
                staged.append(props.lod_collection)
                staged.append(props.lod_distance if t == 'lod_standalone' else -1.0)
                staged.append(props.lod_modifiers if t == 'lod_standalone' and props.lod_modifiers_distance else -1.0)

                if props.lod_collection:
                    lod_groups.add(props.lod_collection)

                # Animated textures
                staged.append(props.uv_material if props.uv_animated else None)
                staged.append(props.uv_speed_u)
                staged.append(props.uv_speed_v)
                staged.append(props.uv_speed_dt if props.uv_step else -1.0)

                # Object geometry visibility
                if props.visibility:
                    staged.append(object_geo_detail_level[props.visibility_detail])
                    is_static = False
                else:
                    staged.append(object_geo_detail_level['off'])

                # Object interaction and physics shape
                staged.append(object_interaction[props.interaction])
                staged.append(object_physics_shape[props.shape])

                # Object flags
                flags = object_flags['none']
                if props.driveable:
                    flags |= object_flags['driveable']
                if props.soccer_ball:
                    flags |= object_flags['soccer_ball']
                    is_static = False
                if props.glow:
                    flags |= object_flags['glow']
                    is_static = False
                if props.shadows:
                    flags |= object_flags['shadows']
                else:
                    is_static = False
                staged.append(flags)
                staged.append((props.glow_color.r, props.glow_color.g, props.glow_color.b))

                # Scripting and output related
                staged.append(props.visible_if)
                staged.append(props.on_kart_collision)
                staged.append(props.custom_xml)

                # Non-static if interactive
                if is_static and (len(props.visible_if) > 0 or len(props.on_kart_collision) > 0):
                    is_static = False

                # Non-static if animated
                if is_static and stk_utils.object_is_animated(obj):
                    is_static = False

                print(staged)

                if is_static:
                    static_objects.append(tuple(staged))
                else:
                    dynamic_objects.append(tuple(staged))

                used_identifiers.append(staged[0])

            # Placeables
            elif t == 'start_position' or t.startswith('item'):
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                placeables.append((
                    obj.name,               # ID
                    placeable_type[t],      # Placeable type
                    props.start_index,      # Start index for start positions
                    props.snap_ground,      # Snap to ground
                    props.ctf_only,         # Enabled in CTF mode only
                ))

                used_identifiers.append(obj.name)

            # Placeables
            elif t == 'start_position' or t.startswith('item'):
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                placeables.append((
                    obj.name,                                       # ID
                    placeable_type[t],                              # Placeable type
                    props.start_index,                              # Start index for start positions
                    props.snap_ground,                              # Snap to ground
                    props.ctf_only,                                 # Enabled in CTF mode only
                    eggs_visibility[props.easteregg_visibility],    # Item visibility (only used in easter-egg mode)
                ))

                used_identifiers.append(obj.name)

        elif obj.type == 'LIGHT' and hasattr(obj.data, 'stk'):
            pass
        elif obj.type == 'CAMERA' and hasattr(obj.data, 'stk'):
            pass
        else:
            continue

    # Create and return scene collection
    return SceneCollection(
        lod_groups,
        np.array(static_objects, dtype=track_object),
        np.array(dynamic_objects, dtype=track_object),
        np.array(placeables, dtype=track_placeable),
        np.array(billboards, dtype=track_billboard),
        np.array(particles, dtype=track_particles),
        np.array(godrays, dtype=track_godrays),
        np.array(audio_sources, dtype=track_audio),
        np.array(action_triggers, dtype=track_action),
        np.array(drivelines, dtype=track_driveline),
        np.array(checklines, dtype=track_checkline),
        np.array(goals, dtype=track_goal),
        np.array(lights, dtype=track_light),
        np.array(cameras, dtype=track_camera),
    )


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
