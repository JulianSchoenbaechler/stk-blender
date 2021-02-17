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

# We then extract each nodes, so far we only support
# * Color
#   * It MUST connected to a texture node so we extract the name of the texture
# * Vector3D
#   * Managed like a texture (for normal maps)
# * Floating point (NO OTHER NODES SHOULD BE CONNECTED)
#   * We simply exctract the value and we add it in the xml
#
# More advanced shader graphs aren't supported
#
# Physical properties (related to gameplay) are stored in custom properties

import bpy, re
import os
from bpy_extras.io_utils import ExportHelper
from collections import OrderedDict

from bpy.props import (StringProperty,
                   BoolProperty,
                   IntProperty,
                   FloatProperty,
                   EnumProperty,
                   PointerProperty
                   )
from bpy.types import (Panel,
                   Operator,
                   PropertyGroup
                   )

from . import stk_utils, stk_panel

bl_info = {
    "name": "SuperTuxKart Material Exporter",
    "description": "Exports material properties to the materials.xml format",
    "author": "Jean-Manuel Clemencon, Joerg Henrichs, Marianne Gagnon",
    "version": (2,0),
    "blender": (2, 80, 0),
    "location": "File > Export",
    "warning": '', # used for warning icon and text in addons panel
    "wiki_url": "https://supertuxkart.net/Community",
    "tracker_url": "https://github.com/supertuxkart/stk-blender/issues",
    "category": "Import-Export"}

# Detect if we are dealing with a SuperTuxKart shader
def is_stk_shader(node):
    # This can happen if we have a node disconnected
    if node == None:
        return False
    if node.bl_static_type == "CUSTOM GROUP":
        if "Antarctica" in node.name:
            return True

    return False

# We make sure we get the root of the node tree (we start from the output and build up)
def get_root_shader(node_network):
    for node in node_network:
        # We check if it's a material output
        if node.bl_static_type == "OUTPUT_MATERIAL":
            try:
                child = node.inputs["Surface"].links[0].from_node
                return child
            except:
                continue

    return None

def write_material_file(path):
    antarctica_materials = []


    from pathlib import Path
    for mat in bpy.data.materials:

        if mat.node_tree != None:

            root = get_root_shader(mat.node_tree.nodes)
            if not is_stk_shader(root):
                continue

            # For now we only support PBR solid
            if root.name == "Antarctica Solid PBR":
                print(f"Exporting material: '{mat.name}'")
                textures = {
                    "shader":"solid",
                    "name": Path(root.node_tree.nodes["Main Texture"].image.filepath).name,
                    "normal-map":Path(root.node_tree.nodes["Normal Map"].image.filepath).name,
                    "gloss-map":Path(root.node_tree.nodes["Data Map"].image.filepath).name
                }
                #print(root.node_tree.nodes['Colorizable'].outputs[0].default_value)
                antarctica_materials.append(textures)

                #print("accessing a property", mat.stk.slowdown_fraction)
                #print("accessing a property", mat.stk.zipper)

    # To replace with correct path and a better system
    xmlmatfile = open(path + "/materials.xml", "w")
    xmlmatfile.write('<?xml version="1.0" encoding="utf-8"?>\n<materials>\n')
    for material in antarctica_materials:

        data_to_export = ""
        for value in material:
            data_to_export += f'{value}="{material[value]}" '

        xmlmatfile.write(f' <material {data_to_export}/>\n')

    xmlmatfile.write('</materials>')
    print("== Material Exported ==")
    


class STK_Material_Export_Operator(bpy.types.Operator, ExportHelper):
    """Export XML flies describing STK materials"""

    bl_idname = ("screen.stk_material_export")
    bl_label = ("Export Materials")

    filename_ext = ".xml"

    output_path: StringProperty(
        name="Output Path",
        description="The output path for the exported track",
        default='//',
        subtype='DIR_PATH'
    )

    def execute(self, context):
        #writeMaterialsFile(self, self.filepath)

        stk_scene = stk_utils.get_stk_context(context, 'scene')
        # pylint: disable=assignment-from-no-return
        output_dir = bpy.path.abspath(os.path.join(self.output_path, stk_scene.identifier))
        
        print("export_materials")
        print(output_dir)

        return {'FINISHED'}


 