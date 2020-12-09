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
import collections
import mathutils
import os
import numpy as np
from . import stk_utils, stk_props

STANDALONE_LOD_PREFIX = '_standalone_'

# TODO: Particle system object placement
# TODO: Library nodes collecting
SceneCollection = collections.namedtuple('SceneCollection', [
    'lod_groups',
    'track_objects',
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
    'cannons',
    'goals',
    'lights',
    'cameras',
    'sun',
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

driveline_type = {
    'driveline_main': 0x00,
    'driveline_additional': 0x01,
    'navmesh': 0x02,
}

camera_type = {
    'end_fixed': 0x00,
    'end_kart': 0x01,
    'cutscene': 0x02,
}

track_object = np.dtype([
    ('id', 'U127'),                         # ID
    ('object', 'O'),                        # Object reference
    ('transform', stk_utils.transform),     # Transform
    ('lod', 'O'),                           # LOD collection reference
    ('lod_distance', np.float32),           # LOD standalone distance (<0 for instances)
    ('lod_modifiers', np.float32),          # LOD modifiers distance (<0 for instances or disabled)
    ('uv_animated', 'O'),                   # Material reference for UV animation
    ('uv_speed_u', np.float32),             # UV animation speed U
    ('uv_speed_v', np.float32),             # UV animation speed V
    ('uv_speed_dt', np.float32),            # UV step animation speed (<0 if disabled)
    ('visibility', np.int8),                # Geometry level visibility (object_geo_detail_level)
    ('interaction', np.int8),               # Interaction type (object_interaction)
    ('shape', np.int8),                     # Physics shape (object_physics_shape)
    ('flags', np.int8),                     # Object flags (object_flags)
    ('glow', stk_utils.vec3),               # Glow color (if glow flag set)
    ('visible_if', 'U127'),                 # Scripting: only enabled if (poll function)
    ('on_collision', 'U127'),               # Scripting: on collision scripting callback
    ('custom_xml', 'U127'),                 # Additional custom XML
])

track_placeable = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('type', np.int8),
    ('start_index', np.int32),
    ('snap_ground', np.bool_),
    ('ctf_only', np.bool_),
    ('visibility', np.int8),
])

track_billboard = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('texture', 'U127'),
    ('size', stk_utils.vec2),
    ('fadeout_start', np.float32),
    ('fadeout_end', np.float32),
])

track_particles = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('file', 'U127'),
    ('distance', np.float32),
    ('emit', np.bool_),
])

track_godrays = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('opacity', np.float32),
    ('color', stk_utils.vec3),
])

track_audio = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('file', 'U127'),
    ('volume', np.float32),
    ('rolloff', np.float32),
    ('distance', np.float32),
    ('trigger', np.float32),
])

track_action = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('action', 'U127'),
    ('distance', np.float32),
    ('timeout', np.float32),
    ('cylindrical', np.bool_),
])

track_driveline = np.dtype([
    ('id', 'U127'),
    ('mesh', 'O'),
    ('type', np.int8),
    ('lower', np.float32),
    ('higher', np.float32),
    ('invisible', np.bool_),
    ('ignore', np.bool_),
    ('direction', np.bool_),
])

track_checkline = np.dtype([
    ('id', 'U127'),
    ('line', stk_utils.line),
    ('index', np.int32),
    ('active', np.int32),
])

track_cannon = np.dtype([
    ('id', 'U127'),
    ('curve', 'O'),
    ('start', stk_utils.line),
    ('end', stk_utils.line),
    ('speed', np.float32),
])

track_goal = np.dtype([
    ('id', 'U127'),
    ('line', stk_utils.line),
    ('team', np.bool_),
])

track_light = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('distance', np.float32),
    ('energy', np.float32),
    ('color', stk_utils.vec3),
    ('visible_if', 'U127'),
])

track_camera = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('type', np.int8),
    ('distance', np.float32),
])


