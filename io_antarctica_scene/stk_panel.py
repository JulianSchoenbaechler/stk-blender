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
from collections import OrderedDict
from bpy.props import PointerProperty
from . import stk_utils, stk_props


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
            return p_stk.condition_poll(cls.info, context) if p_stk else False

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
                if isinstance(info, stk_props.STKPropertyGroup.PanelInfo) or not p_stk.condition_poll(info, context):
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
        Only display this panel if a scene is loaded.

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

            # Delete property_group reference as it can be dynamic for object properties
            # On an add-on reload the reference may survive and therefore the property group gets detected as already
            # existing. With that, the property group never 'reloads'.
            del cls.property_group

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
        elif context.object.proxy is not None:
            layout.label(text="Library nodes can not be configured here.")
        elif context.object.data and context.object.data.users >= 2:
            layout.label(text="This object properties are linked!")
            super().draw(context)
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


class STK_PT_LightProperties(bpy.types.Panel, STKPanelMixin):
    """SuperTuxKart light properties panel.
    """
    bl_idname = 'STK_PT_light_properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = "SuperTuxKart Light Properties"

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
        cls.PANEL_CONTEXT = 'light'

        # Important: initialize before any register call!
        stk_props.STKLightPropertyGroup.initialize()
        # pylint: disable=assignment-from-no-return
        stk_props.STKLightPropertyGroup.__annotations__['type'] = PointerProperty(
            type=bpy.types.Light,
            name="Light Type",
            description="The light type",
            options=set()
        )
        cls.load_panel(stk_props.STKLightPropertyGroup)

    @classmethod
    def unregister(cls):
        """Blender unregister callback.
        """
        cls.unload_panel()

    @classmethod
    def poll(cls, context):
        """Panel poll method.
        Only display this panel if a light is currently selected.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        t = stk_utils.get_stk_scene_type(context)
        return context.light and t != 'none' and t != 'kart'

    def draw(self, context):
        """Panel draw method.
        Check if the type of light can be exported as STK light.

        Parameters
        ----------
        context : bpy.context
            The Blender context object
        """
        if context.light.type != 'POINT' and context.light.type != 'SUN':
            self.layout.label(text="SuperTuxKart does not support this type of light.")
        else:
            super().draw(context)


class STK_PT_CameraProperties(bpy.types.Panel, STKPanelMixin):
    """SuperTuxKart camera properties panel.
    """
    bl_idname = 'STK_PT_camera_properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = "SuperTuxKart Camera Properties"

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
        cls.PANEL_CONTEXT = 'camera'

        # Important: initialize before any register call!
        stk_props.STKCameraPropertyGroup.initialize()
        cls.load_panel(stk_props.STKCameraPropertyGroup)

    @classmethod
    def unregister(cls):
        """Blender unregister callback.
        """
        cls.unload_panel()

    @classmethod
    def poll(cls, context):
        """Panel poll method.
        Only display this panel if a camera is currently selected.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        return context.camera and stk_utils.get_stk_scene_type(context) == 'track'


class STK_PT_MaterialProperties(bpy.types.Panel, STKPanelMixin):
    """SuperTuxKart material properties panel.
    """
    bl_idname = 'STK_PT_material_properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'
    bl_label = "SuperTuxKart Material Properties"

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
        cls.PANEL_CONTEXT = 'material'

        # Important: initialize before any register call!
        stk_props.STKMaterialPropertyGroup.initialize()
        cls.load_panel(stk_props.STKMaterialPropertyGroup)

    @classmethod
    def unregister(cls):
        """Blender unregister callback.
        """
        cls.unload_panel()

    @classmethod
    def poll(cls, context):
        """Panel poll method.
        Only display this panel if the active material uses one of the Antarctica shaders.

        Parameters
        ----------
        context : bpy.context
            The Blender context object

        Returns
        -------
        AnyType
            Value indicating if this panel should be rendered or not
        """
        if not context.material or not context.material.use_nodes or stk_utils.get_stk_scene_type(context) == 'none':
            return False

        return stk_utils.is_stk_material(context.material.node_tree)
