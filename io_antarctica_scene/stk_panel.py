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
import os
from collections import OrderedDict
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, PointerProperty
from . import stk_utils, stk_props

CONTEXT_OBJECT = 0
CONTEXT_SCENE = 1
CONTEXT_MATERIAL = 2

datapath = stk_utils.getDataPath(os.path.dirname(__file__))

SCENE_PROPS = []
STK_PER_OBJECT_TRACK_PROPERTIES = []
STK_PER_OBJECT_KART_PROPERTIES = []
STK_MATERIAL_PROPERTIES = []

if os.path.exists(datapath):
    print("(STK) Loading XML files from ", datapath)

    panel_params_path = os.path.join(datapath, "stk_panel_parameters.xml")
    print("(STK) Loading scene properties from ", panel_params_path)

    SCENE_PROPS = stk_utils.getPropertiesFromXML(panel_params_path, contextLevel=CONTEXT_SCENE)

    object_params_path = os.path.join(datapath, "stk_object_parameters.xml")
    print("(STK) Loading object properties from ", object_params_path)

    STK_PER_OBJECT_TRACK_PROPERTIES = stk_utils.getPropertiesFromXML(object_params_path, contextLevel=CONTEXT_OBJECT)

    kart_params_path = os.path.join(datapath, "stk_kart_object_parameters.xml")
    print("(STK) Loading kart properties from ", kart_params_path)

    STK_PER_OBJECT_KART_PROPERTIES = stk_utils.getPropertiesFromXML(kart_params_path, contextLevel=CONTEXT_OBJECT)

    material_params_path = os.path.join(datapath, "stk_material_parameters.xml")
    print("(STK) Loading material properties from ", material_params_path)

    STK_MATERIAL_PROPERTIES = stk_utils.getPropertiesFromXML(material_params_path, contextLevel=CONTEXT_MATERIAL)
else:
    raise RuntimeError("(STK) Make sure the stkdata folder is installed, cannot locate it!!")


class STK_TypeUnset(bpy.types.Operator):
    bl_idname = ("screen.stk_unset_type")
    bl_label = ("STK Object :: unset type")

    def execute(self, context):
        obj = context.object
        obj["type"] = ""
        return {'FINISHED'}


class STK_MissingProps_Object(bpy.types.Operator):
    bl_idname = ("screen.stk_missing_props_" + str(CONTEXT_OBJECT))
    bl_label = ("Create missing properties")

    def execute(self, context):

        is_track = ("is_stk_track" in context.scene and context.scene["is_stk_track"] == "true")
        is_node = ("is_stk_node" in context.scene and context.scene["is_stk_node"] == "true")
        is_kart = ("is_stk_kart" in context.scene and context.scene["is_stk_kart"] == "true")

        obj = context.object

        if is_kart:
            properties = OrderedDict([])
            for curr in STK_PER_OBJECT_KART_PROPERTIES[1]:
                properties[curr.id] = curr
            stk_utils.createProperties(obj, properties)
        elif is_track or is_node:
            properties = OrderedDict([])
            for curr in STK_PER_OBJECT_TRACK_PROPERTIES[1]:
                properties[curr.id] = curr
            print('creating', properties, 'on', obj.name)
            stk_utils.createProperties(obj, properties)

        return {'FINISHED'}


class STK_MissingProps_Scene(bpy.types.Operator):
    bl_idname = ("screen.stk_missing_props_" + str(CONTEXT_SCENE))
    bl_label = ("Create missing properties")

    def execute(self, context):
        scene = context.scene
        properties = OrderedDict([])
        for curr in SCENE_PROPS[1]:
            properties[curr.id] = curr
        stk_utils.createProperties(scene, properties)
        return {'FINISHED'}


class STK_MissingProps_Material(bpy.types.Operator):
    bl_idname = ("screen.stk_missing_props_" + str(CONTEXT_MATERIAL))
    bl_label = ("Create missing properties")

    def execute(self, context):
        material = getObject(context, CONTEXT_MATERIAL)
        properties = OrderedDict([])
        for curr in STK_MATERIAL_PROPERTIES[1]:
            properties[curr.id] = curr
        stk_utils.createProperties(material, properties)
        return {'FINISHED'}

# ==== PANEL BASE ====


