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
from . import stk_shaders, stk_utils

TextureData = collections.namedtuple('TextureData', [
    'image',    # The image reference
    'output'    # The resulting output filename of the texture
])


def export_textures(context: bpy.context, output_dir: str, report=print):
    """Directly export (save image data) textures used in the materials to disk.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    output_dir : str
        The output folder path where the data should be written to
    report : callable, optional
        A function used for reporting warnings or errors for the submitted data, by default 'print()'
    """
    pass


def write_materials_file(context: bpy.context, output_dir: str, report=print):
    """Writes the materials.xml file for the SuperTuxKart scene to disk.

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
    path = os.path.join(output_dir, 'materials.xml')

    # Prepare animations
    #xml_hat = xml_hat_data(collection.hat)

    # Write kart file
    with open(path, 'w', encoding='utf8', newline="\n") as f:
        f.writelines([
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
            f"<!-- materials.xml generated with SuperTuxKart Exporter Tools v{stk_utils.get_addon_version()} -->\n"
        ])

        # Meta information
        #f.write(f"<kart name                    = \"{stk_scene.name}\"")
        #f.write(f"\n      groups                  = \"{group_name}\"")
        #f.write(f"\n      version                 = \"{stk_utils.KART_FILE_FORMAT_VERSION}\"")
        #f.write(f"\n      type                    = \"{stk_scene.kart_type}\"")
        #f.write(f"\n      rgb                     = \"{color.r:.2f} {color.g:.2f} {color.b:.2f}\"")
        #f.write(f"\n      model-file              = \"{stk_scene.identifier}.spm\"")
        #f.write(">\n")

        #f.write("</kart>\n")
