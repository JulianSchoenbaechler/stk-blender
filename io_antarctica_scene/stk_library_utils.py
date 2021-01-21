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
import bmesh
import collections
import mathutils
import os
import numpy as np
from . import stk_utils, stk_props, stk_track_utils

LibraryNode = collections.namedtuple('LibraryNode', [
    'lod_groups',           # set of bpy.types.Collection (LOD group) and/or bpy.types.Object (LOD standalones)
    'objects',              # NumPy array of library object data (dtype=track_object)
    'billboards',           # NumPy array of billboards (dtype=track_billboard)
    'particles',            # NumPy array of particle emitters (dtype=track_particles)
    'audio_sources',        # NumPy array of audio sources (dtype=track_audio)
    'action_triggers',      # NumPy array of action triggers (dtype=library_action)
    'lights',               # NumPy array of point lights (dtype=track_light)
    'fps',                  # float defining animation speed
])

library_action = np.dtype([
    ('id', 'U127'),
    ('transform', stk_utils.transform),
    ('animation', 'O'),
    ('action', 'U127'),
    ('distance', np.float32),
    ('height', np.float32),
    ('timeout', np.float32),
    ('object', 'O'),
    ('cylindrical', np.bool_),
])


def collect_node(context: bpy.context, report=print):
    """Collect all relevant objects from the Blender scene relevant for library node exporting. The objects get grouped
    together into NumPy arrays which is more cumbersome, but provides better iteration speeds on larger scenes.
    Precosciously filtering and grouping objects reduces the iteration amount necessary for writing track data. All
    relevant data for STK is already collected in this first iteration.
    It should be noted that processing data into NumPy arrays for small scenes like library nodes is slower than
    processing the references directly (as of NumPy's overhead). However for consistency reasons we will keep this
    pattern, and it further allows us to recycle certain functionality of the track export utilities.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    report : callable, optional
        A function used for reporting warnings or errors for this operation, by default 'print()'

    Returns
    -------
    LibraryNode
        A (named) tuple that describes the library node; it consists of all relevant data (or references) necessary for
        the export
    """
    used_identifiers = []
    lod_groups = set()
    node_objects = []
    billboards = []
    particles = []
    audio_sources = []
    action_triggers = []
    lights = []

    # Gather all objects from enabled collections
    # If collections are hidden in viewport or render, all their objects should get ignored
    objects = []

    for col in stk_utils.iter_enabled_collections(context.scene.collection):
        objects.extend(col.objects)

    # Categorize all objects that need to get exported
    for obj in objects:
        # Ignore disabled or direct library references (only accept proxies)
        if obj.hide_viewport or obj.hide_render:
            continue

        if (obj.type == 'MESH' or obj.type == 'EMPTY') and hasattr(obj, 'stk_library'):
            # Categorize objects
            props = obj.stk_library
            t = props.type

            # Library object proxies
            if obj.proxy:
                continue

            # Object (including LOD) with specified properties
            elif obj.type != 'EMPTY' and (t == 'object' or t == 'lod_instance' or t == 'lod_standalone'):
                # Name identifier
                staged = [props.name if len(props.name) > 0 else obj.name]

                # Skip if already an object with this identifier
                if staged[0] in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

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
                    staged.append(stk_track_utils.object_geo_detail_level[props.visibility_detail])
                else:
                    staged.append(stk_track_utils.object_geo_detail_level['off'])

                # Object interaction and physics shape
                staged.append(stk_track_utils.object_interaction[props.interaction])
                staged.append(stk_track_utils.object_physics_shape[props.shape])

                # Object flags
                flags = stk_track_utils.object_flags['none']
                if props.interaction == 'static' and props.driveable:
                    flags |= stk_track_utils.object_flags['driveable']
                if props.interaction == 'movable' and props.soccer_ball:
                    flags |= stk_track_utils.object_flags['soccer_ball']
                if props.glow:
                    flags |= stk_track_utils.object_flags['glow']
                if props.shadows:
                    flags |= stk_track_utils.object_flags['shadows']
                staged.append(flags)
                staged.append(props.mass)
                staged.append(tuple(props.glow_color))

                # Scripting and output related
                staged.append(props.visible_if)
                staged.append(props.on_kart_collision)
                staged.append(props.custom_xml)

                node_objects.append(tuple(staged))
                used_identifiers.append(staged[0])

            # Billboards
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
                if len(obj.material_slots) == 0:
                    report({'WARNING'}, f"The billboard '{obj.name}' has no material assigned!")
                    continue
                else:
                    material = obj.material_slots[obj.data.polygons[0].material_index].material

                    if not stk_utils.is_stk_material(material.node_tree):
                        report({'WARNING'}, f"The material of the billboard '{obj.name}' is not supported!")
                        continue

                normal = mathutils.Vector((0.0, 0.0, 0.0))

                for i in range(0, 4):
                    normal += obj.data.vertices[i].normal

                # Check if billboard faces upwards (angle between normal and up-vector less than 45 degree)
                if normal.angle((0.0, 0.0, 1.0)) < 0.7853981634 or normal.angle((0.0, 0.0, -1.0)) < 0.7853981634:
                    size = (obj.dimensions[0], obj.dimensions[1])
                elif normal.angle((0.0, 1.0, 0.0)) < 0.7853981634 or normal.angle((0.0, -1.0, 0.0)) < 0.7853981634:
                    size = (obj.dimensions[0], obj.dimensions[2])
                else:
                    size = (obj.dimensions[1], obj.dimensions[2])

                billboards.append((
                    obj.name,                                           # ID
                    stk_utils.object_get_transform(obj),                # Transform
                    stk_utils.object_is_ipo_animated(obj),              # Get IPO animation
                    material,                                           # Material
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
                    stk_utils.object_is_ipo_animated(obj),  # Get IPO animation
                    props.particles,                        # Particles file name
                    props.particles_distance,               # Particles clip distance
                    props.particles_emit,                   # Particles auto-emit
                    '',                                     # Particles cutscene condition
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
                    stk_utils.object_is_ipo_animated(obj),                      # Get IPO animation
                    props.sfx,                                                  # Sound file
                    props.sfx_volume,                                           # Sound volume
                    props.sfx_rolloff,                                          # Sound rolloff
                    props.sfx_distance,                                         # Sound hearing distance
                    props.sfx_trigger_distance if props.sfx_trigger else -1.0,  # Sound trigger distance
                    '',                                                         # Sound cutscene condition
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
                    stk_utils.object_is_ipo_animated(obj),  # Get IPO animation
                    props.action,                           # Action call
                    props.action_distance,                  # Trigger distance (radius)
                    props.action_height,                    # Trigger height
                    props.action_timeout,                   # Action re-enable timeout
                    props.action_object,                    # Trigger object
                    props.action_trigger == 'cylinder',     # Trigger shape (point or cylinder)
                ))

                used_identifiers.append(obj.name)

        elif obj.type == 'LIGHT' and hasattr(obj.data, 'stk'):
            # Categorize light
            props = obj.data.stk
            light = obj.data

            # Light
            if light.type == 'POINT':
                # Skip if already an object with this identifier
                if obj.name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{obj.name}' is already staged for export and "
                           "will be ignored! Check if different objects have the same name identifier.")
                    continue

                lights.append((
                    obj.name,                                   # ID
                    stk_utils.object_get_transform(obj),        # Transform
                    stk_utils.object_is_ipo_animated(obj),      # Get IPO animation
                    props.point_distance,                       # Light distance
                    light.energy if light.energy else 100.0,    # Light energy
                    tuple(light.color),                         # Light color
                    props.visible_if,                           # Scripting
                ))

                used_identifiers.append(obj.name)

        else:
            continue

    # Create and return library node
    return LibraryNode(
        lod_groups=lod_groups,
        objects=np.array(node_objects, dtype=stk_track_utils.track_object),
        billboards=np.array(billboards, dtype=stk_track_utils.track_billboard),
        particles=np.array(particles, dtype=stk_track_utils.track_particles),
        audio_sources=np.array(audio_sources, dtype=stk_track_utils.track_audio),
        action_triggers=np.array(action_triggers, dtype=library_action),
        lights=np.array(lights, dtype=stk_track_utils.track_light),
        fps=context.scene.render.fps / context.scene.render.fps_base
    )