class PanelBase:

    def recursivelyAddProperties(self, properties, layout, obj, contextLevel):

        for id in properties.keys():
            curr = properties[id]

            row = layout.row()

            if isinstance(curr, stk_utils.StkPropertyGroup):

                state = "true"
                icon = 'TRIA_DOWN'
                if id in bpy.data.scenes[0]:
                    state = bpy.data.scenes[0][id]
                    if state == "true":
                        icon = 'TRIA_DOWN'
                    else:
                        icon = 'TRIA_RIGHT'

                row.operator(stk_utils.generateOpName("screen.stk_tglbool_", curr.fullid,
                                                      curr.id), text=curr.name, icon=icon, emboss=False)
                row.label(text=" ")  # force the operator to not maximize
                if state == "true":
                    if len(curr.subproperties) > 0:
                        box = layout.box()
                        self.recursivelyAddProperties(curr.subproperties, box, obj, contextLevel)

            elif isinstance(curr, stk_utils.StkBoolProperty):

                state = "false"
                icon = 'CHECKBOX_DEHLT'
                split = row.split(factor=0.8)
                split.label(text=curr.name)
                if id in obj:
                    state = obj[id]
                    if state == "true":
                        icon = 'CHECKBOX_HLT'
                split.operator(stk_utils.generateOpName("screen.stk_tglbool_", curr.fullid,
                                                        curr.id), text="                ", icon=icon, emboss=False)

                if state == "true":
                    if len(curr.subproperties) > 0:
                        if curr.box:
                            box = layout.box()
                            self.recursivelyAddProperties(curr.subproperties, box, obj, contextLevel)
                        else:
                            self.recursivelyAddProperties(curr.subproperties, layout, obj, contextLevel)

            elif isinstance(curr, stk_utils.StkColorProperty):
                row.label(text=curr.name)
                if curr.id in obj:
                    row.prop(obj, '["' + curr.id + '"]', text="")
                    row.operator(stk_utils.generateOpName("screen.stk_apply_color_",
                                                          curr.fullid, curr.id), text="", icon='COLOR')
                else:
                    row.operator('screen.stk_missing_props_' + str(contextLevel))

            elif isinstance(curr, stk_utils.StkCombinableEnumProperty):

                row.label(text=curr.name)

                if curr.id in obj:
                    curr_val = obj[curr.id]

                    for value_id in curr.values:
                        icon = 'CHECKBOX_DEHLT'
                        if value_id in curr_val:
                            icon = 'CHECKBOX_HLT'
                        row.operator(stk_utils.generateOpName("screen.stk_set_", curr.fullid, curr.id +
                                                              "_" + value_id), text=curr.values[value_id].name, icon=icon)
                else:
                    row.operator('screen.stk_missing_props_' + str(contextLevel))

            elif isinstance(curr, stk_utils.StkLabelPseudoProperty):
                row.label(text=curr.name)

            elif isinstance(curr, stk_utils.StkEnumProperty):

                row.label(text=curr.name)

                if id in obj:
                    curr_value = obj[id]
                else:
                    curr_value = ""

                label = curr_value
                if curr_value in curr.values:
                    label = curr.values[curr_value].name

                row.menu(curr.menu_operator_name, text=label)
                #row.operator_menu_enum(curr.getOperatorName(), property="value", text=label)

                if curr_value in curr.values and len(curr.values[curr_value].subproperties) > 0:
                    box = layout.box()
                    self.recursivelyAddProperties(curr.values[curr_value].subproperties, box, obj, contextLevel)

            elif isinstance(curr, stk_utils.StkObjectReferenceProperty):

                row.label(text=curr.name)

                if curr.id in obj:
                    row.prop(obj, '["' + curr.id + '"]', text="")
                    row.menu(stk_utils.generateOpName("STK_MT_object_menu_",
                                                      curr.fullid, curr.id), text="", icon='TRIA_DOWN')
                else:
                    row.operator('screen.stk_missing_props_' + str(contextLevel))

            else:
                row.label(text=curr.name)

                # String or int or float property (Blender chooses the correct widget from the type of the ID-property)
                if curr.id in obj:
                    if "min" in dir(curr) and "max" in dir(curr) and curr.min is not None and curr.max is not None:
                        row.prop(obj, '["' + curr.id + '"]', text="", slider=True)
                    else:
                        row.prop(obj, '["' + curr.id + '"]', text="")
                else:
                    row.operator('screen.stk_missing_props_' + str(contextLevel))