def collect_scene(context: bpy.context, report):
    used_identifiers = []
    lod_groups = set()
    track_objects = []
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
    cannons = []
    goals = []
    lights = []
    cameras = []
    sun = None

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
                track_objects.append(obj)

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
                staged.append(obj)
                staged.append(stk_utils.object_get_transform(obj))

                # LOD
                if t == 'lod_instance' and props.lod_collection and len(props.lod_collection.objects) > 0:
                    staged.append(props.lod_collection)
                    lod_groups.add(props.lod_collection)
                else:
                    staged.append(None)

                if t == 'lod_standalone':
                    staged.append(props.lod_distance)
                    staged.append(props.lod_modifiers if props.lod_modifiers_distance else -1.0)
                    lod_groups.add(obj)
                else:
                    staged.append(-1.0)
                    staged.append(-1.0)

                # Animated textures
                if props.uv_animated and props.uv_material.use_nodes \
                   and stk_utils.is_stk_material(props.uv_material.node_tree):
                    staged.append(props.uv_material)
                    staged.append(props.uv_speed_u)
                    staged.append(props.uv_speed_v)
                    staged.append(props.uv_speed_dt if props.uv_step else - 1.0)
                else:
                    staged.append(None)
                    staged.append(0.0)
                    staged.append(0.0)
                    staged.append(-1.0)

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
                if props.interaction == 'static' and props.driveable:
                    flags |= object_flags['driveable']
                if props.interaction == 'movable' and props.soccer_ball:
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
                staged.append(tuple(props.glow_color))

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

                # TODO: It might be better letting the artist decide if an object is static or not. This branching-logic
                # should act as default to not break compatibility but should be overridable.

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

                visibility = eggs_visibility['none']

                if 'easy' in props.easteregg_visibility:
                    visibility |= eggs_visibility['easy']
                if 'intermediate' in props.easteregg_visibility:
                    visibility |= eggs_visibility['intermediate']
                if 'hard' in props.easteregg_visibility:
                    visibility |= eggs_visibility['hard']

                placeables.append((
                    obj.name,                               # ID
                    stk_utils.object_get_transform(obj),    # Transform
                    placeable_type[t],                      # Placeable type
                    props.start_index,                      # Start index for start positions
                    props.snap_ground,                      # Snap to ground
                    props.ctf_only,                         # Enabled in CTF mode only
                    visibility,                             # Item visibility (only used in easter-egg mode)
                ))

                used_identifiers.append(obj.name)

            # Billboard
            elif obj.type != 'EMPTY' and t == 'billboard':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                # Check billboard shape
                if len(obj.data.vertices) != 4 or len(obj.data.polygons) == 0 or len(obj.data.polygons) > 1:
                    report({'WARNING'}, f"The billboard '{obj.name}' has an invalid shape! Make sure it has no more "
                           "than 4 vertices and consist of only one face.")
                    continue

                # Check billboard material
                material = None

                if len(obj.material_slots) == 0:
                    report({'WARNING'}, f"The billboard '{obj.name}' has no material assigned!")
                    continue
                else:
                    material = obj.material_slots[obj.data.polygons[0].material_index].material

                    if len(material.name) > 127 or not stk_utils.is_stk_material(material.node_tree):
                        report({'WARNING'}, f"The material of the billboard '{obj.name}' is not supported!")
                        continue

                normal = mathutils.Vector((0.0, 0.0, 0.0))

                for i in range(0, 4):
                    normal += obj.data.vertices[i].normal

                size = tuple()

                # Check if billboard faces upwards (angle between normal and up-vector less than 45 degree)
                if normal.angle((0.0, 0.0, 1.0)) < 0.7853981634:
                    size = (obj.dimensions[0], obj.dimensions[1])
                elif normal.angle((0.0, 1.0, 0.0)) < 0.7853981634:
                    size = (obj.dimensions[0], obj.dimensions[2])
                else:
                    size = (obj.dimensions[1], obj.dimensions[2])

                billboards.append((
                    obj.name,                                           # ID
                    stk_utils.object_get_transform(obj),                # Transform
                    material.name,                                      # Material name
                    size,                                               # Size
                    props.fadeout_start if props.fadeout else -1.0,     # Fadeout start
                    props.fadeout_end if props.fadeout else -1.0,       # Fadeout end
                ))

                used_identifiers.append(obj.name)

            # Particles
            elif t == 'particle_emitter':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                particles.append((
                    obj.name,                               # ID
                    stk_utils.object_get_transform(obj),    # Transform
                    props.particles,                        # Particles file name
                    props.particles_distance,               # Particles clip distance
                    props.particles_emit,                   # Particles auto-emit
                ))

                used_identifiers.append(obj.name)

            # Godrays / light shaft
            elif t == 'lightshaft_emitter':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                godrays.append((
                    obj.name,                               # ID
                    stk_utils.object_get_transform(obj),    # Transform
                    props.lightshaft_opacity,               # Light shaft opacity
                    tuple(props.lightshaft_color),          # Light shaft color
                ))

                used_identifiers.append(obj.name)

            # SFX emitter
            elif t == 'sfx_emitter':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                audio_sources.append((
                    obj.name,                                                   # ID
                    stk_utils.object_get_transform(obj),                        # Transform
                    props.sfx,                                                  # Sound file
                    props.sfx_volume,                                           # Sound volume
                    props.sfx_rolloff,                                          # Sound rolloff
                    props.sfx_distance,                                         # Sound hearing distance
                    props.sfx_trigger_distance if props.sfx_trigger else -1.0,  # Sound trigger distance
                ))

                used_identifiers.append(obj.name)

            # Scripting action emitter
            elif t == 'action_trigger':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                action_triggers.append((
                    obj.name,                               # ID
                    stk_utils.object_get_transform(obj),    # Transform
                    props.action,                           # Action call
                    props.action_distance,                  # Trigger distance (radius)
                    props.action_timeout,                   # Action re-enable timeout
                    props.action_trigger == 'cylinder',     # Trigger shape (point or cylinder)
                ))

                used_identifiers.append(obj.name)

            # Driveline / navmesh data
            elif obj.type != 'EMPTY' and (t == 'driveline_main' or t == 'driveline_additional' or t == 'navmesh'):
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                drivelines.append((
                    obj.name,                                   # ID
                    obj.data,                                   # Mesh data
                    driveline_type[t],                          # Driveline type
                    props.driveline_lower,                      # Lower driveline check
                    props.driveline_upper,                      # Upper driveline check
                    props.driveline_invisible,                  # Driveline not visible on
                    props.driveline_ignore,                     # Driveline AI ignore
                    props.driveline_direction == 'reverse',     # Driveline direction
                ))

                used_identifiers.append(obj.name)

            # Checkline / lapline data
            elif obj.type != 'EMPTY' and (t == 'checkline' or t == 'lapline'):
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                line_v1 = obj.matrix_world @ obj.data.vertices[0].co
                line_v2 = obj.matrix_world @ obj.data.vertices[1].co

                line = ((line_v1[0], line_v1[2], line_v1[1]),
                        (line_v2[0], line_v2[2], line_v2[1]))

                checklines.append((
                    obj.name,                   # ID
                    line,                       # Line data
                    props.checkline_index,      # Checkline index
                    props.checkline_activate,   # Activation index
                ))

                used_identifiers.append(obj.name)

            # Cannon
            elif obj.type != 'EMPTY' and t == 'cannon_start':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                if not props.cannon_end_trigger:
                    report({'WARNING'}, f"The cannon '{obj.name}' has no end defined and will be ignored!")
                    continue

                if not props.cannon_path:
                    report({'WARNING'}, f"The cannon '{obj.name}' has no curve defined and will be ignored!")
                    continue

                if len(obj.data.edges) != 1 or len(props.cannon_end_trigger.data.edges) != 1:
                    report({'WARNING'}, f"The cannon '{obj.name}' has invalid start or end lines and will be ignored!")
                    continue

                line_start_v1 = obj.matrix_world @ obj.data.vertices[0].co
                line_start_v2 = obj.matrix_world @ obj.data.vertices[1].co
                line_end_v1 = props.cannon_end_trigger.matrix_world @ props.cannon_end_trigger.data.vertices[1].co
                line_end_v2 = props.cannon_end_trigger.matrix_world @ props.cannon_end_trigger.data.vertices[1].co
                line_start = ((line_start_v1[0], line_start_v1[2], line_start_v1[1]),
                              (line_start_v2[0], line_start_v2[2], line_start_v2[1]))
                line_end = ((line_end_v1[0], line_end_v1[2], line_end_v1[1]),
                            (line_end_v2[0], line_end_v2[2], line_end_v2[1]))

                cannons.append((
                    obj.name,               # ID
                    props.cannon_path,      # Cannon path
                    line_start,             # Cannon start
                    line_end,               # Cannon end
                    props.cannon_speed,     # Cannon speed
                ))

                used_identifiers.append(obj.name)

            # Goal line data
            elif obj.type != 'EMPTY' and t == 'goal':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                line_v1 = obj.matrix_world @ obj.data.vertices[0].co
                line_v2 = obj.matrix_world @ obj.data.vertices[1].co

                line = ((line_v1[0], line_v1[2], line_v1[1]),
                        (line_v2[0], line_v2[2], line_v2[1]))

                goals.append((
                    obj.name,                   # ID
                    line,                       # Line data
                    props.goal_team == 'ally',  # Goal team (true: ally, false: enemy)
                ))

                used_identifiers.append(obj.name)

        elif obj.type == 'LIGHT' and hasattr(obj.data, 'stk'):
            # Categorize light
            props = obj.data.stk
            light = obj.data

            # Sun
            if light.type == 'SUN':
                # Skip if already a sun defined
                if sun:
                    report({'WARNING'}, f"The sun '{obj.name}' will be ignored, as the scene cannot contain multiple "
                           "suns!")
                    continue

                sun = (
                    stk_utils.object_get_transform(obj),    # Transform
                    light.color,                            # Sun diffuse color
                    props.sun_specular,                     # Sun specular color
                )

            # Light
            elif light.type == 'POINT':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                lights.append((
                    obj.name,                                   # ID
                    stk_utils.object_get_transform(obj),        # Transform
                    props.point_distance,                       # Light distance
                    light.energy if light.energy else 100.0,    # Light energy
                    tuple(light.color),                         # Light color
                    props.visible_if,                           # Scripting
                ))

                used_identifiers.append(obj.name)

        elif obj.type == 'CAMERA' and hasattr(obj.data, 'stk'):
            # Categorize light
            props = obj.data.stk
            camera = obj.data

            # If used as a STK camera
            if props.type != 'none':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                cameras.append((
                    obj.name,                               # ID
                    stk_utils.object_get_transform(obj),    # Transform
                    camera_type[props.type],                # Camera type
                    props.distance,                         # End-camera distance
                ))
        else:
            continue

    # Create and return scene collection
    return SceneCollection(
        lod_groups,
        np.array(track_objects, dtype=object),
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
        np.array(cannons, dtype=track_cannon),
        np.array(goals, dtype=track_goal),
        np.array(lights, dtype=track_light),
        np.array(cameras, dtype=track_camera),
        sun,
    )


