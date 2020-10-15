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


class AntarcticaSolidPBR(bpy.types.ShaderNodeCustomGroup):
    """Antarctica solid physical based rendering shader node.

    Represents a shader node that simulates the solid physical based shader in the 'Antarctica' render pipeline of
    SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaSolidPBR'
    bl_label = 'Antarctica Solid PBR'
    bl_description = "Simulates the SuperTuxKart Solid PBR shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_colorizable(self):
        """Get the colorizable toggle."""
        return self.node_tree.nodes['Colorizable'].outputs[0].default_value == 1.0

    def __set_colorizable(self, value):
        """Set the colorizable toggle."""
        self.node_tree.nodes['Colorizable'].outputs[0].default_value = 1.0 if value is True else 0.0

    def __get_hue(self):
        """Get the currently displayed hue value."""
        return self.node_tree.nodes['Hue'].outputs[0].default_value

    def __set_hue(self, value):
        """Set the currently displayed hue value."""
        self.node_tree.nodes['Hue'].outputs[0].default_value = value

    # Colorization and hue properties

    prop_colorizable: bpy.props.BoolProperty(
        name='Colorizable',
        default=False,
        get=__get_colorizable,
        set=__set_colorizable
    )
    prop_colorizationFactor: bpy.props.FloatProperty(
        name='Colorization Factor',
        default=0.0,
        soft_min=0.0,
        precision=3
    )
    prop_hue: bpy.props.FloatProperty(
        name='Hue',
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        precision=3,
        get=__get_hue,
        set=__set_hue
    )
    prop_hueSelect: bpy.props.StringProperty(
        name='Hue Selection',
        default=''
    )

    @staticmethod
    def setup_basecolor(nt, nd_mainTex, nd_colorizable, nd_colorizationMask, nd_hue):
        """Setup a node tree in a given node group object and return the node socket that represents the color output.
        This is the default base color for simulating the Antarctica PBR shader.

        Args:
            nt (bpy.types.ShaderNodeTree): The node tree which should be populated
            nd_mainTex (bpy.types.ShaderNodeTexImage): The image texture node that provides the main material texture
            nd_colorizable (bpy.types.ShaderNodeValue): A value node used as multiplier for the colorization amount
            nd_colorizationMask (bpy.types.ShaderNodeTexImage): The image texture node that provides the colorization
                mask for this material
            nd_hue (bpy.types.ShaderNodeValue): A value node used for colorization hue shift

        Returns:
            bpy.types.NodeSocketColor: An output node socket with the resulting color
        """
        nd_saturation = nt.nodes.new('ShaderNodeHueSaturation')
        nd_hue_add = nt.nodes.new('ShaderNodeMath')
        nd_colorize_multiply = nt.nodes.new('ShaderNodeMath')
        nd_colorize_add = nt.nodes.new('ShaderNodeMath')
        nd_colorize_subtract = nt.nodes.new('ShaderNodeMath')
        nd_vertex = nt.nodes.new('ShaderNodeVertexColor')
        nd_vertex_gt = nt.nodes.new('ShaderNodeMath')
        nd_vertex_mix = nt.nodes.new('ShaderNodeMixRGB')

        nd_hue_add.operation = 'ADD'
        nd_hue_add.inputs[1].default_value = 0.5

        nd_colorize_multiply.operation = 'MULTIPLY'
        nd_colorize_multiply.use_clamp = True
        nd_colorize_add.operation = 'ADD'
        nd_colorize_add.use_clamp = True
        nd_colorize_subtract.operation = 'SUBTRACT'
        nd_colorize_subtract.use_clamp = True
        nd_colorize_subtract.inputs[0].default_value = 1.0

        nd_vertex.outputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        nd_vertex_gt.operation = 'GREATER_THAN'
        nd_vertex_gt.use_clamp = True
        nd_vertex_gt.inputs[1].default_value = 0.0
        nd_vertex_mix.blend_type = 'MULTIPLY'
        nd_vertex_mix.inputs['Fac'].default_value = 1.0

        # Hue/saturation hue input
        nt.links.new(nd_hue_add.outputs[0], nd_saturation.inputs['Hue'])
        nt.links.new(nd_hue.outputs[0], nd_hue_add.inputs[0])

        # Hue/stauration factor input
        nt.links.new(nd_colorize_multiply.outputs[0], nd_saturation.inputs['Fac'])
        nt.links.new(nd_colorize_add.outputs[0], nd_colorize_multiply.inputs[0])
        nt.links.new(nd_colorizable.outputs[0], nd_colorize_multiply.inputs[1])
        nt.links.new(nd_colorize_subtract.outputs[0], nd_colorize_add.inputs[0])
        nt.links.new(nd_colorizationMask.outputs['Color'], nd_colorize_add.inputs[1])
        nt.links.new(nd_mainTex.outputs['Alpha'], nd_colorize_subtract.inputs[1])

        # Hue/stauration color input
        nt.links.new(nd_vertex_mix.outputs[0], nd_saturation.inputs['Color'])
        nt.links.new(nd_mainTex.outputs['Color'], nd_vertex_mix.inputs['Color1'])
        nt.links.new(nd_vertex_gt.outputs[0], nd_vertex_mix.inputs['Fac'])
        nt.links.new(nd_vertex.outputs['Color'], nd_vertex_gt.inputs[0])
        nt.links.new(nd_vertex.outputs['Color'], nd_vertex_mix.inputs['Color2'])

        return nd_saturation.outputs[0]

    @staticmethod
    def setup_datamap(nt, nd_mainTex, nd_dataMap):
        """Setup a node tree in a given node group object and return a tuple containing the node sockets that represents
        the data output values 'specular', 'diffuse' and 'emission'.
        This is the default data interpretation for simulating the Antarctica PBR shader.

        Args:
            nt (bpy.types.ShaderNodeTree): The node tree which should be populated
            nd_mainTex (bpy.types.ShaderNodeTexImage): The image texture node that provides the main material texture
            nd_dataMap (bpy.types.ShaderNodeTexImage): The image texture node that provides the data map texture

        Returns:
            (bpy.types.NodeSocketFloat, bpy.types.NodeSocketFloat, bpy.types.NodeSocketColor):
                The output node sockets for (specular, diffuse, emission)
        """
        nd_gloss_separate = nt.nodes.new('ShaderNodeSeparateRGB')
        nd_diffuse_invert = nt.nodes.new('ShaderNodeMath')
        nd_emission_mix = nt.nodes.new('ShaderNodeMixRGB')

        nd_diffuse_invert.operation = 'SUBTRACT'
        nd_diffuse_invert.use_clamp = True
        nd_diffuse_invert.inputs[0].default_value = 1.0
        nd_emission_mix.blend_type = 'MIX'
        nd_emission_mix.use_clamp = True
        nd_emission_mix.inputs['Color1'].default_value = (0.0, 0.0, 0.0, 0.0)

        nt.links.new(nd_gloss_separate.outputs['G'], nd_diffuse_invert.inputs[1])
        nt.links.new(nd_gloss_separate.outputs['B'], nd_emission_mix.inputs['Fac'])
        nt.links.new(nd_dataMap.outputs['Color'], nd_gloss_separate.inputs[0])
        nt.links.new(nd_mainTex.outputs['Color'], nd_emission_mix.inputs['Color2'])

        # Return (specular, diffuse, emission)
        return (nd_gloss_separate.outputs['R'], nd_diffuse_invert.outputs[0], nd_emission_mix.outputs[0])

    @staticmethod
    def setup_normal(nt, nd_normalMap):
        """Setup a node tree in a given node group object and return  the node socket that represents the materials
        normal vector.
        This is the default normals calculation for simulating the Antarctica PBR shader.

        Args:
            nt (bpy.types.ShaderNodeTree): The node tree which should be populated
            nd_normalMap (bpy.types.ShaderNodeTexImage): The image texture node that provides the normal map texture

        Returns:
            bpy.types.NodeSocketVector: The output node socket for the materials normal
        """
        nd_normal_mapping = nt.nodes.new('ShaderNodeNormalMap')
        nd_normal_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_normal_gt = nt.nodes.new('ShaderNodeMath')

        nd_normal_mix.blend_type = 'MIX'
        nd_normal_mix.inputs['Color1'].default_value = (0.5, 0.5, 1.0, 1.0)
        nd_normal_gt.operation = 'GREATER_THAN'
        nd_normal_gt.use_clamp = True
        nd_normal_gt.inputs[1].default_value = 0.0

        nt.links.new(nd_normal_mix.outputs[0], nd_normal_mapping.inputs['Color'])
        nt.links.new(nd_normal_gt.outputs[0], nd_normal_mix.inputs['Fac'])
        nt.links.new(nd_normalMap.outputs['Color'], nd_normal_gt.inputs[0])
        nt.links.new(nd_normalMap.outputs['Color'], nd_normal_mix.inputs['Color2'])

        return nd_normal_mapping.outputs[0]

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        ntname = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(ntname, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')
        nd_principled = nt.nodes.new('ShaderNodeBsdfPrincipled')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

        # Image texture for PBR data (gloss) map
        nd_dataMap = nt.nodes.new('ShaderNodeTexImage')
        nd_dataMap.name = 'Data Map'

        # PBR data maps color is treated as data
        if nd_dataMap.image:
            nd_dataMap.image.colorspace_settings.is_data = True

        # Image texture for normal map
        nd_normalMap = nt.nodes.new('ShaderNodeTexImage')
        nd_normalMap.name = 'Normal Map'

        # Normal maps color is treated as data
        if nd_normalMap.image:
            nd_normalMap.image.colorspace_settings.is_data = True

        # Image texture for colorization mask
        nd_colorizationMask = nt.nodes.new('ShaderNodeTexImage')
        nd_colorizationMask.name = 'Colorization Mask'

        # Colorization multiplier (for masking/enabling colorization)
        nd_colorizable = nt.nodes.new('ShaderNodeValue')
        nd_colorizable.name = 'Colorizable'
        nd_colorizable.outputs[0].default_value = 0.0

        # Colorization hue
        nd_hue = nt.nodes.new('ShaderNodeValue')
        nd_hue.name = 'Hue'
        nd_hue.outputs[0].default_value = 0.0

        nt.links.new(nd_principled.outputs[0], nd_output.inputs[0])

        nds_basecolor = self.setup_basecolor(nt, nd_mainTex, nd_colorizable, nd_colorizationMask, nd_hue)
        nds_pbr = self.setup_datamap(nt, nd_mainTex, nd_dataMap)
        nds_normal = self.setup_normal(nt, nd_normalMap)

        nt.links.new(nds_basecolor, nd_principled.inputs['Base Color'])
        nt.links.new(nds_pbr[0], nd_principled.inputs['Specular'])
        nt.links.new(nds_pbr[1], nd_principled.inputs['Metallic'])
        nt.links.new(nds_pbr[1], nd_principled.inputs['Roughness'])
        nt.links.new(nds_pbr[2], nd_principled.inputs['Emission'])
        nt.links.new(nds_normal, nd_principled.inputs['Normal'])

        # Assign generated node tree
        self.node_tree = nt

    def copy(self, node):
        """Initialize a new instance of this node from an existing node."""
        self.node_tree = node.node_tree.copy()

    def free(self):
        """Clean up node on removal"""
        bpy.data.node_groups.remove(self.node_tree, do_unlink=True)

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row(align=True).split(factor=0.3)
        prop_layout.label(text='Main Texture')
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')

        # Data (gloss) map texture
        prop_layout = layout.row(align=True).split(factor=0.3)
        prop_layout.label(text='Data Map')
        prop_layout.template_ID(self.node_tree.nodes['Data Map'], 'image', new='image.new', open='image.open')

        # Normal map texture
        prop_layout = layout.row(align=True).split(factor=0.3)
        prop_layout.label(text='Normal Map')
        prop_layout.template_ID(self.node_tree.nodes['Normal Map'], 'image', new='image.new', open='image.open')

        layout.separator()

        # Colorization properties
        layout.prop(self, 'prop_colorizable')

        if self.prop_colorizable is True:
            prop_layout = layout.row(align=True).split(factor=0.3)
            prop_layout.label(text='Colorization Mask')
            prop_layout.template_ID(
                self.node_tree.nodes['Colorization Mask'],
                'image',
                new='image.new',
                open='image.open'
            )

            layout.prop(self, 'prop_colorizationFactor')
            layout.prop(self, 'prop_hue')
            prop_layout = layout.row(align=True).split(factor=0.3)
            prop_layout.label(text='Hue Selection')
            prop_layout.prop(self, 'prop_hueSelect', text='')


class AntarcticaCutoutPBR(bpy.types.ShaderNodeCustomGroup):
    """
    Represents a shader node that simulates the cutout (alpha-test) physical based shader in the 'Antarctica' render
    pipeline of SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaCutoutPBR'
    bl_label = 'Antarctica Cutout PBR'
    bl_description = "Simulates the SuperTuxKart Cutout PBR shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_colorizable(self):
        """Internal getter of the colorizable toggle."""
        return self.node_tree.nodes['Colorizable'].outputs[0].default_value == 1.0

    def __set_colorizable(self, value):
        """Internal setter of the colorizable toggle."""
        self.node_tree.nodes['Colorizable'].outputs[0].default_value = 1.0 if value is True else 0.0

    def __get_hue(self):
        """Internal getter of the currently displayed hue value."""
        return self.node_tree.nodes['Hue'].outputs[0].default_value

    def __set_hue(self, value):
        """Internal setter of the currently displayed hue value."""
        self.node_tree.nodes['Hue'].outputs[0].default_value = value

    # Colorization and hue properties

    prop_colorizable: bpy.props.BoolProperty(
        name='Colorizable',
        default=False,
        get=__get_colorizable,
        set=__set_colorizable
    )
    prop_colorizationFactor: bpy.props.FloatProperty(
        name='Colorization Factor',
        default=0.0,
        soft_min=0.0,
        precision=3
    )
    prop_hue: bpy.props.FloatProperty(
        name='Hue',
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        precision=3,
        get=__get_hue,
        set=__set_hue
    )
    prop_hueSelect: bpy.props.StringProperty(
        name='Hue Selection',
        default=''
    )

    @staticmethod
    def setup_basecolor(nt, nd_mainTex, nd_colorizable, nd_hue):
        """Setup a node tree in a given node group object and return the node socket that represents the color output.
        This is the default base color for simulating the Antarctica PBR shader.

        Args:
            nt (bpy.types.ShaderNodeTree): The node tree which should be populated
            nd_mainTex (bpy.types.ShaderNodeTexImage): The image texture node that provides the main material texture
            nd_colorizable (bpy.types.ShaderNodeValue): A value node used as multiplier for the colorization amount
            nd_hue (bpy.types.ShaderNodeValue): A value node used for colorization hue shift

        Returns:
            (bpy.types.NodeSocketColor, bpy.types.NodeSocketFloat): The output node sockets for (color, alpha)
        """
        nd_saturation = nt.nodes.new('ShaderNodeHueSaturation')
        nd_hue_add = nt.nodes.new('ShaderNodeMath')
        nd_vertex = nt.nodes.new('ShaderNodeVertexColor')
        nd_vertex_gt = nt.nodes.new('ShaderNodeMath')
        nd_vertex_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_alpha_compare = nt.nodes.new('ShaderNodeMath')

        nd_hue_add.operation = 'ADD'
        nd_hue_add.inputs[1].default_value = 0.5

        nd_vertex.outputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        nd_vertex_gt.operation = 'GREATER_THAN'
        nd_vertex_gt.use_clamp = True
        nd_vertex_gt.inputs[1].default_value = 0.0
        nd_vertex_mix.blend_type = 'MULTIPLY'
        nd_vertex_mix.inputs['Fac'].default_value = 1.0

        nd_alpha_compare.operation = 'COMPARE'
        nd_alpha_compare.use_clamp = True
        nd_alpha_compare.inputs[1].default_value = 1.0

        # Hue/saturation hue input
        nt.links.new(nd_hue_add.outputs[0], nd_saturation.inputs['Hue'])
        nt.links.new(nd_hue.outputs[0], nd_hue_add.inputs[0])

        # Hue/stauration factor input
        nt.links.new(nd_colorizable.outputs[0], nd_saturation.inputs['Fac'])

        # Hue/stauration color input
        nt.links.new(nd_vertex_mix.outputs[0], nd_saturation.inputs['Color'])
        nt.links.new(nd_mainTex.outputs['Color'], nd_vertex_mix.inputs['Color1'])
        nt.links.new(nd_vertex_gt.outputs[0], nd_vertex_mix.inputs['Fac'])
        nt.links.new(nd_vertex.outputs['Color'], nd_vertex_gt.inputs[0])
        nt.links.new(nd_vertex.outputs['Color'], nd_vertex_mix.inputs['Color2'])

        # Alpha value input
        nt.links.new(nd_mainTex.outputs['Alpha'], nd_alpha_compare.inputs[0])

        return (nd_saturation.outputs[0], nd_alpha_compare.outputs[0])

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        ntname = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(ntname, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')
        nd_principled = nt.nodes.new('ShaderNodeBsdfPrincipled')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

        # Image texture for PBR data (gloss) map
        nd_dataMap = nt.nodes.new('ShaderNodeTexImage')
        nd_dataMap.name = 'Data Map'

        # PBR data maps color is treated as data
        if nd_dataMap.image:
            nd_dataMap.image.colorspace_settings.is_data = True

        # Colorization multiplier (for masking/enabling colorization)
        nd_colorizable = nt.nodes.new('ShaderNodeValue')
        nd_colorizable.name = 'Colorizable'
        nd_colorizable.outputs[0].default_value = 0.0

        # Colorization hue
        nd_hue = nt.nodes.new('ShaderNodeValue')
        nd_hue.name = 'Hue'
        nd_hue.outputs[0].default_value = 0.0

        nt.links.new(nd_principled.outputs[0], nd_output.inputs[0])

        nds_basecolor = self.setup_basecolor(nt, nd_mainTex, nd_colorizable, nd_hue)
        nds_pbr = AntarcticaSolidPBR.setup_datamap(nt, nd_mainTex, nd_dataMap)

        nt.links.new(nds_basecolor[0], nd_principled.inputs['Base Color'])
        nt.links.new(nds_basecolor[1], nd_principled.inputs['Alpha'])
        nt.links.new(nds_pbr[0], nd_principled.inputs['Specular'])
        nt.links.new(nds_pbr[1], nd_principled.inputs['Metallic'])
        nt.links.new(nds_pbr[1], nd_principled.inputs['Roughness'])
        nt.links.new(nds_pbr[2], nd_principled.inputs['Emission'])

        # Assign generated node tree
        self.node_tree = nt

    def copy(self, node):
        """Initialize a new instance of this node from an existing node."""
        self.node_tree = node.node_tree.copy()

    def free(self):
        """Clean up node on removal"""
        bpy.data.node_groups.remove(self.node_tree, do_unlink=True)

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row(align=True).split(factor=0.3)
        prop_layout.label(text='Main Texture')
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')

        # Data (gloss) map texture
        prop_layout = layout.row(align=True).split(factor=0.3)
        prop_layout.label(text='Data Map')
        prop_layout.template_ID(self.node_tree.nodes['Data Map'], 'image', new='image.new', open='image.open')

        layout.separator()

        # Colorization properties
        layout.prop(self, 'prop_colorizable')

        if self.prop_colorizable is True:
            layout.prop(self, 'prop_colorizationFactor')
            layout.prop(self, 'prop_hue')
            prop_layout = layout.row(align=True).split(factor=0.3)
            prop_layout.label(text='Hue Selection')
            prop_layout.prop(self, 'prop_hueSelect', text='')