# ==== OBJECT PANEL ====


class STK_PT_Object_Panel(bpy.types.Panel, PanelBase):
    bl_label = STK_PER_OBJECT_TRACK_PROPERTIES[0]
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):

        layout = self.layout

        is_track = ("is_stk_track" in context.scene and context.scene["is_stk_track"] == "true")
        is_node = ("is_stk_node" in context.scene and context.scene["is_stk_node"] == "true")
        is_kart = ("is_stk_kart" in context.scene and context.scene["is_stk_kart"] == "true")

        if not is_track and not is_kart and not is_node:
            layout.label(text="(Not a SuperTuxKart scene)")
            return

        obj = context.object

        if obj.proxy is not None:
            layout.label(text="Library nodes cannot be configured here")
            return

        if obj is not None:
            if is_track or is_node:
                properties = OrderedDict([])
                for curr in STK_PER_OBJECT_TRACK_PROPERTIES[1]:
                    properties[curr.id] = curr
                self.recursivelyAddProperties(properties, layout, obj, CONTEXT_OBJECT)

            if is_kart:
                properties = OrderedDict([])
                for curr in STK_PER_OBJECT_KART_PROPERTIES[1]:
                    properties[curr.id] = curr
                self.recursivelyAddProperties(properties, layout, obj, CONTEXT_OBJECT)


# ==== SCENE PANEL ====
class STK_PT_Scene_Panel(bpy.types.Panel, PanelBase):
    bl_label = SCENE_PROPS[0]
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        obj = context.scene

        if obj is not None:

            properties = OrderedDict([])
            for curr in SCENE_PROPS[1]:
                properties[curr.id] = curr

            self.recursivelyAddProperties(properties, layout, obj, CONTEXT_SCENE)


"""
# ==== IMAGE PANEL ====
class STK_OT_CreateImagePreview(bpy.types.Operator):
    bl_idname = ("scene.stk_create_material_preview")
    bl_label = ("STK :: create material preview")

    name: bpy.props.StringProperty()

    def execute(self, context):

        try:
            bpy.ops.texture.new()
            bpy.data.textures[-1].name = "STKPreviewTexture"
            bpy.data.textures["STKPreviewTexture"].type = 'IMAGE'
            bpy.data.textures["STKPreviewTexture"].use_preview_alpha = True
        except:
            print("Exception caught in createPreviewTexture")
            import traceback
            import sys
            traceback.print_exc(file=sys.stdout)

        return {'FINISHED'}


import os

class ImagePickerMenu(bpy.types.Menu):
    bl_idname = "STK_MT_image_menu"
    bl_label  = "SuperTuxKart Image Menu"

    def draw(self, context):
        import bpy.path

        objects = context.scene.objects

        layout = self.layout
        row = layout.row()
        col = row.column()

        blend_path = os.path.abspath(bpy.path.abspath("//"))
        is_lib_node = ('is_stk_node' in context.scene and context.scene['is_stk_node'] == 'true')

        i = 0
        for curr in bpy.data.images:

            if (curr.library is not None): continue
            if (not is_lib_node and not os.path.abspath(bpy.path.abspath(curr.filepath)).startswith(blend_path)): continue

            if (i % 20 == 0):
                col = row.column()
            i += 1
            col.operator("scene.stk_select_image", text=curr.name).name=curr.name


class STK_OT_Select_Image(bpy.types.Operator):
    bl_idname = ("scene.stk_select_image")
    bl_label = ("STK Object :: select image")

    name: bpy.props.StringProperty()

    def execute(self, context):
        global selected_image
        context.scene['selected_image'] = self.name

        if "STKPreviewTexture" not in bpy.data.textures:
            bpy.ops.scene.stk_create_material_preview()

        if "STKPreviewTexture" in bpy.data.textures:
            if self.name in bpy.data.images:
                bpy.data.textures["STKPreviewTexture"].image = bpy.data.images[self.name]
            else:
                bpy.data.textures["STKPreviewTexture"].image = None
        else:
            print("STK Panel : can't create preview texture!")

        if self.name in bpy.data.images:

            properties = OrderedDict([])
            for curr in STK_MATERIAL_PROPERTIES[1]:
                properties[curr.id] = curr

            createProperties(bpy.data.images[self.name], properties)

        return {'FINISHED'}


class STK_PT_Image_Panel(bpy.types.Panel, PanelBase):
    bl_label = STK_MATERIAL_PROPERTIES[0]
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    m_current_image = ''

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        try:
            if "STKPreviewTexture" in bpy.data.textures:
                layout.template_preview(bpy.data.textures["STKPreviewTexture"])
            else:
                layout.label(text="Sorry, no image preview available")
        except:
            layout.label(text="Sorry, no image preview available")

        label = "Select an image"
        if 'selected_image' in context.scene:
            label = context.scene['selected_image']

        self.m_op_name = "scene.stk_image_menu"
        #row.label(label)
        row.menu(self.m_op_name, text=label)

        obj = getObject(context, CONTEXT_MATERIAL)
        if obj is not None:

            properties = OrderedDict([])
            for curr in STK_MATERIAL_PROPERTIES[1]:
                properties[curr.id] = curr

            self.recursivelyAddProperties(properties, layout, obj, CONTEXT_MATERIAL)
"""

