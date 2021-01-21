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
    xml_objects.extend(stk_track.xml_object_data(node.objects, False, node.fps, 1, report))

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
