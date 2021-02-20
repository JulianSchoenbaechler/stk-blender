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
import math
import os
import numpy as np
from . import stk_library_utils as lu
from . import stk_track_utils as tu
from . import stk_utils, stk_track


def xml_action_trigger_data(actions: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the node file for action triggers.

    Parameters
    ----------
    actions : np.ndarray
        An array of action trigger data that should be processed
    fps : float, optional
        The frames-per-second value the animation should run on, by default 25.0
    indent : int, optional
        The tab indent for writing the XML node, by default 1
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(actions) == 0:
        return []

    # Action trigger nodes
    nodes = [f"{'  ' * indent}<!-- action triggers -->"]

    for action in actions:
        # Type, identifier and transform
        attributes = [
            "type=\"action-trigger\"",
            f"id=\"{action['id']}\"",
            stk_utils.transform_to_str(action['transform'])
        ]

        # Trigger type (shape)
        if action['cylindrical']:
            attributes.append(
                f"trigger-type=\"cylinder\" radius=\"{action['distance']:.2f}\" height=\"{action['height']:.2f}\""
            )
        else:
            attributes.append(f"trigger-type=\"point\" distance=\"{action['distance']:.2f}\"")

        # Triggered object in library node
        if action['object']:
            # Reference to the object identifier (always its name, not filename identifier)
            attributes.append(f"triggered-object=\"{action['object'].name}\"")

        # Trigger action and re-enable timeout
        attributes.append(f"action=\"{action['action']}\"")
        attributes.append(f"reenable-timeout=\"{action['timeout']:.2f}\"")

        # Build action node
        if not action['animation']:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            # Set to default rotation mode as rotation does not matter for action triggers (point & cylinder)
            nodes.extend(stk_track.xml_ipo_data(action['id'], action['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</object>")

    return nodes


def xml_object_data(objects: np.ndarray, timeline_markers: bpy.types.TimelineMarkers, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for generic scene objects.
    This method is different to the one in 'stk_track' only be respecting specific timeline markers that control the
    animation flow of the library object.

    Parameters
    ----------
    objects : np.ndarray
        An array of object data that should be processed
    timeline_markers : bpy.types.TimelineMarkers
        The timeline markers of this scene
    fps : float, optional
        The frames-per-second value the animation should run on, by default 25.0
    indent : int, optional
        The tab indent for writing the XML node, by default 1
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(objects) == 0:
        return []

    nodes = []

    # Iterate all objects
    for obj in objects:
        anim_texture = None
        animation_data = stk_utils.object_is_ipo_animated(obj['object'])

        # ID and transform
        attributes = [f"id=\"{obj['object'].name}\"", stk_utils.transform_to_str(obj['transform'])]

        # Object type
        if obj['interaction'] == tu.object_interaction['movable']:
            attributes.append("type=\"movable\"")
        elif animation_data:
            attributes.append(f"type=\"animation\" fps=\"{fps:.2f}\"")
        else:
            attributes.append("type=\"static\"")

        # LOD instance
        is_lod = False

        if obj['lod']:
            attributes.append(f"lod_instance=\"y\" lod_group=\"{obj['lod'].name}\"")
            is_lod = True
        elif obj['lod_distance'] >= 0.0:
            attributes.append(f"lod_instance=\"y\" lod_group=\"{stk_track.STANDALONE_LOD_PREFIX}{obj['id']}\"")
            is_lod = True
        else:
            # Skeletal animation
            anim = 'y' if obj['object'].find_armature() else 'n'
            attributes.append(f"model=\"{obj['id']}.spm\" skeletal-animation=\"{anim}\"")

            # Check if skeletal animation is looped
            if stk_utils.is_skeletal_animation_looped(animation_data):
                attributes.append("looped=\"y\"")

        # Animation flow
        frame_start = []
        frame_end = []

        # Search for 'start' and 'end' timeline markers
        for marker in timeline_markers:
            if marker.name == 'start':
                frame_start.append(marker.frame)
            elif marker.name == 'end':
                frame_end.append(marker.frame)

        if len(frame_start) > 0 and len(frame_end) > 0:
            frame_start.sort()
            frame_end.sort()
            attributes.append(f"frame-start=\"{' '.join(map(str, frame_start))}\"")
            attributes.append(f"frame-end=\"{' '.join(map(str, frame_end))}\"")

        # Geometry level visibility
        if obj['visibility'] != tu.object_geo_detail_level['off']:
            attributes.append(f"geometry-level=\"{obj['visibility']}\"")

        # Object interaction
        if obj['interaction'] == tu.object_interaction['movable']:
            attributes.append(f"interaction=\"movable\" mass=\"{obj['mass']:.1f}\"")
        elif obj['interaction'] == tu.object_interaction['ghost']:
            attributes.append("interaction=\"ghost\"")
        elif obj['interaction'] == tu.object_interaction['physics']:
            attributes.append("interaction=\"physics-only\"")
        elif obj['interaction'] == tu.object_interaction['reset']:
            attributes.append("interaction=\"reset\" reset=\"y\"")
        elif obj['interaction'] == tu.object_interaction['knock']:
            attributes.append("interaction=\"explode\" explode=\"y\"")
        elif obj['interaction'] == tu.object_interaction['flatten']:
            attributes.append("interaction=\"flatten\" flatten=\"y\"")

        # Physics
        # Only define shape:
        # - if not LOD and not ghost or physics-only obj
        # - if LOD and movable (but then ignore exact collision detection)
        if not is_lod and obj['interaction'] != tu.object_interaction['ghost'] and \
           obj['interaction'] != tu.object_interaction['physics']:
            # Append shape
            if obj['shape'] == tu.object_physics_shape['sphere']:
                attributes.append("shape=\"sphere\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_x']:
                attributes.append("shape=\"cylinderX\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_y']:
                attributes.append("shape=\"cylinderY\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_z']:
                attributes.append("shape=\"cylinderZ\"")
            elif obj['shape'] == tu.object_physics_shape['cone_x']:
                attributes.append("shape=\"coneX\"")
            elif obj['shape'] == tu.object_physics_shape['cone_y']:
                attributes.append("shape=\"coneY\"")
            elif obj['shape'] == tu.object_physics_shape['cone_z']:
                attributes.append("shape=\"coneZ\"")
            elif obj['shape'] == tu.object_physics_shape['exact']:
                attributes.append("shape=\"exact\"")
            else:
                attributes.append("shape=\"box\"")

        elif is_lod and obj['interaction'] != tu.object_interaction['movable']:
            # Append shape
            if obj['shape'] == tu.object_physics_shape['sphere']:
                attributes.append("shape=\"sphere\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_x']:
                attributes.append("shape=\"cylinderX\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_y']:
                attributes.append("shape=\"cylinderY\"")
            elif obj['shape'] == tu.object_physics_shape['cylinder_z']:
                attributes.append("shape=\"cylinderZ\"")
            elif obj['shape'] == tu.object_physics_shape['cone_x']:
                attributes.append("shape=\"coneX\"")
            elif obj['shape'] == tu.object_physics_shape['cone_y']:
                attributes.append("shape=\"coneY\"")
            elif obj['shape'] == tu.object_physics_shape['cone_z']:
                attributes.append("shape=\"coneZ\"")
            else:
                attributes.append("shape=\"box\"")

        # Object flags
        if obj['flags'] & tu.object_flags['driveable'] > 0:
            attributes.append("driveable=\"y\"")
        if obj['flags'] & tu.object_flags['soccer_ball'] > 0:
            attributes.append("soccer_ball=\"y\"")
        if obj['flags'] & tu.object_flags['glow'] > 0:
            attributes.append(f"glow=\"{stk_utils.color_to_str(obj['glow'])}\"")
        if obj['flags'] & tu.object_flags['shadows'] == 0:
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
        if not anim_texture and not animation_data:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}>")
            indent += 1

            # Animated texture as sub-node
            if anim_texture:
                nodes.append(f"{'  ' * indent}{anim_texture}")

            # IPO animation
            nodes.extend(stk_track.xml_ipo_data(obj['id'], animation_data, obj['object'].rotation_mode, indent, report))

            indent -= 1
            nodes.append(f"{'  ' * indent}</object>")

    return nodes


def write_node_file(context: bpy.context, node: lu.LibraryNode, output_dir: str, report=print):
    """Writes the node.xml file for the SuperTuxKart library node to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    node : lu.LibraryNode tuple
        A library node tuple containing all the gathered scene data staged for export
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    path = os.path.join(output_dir, 'node.xml')

    # Prepare LOD node data
    xml_lod = stk_track.xml_lod_data(node.lod_groups, True)

    # Prepare dynamic objects
    xml_objects = ["  <!-- node objects -->"]
    xml_objects.extend(xml_object_data(node.objects, context.scene.timeline_markers, node.fps, 1, report))

    # Prepare billboards
    xml_billboards = stk_track.xml_billboard_data(node.billboards, node.fps, 1, report)

    # Prepare action triggers
    xml_action_triggers = xml_action_trigger_data(node.action_triggers, node.fps, 1, report)

    # Prepare sfx emitters
    xml_sfx = stk_track.xml_sfx_data(node.audio_sources, node.fps, 1, report)

    # Prepare particle emitters
    xml_particles = stk_track.xml_particles_data(node.particles, node.fps, 1, report)

    # Prepare dynamic lights
    xml_lights = stk_track.xml_lights_data(node.lights, node.fps, 1)

    # Write scene file
    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- node.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
            "<scene>\n"
        ])

        if xml_lod:
            f.write("\n".join(xml_lod))
            f.write("\n")

        if xml_objects:
            f.write("\n".join(xml_objects))
            f.write("\n")

        if xml_billboards:
            f.write("\n".join(xml_billboards))
            f.write("\n")

        if xml_action_triggers:
            f.write("\n".join(xml_action_triggers))
            f.write("\n")

        if xml_sfx:
            f.write("\n".join(xml_sfx))
            f.write("\n")

        if xml_particles:
            f.write("\n".join(xml_particles))
            f.write("\n")

        if xml_lights:
            f.write("\n".join(xml_lights))
            f.write("\n")

        # all the things...
        f.write("</scene>\n")
