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
from bpy.types import AddonPreferences
from bpy.props import (
    BoolProperty,
    StringProperty
)


class STKAddonPreferences(AddonPreferences):
    bl_idname = __package__

    assets_path: StringProperty(
        name="Assets (Data) Path",
        description="The SuperTuxKart's asset (data) folder where files will get exported to and library nodes can be "
                    "read from",
        subtype='DIR_PATH'
    )

    clean_destination_on_export: BoolProperty(
        name="Clean Destination On Export",
        description="Remove old files from destination folder before export. If toggled off, the exporter will only "
                    "overwrite the files that have changed and not touch the rest. Enabled by default, to prevent "
                    "remaining unused files",
        default=True
    )

    export_images: BoolProperty(
        name="Copy Images On Export",
        description="Also copy used texture images on export",
        default=True
    )

    def draw(self, context):
        layout = self.layout
        #layout.label(text="The data folder contains folders named 'karts', 'tracks', 'textures', etc.")
        layout.prop(self, 'assets_path')
        #layout.operator('screen.stk_pick_assets_path', icon='FILEBROWSER', text="Select...")
        layout.prop(self, 'clean_destination_on_export')
        layout.prop(self, 'export_images')