# Extension to the 'add' menu


class STK_OT_Add_Object(bpy.types.Operator):
    """Create a new SuperTuxKart Object"""
    bl_idname = ("scene.stk_add_object")
    bl_label = ("STK Object :: Add Object")
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty()

    value: bpy.props.EnumProperty(attr="values", name="values", default='banana',
                                  items=[('banana', 'Banana', 'Banana'),
                                         ('item', 'Item (Gift Box)', 'Item (Gift Box)'),
                                         ('light', 'Light', 'Light'),
                                         ('nitro_big', 'Nitro (Big)', 'Nitro (big)'),
                                         ('nitro_small', 'Nitro (Small)', 'Nitro (Small)'),
                                         ('red_flag', 'Red flag', 'Red flag'),
                                         ('blue_flag', 'Blue flag', 'Blue flag'),
                                         ('particle_emitter', 'Particle Emitter', 'Particle Emitter'),
                                         ('sfx_emitter', 'Sound Emitter', 'Sound Emitter'),
                                         ('start', 'Start position (for battle mode)',
                                                   'Start position (for battle mode)')
                                         ])

    def execute(self, context):
        if self.value == 'light':
            bpy.ops.object.add(type='LIGHT', location=context.scene.cursor.location)

            for curr in bpy.data.objects:
                if curr.type == 'LIGHT' and curr.select_get():
                    # FIXME: create associated subproperties if any
                    curr['type'] = self.value
                    break
        else:
            bpy.ops.object.add(type='EMPTY', location=context.scene.cursor.location)

            for curr in bpy.data.objects:
                if curr.type == 'EMPTY' and curr.select_get():
                    # FIXME: create associated subproperties if any
                    curr['type'] = self.value

                    if self.value == 'item':
                        curr.empty_display_type = 'CUBE'
                    elif self.value == 'nitro_big' or self.value == 'nitro_small':
                        curr.empty_display_type = 'CONE'
                    elif self.value == 'sfx_emitter':
                        curr.empty_display_type = 'SPHERE'

                    for prop in STK_PER_OBJECT_TRACK_PROPERTIES[1]:
                        if prop.name == "Type":
                            stk_utils.createProperties(curr, prop.values[self.value].subproperties)
                            break

                    break

        return {'FINISHED'}


# ======== PREFERENCES ========
class StkPanelAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = os.path.basename(os.path.dirname(__file__))

    stk_assets_path: StringProperty(
        name="Assets (data) path",
        # subtype='DIR_PATH',
    )

    stk_delete_old_files_on_export: BoolProperty(
        name="Delete all old files when exporting a track in a folder (*.spm)",
        # subtype='DIR_PATH',
    )

    stk_export_images: BoolProperty(
        name="Copy texture files when exporting a kart, track, or library node"
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="The data folder contains folders named 'karts', 'tracks', 'textures', etc.")
        layout.prop(self, "stk_assets_path")
        layout.operator('screen.stk_pick_assets_path', icon='FILEBROWSER', text="Select...")
        layout.prop(self, "stk_delete_old_files_on_export")
        layout.prop(self, "stk_export_images")