def xml_lod_data(lod_groups: set, indent=1):
    if len(lod_groups) == 0:
        return []

    # Level-of-detail nodes
    node_lod = [f"{'  ' * indent}<!-- Level-of-detail groups -->", f"{'  ' * indent}<lod>"]
    indent += 1

    for lod_group in lod_groups:
        # LOD group
        if isinstance(lod_group, bpy.types.Collection):
            node_lod.append(f"{'  ' * indent}<group name=\"{lod_group.name}\">")
            indent += 1

            # Iterate the whole LOD collection
            for lod_model in lod_group.objects:
                model_props = lod_model.stk_track

                # Skip non-LOD models
                if model_props.type != 'lod_model':
                    continue

                # Gather data for this LOD model in the current group
                node_lod.append("{indent}<static-object model=\"{id}.spm\" lod_distance=\"{dist}\" "
                                "lod_group=\"{group}\" skeletal-animation=\"{anim}\"/>"
                                .format(
                                    indent='  ' * indent,
                                    id=model_props.name if len(model_props.name) > 0 else lod_model.name,
                                    dist=model_props.lod_distance,
                                    group=lod_group.name,
                                    anim='y' if lod_model.find_armature() else 'n'
                                ))

            indent -= 1
            node_lod.append(f"{'  ' * indent}</group>")

        # LOD standalone
        else:
            # 'lod_group' is not a collection but a standalone LOD object ('bpy.types.Object')
            model_props = lod_group.stk_track
            model_id = model_props.name if len(model_props.name) > 0 else lod_group.name
            model_group = f'{STANDALONE_LOD_PREFIX}{model_id}'
            model_skeletal = 'y' if lod_group.find_armature() else 'n'

            node_lod.append(f"    <group name=\"{model_group}\">")
            indent += 1

            # Use modifiers as LOD level
            if model_props.lod_modifiers:
                node_lod.append("{indent}<static-object model=\"{id}.spm\" lod_distance=\"{dist}\" "
                                "lod_group=\"{group}\" skeletal-animation=\"{anim}\"/>"
                                .format(
                                    indent='  ' * indent,
                                    id=model_id,
                                    dist=model_props.lod_modifiers_distance,
                                    group=model_group,
                                    anim=model_skeletal
                                ))
                node_lod.append("{indent}<static-object model=\"{id}_low.spm\" lod_distance=\"{dist}\" "
                                "lod_group=\"{group}\" skeletal-animation=\"{anim}\"/>"
                                .format(
                                    indent='  ' * indent,
                                    id=model_id,
                                    dist=model_props.lod_distance,
                                    group=model_group,
                                    anim=model_skeletal
                                ))

            # Single standalone
            else:
                node_lod.append("{indent}<static-object model=\"{id}.spm\" lod_distance=\"{dist}\" "
                                "lod_group=\"{group}\" skeletal-animation=\"{anim}\"/>"
                                .format(
                                    indent='  ' * indent,
                                    id=model_id,
                                    dist=model_props.lod_distance,
                                    group=model_group,
                                    anim=model_skeletal
                                ))

            indent -= 1
            node_lod.append(f"{'  ' * indent}</group>")

    indent -= 1
    node_lod.append(f"{'  ' * indent}</lod>")

    return node_lod


