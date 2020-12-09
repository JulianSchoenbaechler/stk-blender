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
from . import stk_track_utils as tu
from . import stk_utils, stk_props

STANDALONE_LOD_PREFIX = '_standalone_'


def xml_lod_data(lod_groups: set, indent=1):
    """Creates an iterable of strings that represent the writable XML node for the level-of-detail specification of the
    scene XML file.

    Parameters
    ----------
    lod_groups : set
        A set containing Blender collections and/or objects that define a LOD group or singleton
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
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


def xml_ipo_data(anim: bpy.types.AnimData, indent=2):
    """Creates an iterable of strings that represent the writable XML node for an object's IPO curve animation data
    specification of the scene XML file.

    Parameters
    ----------
    anim : bpy.types.AnimData
        The animation data to be processed
    indent : int, optional
        The tab indent for writing the XML node, by default 2

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """


def xml_object_data(objects: np.ndarray, static=False, indent=1):
    """Creates an iterable of strings that represent the writable XML node for generic scene objects (including static)
    of the scene XML file.

    Parameters
    ----------
    objects : np.ndarray
        An array of object data that should be processed
    static : bool, optional
        True if the objects should be labeled as static, by default False
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
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
        if obj['interaction'] == tu.object_interaction['movable']:
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
        if obj['visibility'] != tu.object_geo_detail_level['off']:
            attributes.append(f"geometry-level=\"{obj['visibility']}\"")

        # Object interaction
        if obj['interaction'] == tu.object_interaction['movable']:
            attributes.append("interaction=\"movable\"")
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


def write_scene_file(stk_scene: stk_props.STKScenePropertyGroup, collection: tu.SceneCollection, output_dir: str):
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
