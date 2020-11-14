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
import numpy as np
from . import stk_utils, stk_track, stk_track_new


class STK_OT_TrackExport(bpy.types.Operator):
    """Export the current scene as a SuperTuxKart track."""
    bl_idname = "stk.export_track"
    bl_label = "Export STK Track"
    bl_description = "Exports the current scene from the context as a SuperTuxKart track"

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):

        dg = bpy.context.evaluated_depsgraph_get()
        scene = stk_track_new.write_scene(context, self.report)
        print("static", scene.static_objects)
        print("dynamic", scene.dynamic_objects)

        for obj in context.scene.objects:
            pass

        # some_seq = np.zeros((len(context.scene.objects) * 3), dtype=stk_utils.vec3)
        # some_seq = [0] * len(context.scene.objects)
        # context.scene.objects.foreach_get('type', some_seq)
        # print(some_seq)

        # for thing in some_seq:
        #    print(thing)

        print("EXPORT!!!!")
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
