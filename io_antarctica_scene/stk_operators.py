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
import io
import os
import numpy as np
from . import stk_utils, stk_kart, stk_kart_utils, stk_track, stk_track_utils, stk_library, stk_library_utils
from bpy.props import (
    IntProperty,
    FloatProperty,
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty
)


class STK_OT_KartExport(bpy.types.Operator):
    """Export the current scene as a SuperTuxKart kart."""
    bl_idname = 'stk.export_kart'
    bl_label = "Export STK Kart"
    bl_description = "Exports the current scene from the context as a SuperTuxKart kart"

    output_path: StringProperty(
        name="Output Path",
        description="The output path for the exported kart",
        default='//',
        subtype='DIR_PATH'
    )

    def invoke(self, context, event):
        # Generate output path
        stk_prefs = context.preferences.addons[__package__].preferences
        stk_scene = stk_utils.get_stk_context(context, 'scene')

        # pylint: disable=assignment-from-no-return
        assets_path = os.path.abspath(bpy.path.abspath(stk_prefs.assets_path))

        # Non-existent assets path
        if not stk_prefs.assets_path or not os.path.isdir(assets_path):
            self.report({'ERROR'}, "No asset (data) directory specified for exporting the SuperTuxKart scene! Check "
                                   "the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        output_path = os.path.join(
            assets_path,
            'karts' if stk_scene.category != 'wip' else 'wip-karts'
        )

        # Invalid assets path
        if not os.path.isdir(output_path):
            self.report({'ERROR'}, "The specified asset (data) directory for exporting the SuperTuxKart scene is "
                                   "invalid! Check the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        self.output_path = output_path

        return self.execute(context)

    def execute(self, context):
        stk_scene = stk_utils.get_stk_context(context, 'scene')
        # pylint: disable=assignment-from-no-return
        output_dir = bpy.path.abspath(os.path.join(self.output_path, stk_scene.identifier))

        # Create track folder if non-existent
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # Ensure the object properties have been loaded
        bpy.ops.stk.reload_object_properties()  # pylint: disable=no-member

        # Get evaluated gependency-graph
        dg = context.evaluated_depsgraph_get()

        # Gather and stage all scene objects that should be exported
        scene = stk_kart_utils.collect_scene(context, self.report)

        # Files staged for copying to destination
        cpy_files = []

        stk_kart.write_kart_file(context, scene, output_dir, self.report)

        # Copy staged files if they exist in the working directory
        import shutil

        for f in cpy_files:
            p_input = bpy.path.abspath(os.path.join('//', f))

            if os.path.isfile(p_input):
                p_output = os.path.join(output_dir, f)
                shutil.copy2(p_input, p_output)

        # Reset frames
        # context.scene.frame_set(context.scene.frame_start)
        return {'FINISHED'}

    @ classmethod
    def poll(self, context):
        """Operator poll method.
        Only execute this operator when scene is a SuperTuxKart kart.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        if not context.scene or not context.scene.stk:
            return False

        return stk_utils.get_stk_scene_type(context) == 'kart'


class STK_OT_TrackExport(bpy.types.Operator):
    """Export the current scene as a SuperTuxKart track."""
    bl_idname = 'stk.export_track'
    bl_label = "Export STK Track"
    bl_description = "Exports the current scene from the context as a SuperTuxKart track"

    output_path: StringProperty(
        name="Output Path",
        description="The output path for the exported track",
        default='//',
        subtype='DIR_PATH'
    )

    def invoke(self, context, event):
        # Generate output path
        stk_prefs = context.preferences.addons[__package__].preferences
        stk_scene = stk_utils.get_stk_context(context, 'scene')

        # pylint: disable=assignment-from-no-return
        assets_path = os.path.abspath(bpy.path.abspath(stk_prefs.assets_path))

        # Non-existent assets path
        if not stk_prefs.assets_path or not os.path.isdir(assets_path):
            self.report({'ERROR'}, "No asset (data) directory specified for exporting the SuperTuxKart scene! Check "
                                   "the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        output_path = os.path.join(
            assets_path,
            'tracks' if stk_scene.category != 'wip' else 'wip-tracks'
        )

        # Invalid assets path
        if not os.path.isdir(output_path):
            self.report({'ERROR'}, "The specified asset (data) directory for exporting the SuperTuxKart scene is "
                                   "invalid! Check the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        self.output_path = output_path

        return self.execute(context)

    def execute(self, context):
        stk_scene = stk_utils.get_stk_context(context, 'scene')
        # pylint: disable=assignment-from-no-return
        output_dir = bpy.path.abspath(os.path.join(self.output_path, stk_scene.identifier))

        # Create track folder if non-existent
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # Ensure the object properties have been loaded
        bpy.ops.stk.reload_object_properties()  # pylint: disable=no-member

        # Get evaluated gependency-graph
        dg = context.evaluated_depsgraph_get()

        # Gather and stage all scene objects that should be exported
        scene = stk_track_utils.collect_scene(context, self.report)

        # Files staged for copying to destination
        cpy_files = ['scripting.as']
        cpy_files += [p['file'] for p in scene.particles]       # Get all assigned particle definition files
        cpy_files += [a['file'] for a in scene.audio_sources]   # Get all assigned audio files

        stk_track.write_scene_file(context, scene, output_dir, self.report)
        stk_track.write_driveline_files(context, scene, output_dir, self.report)
        stk_track.write_track_file(context, scene, output_dir, self.report)

        # Demo: export materials
        for mat in bpy.data.materials:
            image = stk_utils.get_main_texture_stk_material(mat)
            print(mat, image)

            if not image:
                continue

            original_path = image.filepath_raw

            if image.file_format == 'JPEG':
                image.filepath_raw = os.path.join(output_dir, f'{mat.name}.jpg')
            elif image.file_format == 'PNG':
                image.filepath_raw = os.path.join(output_dir, f'{mat.name}.png')
            else:
                print("Error exporting images...")
                continue

            # Save image
            image.save()
            image.filepath_raw = original_path

        # Copy staged files if they exist in the working directory
        import shutil

        for f in cpy_files:
            p_input = bpy.path.abspath(os.path.join('//', f))

            if os.path.isfile(p_input):
                p_output = os.path.join(output_dir, f)
                shutil.copy2(p_input, p_output)

        print("EXPORT!!!!")

        # Reset frames
        context.scene.frame_set(context.scene.frame_start)
        return {'FINISHED'}

    @ classmethod
    def poll(self, context):
        """Operator poll method.
        Only execute this operator when scene is a SuperTuxKart track.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        if not context.scene or not context.scene.stk:
            return False

        return stk_utils.get_stk_scene_type(context) == 'track'


class STK_OT_LibraryExport(bpy.types.Operator):
    """Export the current scene as a SuperTuxKart library node."""
    bl_idname = 'stk.export_library'
    bl_label = "Export STK Library Node"
    bl_description = "Exports the current scene from the context as a SuperTuxKart library node"

    output_path: StringProperty(
        name="Output Path",
        description="The output path for the exported library node",
        default='//',
        subtype='DIR_PATH'
    )

    def invoke(self, context, event):
        # Generate output path
        stk_prefs = context.preferences.addons[__package__].preferences

        # pylint: disable=assignment-from-no-return
        assets_path = os.path.abspath(bpy.path.abspath(stk_prefs.assets_path))

        # Non-existent assets path
        if not stk_prefs.assets_path or not os.path.isdir(assets_path):
            self.report({'ERROR'}, "No asset (data) directory specified for exporting the SuperTuxKart scene! Check "
                                   "the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        output_path = os.path.join(assets_path, 'library')

        # Invalid assets path
        if not os.path.isdir(output_path):
            self.report({'ERROR'}, "The specified asset (data) directory for exporting the SuperTuxKart scene is "
                                   "invalid! Check the path to the assets directory in the add-on's preferences.")
            return {'CANCELLED'}

        self.output_path = output_path

        return self.execute(context)

    def execute(self, context):
        stk_scene = stk_utils.get_stk_context(context, 'scene')
        # pylint: disable=assignment-from-no-return
        output_dir = bpy.path.abspath(os.path.join(self.output_path, stk_scene.identifier))

        # Create track folder if non-existent
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # Ensure the object properties have been loaded
        bpy.ops.stk.reload_object_properties()  # pylint: disable=no-member

        # Get evaluated gependency-graph
        dg = context.evaluated_depsgraph_get()

        # Gather and stage all scene objects that should be exported
        node = stk_library_utils.collect_node(context, self.report)

        # Files staged for copying to destination
        cpy_files = ['scripting.as']
        cpy_files += [p['file'] for p in node.particles]        # Get all assigned particle definition files
        cpy_files += [a['file'] for a in node.audio_sources]    # Get all assigned audio files

        stk_library.write_node_file(context, node, output_dir, self.report)

        # Copy staged files if they exist in the working directory
        import shutil

        for f in cpy_files:
            p_input = bpy.path.abspath(os.path.join('//', f))

            if os.path.isfile(p_input):
                p_output = os.path.join(output_dir, f)
                shutil.copy2(p_input, p_output)

        # Reset frames
        context.scene.frame_set(context.scene.frame_start)
        return {'FINISHED'}

    @ classmethod
    def poll(self, context):
        """Operator poll method.
        Only execute this operator when scene is a SuperTuxKart library.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        if not context.scene or not context.scene.stk:
            return False

        return stk_utils.get_stk_scene_type(context) == 'library'


class STK_OT_DemoOperator(bpy.types.Operator):
    bl_idname = 'stk.demo'
    bl_label = "STK Test Operator"
    bl_description = "Demo..."

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        from timeit import default_timer as timer
        # Ensure the object properties have been loaded
        bpy.ops.stk.reload_object_properties()

        # Get evaluated gependency-graph
        dg = context.evaluated_depsgraph_get()

        # Gather and stage all scene objects that should be exported
        scene = stk_track_utils.collect_scene(context, self.report)

        #start = timer()
        # for _ in range(100):
        # stk_track_utils.parse_driveline(context.active_object.data)
        #print(timer() - start)

        return {'FINISHED'}

    @ classmethod
    def poll(self, context):
        """Operator poll method.
        Only execute this operator when scene is a SuperTuxKart track.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        if not context.scene or not context.scene.stk:
            return False

        return stk_utils.get_stk_scene_type(context) == 'track'


class STK_MT_ExportMenu(bpy.types.Menu):
    bl_idname = 'STK_MT_export_menu'
    bl_label = "STK Export"
    bl_description = "Export operators for the current SuperTuxKart scene"

    def draw(self, context):
        layout = self.layout
        layout.operator('stk.export_track', text="Export Track")
