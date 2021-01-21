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

STANDALONE_LOD_PREFIX = '_standalone_'


def xml_lod_data(lod_groups: set, is_library=False, indent=1):
    """Creates an iterable of strings that represent the writable XML node for the level-of-detail specification of the
    scene file.

    Parameters
    ----------
    lod_groups : set
        A set containing Blender collections and/or objects that define a LOD group or singleton
    is_library : bool
        Indicator if this STK scene is a library node
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
    node_lod = [f"{'  ' * indent}<!-- level-of-detail groups -->", f"{'  ' * indent}<lod>"]
    indent += 1

    for lod_group in lod_groups:
        # LOD group
        if isinstance(lod_group, bpy.types.Collection):
            node_lod.append(f"{'  ' * indent}<group name=\"{lod_group.name}\">")
            indent += 1

            # Iterate the whole LOD collection
            for lod_model in lod_group.objects:
                model_props = lod_model.stk_track if not is_library else lod_model.stk_library

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
            model_props = lod_group.stk_track if not is_library else lod_group.stk_library
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


def xml_curve_data(curve: bpy.types.Curve, space: mathutils.Matrix, extend='const', speed=50.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML node of the scene file for a 3d curve (e.g.
    cannon) data specification.

    Parameters
    ----------
    curve : bpy.types.Curve
        The curve data to be processed
    space : mathutils.Matrix
        The transformation matrix that should be applied to the curve data
    extend : str
        The curve extrapolation; 'const' or 'cyclic'
    speed : float
        The speed value the curve will be processed/evaluated
    indent : int, optional
        The tab indent for writing the XML node, by default 2
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if len(curve.splines) > 1:
        report({'WARNING'}, f"The curve '{curve.name}' contains multiple splines! Only one will be considered.")

    if curve.splines[0].type != 'BEZIER':
        report({'ERROR'}, f"The curve '{curve.name}' must use an underlying spline of type bezier.")
        return []

    points = []

    for pt in curve.splines[0].bezier_points:
        points.append((
            stk_utils.translation_stk_axis_conversion(pt.co, space),            # c
            stk_utils.translation_stk_axis_conversion(pt.handle_left, space),   # h1
            stk_utils.translation_stk_axis_conversion(pt.handle_right, space)   # h2
        ))

    # As we do not operate on this array this is not really necessary, we just keep consistency
    # The performance hit of the NumPy overhead is tolerable for this case though
    packed_pt = np.array(points, dtype=stk_utils.keyframe3d)

    nodes = [f"{'  ' * indent}<curve channel=\"LocXYZ\" interpolation=\"bezier\" extend=\"{extend}\" "
             f"speed=\"{speed:.1f}\">"]
    indent += 1

    for pt in packed_pt:
        nodes.append(f"{'  ' * indent}<p c=\"{pt['c']['x']:.2f} {pt['c']['y']:.2f} {pt['c']['z']:.2f}\" "
                     f"h1=\"{pt['h1']['x']:.2f} {pt['h1']['y']:.2f} {pt['h1']['z']:.2f}\" "
                     f"h2=\"{pt['h2']['x']:.2f} {pt['h2']['y']:.2f} {pt['h2']['z']:.2f}\"/>")

    indent -= 1
    nodes.append(f"{'  ' * indent}</curve>")

    return nodes


def xml_ipo_data(obj_id: str, animation_data: bpy.types.AnimData, rotation_mode: str, indent=2, report=print):
    """Creates an iterable of strings that represent the writable XML node of the scene file for an object's IPO curve
    animation data specification.

    Parameters
    ----------
    obj_id : str
        The object identifier the animation data belongs to
    animation_data : bpy.types.AnimData
        The animation data to be processed
    rotation_mode : str
        The rotation mode that is used for the animated rotation of the object
    indent : int, optional
        The tab indent for writing the XML node, by default 2
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if not animation_data or not animation_data.action:
        return []

    # Check rotation mode of the animated object, report on incorrect selection
    # STK does the axis order conversion for us, so make sure the order of Euler axes are XYZ (not XZY)
    # https://github.com/supertuxkart/stk-code/blob/82b7ab/src/animations/three_d_animation.cpp#L98-L101
    if rotation_mode == 'QUATERNION' or rotation_mode == 'AXIS_ANGLE':
        report({'ERROR'}, f"The rotation mode of the object with the identifier '{obj_id}' is not supported in "
               " SuperTuxKart! The animation curves of the rotation of this object can not be exported correctly. "
               "Please use the 'XYZ Euler' rotation mode for animated objects.")
    elif rotation_mode != 'XYZ':
        report({'WARNING'}, f"The rotation order of the object with the identifier '{obj_id}' is incorrect! "
               f"'XYZ Euler' should be used, but '{rotation_mode} Euler' is selected. The animation of this object "
               " will likely look different in-game.")

    axes = ('X', 'Z', 'Y')  # Swap Y and Z axis
    node_curves = []

    for curve in animation_data.action.fcurves:
        factor = 1

        if curve.data_path == 'location':
            channel = f'Loc{axes[curve.array_index]}'
        elif curve.data_path == 'rotation_euler':
            channel = f'Rot{axes[curve.array_index]}'
            factor = -57.2957795131  # rad2deg
        elif curve.data_path == 'scale':
            channel = f'Scale{axes[curve.array_index]}'
        else:
            # Do not report on armature bone curves
            if 'pose.bones' not in curve.data_path:
                report({'WARNING'}, f"Unknown IPO curve type '{curve.data_path}' (animation)!")
            continue

        # Extrapolation of the curve (constant or cyclic)
        extrapolation = 'const' if len([m for m in curve.modifiers if m.type == 'CYCLES']) == 0 else 'cyclic'
        interpolation = 'const'
        changed_interpolation = False
        keyframes = []

        # Gather keyframe points of the curve (packing)
        for i, kp in enumerate(curve.keyframe_points):
            if kp.interpolation != 'CONSTANT' and kp.interpolation != 'LINEAR':
                # Change interpolation method
                # Mixture of interpolation method if change happens after first iteration
                if interpolation != 'bezier':
                    interpolation = 'bezier'
                    changed_interpolation |= i > 0

                keyframes.append((
                    (kp.co[0], kp.co[1]),
                    (kp.handle_left[0], kp.handle_left[1]),
                    (kp.handle_right[0], kp.handle_right[1]),
                ))
            else:
                # Change interpolation method; bezier interpolation is the fallback
                # Mixture of interpolation method if change happens after first iteration
                if interpolation == 'bezier':
                    changed_interpolation = True
                elif kp.interpolation == 'LINEAR':
                    interpolation = 'linear'
                    changed_interpolation |= i > 0

                keyframes.append((
                    (kp.co[0], kp.co[1]),
                    (kp.co[0], kp.co[1]),
                    (kp.co[0], kp.co[1]),
                ))

        # As we do not operate on this array this is not really necessary, we just keep consistency
        # The performance hit of the NumPy overhead is tolerable for this case though
        packed_kp = np.array(keyframes, dtype=stk_utils.keyframe2d)
        node_curves.append(f"{'  ' * indent}<curve channel=\"{channel}\" interpolation=\"{interpolation}\" "
                           f"extend=\"{extrapolation}\">")
        indent += 1

        if interpolation == 'bezier':
            for kp in packed_kp:
                node_curves.append("{}<p c=\"{:.1f} {:.3f}\" h1=\"{:.1f} {:.3f}\" h2=\"{:.1f} {:.3f}\"/>".format(
                    '  ' * indent,
                    kp['c']['x'], kp['c']['y'] * factor,
                    kp['h1']['x'], kp['h1']['y'] * factor,
                    kp['h2']['x'], kp['h2']['y'] * factor
                ))

        else:
            for kp in packed_kp:
                node_curves.append("{}<p c=\"{:.1f} {:.3f}\"/>".format(
                    '  ' * indent,
                    kp['c']['x'], kp['c']['y'] * factor
                ))

        # Report inconsistent keyframe points interpolation
        if changed_interpolation:
            report({'WARNING'}, f"The object with the identifier '{obj_id}' uses a mixture of different keyframe "
                   "interpolations in its IPO curve! Check the objects F-Curves in the Graph Editor. SuperTuxKart "
                   "supports 'Constant', 'Linear' and 'Bezier' interpolations, but only if all keyframe points on a "
                   "curve use the same interpolation method.")

        indent -= 1
        node_curves.append(f"{'  ' * indent}</curve>")

    return node_curves


