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


def xml_sfx_data(stk_scene: stk_props.STKScenePropertyGroup, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing the kart sfx.

    Parameters
    ----------
    stk_scene : stk_props.STKScenePropertyGroup
        The STK scene properties used for accessing sfx data
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    node = []

    if stk_scene.sfx_skid == 'custom':
        # Skid sfx audio settings
        attributes = [f"name=\"{stk_scene.sfx_skid_file}\""]
        attributes.append(f"volume=\"{stk_scene.sfx_volume:.2f}\"")
        attributes.append(f"rolloff=\"{stk_scene.sfx_rolloff:.2f}\"")
        attributes.append(f"max_dist=\"{stk_scene.sfx_distance:.2f}\"")

        # Add skid to sound node
        node.append(f"{'  ' * indent}<sounds engine=\"{stk_scene.sfx_engine}\">")
        node.append(f"{'  ' * (indent + 1)}<skid {' '.join(attributes)}/>")
        node.append(f"{'  ' * indent}</sounds>")
    else:
        node.append(f"{'  ' * indent}<sounds engine=\"{stk_scene.sfx_engine}\"/>")

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


def xml_speed_weighted_data(objects: list, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing speed-weighted objects of the
    kart.

    Parameters
    ----------
    objects : list of ku.SpeedWeighted
        A list of speed-weighted objects
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if not objects:
        return []

    # Build XML node
    node = [f"{'  ' * indent}<speed-weighted-objects>"]
    indent += 1

    # Speed-weighted object data
    for sw in objects:
        transform = stk_utils.object_get_transform(sw.object)
        attributes = [stk_utils.btransform_to_str(transform, ('position', 'rotation', 'scale'))]

        if sw.object.parent and sw.object.parent_type == 'BONE':
            attributes.append(f"bone=\"{sw.object.parent_bone}\"")

        attributes.append(f"model=\"{sw.name}.spm\"\n")
        attributes.append(f"{'  ' * indent}       strength-factor=\"{sw.strength:.2f}\"")
        attributes.append(f"speed-factor=\"{sw.speed:.2f}\"")
        attributes.append(f"texture-speed-x=\"{sw.uv_speed_u:.3f}\"")
        attributes.append(f"texture-speed-y=\"{sw.uv_speed_v:.3f}\"")

        node.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")

    indent -= 1
    node.append(f"{'  ' * indent}</speed-weighted-objects>")

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


def xml_headlights_data(objects: list, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing headlight objects of the kart.

    Parameters
    ----------
    objects : list of ku.Instanced
        A list of instanced objects
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if not objects:
        return []

    # Build XML node
    node = [f"{'  ' * indent}<headlights>"]
    indent += 1

    # Instanced object data
    for i in objects:
        transform = stk_utils.object_get_transform(i.object)
        attributes = [stk_utils.btransform_to_str(transform, ('position', 'rotation', 'scale'))]

        if i.object.parent and i.object.parent_type == 'BONE':
            attributes.append(f"bone=\"{i.object.parent_bone}\"")

        attributes.append(f"model=\"{i.name}.spm\"")

        node.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")

    indent -= 1
    node.append(f"{'  ' * indent}</headlights>")

    return node


def xml_hat_data(obj: bpy.types.Object, indent=1):
    """Creates an iterable of strings that represent the writable XML node describing the hat position of the kart.

    Parameters
    ----------
    obj : bpy.types.Object
        The hat positioner object
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if not obj:
        return []

    transform = stk_utils.object_get_transform(obj)
    attributes = [stk_utils.btransform_to_str(transform, ('position', 'rotation', 'scale'))]

    if obj.parent and obj.parent_type == 'BONE':
        attributes.append(f"bone=\"{obj.parent_bone}\"")

    # Build XML node
    return [f"{'  ' * indent}<hat {' '.join(attributes)}/>"]


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

    # Highlight color
    # For some freakin reason the RGB values in kart exports are float-ranges from 0-1. That's nice, but why the hell
    # are tracks and library objects not handled the same way? We need to serialize to byte-range in Blender and
    # deserialize in STKs codebase back to 0-1. Only because someone thought that's great.
    color = stk_scene.highlight_color

    # Prepare animations
    xml_animations = xml_animation_data(context.scene.timeline_markers,
                                        context.scene.render.fps / context.scene.render.fps_base)

    # Prepare sounds
    xml_sfx = xml_sfx_data(stk_scene)

    # Prepare wheels
    xml_wheels = xml_wheel_data(collection.wheels)

    # Prepare speed-weighted objects
    xml_speed_weighted = xml_speed_weighted_data(collection.speed_weighted)

    # Prepare nitro emitters
    xml_nitro_emitters = xml_nitro_emitter_data(collection.nitro_emitters)

    # Prepare headlight objects
    xml_headlights = xml_headlights_data(collection.headlights)

    # Prepare animations
    xml_hat = xml_hat_data(collection.hat)

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
        f.write(f"\n      rgb                     = \"{color.r:.2f} {color.g:.2f} {color.b:.2f}\"")
        f.write(f"\n      model-file              = \"{stk_scene.identifier}.spm\"")

        if stk_scene.icon:
            f.write(f"\n      icon-file               = \"{os.path.basename(stk_scene.icon.filepath_raw)}\"")

        if stk_scene.icon_minimap:
            f.write(f"\n      minimap-icon-file       = \"{os.path.basename(stk_scene.icon_minimap.filepath_raw)}\"")

        if stk_scene.shadow:
            f.write(f"\n      shadow-file             = \"{os.path.basename(stk_scene.shadow.filepath_raw)}\"")

        f.write(">\n")

        # Maximum lean formula
        if stk_scene.lean:
            f.write(f"  <lean max=\"{stk_scene.lean_max}\"/>\n")

        # Animation tree
        if xml_animations:
            f.write("\n".join(xml_animations))
            f.write("\n")

        # Engine and skid sounds
        f.write("\n".join(xml_sfx))
        f.write("\n")

        # Exhaust particles
        f.write(f"  <exhaust file=\"{stk_scene.exhaust_particles if stk_scene.exhaust else 'kart_exhaust.xml'}\"/>\n")

        # Wheels
        f.write("\n".join(xml_wheels))
        f.write("\n")

        # Speed-weighted objects
        if xml_speed_weighted:
            f.write("\n".join(xml_speed_weighted))
            f.write("\n")

        # Nitro emitters
        if xml_nitro_emitters:
            f.write("\n".join(xml_nitro_emitters))
            f.write("\n")

        # Headlight objects
        if xml_headlights:
            f.write("\n".join(xml_headlights))
            f.write("\n")

        # Hat position
        if xml_hat:
            f.write("\n".join(xml_hat))
            f.write("\n")

        f.write("</kart>\n")
