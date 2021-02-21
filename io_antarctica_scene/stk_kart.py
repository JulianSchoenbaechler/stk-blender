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
import os
import numpy as np
from . import stk_kart_utils as ku
from . import stk_props, stk_shaders, stk_utils

ANIM_IDENTIFIERS = [
    'straight', 'right', 'left',
    'start-winning', 'start-winning-loop', 'end-winning', 'end-winning-straight',
    'start-losing', 'start-losing-loop', 'end-losing', 'end-losing-straight',
    'start-explosion', 'end-explosion',
    'start-jump', 'start-jump-loop', 'end-jump',
    'backpedal', 'backpedal-right', 'backpedal-left',
    'selection-start', 'selection-end'
]

WHEEL_ORDER = [
    'front-left', 'front-right',
    'rear-left', 'rear-right'
]


def xml_animation_data(timeline_markers: bpy.types.TimelineMarkers, fps=25.0, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing the kart animations.

    Parameters
    ----------
    timeline_markers : bpy.types.TimelineMarkers
        The timeline markers of this scene
    fps : float, optional
        The frames-per-second value the animation should run on, by default 25.0
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    attributes = [f"speed = \"{fps:.1f}\""]

    # Collect markers
    for marker in timeline_markers:
        if marker.name in ANIM_IDENTIFIERS:
            attributes.append(f"{marker.name.ljust(22)}= \"{marker.frame}\"")

    # No animations
    if len(attributes) == 1:
        return []

    # Build XML node
    node = [f"{'  ' * indent}<animations {attributes.pop(0)}"]
    node.extend([f"{'  ' * indent}            {attr}" for attr in attributes])
    node[len(node) - 1] += "/>"

    return node


def xml_wheel_data(wheels: list, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing the kart wheels.

    Parameters
    ----------
    wheels : list
        A list with exactly 4 objects
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if len(wheels) != 4:
        return []

    ordered = {}

    # Order wheels
    for wheel in wheels:
        pos = wheel.location

        if pos.x < 0.0:  # left
            if pos.y > 0.0:  # front
                ordered[WHEEL_ORDER[0]] = wheel
            else:  # rear
                ordered[WHEEL_ORDER[2]] = wheel
        else:  # right
            if pos.y > 0.0:  # front
                ordered[WHEEL_ORDER[1]] = wheel
            else:  # rear
                ordered[WHEEL_ORDER[3]] = wheel

    # Build XML node
    node = [f"{'  ' * indent}<wheels>"]
    indent += 1

    for n in WHEEL_ORDER:
        transform = stk_utils.object_get_transform(ordered[n])
        node.append("{indent}<{name} {position} {model}/>".format(
            indent='  ' * indent, name=n,
            position=stk_utils.btransform_to_xyz_str(transform, 'position'),
            model=f'model="wheel-{n}.spm"'
        ))

    indent -= 1
    node.append(f"{'  ' * indent}</wheels>")

    return node


def xml_nitro_emitter_data(emitters: list, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing the kart nitro emitters.

    Parameters
    ----------
    emitters : list
        A list of object transforms (does not contain more than 2 items)
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if not emitters:
        return []

    if len(emitters) == 1:
        emitters.append(emitters[0])

    # Build XML node
    node = [f"{'  ' * indent}<nitro-emitter>"]
    indent += 1
    node.append(f"{'  ' * indent}<nitro-emitter-a {stk_utils.btransform_to_xyz_str(emitters[0], 'position')}/>")
    node.append(f"{'  ' * indent}<nitro-emitter-b {stk_utils.btransform_to_xyz_str(emitters[1], 'position')}/>")
    indent -= 1
    node.append(f"{'  ' * indent}</nitro-emitter>")

    return node


def write_kart_file(context: bpy.context, collection: ku.SceneCollection, output_dir: str, report=print):
    """Writes the kart.xml file for the SuperTuxKart kart to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    collection : ku.SceneCollection tuple
        A scene collection tuple containing all the gathered scene data staged for export
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    stk_scene = stk_utils.get_stk_context(context, 'scene')
    path = os.path.join(output_dir, 'kart.xml')
    origin_frame = context.scene.timeline_markers.get('straight')

    # Set kart to initial transformation state (straight, no steering)
    if origin_frame:
        context.scene.frame_set(origin_frame.frame)
    else:
        context.scene.frame_set(context.scene.frame_start)

    # Special cases for group names
    if stk_scene.category == 'add-ons':
        group_name = 'Add-Ons'
    elif stk_scene.category == 'wip':
        group_name = 'wip-kart'
    else:
        group_name = stk_scene.category

    # Prepare animations
    xml_animations = xml_animation_data(context.scene.timeline_markers,
                                        context.scene.render.fps / context.scene.render.fps_base)

    # Prepare animations
    xml_wheels = xml_wheel_data(collection.wheels)

    # Prepare animations
    xml_nitro_emitters = xml_nitro_emitter_data(collection.nitro_emitters)

    # Write kart file
    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- kart.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
        ])

        # Meta information
        f.write(f"<kart name                    = \"{stk_scene.name}\"")
        f.write(f"\n      groups                  = \"{group_name}\"")
        f.write(f"\n      version                 = \"{stk_utils.KART_FILE_FORMAT_VERSION}\"")
        f.write(f"\n      type                    = \"{stk_scene.kart_type}\"")
        f.write(f"\n      rgb                     = \"{stk_utils.bcolor_to_str(stk_scene.highlight_color)}\"")
        f.write(f"\n      model-file              = \"{stk_scene.identifier}.spm\"")

        if stk_scene.icon:
            f.write(f"\n      icon-file               = \"{os.path.basename(stk_scene.icon.filepath_raw)}\"")

        if stk_scene.icon_minimap:
            f.write(f"\n      minimap-icon-file       = \"{os.path.basename(stk_scene.icon_minimap.filepath_raw)}\"")

        if stk_scene.shadow:
            f.write(f"\n      shadow-file             = \"{os.path.basename(stk_scene.shadow.filepath_raw)}\"")

        f.write(">\n")

        # Animation tree
        f.write("\n".join(xml_animations))
        f.write("\n")

        # Engine sound
        f.write(f"  <sounds engine=\"{stk_scene.sfx_engine}\"/>\n")

        # Wheels
        f.write("\n".join(xml_wheels))
        f.write("\n")

        # Nitro emitters
        f.write("\n".join(xml_nitro_emitters))
        f.write("\n")

        f.write("</kart>\n")

        # Meta information
        #f.write(f"<track name                    = \"{stk_scene.name}\"")
        #f.write(f"\n       groups                  = \"{group_name}\"")
        #f.write(f"\n       version                 = \"{stk_utils.FILE_FORMAT_VERSION}\"")
        #f.write(f"\n       designer                = \"{str_sanitize(stk_scene.designer)}\"")
#
        # if stk_scene.screenshot:
        #    f.write(f"\n       screenshot              = \"{os.path.basename(stk_scene.screenshot.filepath_raw)}\"")
#
        # if stk_scene.music:
        #    f.write(f"\n       music                   = \"{stk_scene.music}\"")
#
        # Track type specific
        # if stk_scene.track_type == 'arena':
        #    f.write(f"\n       arena                   = \"y\"")
        #    f.write(f"\n       ctf                     = \"{'y' if stk_scene.ctf_active else 'n'}\"")
#
        #f.write(f"\n       soccer                  = \"{'y' if stk_scene.track_type == 'soccer' else 'n'}\"")
        #f.write(f"\n       cutscene                = \"{'y' if stk_scene.track_type == 'cutscene' else 'n'}\"")
        #f.write(f"\n       internal                = \"{'y' if stk_scene.track_type == 'cutscene' else 'n'}\"")
#
        # if stk_scene.track_type == 'race':
        #    f.write(f"\n       reverse                 = \"{'y' if stk_scene.reverse else 'n'}\"")
        #    f.write(f"\n       default-number-of-laps  = \"{stk_scene.lap_count}\"")
#
        # General track properties
        #f.write(f"\n       smooth-normals          = \"{'y' if stk_scene.smooth_normals else 'n'}\"")
        #f.write(f"\n       auto-rescue             = \"{'y' if stk_scene.auto_reset else 'n'}\"")
        #f.write(f"\n       shadows                 = \"{'y' if stk_scene.shadows else 'n'}\"")
        #f.write(f"\n       is-during-day           = \"{'y' if stk_scene.daytime == 'day' else 'n'}\"")
        # f.write("/>\n")