def xml_ipo_data(object: bpy.types.Object):
    pass


def xml_object_data(objects: np.ndarray, static=False, indent=1):
    if np.size(objects) == 0:
        return []

    nodes = []
    tag_name = None

    if static:
        tag_name = 'static-object'
    else:
        tag_name = 'object'

    # Iterate all objects
    for obj in objects:
        anim_texture = None
        ipo_data = None

        # ID and transform
        attributes = [f"id=\"{obj['object'].name}\"", stk_utils.transform_to_str(obj['transform'])]

        # Object type
        if obj['interaction'] == object_interaction['movable']:
            attributes.append("type=\"movable\"")
        elif obj['object'].animation_data:
            attributes.append("type=\"animation\"")
        else:
            attributes.append("type=\"static\"")

        # LOD instance
        is_lod = False

        if obj['lod']:
            attributes.append(f"lod_instance=\"y\" lod_group=\"{obj['lod'].name}\"")
            is_lod = True
        elif obj['lod_distance'] >= 0.0:
            attributes.append(f"lod_instance=\"y\" lod_group=\"{STANDALONE_LOD_PREFIX}{obj['id']}\"")
            is_lod = True
        else:
            # Skeletal animation
            anim = 'y' if obj['object'].find_armature() else 'n'
            attributes.append(f"model=\"{obj['id']}.spm\" skeletal-animation=\"{anim}\"")

        # Geometry level visibility
        if obj['visibility'] != object_geo_detail_level['off']:
            attributes.append(f"geometry-level=\"{obj['visibility']}\"")

        # Object interaction
        if obj['interaction'] == object_interaction['movable']:
            attributes.append("interaction=\"movable\"")
        elif obj['interaction'] == object_interaction['ghost']:
            attributes.append("interaction=\"ghost\"")
        elif obj['interaction'] == object_interaction['physics']:
            attributes.append("interaction=\"physics-only\"")
        elif obj['interaction'] == object_interaction['reset']:
            attributes.append("interaction=\"reset\" reset=\"y\"")
        elif obj['interaction'] == object_interaction['knock']:
            attributes.append("interaction=\"explode\" explode=\"y\"")
        elif obj['interaction'] == object_interaction['flatten']:
            attributes.append("interaction=\"flatten\" flatten=\"y\"")

        # Physics
        # Only define shape:
        # - if not LOD and not ghost or physics-only obj
        # - if LOD and movable (but then ignore exact collision detection)
        if not is_lod and obj['interaction'] != object_interaction['ghost'] and \
           obj['interaction'] != object_interaction['physics']:
            # Append shape
            if obj['shape'] == object_physics_shape['sphere']:
                attributes.append("shape=\"sphere\"")
            elif obj['shape'] == object_physics_shape['cylinder_x']:
                attributes.append("shape=\"cylinderX\"")
            elif obj['shape'] == object_physics_shape['cylinder_y']:
                attributes.append("shape=\"cylinderY\"")
            elif obj['shape'] == object_physics_shape['cylinder_z']:
                attributes.append("shape=\"cylinderZ\"")
            elif obj['shape'] == object_physics_shape['cone_x']:
                attributes.append("shape=\"coneX\"")
            elif obj['shape'] == object_physics_shape['cone_y']:
                attributes.append("shape=\"coneY\"")
            elif obj['shape'] == object_physics_shape['cone_z']:
                attributes.append("shape=\"coneZ\"")
            elif obj['shape'] == object_physics_shape['exact']:
                attributes.append("shape=\"exact\"")
            else:
                attributes.append("shape=\"box\"")

        elif is_lod and obj['interaction'] != object_interaction['movable']:
            # Append shape
            if obj['shape'] == object_physics_shape['sphere']:
                attributes.append("shape=\"sphere\"")
            elif obj['shape'] == object_physics_shape['cylinder_x']:
                attributes.append("shape=\"cylinderX\"")
            elif obj['shape'] == object_physics_shape['cylinder_y']:
                attributes.append("shape=\"cylinderY\"")
            elif obj['shape'] == object_physics_shape['cylinder_z']:
                attributes.append("shape=\"cylinderZ\"")
            elif obj['shape'] == object_physics_shape['cone_x']:
                attributes.append("shape=\"coneX\"")
            elif obj['shape'] == object_physics_shape['cone_y']:
                attributes.append("shape=\"coneY\"")
            elif obj['shape'] == object_physics_shape['cone_z']:
                attributes.append("shape=\"coneZ\"")
            else:
                attributes.append("shape=\"box\"")

        # Object flags
        if obj['flags'] & object_flags['driveable'] > 0:
            attributes.append("driveable=\"y\"")
        if obj['flags'] & object_flags['soccer_ball'] > 0:
            attributes.append("soccer_ball=\"y\"")
        if obj['flags'] & object_flags['glow'] > 0:
            attributes.append(f"glow=\"{stk_utils.color_to_str(obj['glow'])}\"")
        if obj['flags'] & object_flags['shadows'] == 0:
            attributes.append("shadow-pass=\"n\"")

        # Scripting
        if obj['visible_if'] and len(obj['visible_if']):
            attributes.append(f"if=\"{obj['visible_if']}\"")
        if obj['on_collision'] and len(obj['on_collision']):
            attributes.append(f"on-kart-collision=\"{obj['on_collision']}\"")

        # Custom XML
        if obj['custom_xml'] and len(obj['custom_xml']):
            attributes.append(obj['custom_xml'])

        # Animated texture (object specific)
        if obj['uv_animated']:
            image = stk_utils.get_main_texture_stk_material(obj['uv_animated'])
            anim_texture_attributes = [
                f"name=\"{obj['uv_animated'].name}.{'png' if image.file_format == 'PNG' else 'jpg'}\""
            ]

            if obj['uv_speed_dt'] >= 0.0:
                anim_texture_attributes.append(f"animByStep=\"y\" dt=\"{obj['uv_speed_dt']:.3f}\"")

            anim_texture_attributes.append(f"dx=\"{obj['uv_speed_u']:.5f}\"")
            anim_texture_attributes.append(f"dy=\"{obj['uv_speed_v']:.5f}\"")

            anim_texture = f"<animated-texture {' '.join(anim_texture_attributes)}/>"

        # Build object node
        if not anim_texture and not ipo_data:
            nodes.append(f"{'  ' * indent}<{tag_name} {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<{tag_name} {' '.join(attributes)}>")
            indent += 1

            # Animated texture as sub-node
            if anim_texture:
                nodes.append(f"{'  ' * indent}{anim_texture}")

            indent -= 1
            nodes.append(f"{'  ' * indent}</{tag_name}>")

    return nodes


def write_scene_file(stk_scene: stk_props.STKScenePropertyGroup, collection: SceneCollection, output_dir: str):
    path = os.path.join(output_dir, 'scene.xml')

    # Prepare LOD node data
    xml_lod = xml_lod_data(collection.lod_groups)

    # Prepare static track data
    xml_track = [
        "  <!-- Track model and static objects -->",
        f"  <track model=\"{stk_scene.identifier}_track.spm\" x=\"0\" y=\"0\" z=\"0\">",
        "\n".join(xml_object_data(collection.static_objects, True, 2)),
        "  </track>"
    ]

    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            "<scene>\n"
        ])

        f.write("\n".join(xml_lod))
        f.write("\n")
        f.write("\n".join(xml_track))

        # all the things...
        f.write("\n</scene>\n")