class STK_FolderPicker_Operator(bpy.types.Operator):
    bl_idname = "screen.stk_pick_assets_path"
    bl_label = "Select the SuperTuxKart assets (data) folder"

    filepath: bpy.props.StringProperty(subtype="DIR_PATH")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        import bpy.path
        import os.path
        preferences = context.preferences
        addon_prefs = preferences.addons[os.path.basename(os.path.dirname(__file__))].preferences
        addon_prefs.stk_assets_path = os.path.dirname(bpy.path.abspath(self.filepath))
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ==== QUICK EXPORT PANEL ====


class STK_PT_Quick_Export_Panel(bpy.types.Panel):
    bl_label = "Quick Exporter"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        isNotANode = ('is_stk_node' not in context.scene) or (context.scene['is_stk_node'] != 'true')
        layout = self.layout

        # ==== Types group ====
        row = layout.row()

        assets_path = context.preferences.addons[os.path.basename(
            os.path.dirname(__file__))].preferences.stk_assets_path

        if assets_path is not None and len(assets_path) > 0:
            row.label(text='Assets (data) path: ' + assets_path)
        else:
            row.label(text='Assets (data) path: [please select path]')
        row.operator('screen.stk_pick_assets_path', icon='FILEBROWSER', text="")

        if assets_path is None or len(assets_path) == 0:
            return

        # row = layout.row()
        # row.prop(the_scene, 'stk_track_export_images', text="Copy texture files")

        row = layout.row()
        row.operator("screen.stk_kart_export", text="Export Kart", icon='AUTO')

        if isNotANode:
            row.operator("screen.stk_track_export", text="Export Track", icon='TRACKING')
        else:
            row.operator("screen.stk_track_export", text="Export Library Node", icon='GROUP')

        if (assets_path is None or len(assets_path) == 0) \
                and bpy.context.mode != 'OBJECT':
            row.enabled = False


