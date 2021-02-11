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
# The custom STK PBR shader is not yet implemented
# Use a principled BSDF shader for now
def is_stk_shader(node):
    if node.bl_static_type == "BSDF_PRINCIPLED":
    #if node.bl_static_type == "GROUP":
        # if node.node_tree.name == "stk_pbr_shader":
        return True
    else:
        return False

# We make sure we get the root of the node tree (we start from the output and build up)
def get_root_shader(node_network):
    print("We found: nodes", len(node_network))
    for node in node_network:
        # We check if it's a material output
        if node.bl_static_type == "OUTPUT_MATERIAL":
            try:
                child = node.inputs["Surface"].links[0].from_node
                return child
            except:
                continue

    return None

class STK_Material_Export_Operator(bpy.types.Operator, ExportHelper):
    """Export XML flies describing STK materials"""

    bl_idname = ("screen.stk_material_export")
    bl_label = ("Export Materials")

    filename_ext = ".xml"
    filepath: bpy.props.StringProperty()

    def execute(self, context):
        #writeMaterialsFile(self, self.filepath)


        antarctica_materials = []


        from pathlib import Path
        for mat in bpy.data.materials:

            if mat.node_tree != None:
                root = get_root_shader(mat.node_tree.nodes)

                # This can happen if the node is disconnected
                if root == None:
                    continue
                
                # For now we assume users will not create custom nodes called antarctica
                print("static type", root.bl_static_type)
                if "Antarctica" in root.name:
                    print("Antarctica material detected: ", mat.name)

                    # For now we only support PBR solid
                    if root.name == "Antarctica Solid PBR":
                        print("We export this material")
                        textures = {
                            "shader":"solid",
                            "name": Path(root.node_tree.nodes["Main Texture"].image.filepath).name,
                            "normal-map":Path(root.node_tree.nodes["Normal Map"].image.filepath).name,
                            "gloss-map":Path(root.node_tree.nodes["Data Map"].image.filepath).name
                        }
                        antarctica_materials.append(textures)

        # To replace with correct path
        xmlmatfile = open("C:\\Users\\Administrator\\Documents\\supertuxkart\\stk-media-hd\\library\\streetFurniture\\test_export_library\\library_node_test\\materials.xml", "w")
        xmlmatfile.write('<?xml version="1.0" encoding="utf-8"?>\n<materials>\n')
        for material in antarctica_materials:

            data_to_export = ""
            for value in material:
                data_to_export += f'{value}="{material[value]}" '

            xmlmatfile.write(f' <material {data_to_export}/>\n')

        xmlmatfile.write('</materials>')
        print("== Material Exported ==")
        return {'FINISHED'}
#node_tree.nodes["Antarctica Solid PBR"].prop_colorizationFactor