def xml_object_data(objects: np.ndarray, static=False, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for generic scene objects
    (including static).

    Parameters
    ----------
    objects : np.ndarray
        An array of object data that should be processed
    static : bool, optional
        True if the objects should be labeled as static, by default False
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
    tag_name = None

    if static:
        tag_name = 'static-object'
    else:
        tag_name = 'object'

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
            attributes.append(f"lod_instance=\"y\" lod_group=\"{STANDALONE_LOD_PREFIX}{obj['id']}\"")
            is_lod = True
        else:
            # Skeletal animation
            anim = 'y' if obj['object'].find_armature() else 'n'
            attributes.append(f"model=\"{obj['id']}.spm\" skeletal-animation=\"{anim}\"")

            # Check if skeletal animation is looped
            if stk_utils.is_skeletal_animation_looped(animation_data):
                attributes.append("looped=\"y\"")

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
            nodes.append(f"{'  ' * indent}<{tag_name} {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<{tag_name} {' '.join(attributes)}>")
            indent += 1

            # Animated texture as sub-node
            if anim_texture:
                nodes.append(f"{'  ' * indent}{anim_texture}")

            # IPO animation
            nodes.extend(xml_ipo_data(obj['id'], animation_data, obj['object'].rotation_mode, indent, report))

            indent -= 1
            nodes.append(f"{'  ' * indent}</{tag_name}>")

    return nodes


def xml_library_data(library_objects: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for library objects.

    Parameters
    ----------
    library_objects : np.ndarray
        An array of library object data that should be processed
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
    if np.size(library_objects) == 0:
        return []

    # Library nodes
    nodes = [f"{'  ' * indent}<!-- library nodes -->"]

    for obj in library_objects:
        # Identifier, transform and library node name/id
        attributes = [f"id=\"{obj['id']}\"", stk_utils.transform_to_str(obj['transform']), f"name=\"{obj['name']}\""]

        # Build library node
        if not obj['animation']:
            nodes.append(f"{'  ' * indent}<library {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<library {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            nodes.extend(xml_ipo_data(obj['id'], obj['animation'], obj['rotation_mode'], indent + 1, report))
            nodes.append(f"{'  ' * indent}</library>")

    return nodes


def xml_billboard_data(billboards: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for billboard objects.

    Parameters
    ----------
    billboards : np.ndarray
        An array of billboard data that should be processed
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
    if np.size(billboards) == 0:
        return []

    # Billboards nodes
    nodes = [f"{'  ' * indent}<!-- billboards -->"]

    for billboard in billboards:
        # Type, identifier and transform
        attributes = [
            "type=\"billboard\"",
            f"id=\"{billboard['id']}\"",
            stk_utils.transform_to_xyz_str(billboard['transform'])
        ]

        # Add image texture
        image = stk_utils.get_main_texture_stk_material(billboard['material'])
        attributes.append(
            f"texture=\"{billboard['material'].name}.{'png' if image.file_format == 'PNG' else 'jpg'}\""
        )

        # Billboard size
        attributes.append(f"width=\"{billboard['size']['x']:.2f}\" height=\"{billboard['size']['y']:.2f}\"")

        # Billboard fading
        if billboard['fadeout_start'] >= 0 and billboard['fadeout_end'] >= 0:
            attributes.append("fadeout=\"y\"")
            attributes.append(f"start=\"{billboard['fadeout_start']:.2f}\" end=\"{billboard['fadeout_end']:.2f}\"")

        # Build billboard node
        if not billboard['animation']:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            # Set to default rotation mode as rotation does not matter for billboards
            nodes.extend(xml_ipo_data(billboard['id'], billboard['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</object>")

    return nodes


def xml_action_trigger_data(actions: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for action triggers.

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
            nodes.extend(xml_ipo_data(action['id'], action['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</object>")

    return nodes


def xml_cutscene_camera_data(cameras: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for cutscene cameras.

    Parameters
    ----------
    cameras : np.ndarray
        An array of camera data that should be processed
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
    if np.size(cameras) == 0:
        return []

    # Action trigger nodes
    nodes = [f"{'  ' * indent}<!-- cutscene cameras -->"]

    for camera in cameras:
        # Skip if not a cutscene camera
        if camera['type'] != tu.camera_type['cutscene']:
            continue

        # Type, identifier and transform
        attributes = [
            "type=\"cutscene_camera\"",
            f"id=\"{camera['id']}\"",
            stk_utils.transform_to_str(camera['transform'])
        ]

        # Build action node
        if not camera['animation']:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            nodes.extend(xml_ipo_data(camera['id'], camera['animation'], camera['rotation_mode'], indent + 1, report))
            nodes.append(f"{'  ' * indent}</object>")

    # Return empty array if no cutscene cameras in scene
    return nodes if len(nodes) > 1 else []


def xml_sfx_data(audio_sources: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for sound emitters.

    Parameters
    ----------
    audio_sources : np.ndarray
        An array of sound emitter data that should be processed
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
    if np.size(audio_sources) == 0:
        return []

    # Sound emitter nodes
    nodes = [f"{'  ' * indent}<!-- sfx emitters -->"]

    for sfx in audio_sources:
        # Type, identifier and transform
        attributes = [
            "type=\"sfx-emitter\"",
            f"id=\"{sfx['id']}\"",
            stk_utils.transform_to_xyz_str(sfx['transform'])
        ]

        # SFX audio settings
        attributes.append(f"sound=\"{sfx['file']}\"")
        attributes.append(f"volume=\"{sfx['volume']:.2f}\"")
        attributes.append(f"rolloff=\"{sfx['rolloff']:.2f}\"")
        attributes.append(f"max_dist=\"{sfx['distance']:.2f}\"")

        # Trigger on approach
        if sfx['trigger'] >= 0.0:
            attributes.append(f"play-when-near=\"y\" distance=\"{sfx['trigger']:.2f}\"")

        # SFX emitter cutscene condition
        if len(sfx['condition']) > 0:
            attributes.append(f"conditions=\"{sfx['condition']}\"")

        # Build sfx emitter node
        if not sfx['animation']:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<object {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            # Set to default rotation mode as rotation does not matter for SFX emitters
            nodes.extend(xml_ipo_data(sfx['id'], sfx['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</object>")

    return nodes


def xml_particles_data(particles: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for particle emitters.

    Parameters
    ----------
    particles : np.ndarray
        An array of particle emitter data that should be processed
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
    if np.size(particles) == 0:
        return []

    # Particle emitter nodes
    nodes = [f"{'  ' * indent}<!-- particle emitters -->"]

    for emitter in particles:
        # Identifier and transform
        attributes = [f"id=\"{emitter['id']}\"", stk_utils.transform_to_xyzh_str(emitter['transform'])]

        # Particles definition file
        attributes.append(f"kind=\"{emitter['file']}\"")

        # Particle emitter clipping distance
        if emitter['distance'] != 0.0:
            attributes.append(f"clip_distance=\"{int(math.ceil(emitter['distance']))}\"")

        # Particles emitter auto-emit
        attributes.append(f"auto_emit=\"{'y' if emitter['emit'] else 'n'}\"")

        # Particle emitter cutscene condition
        if len(emitter['condition']) > 0:
            attributes.append(f"conditions=\"{emitter['condition']}\"")

        # Build particle emitter node
        if not emitter['animation']:
            nodes.append(f"{'  ' * indent}<particle-emitter {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<particle-emitter {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            # Set to default rotation mode as rotation does not matter for particle emitters
            nodes.extend(xml_ipo_data(emitter['id'], emitter['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</particle-emitter>")

    return nodes


def xml_godrays_data(godrays: np.ndarray, indent=1):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for particle emitters.

    Parameters
    ----------
    godrays : np.ndarray
        An array of godrays emitter data that should be processed
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(godrays) == 0:
        return []

    # Godray emitter nodes
    nodes = [f"{'  ' * indent}<!-- godrays -->"]

    for emitter in godrays:
        # Identifier and transform
        attributes = [f"id=\"{emitter['id']}\"", stk_utils.transform_to_xyz_str(emitter['transform'])]

        # Godrays opacity and color
        attributes.append(f"opacity=\"{emitter['opacity']:.2f}\" color=\"{stk_utils.color_to_str(emitter['color'])}\"")

        # Build godrays emitter node
        nodes.append(f"{'  ' * indent}<lightshaft {' '.join(attributes)}/>")

    return nodes


def xml_lights_data(lights: np.ndarray, fps=25.0, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for dynamic lights.

    Parameters
    ----------
    lights : np.ndarray
        An array of dynamic light data that should be processed
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
    if np.size(lights) == 0:
        return []

    # Light nodes
    nodes = [f"{'  ' * indent}<!-- dynamic lights -->"]

    for light in lights:
        # Identifier and transform
        attributes = [f"id=\"{light['id']}\"", stk_utils.transform_to_xyzh_str(light['transform'])]

        # Light properties
        attributes.append(f"distance=\"{light['distance']:.2f}\"")
        attributes.append(f"energy=\"{(light['energy'] * 0.01):.2f}\"")
        attributes.append(f"color=\"{stk_utils.color_to_str(light['color'])}\"")

        # Scripting
        if light['visible_if'] and len(light['visible_if']):
            attributes.append(f"if=\"{light['visible_if']}\"")

        # Build light node
        if not light['animation']:
            nodes.append(f"{'  ' * indent}<light {' '.join(attributes)}/>")
        else:
            nodes.append(f"{'  ' * indent}<light {' '.join(attributes)} fps=\"{fps:.2f}\">")

            # IPO animation
            # Set to default rotation mode as rotation does not matter for dynamic lights
            nodes.extend(xml_ipo_data(light['id'], light['animation'], 'XYZ', indent + 1, report))
            nodes.append(f"{'  ' * indent}</light>")

    return nodes


def xml_placeables_data(placeables: np.ndarray, indent=1):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for placeables/items.

    Parameters
    ----------
    placeables : np.ndarray
        An array of placeables data that should be processed
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(placeables) == 0:
        return []

    # Placeable nodes
    nodes = [f"{'  ' * indent}<!-- placeables/items -->"]
    nodes_gift = []
    nodes_banana = []
    nodes_nitro_small = []
    nodes_nitro_big = []
    nodes_flags = []

    for item in placeables:
        # Ignore start positions and easter eggs
        if item['type'] == tu.placeable_type['start_position'] or item['type'] == tu.placeable_type['item_easteregg']:
            continue

        # Identifier and transform
        attributes = [
            f"id=\"{item['id']}\"",
            stk_utils.transform_to_xyz_str(item['transform'], True)
        ]

        # Snap/drop to ground
        if not item['snap_ground']:
            attributes.append("drop=\"n\"")

        # Bananas
        if item['type'] == tu.placeable_type['item_banana']:
            if item['ctf_only']:
                attributes.append("ctf=\"y\"")
            nodes_banana.append(f"{'  ' * indent}<banana {' '.join(attributes)}/>")

        # Small nitro cans
        elif item['type'] == tu.placeable_type['item_nitro_small']:
            if item['ctf_only']:
                attributes.append("ctf=\"y\"")
            nodes_nitro_small.append(f"{'  ' * indent}<small-nitro {' '.join(attributes)}/>")

        # Big nitro cans
        elif item['type'] == tu.placeable_type['item_nitro_big']:
            if item['ctf_only']:
                attributes.append("ctf=\"y\"")
            nodes_nitro_big.append(f"{'  ' * indent}<big-nitro {' '.join(attributes)}/>")

        # CTF flag red
        elif item['type'] == tu.placeable_type['item_flag_red']:
            nodes_flags.append(f"{'  ' * indent}<red-flag {' '.join(attributes)}/>")

        # CTF flag blue
        elif item['type'] == tu.placeable_type['item_flag_blue']:
            nodes_flags.append(f"{'  ' * indent}<blue-flag {' '.join(attributes)}/>")

        # Item gift boxes
        else:
            if item['ctf_only']:
                attributes.append("ctf=\"y\"")
            nodes_gift.append(f"{'  ' * indent}<item {' '.join(attributes)}/>")

    # Collect all different nodes (sorted)
    nodes.extend(nodes_gift + nodes_banana + nodes_nitro_small + nodes_nitro_big + nodes_flags)

    return nodes


def xml_start_positions_data(placeables: np.ndarray, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML nodes of the scene file for start positions.

    Parameters
    ----------
    placeables : np.ndarray
        An array of placeables data that should be processed
    indent : int, optional
        The tab indent for writing the XML node, by default 1
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(placeables) == 0:
        return []

    # Start position nodes
    nodes_start = {}
    nodes_ctf_start = {}

    for item in placeables:
        # Ignore everything except start positions
        if item['type'] != tu.placeable_type['start_position']:
            continue

        # Write start positions
        if item['ctf_only']:
            if item['start_index'] in nodes_ctf_start:
                report({'WARNING'}, f"Start position index '{item['start_index']}' is already used! This start "
                       "position will be ignored.")
                continue

            nodes_ctf_start[item['start_index']] = "{}<ctf-start {}/>".format(
                '  ' * indent,
                stk_utils.transform_to_xyz_str(item['transform'], True)
            )
        else:
            if item['start_index'] in nodes_start:
                report({'WARNING'}, f"Start position index '{item['start_index']}' is already used! This start "
                       "position will be ignored.")
                continue

            nodes_start[item['start_index']] = "{}<start {}/>".format(
                '  ' * indent,
                stk_utils.transform_to_xyz_str(item['transform'], True)
            )

    # Check number of start positions
    if nodes_start and len(nodes_start) < 4:
        report({'WARNING'}, "For arenas, there should be at least 4 start positions defined!")
    if nodes_ctf_start and len(nodes_ctf_start) < 16:
        report({'WARNING'}, "For capture the flag arena mode, there should be at least 16 start positions defined!")

    # Collect all different nodes (sorted)
    return [nodes_start[key] for key in sorted(nodes_start.keys())] + \
           [nodes_ctf_start[key] for key in sorted(nodes_ctf_start.keys())]


def xml_check_structures_data(main_driveline: tu.track_driveline, checklines: np.ndarray, cannons: np.ndarray,
                              goals: np.ndarray, indent=1, report=print):
    """Creates an iterable of strings that represent the writable XML node of the scene file for check structures. This
    includes check/lap-lines, cannons and goal triggers.

    Parameters
    ----------
    main_driveline : tu.track_driveline
        The driveline structure of the race track
    checklines : np.ndarray
        All the check and lap lines gathered in the scene for this race track
    cannons : np.ndarray
        All the cannons gathered in the scene for this track
    goals : np.ndarray
        All the goal lines gathered in the scene for this soccer arena
    indent : int, optional
        The tab indent for writing the XML node, by default 1
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    checks_node = [f"{'  ' * indent}<!-- check structures -->", f"{'  ' * indent}<checks>"]
    indent += 1

    # Process checklines of track driveline
    if main_driveline and np.size(checklines) > 0:
        # 'groups' dictionary has following structure:
        # key:      group index (the one set in the Blender object panel)
        # value:    tuple where [0] are the XML node element indicies of the checkline and [1] the group indicies to
        #           activate
        groups = {0: {0}}

        i = 1
        for check in checklines:
            index = check['index']

            if index in groups:
                groups[index].add(i)
            else:
                groups[index] = {i}

            i += 1

        # Write main driveline lap check
        if main_driveline['activate'] in groups:
            checks_node.append("{}<check-lap kind=\"lap\" same-group=\"{}\" other-ids=\"{}\"/>".format(
                '  ' * indent,
                ' '.join(map(str, groups[0])),
                ' '.join(map(str, groups[main_driveline['activate']])),
            ))
        else:
            report({'WARNING'}, "Main driveline activates a checkline index that does not exist "
                   f"({main_driveline['activate']})! Lap counting might not work correctly.")

        # Write activation checkline data
        for check in checklines:
            same = check['index']
            other = check['activate']
            attributes = []

            # Points to a valid checkline?
            if other in groups:
                attributes.append(f"kind=\"{'lap' if same == 0 else 'activate'}\"")
                attributes.append(stk_utils.line_to_str(check['line']))
                attributes.append(f"same-group=\"{' '.join(map(str, groups[same]))}\"")
                attributes.append(f"other-ids=\"{' '.join(map(str, groups[other]))}\"")

                checks_node.append(f"{'  ' * indent}<check-line {' '.join(attributes)}/>")
            else:
                report({'WARNING'}, f"Checkline with identifier '{check['id']}' activates a checkline index that does "
                       f"not exist ({check['activate']})! Lap counting might not work correctly.")

    # Process all cannons on the track
    for cannon in cannons:
        checks_node.append("{}<cannon {} {}>".format(
            '  ' * indent,
            stk_utils.line_to_str(cannon['start']),
            stk_utils.line_to_str(cannon['end'], 'target-p')
        ))

        checks_node.extend(xml_curve_data(
            cannon['curve'].data,
            cannon['curve'].matrix_world,
            'const',
            cannon['speed'],
            indent + 1,
            report
        ))
        checks_node.append(f"{'  ' * indent}</cannon>")

    # Process all soccer goals
    for goal in goals:
        if goal['team']:
            checks_node.append(f"{'  ' * indent}<goal {stk_utils.line_to_str(goal['line'])} first_goal=\"y\"/>")
        else:
            checks_node.append(f"{'  ' * indent}<goal {stk_utils.line_to_str(goal['line'])}/>")

    indent -= 1
    checks_node.append(f"{'  ' * indent}</checks>")

    return checks_node


def xml_sky_data(sky, sh=None, indent=1, report=print):
    """Creates a string that represent the writable XML node of the scene file for the sky data.

    Parameters
    ----------
    sky : mathutils.Color or tuple of bpy.types.Image
        A specified sky color as Blender color tuple or collection of 6 skybox textures
    sh : tuple of bpy.types.Image
        A specified spherical harmonics ambient map as collection of 6 skybox textures
    indent : int, optional
        The tab indent for writing the XML node, by default 1
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'

    Returns
    -------
    str
        The formatted sky-color/sky-box XML node
    """
    if isinstance(sky, mathutils.Color):
        return f"{'  ' * indent}<sky-color rgb=\"{stk_utils.bcolor_to_str(sky)}\"/>"

    # Check textures
    for i in range(6):
        if not sky[i]:
            report({'WARNING'}, "Antarctica Skybox material missing textures! Unable to export the skybox correctly.")
            return ''

        if sh and not sh[i]:
            report({'WARNING'}, "Antarctica Skybox material missing ambient textures! Spherical harmonics textures "
                   "will be ignored.")
            sh = None

    attributes = ["texture=\"{} {} {} {} {} {}\"".format(bpy.path.basename(sky[4].filepath_raw),   # Top
                                                         bpy.path.basename(sky[5].filepath_raw),   # Bottom
                                                         bpy.path.basename(sky[1].filepath_raw),   # East
                                                         bpy.path.basename(sky[3].filepath_raw),   # West
                                                         bpy.path.basename(sky[2].filepath_raw),   # South
                                                         bpy.path.basename(sky[0].filepath_raw))]  # Nord

    # Use spherical harmonics ambient map
    if sh:
        attributes = ["sh-texture=\"{} {} {} {} {} {}\"".format(bpy.path.basename(sh[4].filepath_raw),   # Top
                                                                bpy.path.basename(sh[5].filepath_raw),   # Bottom
                                                                bpy.path.basename(sh[1].filepath_raw),   # East
                                                                bpy.path.basename(sh[3].filepath_raw),   # West
                                                                bpy.path.basename(sh[2].filepath_raw),   # South
                                                                bpy.path.basename(sh[0].filepath_raw))]  # Nord

    return f"{'  ' * indent}<sky-box {' '.join(attributes)}/>"


def xml_sun_data(sun: tuple, ambient: mathutils.Color, stk_scene: stk_props.STKScenePropertyGroup, indent=1):
    """Creates a string that represent the writable XML node of the scene file for the sun.

    Parameters
    ----------
    sun : tuple, including transform diffuse and specular color
        The sun lighting data to be written
    ambient : mathutils.Color or None
        The worlds ambient light color, None if the ambient is specified through an ambient map
    stk_scene : stk_props.STKScenePropertyGroup
        The STK scene properties used for accessing screen-space fog data (which is stored in the sun XML node)
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    str
        The formatted sun XML node
    """
    # Default lighting
    if not sun:
        attributes = ["xyz=\"0.00 60.00 0.00\" sun-diffuse=\"204 204 204\" sun-specular=\"255 255 255\""]
    else:
        # Position and color of the sun
        # Transform is the first element in the tuple (index 0)
        #  - xyz is the first element in the transform tuple (nested index 0)
        #  - then accessing each axis with [0] [1] [2]
        attributes = [
            f"xyz=\"{sun[0][0][0]:.2f} {sun[0][0][1]:.2f} {sun[0][0][2]:.2f}\"",
            f"sun-diffuse=\"{stk_utils.bcolor_to_str(sun[1])}\"",
            f"sun-specular=\"{stk_utils.bcolor_to_str(sun[2])}\""
        ]

    # Ambient lighting color
    if ambient:
        attributes.append(f"ambient=\"{stk_utils.bcolor_to_str(ambient)}\"")

    # Screen-space fog
    if stk_scene.fog:
        attributes.append(f"fog=\"y\" fog-color=\"{stk_utils.bcolor_to_str(stk_scene.fog_color)}\"")
        attributes.append(f"fog-max=\"{stk_scene.fog_max:.2f}\"")
        attributes.append(f"fog-start=\"{stk_scene.fog_from:.2f}\"")
        attributes.append(f"fog-end=\"{stk_scene.fog_to:.2f}\"")

    # Build sun XML node
    return f"{'  ' * indent}<sun {' '.join(attributes)}/>"


def xml_weather_data(stk_scene: stk_props.STKScenePropertyGroup, indent=1):
    """Creates a string that represent the writable XML node of the scene file for the weather.

    Parameters
    ----------
    stk_scene : stk_props.STKScenePropertyGroup
        The STK scene properties used for accessing weather data
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    str
        The formatted weather XML node
    """
    attributes = []

    # Weather effect (particles)
    if stk_scene.weather == 'rain':
        attributes.append("particles=\"rain.xml\"")
    elif stk_scene.weather == 'snow':
        attributes.append("particles=\"snow.xml\"")

    # Lightning
    if stk_scene.weather_lightning:
        attributes.append("lightning=\"y\"")

    # Weather sound effect
    if len(stk_scene.weather_sound) > 0:
        attributes.append(f"sound=\"{stk_scene.weather_sound}\"")

    # Build weather XML node
    if attributes:
        return f"{'  ' * indent}<weather {' '.join(attributes)}/>"
    else:
        return None


def xml_end_cameras_data(cameras: np.ndarray, indent=1):
    """Creates an iterable of strings that represent the writable XML node of the scene file for end cameras.

    Parameters
    ----------
    cameras : np.ndarray
        An array of camera data that should be processed
    indent : int, optional
        The tab indent for writing the XML node, by default 1

    Returns
    -------
    list of str
        Each element represents a line for writing the formatted XML data
    """
    if np.size(cameras) == 0:
        return []

    # End camera node
    node = [f"{'  ' * indent}<end-cameras>"]
    indent += 1

    for camera in cameras:
        # Ignore cutscene cameras
        if camera['type'] == tu.camera_type['cutscene']:
            continue

        # Camera properties
        attributes = [
            f"type=\"{'static_follow_kart' if camera['type'] == tu.camera_type['end_fixed'] else 'ahead_of_kart'}\"",
            stk_utils.transform_to_xyz_str(camera['transform']),
            f"distance=\"{camera['distance']:.2f}\""
        ]

        # Build node
        node.append(f"{'  ' * indent}<camera {' '.join(attributes)}/> <!-- {camera['id']} -->")

    indent -= 1
    node.append(f"{'  ' * indent}</end-cameras>")

    return node


def write_scene_file(context: bpy.context, collection: tu.SceneCollection, output_dir: str, report=print):
    """Writes the scene.xml file for the SuperTuxKart track to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    collection : tu.SceneCollection tuple
        A scene collection tuple containing all the gathered scene data staged for export
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    stk_scene = stk_utils.get_stk_context(context, 'scene')
    world = context.scene.world

    path = os.path.join(output_dir, 'scene.xml')

    # Prepare LOD node data
    xml_lod = xml_lod_data(collection.lod_groups)

    # Prepare static track data (including static objects)
    xml_track = [
        "  <!-- track model and static objects -->",
        f"  <track model=\"{stk_scene.identifier}_track.spm\" x=\"0\" y=\"0\" z=\"0\">",
        "\n".join(xml_object_data(collection.static_objects, True, collection.fps, 2, report)),
        "  </track>"
    ]

    # Prepare library objects
    xml_library_objects = xml_library_data(collection.library_objects, collection.fps, 1, report)

    # Prepare dynamic objects
    xml_objects = ["  <!-- dynamic/animated and non-static objects -->"]
    xml_objects.extend(xml_object_data(collection.dynamic_objects, False, collection.fps, 1, report))

    # Prepare billboards
    xml_billboards = xml_billboard_data(collection.billboards, collection.fps, 1, report)

    # Prepare action triggers
    xml_action_triggers = xml_action_trigger_data(collection.action_triggers, collection.fps, 1, report)

    # Prepare cutscene cameras
    xml_cutscene_cameras = xml_cutscene_camera_data(collection.cameras, collection.fps, 1, report)

    # Prepare sfx emitters
    xml_sfx = xml_sfx_data(collection.audio_sources, collection.fps, 1, report)

    # Prepare particle emitters
    xml_particles = xml_particles_data(collection.particles, collection.fps, 1, report)

    # Prepare godrays emitters
    xml_godrays = xml_godrays_data(collection.godrays, 1)

    # Prepare dynamic lights
    xml_lights = xml_lights_data(collection.lights, collection.fps, 1)

    # Prepare placeables/items emitters
    xml_placeables = xml_placeables_data(collection.placeables, 1)

    # Prepare start positions and start row definitions
    xml_start_positions = ["  <!-- start positions -->"]

    if stk_scene.track_type == 'race':
        xml_start_positions.append(
            f"  <default-start karts-per-row=\"{stk_scene.start_rows:d}\" "
            f"forwards-distance=\"{stk_scene.start_forward:.2f}\" "
            f"sidewards-distance=\"{stk_scene.start_side:.2f}\" "
            f"upwards-distance=\"{stk_scene.start_up:.2f}\"/>"
        )

    elif stk_scene.track_type == 'arena' or stk_scene.track_type == 'soccer':
        xml_start_positions.append(xml_start_positions_data(collection.placeables, 1, report))

    # Prepare check structures
    xml_check_structures = xml_check_structures_data(
        collection.drivelines[0] if np.size(collection.drivelines) > 0 else None,
        collection.checklines,
        collection.cannons,
        collection.goals,
        1,
        report
    )

    # Prepare scene lighting and weather effects
    xml_light_weather = ["  <!-- scene lighting and weather effects -->"]

    world_material = stk_utils.is_stk_material(world.node_tree)

    # Prepare camera rendering and end cameras
    xml_cameras = ["  <!-- camera rendering and end cameras -->", f"  <camera far=\"{stk_scene.far_clip:.1f}\"/>"]
    xml_cameras.extend(xml_end_cameras_data(collection.cameras, 1))

    # Gather world material
    if world.use_nodes and world_material:
        if isinstance(world_material, stk_shaders.AntarcticaSkybox):
            world_ambient = world_material.prop_ambient if not world_material.prop_use_map else None
            xml_light_weather.append(xml_sky_data(
                (
                    world_material.get_texture('Texture North'),
                    world_material.get_texture('Texture East'),
                    world_material.get_texture('Texture South'),
                    world_material.get_texture('Texture West'),
                    world_material.get_texture('Texture Top'),
                    world_material.get_texture('Texture Bottom'),
                ),
                (
                    world_material.get_texture('Ambient North'),
                    world_material.get_texture('Ambient East'),
                    world_material.get_texture('Ambient South'),
                    world_material.get_texture('Ambient West'),
                    world_material.get_texture('Ambient Top'),
                    world_material.get_texture('Ambient Bottom'),
                ) if world_material.prop_use_map else None
            ))
        else:
            world_ambient = world_material.prop_ambient
            xml_light_weather.append(xml_sky_data(world_material.prop_color))
    else:
        world_ambient = mathutils.Color((0.5, 0.5, 0.5))
        xml_light_weather.append(xml_sky_data(world.color))

    # Prepare sun
    xml_light_weather.append(xml_sun_data(collection.sun, world_ambient, stk_scene))

    # Prepare weather effect
    xml_weather = xml_weather_data(stk_scene)

    if xml_weather:
        xml_light_weather.append(xml_weather_data(stk_scene))

    # Write scene file
    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- scene.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
            "<scene>\n"
        ])

        if xml_lod:
            f.write("\n".join(xml_lod))
            f.write("\n")

        f.write("\n".join(xml_track))
        f.write("\n")

        f.write("\n".join(xml_start_positions))
        f.write("\n")

        # Write check structures early on (before object and special objects tags) as objects that utilize scripting
        # functions (action triggers, sfx emitters as well as conditional objects 'if') mess up lap counting if defined
        # before the checklines
        f.write("\n".join(xml_check_structures))
        f.write("\n")

        if xml_library_objects:
            f.write("\n".join(xml_library_objects))
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

        if xml_cutscene_cameras:
            f.write("\n".join(xml_cutscene_cameras))
            f.write("\n")

        if xml_sfx:
            f.write("\n".join(xml_sfx))
            f.write("\n")

        if xml_particles:
            f.write("\n".join(xml_particles))
            f.write("\n")

        if xml_godrays:
            f.write("\n".join(xml_godrays))
            f.write("\n")

        if xml_lights:
            f.write("\n".join(xml_lights))
            f.write("\n")

        if xml_placeables:
            f.write("\n".join(xml_placeables))
            f.write("\n")

        f.write("\n".join(xml_light_weather))
        f.write("\n")

        f.write("\n".join(xml_cameras))
        f.write("\n")

        # all the things...
        f.write("</scene>\n")


def write_driveline_files(context: bpy.context, collection: tu.SceneCollection, output_dir: str, report=print):
    """Writes the quads.xml and graph.xml file for the SuperTuxKart track drivelines to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    collection : tu.SceneCollection tuple
        A scene collection tuple containing all the gathered scene data staged for export
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    if np.size(collection.drivelines) == 0:
        return

    quads_path = os.path.join(output_dir, 'quads.xml')
    graph_path = os.path.join(output_dir, 'graph.xml')
    quads_data = []
    graph_data = []

    dir_values = tu.driveline_direction
    main_data = collection.drivelines[0]['data']
    main_size = np.size(main_data.mid, axis=0)
    # A reshaping of the view is necessary as NumPy does not like custom dtypes for operations between arrays
    main_loop = main_data.mid.view(dtype=np.float32).reshape(main_size, 3)

    is_main = True
    quad_count = 0

    for driveline in collection.drivelines:
        data = driveline['data']
        size = np.size(data.mid, axis=0)
        attr_vis_ai = []
        attr_dir = []

        # Visibility and AI behavior
        if not is_main and driveline['invisible']:
            attr_vis_ai.append("invisible=\"y\"")

        if not is_main and driveline['ignore']:
            attr_vis_ai.append("ai-ignore=\"y\"")

        # Drivable direction
        if driveline['direction'] != dir_values['none'] and driveline['direction'] != dir_values['both']:
            attr_dir.append("direction=\"{}\"".format(
                'forward' if driveline['direction'] == dir_values['forward'] else 'reverse'
            ))

        # Height testing
        if is_main:
            quads_data.append(f"  <height-testing max=\"{driveline['higher']:.2f}\" min=\"{driveline['lower']:.2f}\"/>")

        quads_data.append(f"  <!-- driveline: {driveline['id']} -->")

        # Iterate through quad data
        for i in np.arange(size):
            p = []

            if i == 0:
                p.append(f"p0=\"{data.left[i][0]:.2f} {data.left[i][1]:.2f} {data.left[i][2]:.2f}\"")
                p.append(f"p1=\"{data.right[i][0]:.2f} {data.right[i][1]:.2f} {data.right[i][2]:.2f}\"")
                p.append(f"p2=\"{data.right[i + 1][0]:.2f} {data.right[i + 1][1]:.2f} {data.right[i + 1][2]:.2f}\"")
                p.append(f"p3=\"{data.left[i + 1][0]:.2f} {data.left[i + 1][1]:.2f} {data.left[i + 1][2]:.2f}\"")
                quads_data.append(f"  <quad {' '.join(attr_vis_ai + attr_dir + p)}/>")
            else:
                p.append(f"p0=\"{quad_count - 1}:3\"")
                p.append(f"p1=\"{quad_count - 1}:2\"")
                p.append(f"p2=\"{data.right[i + 1][0]:.2f} {data.right[i + 1][1]:.2f} {data.right[i + 1][2]:.2f}\"")
                p.append(f"p3=\"{data.left[i + 1][0]:.2f} {data.left[i + 1][1]:.2f} {data.left[i + 1][2]:.2f}\"")

                if i != size - 1:
                    quads_data.append(f"  <quad {' '.join(attr_dir + p)}/>")
                else:
                    quads_data.append(f"  <quad {' '.join(attr_vis_ai + attr_dir + p)}/>")

            quad_count += 1

        # Closing quad for main driveline
        if is_main:
            p = [f"p0=\"{quad_count - 1}:3\"", f"p1=\"{quad_count - 1}:2\"", "p2=\"0:1\"", "p3=\"0:0\""]
            quads_data.append(f"  <quad {' '.join(attr_dir + p)}/>")
            graph_data.append(f"  <!-- main loop: {driveline['id']} -->")
            graph_data.append(f"  <edge-loop from=\"0\" to=\"{quad_count}\"/>")
            quad_count += 1
            is_main = False  # Only first driveline in collection is the main
        else:
            # Calculate entry and exit points of this driveline
            dl_from = np.repeat([data.access_point], main_size, axis=0)
            dl_to = np.repeat([data.end_point], main_size, axis=0)
            graph_from = np.argmin(np.linalg.norm(dl_from - main_loop, axis=1))
            graph_to = np.argmin(np.linalg.norm(dl_to - main_loop, axis=1))
            graph_data.append(f"  <!-- additional loop: {driveline['id']} -->")
            graph_data.append(f"  <edge from=\"{graph_from}\" to=\"{quad_count - size}\"/>")
            graph_data.append(f"  <edge-line from=\"{quad_count - size}\" to=\"{quad_count - 1}\"/>")
            graph_data.append(f"  <edge from=\"{quad_count - 1}\" to=\"{graph_to}\"/>")

    graph_data.insert(0, f"  <node-list from-quad=\"0\" to-quad=\"{quad_count - 1}\"/>")

    # Write quads and graph file
    with open(quads_path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- quads.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
            "<quads>\n"
        ])
        f.write("\n".join(quads_data))
        f.write("\n</quads>\n")

    with open(graph_path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- graph.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
            "<graph>\n"
        ])
        f.write("\n".join(graph_data))
        f.write("\n</graph>\n")


def write_track_file(context: bpy.context, collection: tu.SceneCollection, output_dir: str, report=print):
    """Writes the track.xml file for the SuperTuxKart track to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    collection : tu.SceneCollection tuple
        A scene collection tuple containing all the gathered scene data staged for export
    output_dir : str
        The output folder path where the XML file should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    stk_scene = stk_utils.get_stk_context(context, 'scene')
    path = os.path.join(output_dir, 'track.xml')

    def str_sanitize(val: str):
        from xml.sax.saxutils import escape
        return escape(val).encode('ascii', 'xmlcharrefreplace').decode('ascii')

    # Special cases for group names
    if stk_scene.category == 'add-ons':
        group_name = 'Add-Ons'
    elif stk_scene.category == 'wip':
        group_name = 'wip-track'
    else:
        group_name = stk_scene.category

    # Write scene file
    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- track.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
        ])

        # Meta information
        f.write(f"<track name                    = \"{stk_scene.name}\"")
        f.write(f"\n       groups                  = \"{group_name}\"")
        f.write(f"\n       version                 = \"{stk_utils.FILE_FORMAT_VERSION}\"")
        f.write(f"\n       designer                = \"{str_sanitize(stk_scene.designer)}\"")

        if stk_scene.screenshot:
            f.write(f"\n       screenshot              = \"{os.path.basename(stk_scene.screenshot.filepath_raw)}\"")

        if stk_scene.music:
            f.write(f"\n       music                   = \"{stk_scene.music}\"")

        # Track type specific
        if stk_scene.track_type == 'arena':
            f.write(f"\n       arena                   = \"y\"")
            f.write(f"\n       ctf                     = \"{'y' if stk_scene.ctf_active else 'n'}\"")

        f.write(f"\n       soccer                  = \"{'y' if stk_scene.track_type == 'soccer' else 'n'}\"")
        f.write(f"\n       cutscene                = \"{'y' if stk_scene.track_type == 'cutscene' else 'n'}\"")
        f.write(f"\n       internal                = \"{'y' if stk_scene.track_type == 'cutscene' else 'n'}\"")

        if stk_scene.track_type == 'race':
            f.write(f"\n       reverse                 = \"{'y' if stk_scene.reverse else 'n'}\"")
            f.write(f"\n       default-number-of-laps  = \"{stk_scene.lap_count}\"")

        # General track properties
        f.write(f"\n       smooth-normals          = \"{'y' if stk_scene.smooth_normals else 'n'}\"")
        f.write(f"\n       auto-rescue             = \"{'y' if stk_scene.auto_reset else 'n'}\"")
        f.write(f"\n       shadows                 = \"{'y' if stk_scene.shadows else 'n'}\"")
        f.write(f"\n       is-during-day           = \"{'y' if stk_scene.daytime == 'day' else 'n'}\"")
        f.write("/>\n")