class STKPanelMixin:
    """A class mixin used for (dynamically) setting up panels, including sub-panels in Blender.

    The class contains the basic helper methods for initializing and drawing a panel, already hooked up to the
    registration logic.
    """
    PANEL_CONTEXT = 'scene'

    @classmethod
    def initialize(cls, property_group, path):
        """Initializes this panel object.
        Panels must be initialized before they get registered in Blender.

        Parameters
        ----------
        property_group : stk_props.STKPropertyGroup
            The property group that holds the data for this panel
        path : list of str
            A list describing the nested path of this panel
            Example:
            ['my_panel'] indicates that this panel is a sub-panel with the identifier 'my_panel'
            ['my_panel', 'my_nested_panel'] indicates that this panel (with the identifier 'my_nested_panel') is a
            sub-panel of the sub-panel 'my_panel'
        """
        cls.property_group = property_group
        cls.path = path
        cls.subpanels = []  # Hold the reference to sub-panels (for proper release)

        definitions = property_group.ui_definitions
        info = None

        # Search the property infos for the properties of this panels by traversing the path
        for n in path:
            if n in definitions:
                info = definitions[n]
                definitions = definitions[n].properties
            else:
                definitions = OrderedDict()
                break

        cls.ui_definitions = definitions
        cls.info = info

    @classmethod
    def generate_subpanel(cls, id, info):
        """Dynamically create panel class that should be nested (sub-panel) and register it.

        Parameters
        ----------
        id : str
            Panel identifier
        info : stk_props.STKPropertyGroup.PanelInfo
            Panel data container
        """
        from bpy.utils import register_class

        panel_options = set()

        # Has no label, so hide the header
        if not info.label:
            panel_options.add('HIDE_HEADER')

        # Is not expanded, collapse on init
        if not info.expanded:
            panel_options.add('DEFAULT_CLOSED')

        panel = type(
            f"{cls.__name__}_{id}",
            (bpy.types.Panel, STKPanelMixin),
            {
                'bl_idname': f"{getattr(cls, 'bl_idname')}_{id}",
                'bl_space_type': getattr(cls, 'bl_space_type'),
                'bl_region_type': getattr(cls, 'bl_region_type'),
                'bl_context': getattr(cls, 'bl_context'),
                'bl_label': info.label if info.label else "",
                'bl_options': panel_options,
                'bl_parent_id': getattr(cls, 'bl_idname')
            }
        )

        # Initialize and register generated panel, extending the path
        cls.subpanels.append(panel)
        panel.PANEL_CONTEXT = cls.PANEL_CONTEXT
        panel.initialize(cls.property_group, [*cls.path, id])
        register_class(panel)

    @classmethod
    def create_subpanels(cls):
        """Create all sub-panels of this panel.
        Will destroy and clean up sub-panels that already exists and handles registration.
        """
        if len(cls.subpanels) > 0:
            cls.destroy_subpanels()

        for prop, info in cls.ui_definitions.items():
            if isinstance(info, cls.property_group.PanelInfo):
                cls.generate_subpanel(prop, info)

    @classmethod
    def destroy_subpanels(cls):
        """Destroy and clean up all sub-panels of this panel and unregisters them.
        """
        from bpy.utils import unregister_class

        if not hasattr(cls, 'subpanels'):
            return

        for panel in cls.subpanels:
            unregister_class(panel)

        cls.subpanels.clear()

    @classmethod
    def register(cls):
        """Will forward the call to start create all necessary sub-panels.
        Override this class method for the initial (main) panel for more control.
        """
        cls.create_subpanels()

    @classmethod
    def unregister(cls):
        """Will forward the call to destroy and clean up all necessary sub-panels.
        Override this class method for the initial (main) panel for more control.
        """
        cls.destroy_subpanels()

    @classmethod
    def poll(cls, context):
        """Default panel poll method.
        Will evaluate the assigned conditions of its panel info (data).

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        bool
            Value indicating if this panel should be rendered or not
        """
        if cls.info:
            p_stk = stk_utils.get_stk_context(context, cls.PANEL_CONTEXT)
            return p_stk.condition_poll(cls.info) if p_stk else False

        return True

    def draw(self, context):
        """Default panel draw method.
        Will iterate through its assigned properties and draw them from the provided property group.

        Parameters
        ----------
        context : bpy.context
            The Blender context object
        """
        cls = self.__class__
        layout = self.layout
        p_stk = stk_utils.get_stk_context(context, cls.PANEL_CONTEXT)

        # Nested function for easier recursion
        def draw_props(layout, definitions):
            for prop, info in definitions.items():
                # Not displaying panel or conditionally excluded properties
                if isinstance(info, stk_props.STKPropertyGroup.PanelInfo) or not p_stk.condition_poll(info):
                    continue

                # Draw box containing properties
                elif isinstance(info, stk_props.STKPropertyGroup.BoxInfo):
                    draw_props(layout.box(), info.properties)

                # Draw separator
                elif isinstance(info, stk_props.STKPropertyGroup.SeparatorInfo):
                    layout.separator(factor=info.factor)

                # Draw property with an id property template
                elif isinstance(info, stk_props.STKPropertyGroup.IDPropertyInfo):
                    col = layout.column()
                    col.label(text=info.label)
                    col.template_ID(
                        data=p_stk,
                        property=prop,
                        new=info.operator_new,
                        open=info.operator_open,
                        unlink=info.operator_unlink
                    )

                # Draw property or label
                else:
                    if hasattr(p_stk, prop):
                        layout.use_property_split = True
                        layout.use_property_decorate = False
                        layout.prop(data=p_stk, property=prop)
                    else:
                        layout.label(text=info.label)

        # Recursively drawing properties
        draw_props(layout, cls.ui_definitions)


