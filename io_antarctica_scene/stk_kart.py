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
from . import stk_track_utils as tu
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

    frames = f"\n{'  ' * indent}            ".join(attributes)
    return f"{'  ' * indent}<animations {frames}/>\n"


def collect_and_write_kart_file(context: bpy.context, output_dir: str, report=print):
    """Collect kart specific scene data and writes the kart.xml file for the SuperTuxKart track to disk.
    This method of parsing the Blender scene is straightforward and simple. Much overhead is not really necessary as
    kart data is (for historic reasons) fundamentally different. So there is no benefit in using e.g. NumPy structures.
    The scenes are not that complex (it's a kart after all) and code from track/library export cannot really be reused.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    stk_scene = stk_utils.get_stk_context(context, 'scene')
    path = os.path.join(output_dir, 'kart.xml')

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

        if (obj.type == 'MESH' or obj.type == 'EMPTY') and hasattr(obj, 'stk_kart'):
            # Categorize objects
            props = obj.stk_kart
            t = props.type

            # Library object proxies
            if obj.proxy:
                continue

    # Special cases for group names
    if stk_scene.category == 'add-ons':
        group_name = 'Add-Ons'
    elif stk_scene.category == 'wip':
        group_name = 'wip-kart'
    else:
        group_name = stk_scene.category

    xml_animations = xml_animation_data(context.scene.timeline_markers,
                                        context.scene.render.fps / context.scene.render.fps_base)

    # Write scene file
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
        f.write(xml_animations)

        # Engine sound
        f.write(f"  <sounds engine=\"{stk_scene.sfx_engine}\"/>\n")

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