class STK_PT_SceneProperties(bpy.types.Panel, STKPanelMixin):
    """SuperTuxKart scene properties panel.
    """
    bl_idname = 'STK_PT_scene_properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    bl_label = "SuperTuxKart Scene Properties"

    @classmethod
    def load_panel(cls, property_group):
        """Cleanly load this panel by providing a corresponding property group reference.

        Parameters
        ----------
        property_group : stk.props.STKPropertyGroup
            The corresponding property group (must be fully initialized, but not yet registered)
        """
        from bpy.utils import register_class

        register_class(property_group)

        # Use the scene context for this panel
        # Initialize and build sub-panels
        cls.initialize(property_group, [])
        cls.create_subpanels()

    @classmethod
    def unload_panel(cls):
        """Cleanly unload this panel and its resources.
        """
        from bpy.utils import unregister_class

        # Clean up and unregister
        cls.destroy_subpanels()
        unregister_class(cls.property_group)

    @classmethod
    def register(cls):
        """Blender register callback.
        """
        cls.PANEL_CONTEXT = 'scene'

        # Important: initialize before any register call!
        stk_props.STKScenePropertyGroup.initialize()
        cls.load_panel(stk_props.STKScenePropertyGroup)

    @classmethod
    def unregister(cls):
        """Blender unregister callback.
        """
        cls.unload_panel()

    @classmethod
    def poll(cls, context):
        """Panel poll method.
        Only display this panel if the active object is of type 'MESH' or 'EMPTY'.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        return context.scene


class STK_PT_ObjectProperties(bpy.types.Panel, STKPanelMixin):
    """SuperTuxKart object properties panel.
    """
    bl_idname = 'STK_PT_object_properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_label = "SuperTuxKart Object Properties"

    @classmethod
    def load_panel(cls, property_group):
        """Cleanly load this panel by providing a corresponding property group reference.

        Parameters
        ----------
        property_group : stk.props.STKPropertyGroup
            The corresponding property group (must be fully initialized, but not yet registered)
        """
        from bpy.utils import register_class

        register_class(property_group)

        # Use the object context for this panel
        # Initialize and build sub-panels
        cls.initialize(property_group, [])
        cls.create_subpanels()

    @classmethod
    def unload_panel(cls):
        """Cleanly unload this panel and its resources.
        """
        from bpy.utils import unregister_class

        # Clean up and unregister
        cls.destroy_subpanels()

        if hasattr(cls, 'property_group'):
            unregister_class(cls.property_group)

    @classmethod
    def register(cls):
        """Blender register callback.
        """
        from bpy.utils import register_class

        cls.PANEL_CONTEXT = 'object'

        # Important: initialize before any register call!
        stk_props.STKKartObjectPropertyGroup.initialize()
        stk_props.STKTrackObjectPropertyGroup.initialize()
        stk_props.STKLibraryObjectPropertyGroup.initialize()

        register_class(cls.STK_OT_ReloadObjectProperties)

    @classmethod
    def unregister(cls):
        """Blender unregister callback.
        """
        from bpy.utils import unregister_class

        cls.unload_panel()
        unregister_class(cls.STK_OT_ReloadObjectProperties)

    @classmethod
    def poll(cls, context):
        """Panel poll method.
        Only display this panel if the active object is of type 'MESH' or 'EMPTY'.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        bool
            Value indicating if this panel should be rendered or not
        """
        if stk_utils.get_stk_scene_type(context) == 'none':
            return False

        obj = context.active_object
        return obj and (obj.type == 'MESH' or obj.type == 'EMPTY')

    def draw(self, context):
        """Panel draw method.
        Check if the object panel properties and definitions have been initialized. Display the operator to do so if
        not; otherwise continue by calling the default draw method.

        Parameters
        ----------
        context : bpy.context
            The Blender context object
        """
        layout = self.layout
        p_stk = stk_utils.get_stk_context(context, self.PANEL_CONTEXT)

        if not p_stk:
            stk_scene = stk_utils.get_stk_scene_type(context)
            layout.operator('stk.reload_object_properties', text=f"Setup {stk_scene.title()} Properties")
        else:
            super().draw(context)

    class STK_OT_ReloadObjectProperties(bpy.types.Operator):
        """Operator that will conditionally reload this panel.
        Loads the panel with the correct property group assigned, specified by the STK scene type.
        """
        bl_idname = 'stk.reload_object_properties'
        bl_label = "Reload STK Object Properties"
        bl_description = "Reload and setup the object properties panel. This needs to be done every time the scene " \
                         "type changes. No worries, the values of the properties will still be saved for every " \
                         "object. This is for setting up the UI layout for this panel."

        def execute(self, context):
            """Executes this operator.

            Parameters
            ----------
            context : bpy.context
                Blender context object

            Returns
            -------
            set of str
                The result of the operator
            """
            stk_scene = stk_utils.get_stk_scene_type(context)
            property_group = None

            if stk_scene == 'kart':
                property_group = stk_props.STKKartObjectPropertyGroup
            elif stk_scene == 'track':
                property_group = stk_props.STKTrackObjectPropertyGroup
            elif stk_scene == 'library':
                property_group = stk_props.STKLibraryObjectPropertyGroup
            else:
                return {'CANCELLED'}

            panel = STK_PT_ObjectProperties

            # Need to reload?
            if hasattr(panel, 'property_group'):
                if panel.property_group is not property_group:
                    panel.unload_panel()
                    panel.load_panel(property_group)
            else:
                panel.load_panel(property_group)

            return {'FINISHED'}
