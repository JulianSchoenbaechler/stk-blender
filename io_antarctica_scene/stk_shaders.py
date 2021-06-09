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
from bpy.props import (BoolProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       StringProperty,
                       PointerProperty)
from bpy.types import (NodeTree,
                       NodeSocket)

# The specular value of the PBR calculations are hardcoded, see:
# https://github.com/supertuxkart/stk-code/commit/dfed11c6a8e59b791f18f3b228f4527451b751a6
# STK actually is not quite fully PBR yet
PBR_SPECULAR_VALUE = 0.04


class AntarcticaMixin:
    """A mixin that every Antarctica shader node must implement. It defines default getter/setter callbacks that can be
    used. It also declares the main texture property: STK's material properties are always bound to one main texture.
    """
    bl_width_default = 340
    bl_width_min = 250

    def _get_colorizable(self):
        """Internal getter of the colorizable toggle."""
        return self.node_tree.nodes['Colorizable'].outputs[0].default_value == 1.0

    def _set_colorizable(self, value: bool):
        """Internal setter of the colorizable toggle."""
        self.node_tree.nodes['Colorizable'].outputs[0].default_value = 1.0 if value else 0.0

    def _get_colorization_factor(self):
        """Internal getter of the colorization factor."""
        return self.node_tree.nodes['Colorization Factor'].outputs[0].default_value

    def _set_colorization_factor(self, value: bool):
        """Internal setter of the colorization factor."""
        self.node_tree.nodes['Colorization Factor'].outputs[0].default_value = value

    def _get_hue(self):
        """Internal getter of the currently displayed hue value."""
        return self.node_tree.nodes['Hue'].outputs[0].default_value

    def _set_hue(self, value: float):
        """Internal setter of the currently displayed hue value."""
        self.node_tree.nodes['Hue'].outputs[0].default_value = value

    def _get_mask(self):
        """Internal getter of the alpha mask toggle."""
        return self.node_tree.nodes['Mask Influence'].outputs[0].default_value == 1.0

    def _set_mask(self, value: bool):
        """Internal setter of the alpha mask toggle."""
        self.node_tree.nodes['Mask Influence'].outputs[0].default_value = 1.0 if value else 0.0

    def _get_texture(self, name: str):
        """Internal getter for texture images.

        Parameters
        ----------
        name : str
            The name of the image node to access

        Returns
        -------
        bpy.types.Image
            The image reference of the texture
        """
        image_node = self.node_tree.nodes.get(name)
        return image_node.image if image_node else None

    def _set_texture(self, name: str, image: bpy.types.Image):
        """Internal setter for texture images.

        Parameters
        ----------
        name : str
            The name of the image node to access
        image : bpy.types.Image
            The image reference
        """
        image_node = self.node_tree.nodes.get(name)

        if image_node:
            image_node.image = image

    def __update_main(self, context):
        """Update callback for main texture property."""
        print(self.main_texture)
        self._set_texture('Main Texture', self.main_texture)

    # Every shader node always has a main texture
    main_texture: PointerProperty(
        type=bpy.types.Image,
        name="Main Texture",
        update=__update_main
    )

    def copy(self, node):
        """Initialize a new instance of this node from an existing node."""
        self.node_tree = node.node_tree.copy()

    def free(self):
        """Clean up node on removal"""
        self.node_tree.nodes.clear()
        bpy.data.node_groups.remove(self.node_tree, do_unlink=True)


class AntarcticaSolidPBR(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """Represents a shader node that simulates the solid physical based shader in the 'Antarctica' render pipeline of
    SuperTuxKart. This class also stores shader specific properties for export.
    """
    bl_name = 'AntarcticaSolidPBR'
    bl_label = "Antarctica Solid PBR"
    bl_description = "Simulates the SuperTuxKart Solid PBR shader"

    def __update_data(self, context):
        self._set_texture('Data Map', self.data_map)

    def __update_normal(self, context):
        self._set_texture('Normal Map', self.normal_map)

    def __update_colorization(self, context):
        self._set_texture('Colorization Mask', self.colorization_mask)

    # Texture properties
    data_map: PointerProperty(
        type=bpy.types.Image,
        name="Data Map",
        update=__update_data
    )
    normal_map: PointerProperty(
        type=bpy.types.Image,
        name="Normal Map",
        update=__update_normal
    )
    colorization_mask: PointerProperty(
        type=bpy.types.Image,
        name="Colorization Mask",
        update=__update_colorization
    )

    # Colorization and hue properties
    colorizable: BoolProperty(
        name="Colorizable",
        default=False,
        get=AntarcticaMixin._get_colorizable,
        set=AntarcticaMixin._set_colorizable
    )
    colorization_factor: FloatProperty(
        name="Colorization Factor",
        default=0.0,
        min=0.0,
        max=2.5,
        soft_min=0.0,
        soft_max=1.2,
        precision=3,
        get=AntarcticaMixin._get_colorization_factor,
        set=AntarcticaMixin._set_colorization_factor
    )
    hue: FloatProperty(
        name="Hue Preview",
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        precision=3,
        get=AntarcticaMixin._get_hue,
        set=AntarcticaMixin._set_hue
    )
    hue_select: StringProperty(
        name="Hue Selection",
        default=''
    )

    @staticmethod
    def setup_vertexcolor(nt: NodeTree, nds_color: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the color output.
        This is the texture color mixed with the vertex color data.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_color : bpy.types.NodeSocketColor
            The color value that should be mixed with the vertex colors

        Returns
        -------
        bpy.types.NodeSocketColor
            An output node socket with the resulting color
        """
        nd_vertex = nt.nodes.new('ShaderNodeVertexColor')
        nd_gt = nt.nodes.new('ShaderNodeMath')
        nd_mix = nt.nodes.new('ShaderNodeMixRGB')

        nd_gt.operation = 'GREATER_THAN'
        nd_gt.use_clamp = True
        nd_gt.inputs[1].default_value = 0.0
        nd_mix.blend_type = 'MULTIPLY'
        nd_mix.inputs['Fac'].default_value = 1.0

        nt.links.new(nds_color, nd_mix.inputs['Color1'])
        nt.links.new(nd_gt.outputs[0], nd_mix.inputs['Fac'])
        nt.links.new(nd_vertex.outputs['Color'], nd_gt.inputs[0])
        nt.links.new(nd_vertex.outputs['Color'], nd_mix.inputs['Color2'])

        return nd_mix.outputs[0]

    @staticmethod
    def setup_colorization_mask(nt: NodeTree, nds_tex_alpha: NodeSocket, nds_mask_alpha: NodeSocket,
                                nds_colorizable: NodeSocket, nds_colorization_factor: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the masking output.
        This is the default colorization mask interpretation simulating the one from the Antarctica shaders.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_tex_alpha : bpy.types.NodeSocketFloat
            The alpha value of the main material texture
        nds_mask_alpha : bpy.types.NodeSocketFloat
            The alpha value of the mask texture
        nds_colorizable : bpy.types.NodeSocketFloat
            A value used as multiplier for the colorization amount
        nds_colorization_factor : bpy.types.NodeSocketFloat
            A value representing the applied colorization factor

        Returns
        -------
        bpy.types.NodeSocketFloat
            An output node socket with the resulting alpha mask value
        """
        # For masking colorization (enable/disable)
        nd_mask_lt = nt.nodes.new('ShaderNodeMath')
        nd_mask_add = nt.nodes.new('ShaderNodeMath')

        # For combining mask and texture alpha values
        nd_combine_min = nt.nodes.new('ShaderNodeMath')
        nd_combine_mul = nt.nodes.new('ShaderNodeMath')
        nd_combine_lt = nt.nodes.new('ShaderNodeMath')
        nd_combine_range = nt.nodes.new('ShaderNodeMapRange')

        nd_mask_lt.operation = 'LESS_THAN'
        nd_mask_lt.inputs[1].default_value = 1.0   # toggle on < 1.0
        nd_mask_lt.use_clamp = True
        nd_mask_add.operation = 'ADD'
        nd_mask_add.use_clamp = True

        nd_combine_min.operation = 'MINIMUM'
        nd_combine_min.use_clamp = True
        nd_combine_mul.operation = 'MULTIPLY'
        nd_combine_mul.inputs[1].default_value = 0.4    # 102 / 255 (input ranging from 0.0 to 2.5)
        nd_combine_mul.use_clamp = True
        nd_combine_lt.operation = 'LESS_THAN'
        nd_combine_lt.inputs[1].default_value = 0.5    # toggle on < 0.5
        nd_combine_lt.use_clamp = True
        nd_combine_range.interpolation_type = 'LINEAR'
        nd_combine_range.inputs['From Min'].default_value = 0.0
        nd_combine_range.inputs['From Max'].default_value = 1.0
        nd_combine_range.clamp = True

        # Masking colorization
        nt.links.new(nds_colorizable, nd_mask_lt.inputs[0])
        nt.links.new(nd_mask_lt.outputs[0], nd_mask_add.inputs[0])

        # Masking colorization
        nt.links.new(nds_tex_alpha, nd_combine_min.inputs[0])
        nt.links.new(nds_mask_alpha, nd_combine_min.inputs[1])
        nt.links.new(nds_colorization_factor, nd_combine_mul.inputs[0])
        nt.links.new(nd_combine_min.outputs[0], nd_combine_lt.inputs[0])
        nt.links.new(nd_combine_lt.outputs[0], nd_combine_range.inputs['Value'])
        nt.links.new(nd_combine_min.outputs[0], nd_combine_range.inputs['To Min'])
        nt.links.new(nd_combine_mul.outputs[0], nd_combine_range.inputs['To Max'])
        nt.links.new(nd_combine_range.outputs[0], nd_mask_add.inputs[1])

        return nd_mask_add.outputs[0]

    @staticmethod
    def setup_colorization(nt: NodeTree, nds_color: NodeSocket, nds_mask_alpha: NodeSocket, nds_hue: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the colorization
        output. This is the default colorization interpretation simulating the one from the Antarctica shaders.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_color : bpy.types.NodeSocketColor
            The color value that should be colorized
        nds_mask_alpha : bpy.types.NodeSocketFloat
            The alpha value of the mask texture
        nds_hue : bpy.types.NodeSocketFloat
            A value used for colorization hue shift

        Returns
        -------
        bpy.types.NodeSocketColor
            An output node socket with the resulting color value
        """
        # For masking colorization (enable/disable)
        nd_mask_value_gt = nt.nodes.new('ShaderNodeMath')
        nd_mask_color_gt = nt.nodes.new('ShaderNodeMath')

        # Split/combine hsv colors
        nd_hsv_separate = nt.nodes.new('ShaderNodeSeparateHSV')
        nd_hsv_combine = nt.nodes.new('ShaderNodeCombineHSV')

        # Controlling the saturation (colorizatino factor can alter the mask alpha)
        nd_saturation_mul = nt.nodes.new('ShaderNodeMath')
        nd_saturation_max = nt.nodes.new('ShaderNodeMath')
        nd_saturation_range = nt.nodes.new('ShaderNodeMapRange')

        # Hue
        nd_hue_range = nt.nodes.new('ShaderNodeMapRange')
        nd_hue_mix = nt.nodes.new('ShaderNodeMixRGB')

        nd_mask_value_gt.operation = 'GREATER_THAN'
        nd_mask_value_gt.inputs[0].default_value = 0.5    # toggle on <= 0.5
        nd_mask_value_gt.use_clamp = True
        nd_mask_color_gt.operation = 'GREATER_THAN'
        nd_mask_color_gt.inputs[1].default_value = 0.0    # toggle on > 0.0
        nd_mask_color_gt.use_clamp = True

        nd_saturation_mul.operation = 'MULTIPLY'
        nd_saturation_mul.use_clamp = False
        nd_saturation_mul.inputs[1].default_value = 2.5  # alpha * 0.4 * 2.5 = alpha
        nd_saturation_max.operation = 'MAXIMUM'
        nd_saturation_max.use_clamp = False
        nd_saturation_range.interpolation_type = 'LINEAR'
        nd_saturation_range.inputs['From Min'].default_value = 0.0
        nd_saturation_range.inputs['From Max'].default_value = 1.0
        nd_saturation_range.clamp = True

        nd_hue_range.interpolation_type = 'LINEAR'
        nd_hue_range.inputs['From Min'].default_value = 0.0
        nd_hue_range.inputs['From Max'].default_value = 1.0
        nd_hue_range.clamp = True
        nd_hue_mix.blend_type = 'MIX'
        nd_hue_mix.use_clamp = True

        nt.links.new(nds_mask_alpha, nd_mask_value_gt.inputs[1])
        nt.links.new(nd_mask_value_gt.outputs[0], nd_hue_range.inputs['Value'])
        nt.links.new(nd_mask_value_gt.outputs[0], nd_saturation_range.inputs['Value'])
        nt.links.new(nds_hue, nd_mask_color_gt.inputs[0])
        nt.links.new(nd_mask_color_gt.outputs[0], nd_hue_mix.inputs['Fac'])

        nt.links.new(nds_color, nd_hsv_separate.inputs[0])
        nt.links.new(nd_hsv_separate.outputs['V'], nd_hsv_combine.inputs['V'])
        nt.links.new(nds_color, nd_hue_mix.inputs['Color1'])
        nt.links.new(nd_hsv_combine.outputs[0], nd_hue_mix.inputs['Color2'])

        nt.links.new(nds_mask_alpha, nd_saturation_mul.inputs[0])
        nt.links.new(nd_hsv_separate.outputs['S'], nd_saturation_max.inputs[0])
        nt.links.new(nd_hsv_separate.outputs['S'], nd_saturation_range.inputs['To Min'])
        nt.links.new(nd_saturation_mul.outputs[0], nd_saturation_max.inputs[1])
        nt.links.new(nd_saturation_max.outputs[0], nd_saturation_range.inputs['To Max'])
        nt.links.new(nd_saturation_range.outputs[0], nd_hsv_combine.inputs['S'])

        nt.links.new(nd_hsv_separate.outputs['H'], nd_hue_range.inputs['To Min'])
        nt.links.new(nds_hue, nd_hue_range.inputs['To Max'])
        nt.links.new(nd_hue_range.outputs[0], nd_hsv_combine.inputs['H'])

        return nd_hue_mix.outputs[0]

    @staticmethod
    def setup_basecolor(nt: NodeTree, nds_tex_color: NodeSocket, nds_tex_alpha: NodeSocket, nds_mask_alpha: NodeSocket,
                        nds_colorizable: NodeSocket, nds_colorization_factor: NodeSocket, nds_hue: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the color output.
        This is the default base color for simulating the Antarctica PBR shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_tex_color : bpy.types.NodeSocketColor
            The image texture color of the main material texture
        nds_tex_alpha : bpy.types.NodeSocketFloat
            The alpha value of the main material texture
        nds_mask_alpha : bpy.types.NodeSocketFloat
            The alpha value of the mask texture
        nds_colorizable : bpy.types.NodeSocketFloat
            A value used as multiplier for the colorization amount
        nds_colorization_factor : bpy.types.NodeSocketFloat
            A value representing the applied colorization factor
        nds_hue : bpy.types.NodeSocketFloat
            A value used for colorization hue shift

        Returns
        -------
        bpy.types.NodeSocketColor
            An output node socket with the resulting color
        """
        nds_color = AntarcticaSolidPBR.setup_vertexcolor(nt, nds_tex_color)
        nds_colorization_mask = AntarcticaSolidPBR.setup_colorization_mask(
            nt,
            nds_tex_alpha,
            nds_mask_alpha,
            nds_colorizable,
            nds_colorization_factor
        )
        return AntarcticaSolidPBR.setup_colorization(nt, nds_color, nds_colorization_mask, nds_hue)

    @staticmethod
    def setup_emission(nt: NodeTree, nds_color: NodeSocket, nds_glow: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the emission
        output. This is the default emission implementation for simulating the one of the Antarctica shaders.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_color : bpy.types.NodeSocketColor
            The color of the emission
        nds_glow : bpy.types.NodeSocketFloat
            The glow intensity value

        Returns
        -------
        bpy.types.NodeSocketColor
            An output node socket with the resulting emission color
        """
        # Emission color intensity
        nd_emission_pow = nt.nodes.new('ShaderNodeMixRGB')
        nd_emission_mul = nt.nodes.new('ShaderNodeMixRGB')
        nd_emission_add = nt.nodes.new('ShaderNodeMixRGB')

        # Glow intensity
        nd_glow_pow = nt.nodes.new('ShaderNodeMath')
        nd_glow_mul = nt.nodes.new('ShaderNodeMath')

        # Mix (multiply) output
        nd_mix_mul = nt.nodes.new('ShaderNodeMixRGB')

        nd_emission_pow.blend_type = 'MULTIPLY'
        nd_emission_pow.inputs['Fac'].default_value = 1.0
        nd_emission_pow.use_clamp = False
        nd_emission_mul.blend_type = 'MULTIPLY'
        nd_emission_mul.inputs['Fac'].default_value = 1.0
        nd_emission_mul.use_clamp = False
        nd_emission_add.blend_type = 'ADD'
        nd_emission_add.inputs['Fac'].default_value = 1.0
        nd_emission_add.use_clamp = False

        nd_glow_pow.operation = 'MULTIPLY'
        nd_glow_pow.use_clamp = True
        nd_glow_mul.operation = 'MULTIPLY'
        nd_glow_mul.inputs[1].default_value = 10.0    # 10x
        nd_glow_mul.use_clamp = False

        nd_mix_mul.blend_type = 'MULTIPLY'
        nd_mix_mul.inputs['Fac'].default_value = 1.0
        nd_mix_mul.use_clamp = False

        nt.links.new(nds_color, nd_emission_pow.inputs['Color1'])
        nt.links.new(nds_color, nd_emission_pow.inputs['Color2'])
        nt.links.new(nds_color, nd_emission_add.inputs['Color1'])
        nt.links.new(nd_emission_pow.outputs[0], nd_emission_mul.inputs['Color1'])
        nt.links.new(nd_emission_mul.outputs[0], nd_emission_add.inputs['Color2'])

        nt.links.new(nds_glow, nd_glow_pow.inputs[0])
        nt.links.new(nds_glow, nd_glow_pow.inputs[1])
        nt.links.new(nd_glow_pow.outputs[0], nd_glow_mul.inputs[0])
        nt.links.new(nd_glow_mul.outputs[0], nd_emission_mul.inputs['Color2'])

        nt.links.new(nd_emission_add.outputs[0], nd_mix_mul.inputs['Color1'])
        nt.links.new(nds_glow, nd_mix_mul.inputs['Color2'])

        return nd_mix_mul.outputs[0]

    @staticmethod
    def setup_datamap(nt: NodeTree, nds_color: NodeSocket, nds_data: NodeSocket):
        """Setup a node tree in a given node group object and return a tuple containing the node sockets that represents
        the data output values 'roughness', 'metallic' and 'emission'.
        This is the default data interpretation for simulating the Antarctica PBR shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_color : bpy.types.NodeSocketColor
            The base color value of the material
        nds_data : bpy.types.NodeSocketColor
            The color of the data map

        Returns
        -------
        (bpy.types.NodeSocketFloat, bpy.types.NodeSocketFloat, bpy.types.NodeSocketColor)
            The output node sockets for (roughness, metallic, emission)
        """
        nd_gloss_separate = nt.nodes.new('ShaderNodeSeparateRGB')
        nd_diffuse_invert = nt.nodes.new('ShaderNodeMath')

        nd_diffuse_invert.operation = 'SUBTRACT'
        nd_diffuse_invert.inputs[0].default_value = 1.0
        nd_diffuse_invert.use_clamp = True

        nt.links.new(nds_data, nd_gloss_separate.inputs[0])
        nt.links.new(nd_gloss_separate.outputs['R'], nd_diffuse_invert.inputs[1])

        nds_emission = AntarcticaSolidPBR.setup_emission(nt, nds_color, nd_gloss_separate.outputs['B'])

        # Return (roughness, metallic, emission)
        return (nd_diffuse_invert.outputs[0], nd_gloss_separate.outputs['G'], nds_emission)

    @staticmethod
    def setup_normal(nt: NodeTree, nds_normal_color: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the materials
        normal vector. This is the default normals calculation for simulating the Antarctica PBR shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_normal_color : bpy.types.ShaderNodeTexImage
            The color of the normal map

        Returns
        -------
        bpy.types.NodeSocketVector
            The output node socket for the materials normal
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
        nt.links.new(nds_normal_color, nd_normal_gt.inputs[0])
        nt.links.new(nds_normal_color, nd_normal_mix.inputs['Color2'])

        return nd_normal_mapping.outputs[0]

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = f".{self.bl_name}_nodetree"
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')
        nd_principled = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nd_principled.inputs['Specular'].default_value = PBR_SPECULAR_VALUE

        # Image texture for main texture
        nd_main_tex = nt.nodes.new('ShaderNodeTexImage')
        nd_main_tex.name = 'Main Texture'

        # Image texture for PBR data (gloss) map
        nd_data_map = nt.nodes.new('ShaderNodeTexImage')
        nd_data_map.name = 'Data Map'

        # PBR data map color is treated as data
        if nd_data_map.image:
            nd_data_map.image.colorspace_settings.is_data = True

        # Image texture for normal map
        nd_normal_map = nt.nodes.new('ShaderNodeTexImage')
        nd_normal_map.name = 'Normal Map'

        # Normal map color is treated as data
        if nd_normal_map.image:
            nd_normal_map.image.colorspace_settings.is_data = True

        # Image texture for colorization mask
        nd_colorization_mask = nt.nodes.new('ShaderNodeTexImage')
        nd_colorization_mask.name = 'Colorization Mask'

        # Colorization multiplier (for masking/enabling colorization)
        nd_colorizable = nt.nodes.new('ShaderNodeValue')
        nd_colorizable.name = 'Colorizable'
        nd_colorizable.outputs[0].default_value = 0.0

        # Colorization factor (for tweaking saturation)
        nd_colorization_factor = nt.nodes.new('ShaderNodeValue')
        nd_colorization_factor.name = 'Colorization Factor'
        nd_colorization_factor.outputs[0].default_value = 0.0

        # Colorization hue
        nd_hue = nt.nodes.new('ShaderNodeValue')
        nd_hue.name = 'Hue'
        nd_hue.outputs[0].default_value = 0.0

        nt.links.new(nd_principled.outputs[0], nd_output.inputs[0])

        # Build tree
        nds_basecolor = self.setup_basecolor(
            nt,
            nd_main_tex.outputs['Color'],
            nd_main_tex.outputs['Alpha'],
            nd_colorization_mask.outputs['Alpha'],
            nd_colorizable.outputs[0],
            nd_colorization_factor.outputs[0],
            nd_hue.outputs[0]
        )
        nds_data = self.setup_datamap(nt, nd_main_tex.outputs['Color'], nd_data_map.outputs['Color'])
        nds_normal = self.setup_normal(nt, nd_normal_map.outputs['Color'])

        nt.links.new(nds_basecolor, nd_principled.inputs['Base Color'])
        nt.links.new(nds_data[0], nd_principled.inputs['Roughness'])
        nt.links.new(nds_data[1], nd_principled.inputs['Metallic'])
        nt.links.new(nds_data[2], nd_principled.inputs['Emission'])
        nt.links.new(nds_normal, nd_principled.inputs['Normal'])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self, 'main_texture', new='image.new', open='image.open')

        # Data (gloss) map texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Data Map")
        prop_layout.template_ID(self, 'data_map', new='image.new', open='image.open')

        # Normal map texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Normal Map")
        prop_layout.template_ID(self, 'normal_map', new='image.new', open='image.open')

        layout.separator()

        # Colorization properties
        layout.prop(self, 'colorizable')

        if self.colorizable:
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Colorization Mask")
            prop_layout.template_ID(self, 'colorization_mask', new='image.new', open='image.open')

            layout.prop(self, 'colorization_factor')
            layout.prop(self, 'hue')
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Hue Selection")
            prop_layout.prop(self, 'hue_select', text="")


class AntarcticaCutoutPBR(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """
    Represents a shader node that simulates the cutout (alpha-test) physical based shader in the 'Antarctica' render
    pipeline of SuperTuxKart. This class also stores shader specific properties for export.
    """
    bl_name = 'AntarcticaCutoutPBR'
    bl_label = "Antarctica Cutout PBR"
    bl_description = "Simulates the SuperTuxKart Cutout PBR shader"

    def __update_data(self, context):
        self._set_texture('Data Map', self.data_map)

    def __update_normal(self, context):
        self._set_texture('Normal Map', self.normal_map)

    def __update_alpha(self, context):
        self._set_texture('Alpha Mask', self.alpha_mask)

    # Texture properties
    data_map: PointerProperty(
        type=bpy.types.Image,
        name="Data Map",
        update=__update_data
    )
    normal_map: PointerProperty(
        type=bpy.types.Image,
        name="Normal Map",
        update=__update_normal
    )
    alpha_mask: PointerProperty(
        type=bpy.types.Image,
        name="Alpha Mask",
        update=__update_alpha
    )

    # Colorization and hue properties
    colorizable: BoolProperty(
        name="Colorizable",
        default=False,
        get=AntarcticaMixin._get_colorizable,
        set=AntarcticaMixin._set_colorizable
    )
    hue: FloatProperty(
        name="Hue Preview",
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        precision=3,
        get=AntarcticaMixin._get_hue,
        set=AntarcticaMixin._set_hue
    )
    hue_select: StringProperty(
        name="Hue Selection",
        default=''
    )

    @staticmethod
    def setup_basecolor(nt: NodeTree, nds_tex_color: NodeSocket, nds_colorizable: NodeSocket, nds_hue: NodeSocket):
        """Setup a node tree in a given node group object and return the node socket that represents the color output.
        This is the default base color for simulating the Antarctica PBR shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nds_tex_color : bpy.types.NodeSocketColor
            The image texture color of the main material texture
        nds_colorizable : bpy.types.NodeSocketFloat
            A value used as multiplier for the colorization amount
        nds_hue : bpy.types.NodeSocketFloat
            A value used for colorization hue shift

        Returns
        -------
        bpy.types.NodeSocketColor
            An output node socket with the resulting color
        """
        # For masking colorization (enable/disable)
        nd_mask_lt = nt.nodes.new('ShaderNodeMath')

        nd_mask_lt.operation = 'LESS_THAN'
        nd_mask_lt.inputs[1].default_value = 1.0   # toggle on < 1.0
        nd_mask_lt.use_clamp = True

        nt.links.new(nds_colorizable, nd_mask_lt.inputs[0])

        nds_color = AntarcticaSolidPBR.setup_vertexcolor(nt, nds_tex_color)
        return AntarcticaSolidPBR.setup_colorization(nt, nds_color, nd_mask_lt.outputs[0], nds_hue)

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = f".{self.bl_name}_nodetree"
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')
        nd_principled = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nd_principled.inputs['Specular'].default_value = PBR_SPECULAR_VALUE

        # Image texture for main texture
        nd_main_tex = nt.nodes.new('ShaderNodeTexImage')
        nd_main_tex.name = 'Main Texture'

        # Image texture for PBR data (gloss) map
        nd_data_map = nt.nodes.new('ShaderNodeTexImage')
        nd_data_map.name = 'Data Map'

        # PBR data map color is treated as data
        if nd_data_map.image:
            nd_data_map.image.colorspace_settings.is_data = True

        # Image texture for normal map
        nd_normal_map = nt.nodes.new('ShaderNodeTexImage')
        nd_normal_map.name = 'Normal Map'

        # Normal map color is treated as data
        if nd_normal_map.image:
            nd_normal_map.image.colorspace_settings.is_data = True

        # Image texture for alpha mask
        nd_alpha_mask = nt.nodes.new('ShaderNodeTexImage')
        nd_alpha_mask.name = 'Alpha Mask'

        # Colorization multiplier (for masking/enabling colorization)
        nd_colorizable = nt.nodes.new('ShaderNodeValue')
        nd_colorizable.name = 'Colorizable'
        nd_colorizable.outputs[0].default_value = 0.0

        # Colorization hue
        nd_hue = nt.nodes.new('ShaderNodeValue')
        nd_hue.name = 'Hue'
        nd_hue.outputs[0].default_value = 0.0

        nt.links.new(nd_principled.outputs[0], nd_output.inputs[0])

        # Build tree
        nds_basecolor = self.setup_basecolor(
            nt,
            nd_main_tex.outputs['Color'],
            nd_colorizable.outputs[0],
            nd_hue.outputs[0]
        )
        nds_data = AntarcticaSolidPBR.setup_datamap(nt, nd_main_tex.outputs['Color'], nd_data_map.outputs['Color'])
        nds_normal = AntarcticaSolidPBR.setup_normal(nt, nd_normal_map.outputs['Color'])

        nt.links.new(nds_basecolor, nd_principled.inputs['Base Color'])
        nt.links.new(nds_data[0], nd_principled.inputs['Roughness'])
        nt.links.new(nds_data[1], nd_principled.inputs['Metallic'])
        nt.links.new(nds_data[2], nd_principled.inputs['Emission'])
        nt.links.new(nds_normal, nd_principled.inputs['Normal'])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self, 'main_texture', new='image.new', open='image.open')

        # Data (gloss) map texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Data Map")
        prop_layout.template_ID(self, 'data_map', new='image.new', open='image.open')

        # Normal map texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Normal Map")
        prop_layout.template_ID(self, 'normal_map', new='image.new', open='image.open')

        # Alpha mask texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Alpha Mask")
        prop_layout.template_ID(self, 'alpha_mask', new='image.new', open='image.open')

        layout.separator()

        # Colorization properties
        layout.prop(self, 'colorizable')

        if self.colorizable:
            layout.prop(self, 'hue')
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Hue Selection")
            prop_layout.prop(self, 'hue_select', text="")


class AntarcticaTransparent(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """
    Represents a shader node that simulates the transparent (alpha-blend) shader in the 'Antarctica' render pipeline of
    SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaTransparent'
    bl_label = "Antarctica Transparent"
    bl_description = "Simulates the SuperTuxKart Transparent shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_mask(self):
        """Internal getter of the alpha mask toggle."""
        return self.node_tree.nodes['Mask Influence'].outputs[0].default_value == 1.0

    def __set_mask(self, value):
        """Internal setter of the alpha mask toggle."""
        self.node_tree.nodes['Mask Influence'].outputs[0].default_value = 1.0 if value else 0.0

    # Mask properties
    prop_mask: bpy.props.BoolProperty(
        name="Use Alpha Mask",
        default=False,
        get=__get_mask,
        set=__set_mask
    )

    @staticmethod
    def setup_alpha(nt, nd_mainTex, nd_mask, nd_maskTex):
        """Setup a node tree in a given node group object and return the node socket that represents the alpha output of
        the appliead alpha mask.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nd_mainTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the main material texture
        nd_mask : bpy.types.ShaderNodeValue
            A value node used as multiplier for the alpha mask influence
        nd_maskTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the alpha mask

        Returns
        -------
        bpy.types.NodeSocketFloat
            The output node socket for the alpha value
        """
        nd_map_range = nt.nodes.new('ShaderNodeMapRange')
        nd_multiply = nt.nodes.new('ShaderNodeMath')
        nd_light_path = nt.nodes.new('ShaderNodeLightPath')

        nd_map_range.clamp = True
        nd_map_range.interpolation_type = 'LINEAR'
        nd_map_range.inputs['From Min'].default_value = 0.0
        nd_map_range.inputs['From Max'].default_value = 1.0

        nd_multiply.operation = 'MULTIPLY'

        # Transparency factor
        nt.links.new(nd_light_path.outputs['Is Camera Ray'], nd_multiply.inputs[0])
        nt.links.new(nd_map_range.outputs[0], nd_multiply.inputs[1])
        nt.links.new(nd_mask.outputs[0], nd_map_range.inputs['Value'])
        nt.links.new(nd_mainTex.outputs['Alpha'], nd_map_range.inputs['To Min'])
        nt.links.new(nd_maskTex.outputs['Color'], nd_map_range.inputs['To Max'])

        return nd_multiply.outputs[0]

    @staticmethod
    def setup_colorshader(nt, nd_mainTex):
        """Setup a node tree in a given node group object and return the node socket that represents the shader output.
        This is the default colored emission for simulating the Antarctica transparent (alpha-blend) shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nd_mainTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the main material texture

        Returns
        -------
        bpy.types.NodeSocketShader
            The output node socket for the colored emission shader
        """
        nd_shader_emission = nt.nodes.new('ShaderNodeEmission')
        nd_shader_emission.inputs['Strength'].default_value = 1.0

        nt.links.new(nd_mainTex.outputs['Color'], nd_shader_emission.inputs['Color'])

        return nd_shader_emission.outputs[0]

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

        # Image texture for alpha mask
        nd_maskTex = nt.nodes.new('ShaderNodeTexImage')
        nd_maskTex.name = 'Alpha Mask'

        # Alpha mask influence
        nd_mask = nt.nodes.new('ShaderNodeValue')
        nd_mask.name = 'Mask Influence'
        nd_mask.outputs[0].default_value = 0.0

        # Mixing transparent with color emission
        nd_shader_mix = nt.nodes.new('ShaderNodeMixShader')
        nd_shader_transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
        nd_shader_transparent.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        nds_transparency = self.setup_alpha(nt, nd_mainTex, nd_mask, nd_maskTex)
        nds_color = self.setup_colorshader(nt, nd_mainTex)

        # Mixing shaders
        nt.links.new(nds_transparency, nd_shader_mix.inputs['Fac'])
        nt.links.new(nd_shader_transparent.outputs[0], nd_shader_mix.inputs[1])
        nt.links.new(nds_color, nd_shader_mix.inputs[2])
        nt.links.new(nd_shader_mix.outputs[0], nd_output.inputs[0])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')

        layout.separator()

        # Mask properties
        layout.prop(self, 'prop_mask')

        if self.prop_mask:
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Alpha Mask")
            prop_layout.template_ID(self.node_tree.nodes['Alpha Mask'], 'image', new='image.new', open='image.open')


class AntarcticaTransparentAdditive(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """
    Represents a shader node that simulates the transparent additive (alpha-additive) shader in the 'Antarctica' render
    pipeline of SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaTransparentAdditive'
    bl_label = "Antarctica Transparent Additive"
    bl_description = "Simulates the SuperTuxKart Transparent Additive shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_mask(self):
        """Internal getter of the alpha mask toggle."""
        return self.node_tree.nodes['Mask Influence'].outputs[0].default_value == 1.0

    def __set_mask(self, value):
        """Internal setter of the alpha mask toggle."""
        self.node_tree.nodes['Mask Influence'].outputs[0].default_value = 1.0 if value else 0.0

    # Mask properties
    prop_mask: bpy.props.BoolProperty(
        name="Use Alpha Mask",
        default=False,
        get=__get_mask,
        set=__set_mask
    )

    @staticmethod
    def setup_colorshader(nt, nd_mainTex):
        """Setup a node tree in a given node group object and return the node socket that represents the shader output.
        This is the default colored emission for simulating the Antarctica transparent additive (alpha-additive) shader.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nd_mainTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the main material texture

        Returns
        -------
        bpy.types.NodeSocketShader
            The output node socket for the colored emission shader
        """
        nd_shader_add = nt.nodes.new('ShaderNodeAddShader')
        nd_shader_emission = nt.nodes.new('ShaderNodeEmission')
        nd_color_mix = nt.nodes.new('ShaderNodeMixRGB')

        nd_shader_emission.inputs['Strength'].default_value = 2.0

        nd_color_mix.blend_type = 'MULTIPLY'
        nd_color_mix.inputs['Fac'].default_value = 1.0
        nd_color_mix.inputs['Color2'].default_value = (2.0, 2.0, 2.0, 2.0)

        nt.links.new(nd_shader_emission.outputs[0], nd_shader_add.inputs[0])
        nt.links.new(nd_shader_emission.outputs[0], nd_shader_add.inputs[1])
        nt.links.new(nd_color_mix.outputs[0], nd_shader_emission.inputs['Color'])
        nt.links.new(nd_mainTex.outputs['Color'], nd_color_mix.inputs['Color1'])

        return nd_shader_add.outputs[0]

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

        # Image texture for alpha mask
        nd_maskTex = nt.nodes.new('ShaderNodeTexImage')
        nd_maskTex.name = 'Alpha Mask'

        # Alpha mask influence
        nd_mask = nt.nodes.new('ShaderNodeValue')
        nd_mask.name = 'Mask Influence'
        nd_mask.outputs[0].default_value = 0.0

        # Mixing transparent with color emission
        nd_shader_mix = nt.nodes.new('ShaderNodeMixShader')
        nd_shader_transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
        nd_shader_transparent.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        nds_transparency = AntarcticaTransparent.setup_alpha(nt, nd_mainTex, nd_mask, nd_maskTex)
        nds_color = self.setup_colorshader(nt, nd_mainTex)

        # Mixing shaders
        nt.links.new(nds_transparency, nd_shader_mix.inputs['Fac'])
        nt.links.new(nd_shader_transparent.outputs[0], nd_shader_mix.inputs[1])
        nt.links.new(nds_color, nd_shader_mix.inputs[2])
        nt.links.new(nd_shader_mix.outputs[0], nd_output.inputs[0])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')

        layout.separator()

        # Mask properties
        layout.prop(self, 'prop_mask')

        if self.prop_mask:
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Alpha Mask")
            prop_layout.template_ID(self.node_tree.nodes['Alpha Mask'], 'image', new='image.new', open='image.open')


class AntarcticaUnlit(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """
    Represents a shader node that simulates the unlit shader in the 'Antarctica' render pipeline of SuperTuxKart. This
    class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaUnlit'
    bl_label = "Antarctica Unlit"
    bl_description = "Simulates the SuperTuxKart Unlit shader"
    bl_width_default = 280
    bl_width_min = 200

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

        # Build up transparency for non-camera rays
        nd_shader_mix = nt.nodes.new('ShaderNodeMixShader')
        nd_shader_transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
        nd_light_path = nt.nodes.new('ShaderNodeLightPath')

        nd_shader_transparent.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        # Basic emission color
        nds_color = AntarcticaTransparent.setup_colorshader(nt, nd_mainTex)

        # Mixing shaders
        nt.links.new(nd_light_path.outputs['Is Camera Ray'], nd_shader_mix.inputs['Fac'])
        nt.links.new(nd_shader_transparent.outputs[0], nd_shader_mix.inputs[1])
        nt.links.new(nds_color, nd_shader_mix.inputs[2])
        nt.links.new(nd_shader_mix.outputs[0], nd_output.inputs[0])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')


class AntarcticaCustom(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """Represents a shader node that offers options for accessing a custom shader for the 'Antarctica' render pipeline
    of SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaCustom'
    bl_label = "Antarctica Custom"
    bl_description = "Accesses a custom SuperTuxKart shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_colorizable(self):
        """Getter of the colorizable toggle."""
        return self.node_tree.nodes['Colorizable'].outputs[0].default_value == 1.0

    def __set_colorizable(self, value):
        """Setter of the colorizable toggle."""
        self.node_tree.nodes['Colorizable'].outputs[0].default_value = 1.0 if value else 0.0

    def __get_hue(self):
        """Getter of the currently displayed hue value."""
        return self.node_tree.nodes['Hue'].outputs[0].default_value

    def __set_hue(self, value):
        """Setter of the currently displayed hue value."""
        self.node_tree.nodes['Hue'].outputs[0].default_value = value

    # Shader properties
    prop_shader: bpy.props.StringProperty(
        name="Shader",
        default=''
    )
    prop_secondary: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Secondary UV Texture"
    )

    # Additional samplers foldout
    prop_texture_foldout: bpy.props.BoolProperty(
        name="Additional Texture Samplers",
        default=False
    )

    # Additional texture samplers
    prop_texture2: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Texture Layer 2"
    )
    prop_texture3: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Texture Layer 3"
    )
    prop_texture4: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Texture Layer 4"
    )
    prop_texture5: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Texture Layer 5"
    )
    prop_mask: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Mask"
    )

    # Colorization and hue properties
    prop_colorizable: bpy.props.BoolProperty(
        name="Colorizable",
        default=False,
        get=__get_colorizable,
        set=__set_colorizable
    )
    prop_colorizationFactor: bpy.props.FloatProperty(
        name="Colorization Factor",
        default=0.0,
        soft_min=0.0,
        precision=3
    )
    prop_hue: bpy.props.FloatProperty(
        name="Hue",
        default=0.0,
        soft_min=0.0,
        soft_max=1.0,
        precision=3,
        get=__get_hue,
        set=__set_hue
    )
    prop_hueSelect: bpy.props.StringProperty(
        name="Hue Selection",
        default=''
    )

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')
        nd_principled = nt.nodes.new('ShaderNodeBsdfPrincipled')

        # Image texture for main texture
        nd_mainTex = nt.nodes.new('ShaderNodeTexImage')
        nd_mainTex.name = 'Main Texture'

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

        # Default material
        nd_principled.inputs['Specular'].default_value = PBR_SPECULAR_VALUE
        nd_principled.inputs['Roughness'].default_value = 1.0

        nds_basecolor = AntarcticaSolidPBR.setup_basecolor(nt, nd_mainTex, nd_colorizable, nd_colorizationMask, nd_hue)

        nt.links.new(nd_principled.outputs[0], nd_output.inputs[0])
        nt.links.new(nds_basecolor, nd_principled.inputs['Base Color'])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Shader")
        prop_layout.prop(self, 'prop_shader', text="")

        # Main texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Main Texture")
        prop_layout.template_ID(self.node_tree.nodes['Main Texture'], 'image', new='image.new', open='image.open')

        # Secondary UV texture
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Secondary UV Texture")
        prop_layout.template_ID(self, 'prop_secondary', new='image.new', open='image.open')

        layout.separator()

        prop_layout = layout.row()
        prop_layout.alignment = 'LEFT'

        prop_layout.prop(
            self,
            'prop_texture_foldout',
            icon='DISCLOSURE_TRI_DOWN' if self.prop_texture_foldout else 'DISCLOSURE_TRI_RIGHT',
            emboss=False
        )

        if self.prop_texture_foldout:
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Texture Layer 2")
            prop_layout.template_ID(self, 'prop_texture2', new='image.new', open='image.open')

            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Texture Layer 3")
            prop_layout.template_ID(self, 'prop_texture3', new='image.new', open='image.open')

            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Texture Layer 4")
            prop_layout.template_ID(self, 'prop_texture4', new='image.new', open='image.open')

            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Texture Layer 5")
            prop_layout.template_ID(self, 'prop_texture5', new='image.new', open='image.open')

            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Mask")
            prop_layout.template_ID(self, 'prop_mask', new='image.new', open='image.open')

        layout.separator()

        # Colorization properties
        layout.prop(self, 'prop_colorizable')

        if self.prop_colorizable:
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text="Colorization Mask")
            prop_layout.template_ID(
                self.node_tree.nodes['Colorization Mask'],
                'image',
                new='image.new',
                open='image.open'
            )

            layout.prop(self, 'prop_colorizationFactor')
            layout.prop(self, 'prop_hue')
            prop_layout = layout.row().split(factor=0.4)
            prop_layout.label(text='Hue Selection')
            prop_layout.prop(self, 'prop_hueSelect', text="")


class AntarcticaBackground(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """Represents a shader node for the worlds environment that simulates the plain color background in the 'Antarctica'
    render pipeline of SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaBackground'
    bl_label = "Antarctica Background (Plain)"
    bl_description = "Accesses the SuperTuxKart plain color background shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_color(self):
        """Getter of the background color value."""
        return self.node_tree.nodes['Color'].inputs['Color'].default_value[:3]

    def __set_color(self, value):
        """Setter of the background color value."""
        self.node_tree.nodes['Color'].inputs['Color'].default_value = (value[0], value[1], value[2], 1.0)

    def __get_ambient(self):
        """Getter of the ambient color value."""
        return self.node_tree.nodes['Ambient'].inputs['Color'].default_value[:3]

    def __set_ambient(self, value):
        """Setter of the ambient color value."""
        self.node_tree.nodes['Ambient'].inputs['Color'].default_value = (value[0], value[1], value[2], 1.0)

    # Shader properties
    prop_color: bpy.props.FloatVectorProperty(
        name="Color",
        default=(0.3, 0.4, 1.0),
        subtype='COLOR',
        min=0.0,
        max=1.0,
        get=__get_color,
        set=__set_color
    )
    prop_ambient: bpy.props.FloatVectorProperty(
        name="Ambient Color",
        default=(0.4, 0.4, 0.4),
        subtype='COLOR',
        min=0.0,
        max=1.0,
        get=__get_ambient,
        set=__set_ambient
    )

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')

        # Mixing background shaders based on camera ray
        nd_shader_mix = nt.nodes.new('ShaderNodeMixShader')
        nd_light_path = nt.nodes.new('ShaderNodeLightPath')

        # Background shaders
        nd_bg_color = nt.nodes.new('ShaderNodeBackground')
        nd_bg_color.name = 'Color'
        nd_bg_color.inputs['Color'].default_value = (0.3, 0.4, 1.0, 1.0)

        nd_bg_ambient = nt.nodes.new('ShaderNodeBackground')
        nd_bg_ambient.name = 'Ambient'
        nd_bg_ambient.inputs['Color'].default_value = (0.4, 0.4, 0.4, 1.0)

        # Link tree
        nt.links.new(nd_shader_mix.outputs[0], nd_output.inputs[0])
        nt.links.new(nd_light_path.outputs['Is Camera Ray'], nd_shader_mix.inputs['Fac'])
        nt.links.new(nd_bg_ambient.outputs[0], nd_shader_mix.inputs[1])
        nt.links.new(nd_bg_color.outputs[0], nd_shader_mix.inputs[2])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Color")
        prop_layout.prop(self, 'prop_color', text="Color")

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Ambient")
        prop_layout.prop(self, 'prop_ambient', text="")


class AntarcticaSkybox(bpy.types.ShaderNodeCustomGroup, AntarcticaMixin):
    """Represents a shader node for the worlds environment that simulates the skybox background in the 'Antarctica'
    render pipeline of SuperTuxKart. This class also stores shader specific properties for export.
    """

    bl_name = 'AntarcticaSkybox'
    bl_label = "Antarctica Sky Box"
    bl_description = "Accesses the SuperTuxKart skybox background shader"
    bl_width_default = 280
    bl_width_min = 200

    def __get_ambient(self):
        """Getter of the ambient color value."""
        return self.node_tree.nodes['Ambient'].inputs['Color1'].default_value[:3]

    def __set_ambient(self, value):
        """Setter of the ambient color value."""
        self.node_tree.nodes['Ambient'].inputs['Color1'].default_value = (value[0], value[1], value[2], 1.0)

    def __get_use_ambient(self):
        """Getter of the ambient color value."""
        return self.node_tree.nodes['Ambient'].inputs['Fac'].default_value > 0.001

    def __set_use_ambient(self, value):
        """Setter of the ambient color value."""
        self.node_tree.nodes['Ambient'].inputs['Fac'].default_value = 1.0 if value else 0.0
    # Shader properties

    # Use ambient light map (skybox)
    prop_use_map: bpy.props.BoolProperty(
        name="Use Ambient Light Map",
        default=False,
        get=__get_use_ambient,
        set=__set_use_ambient
    )

    # Ambient light color
    prop_ambient: bpy.props.FloatVectorProperty(
        name="Ambient Color",
        default=(0.4, 0.4, 0.4),
        subtype='COLOR',
        min=0.0,
        max=1.0,
        get=__get_ambient,
        set=__set_ambient
    )

    @staticmethod
    def setup_skybox(nt, nd_northTex, nd_eastTex, nd_southTex, nd_westTex, nd_topTex, nd_bottomTex):
        """Setup a node tree in a given node group object and return the node socket that represents the output color of
        a skybox (cube map). Expects six different texture nodes as skybox input.

        Parameters
        ----------
        nt : bpy.types.ShaderNodeTree
            The node tree which should be populated
        nd_northTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (north)
        nd_eastTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (east)
        nd_southTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (south)
        nd_westTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (west)
        nd_topTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (top)
        nd_bottomTex : bpy.types.ShaderNodeTexImage
            The image texture node that provides the cube map texture (bottom)

        Returns
        -------
        bpy.types.NodeSocketColor
            The output node socket for the skybox color
        """

        nd_texCoord = nt.nodes.new('ShaderNodeTexCoord')
        nd_separate = nt.nodes.new('ShaderNodeSeparateXYZ')

        nd_c0_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c1_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c2_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c3_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c4_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c5_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_c0_mix.blend_type = 'MULTIPLY'
        nd_c0_mix.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 0.0)
        nd_c2_mix.blend_type = 'ADD'
        nd_c3_mix.blend_type = 'ADD'
        nd_c4_mix.blend_type = 'ADD'
        nd_c5_mix.blend_type = 'ADD'

        def create_uv(u, v):
            nd_combine = nt.nodes.new('ShaderNodeCombineXYZ')
            nt.links.new(u, nd_combine.inputs['X'])
            nt.links.new(v, nd_combine.inputs['Y'])

            return nd_combine.outputs[0]

        def math_node(operation, *inputs):
            nd_math = nt.nodes.new('ShaderNodeMath')
            nd_math.operation = operation

            for i, value in enumerate(inputs):
                if isinstance(value, bpy.types.NodeSocket):
                    nt.links.new(value, nd_math.inputs[i])
                else:
                    nd_math.inputs[i].default_value = value

            return nd_math.outputs[0]

        # Setup variables
        nt.links.new(nd_texCoord.outputs['Normal'], nd_separate.inputs[0])
        x = nd_separate.outputs['X']
        y = nd_separate.outputs['Y']
        z = nd_separate.outputs['Z']
        gt_x = math_node('GREATER_THAN', x, 0.0)
        gt_y = math_node('GREATER_THAN', y, 0.0)
        gt_z = math_node('GREATER_THAN', z, 0.0)
        lt_x = math_node('LESS_THAN', x, 0.0)
        lt_y = math_node('LESS_THAN', y, 0.0)
        lt_z = math_node('LESS_THAN', z, 0.0)
        abs_x = math_node('ABSOLUTE', x)
        abs_y = math_node('ABSOLUTE', y)
        abs_z = math_node('ABSOLUTE', z)

        mask_north_south = math_node(
            'MULTIPLY',
            math_node('LESS_THAN', abs_x, abs_y),
            math_node('LESS_THAN', abs_z, abs_y)
        )

        mask_east_west = math_node(
            'MULTIPLY',
            math_node('LESS_THAN', abs_y, abs_x),
            math_node('LESS_THAN', abs_z, abs_x)
        )

        mask_top_bottom = math_node(
            'MULTIPLY',
            math_node('LESS_THAN', abs_x, abs_z),
            math_node('LESS_THAN', abs_y, abs_z)
        )

        # UVs
        # North
        div_horizontal = math_node('DIVIDE', x, y)
        u_north = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)
        div_horizontal = math_node('DIVIDE', z, y)
        v_north = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)

        # South
        u_south = u_north
        v_south = math_node('SUBTRACT', 1.0, v_north)

        # East
        div_horizontal = math_node('MULTIPLY', math_node('DIVIDE', y, x), -1.0)
        u_east = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)
        div_horizontal = math_node('DIVIDE', z, x)
        v_east = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)

        # West
        u_west = u_east
        v_west = math_node('SUBTRACT', 1.0, v_east)

        # Top
        div_horizontal = math_node('MULTIPLY', math_node('DIVIDE', y, z), -1.0)
        u_top = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)
        div_horizontal = math_node('MULTIPLY', math_node('DIVIDE', x, z), -1.0)
        v_top = math_node('MULTIPLY_ADD', div_horizontal, 0.5, 0.5)

        # Bottom
        u_bottom = u_top
        v_bottom = math_node('SUBTRACT', 1.0, v_top)

        # Link UV coordinates to textures
        nt.links.new(create_uv(u_north, v_north), nd_northTex.inputs['Vector'])
        nt.links.new(create_uv(u_east, v_east), nd_eastTex.inputs['Vector'])
        nt.links.new(create_uv(u_south, v_south), nd_southTex.inputs['Vector'])
        nt.links.new(create_uv(u_west, v_west), nd_westTex.inputs['Vector'])
        nt.links.new(create_uv(u_top, v_top), nd_topTex.inputs['Vector'])
        nt.links.new(create_uv(u_bottom, v_bottom), nd_bottomTex.inputs['Vector'])

        # Plane
        factor_north = math_node('SUBTRACT', 1.0, math_node('MULTIPLY', mask_north_south, lt_y))
        factor_south = math_node('MULTIPLY', mask_north_south, gt_y)
        factor_east = math_node('MULTIPLY', mask_east_west, lt_x)
        factor_west = math_node('MULTIPLY', mask_east_west, gt_x)
        factor_top = math_node('MULTIPLY', mask_top_bottom, lt_z)
        factor_bottom = math_node('MULTIPLY', mask_top_bottom, gt_z)

        # Add all colors together
        nt.links.new(factor_north, nd_c0_mix.inputs['Fac'])
        nt.links.new(factor_east, nd_c1_mix.inputs['Fac'])
        nt.links.new(factor_south, nd_c2_mix.inputs['Fac'])
        nt.links.new(factor_west, nd_c3_mix.inputs['Fac'])
        nt.links.new(factor_top, nd_c4_mix.inputs['Fac'])
        nt.links.new(factor_bottom, nd_c5_mix.inputs['Fac'])

        nt.links.new(nd_northTex.outputs['Color'], nd_c0_mix.inputs['Color1'])
        nt.links.new(nd_c0_mix.outputs['Color'], nd_c1_mix.inputs['Color1'])
        nt.links.new(nd_eastTex.outputs['Color'], nd_c1_mix.inputs['Color2'])
        nt.links.new(nd_c1_mix.outputs['Color'], nd_c2_mix.inputs['Color1'])
        nt.links.new(nd_southTex.outputs['Color'], nd_c2_mix.inputs['Color2'])
        nt.links.new(nd_c2_mix.outputs['Color'], nd_c3_mix.inputs['Color1'])
        nt.links.new(nd_westTex.outputs['Color'], nd_c3_mix.inputs['Color2'])
        nt.links.new(nd_c3_mix.outputs['Color'], nd_c4_mix.inputs['Color1'])
        nt.links.new(nd_topTex.outputs['Color'], nd_c4_mix.inputs['Color2'])
        nt.links.new(nd_c4_mix.outputs['Color'], nd_c5_mix.inputs['Color1'])
        nt.links.new(nd_bottomTex.outputs['Color'], nd_c5_mix.inputs['Color2'])

        return nd_c5_mix.outputs['Color']

    def init(self, context):
        """Initialize a new instance of this node. Setup all main input and output nodes for this custom group."""
        # Setup node tree
        nt_name = '.' + self.bl_name + '_nodetree'
        nt = bpy.data.node_groups.new(nt_name, 'ShaderNodeTree')
        nt.outputs.new('NodeSocketShader', 'Output')

        # Output node
        nd_output = nt.nodes.new('NodeGroupOutput')

        # Mixing background shaders based on camera ray
        nd_shader_mix = nt.nodes.new('ShaderNodeMixShader')
        nd_light_path = nt.nodes.new('ShaderNodeLightPath')

        # Background shaders
        nd_bg_color = nt.nodes.new('ShaderNodeBackground')
        nd_bg_color.name = 'Color'

        nd_bg_ambient = nt.nodes.new('ShaderNodeBackground')

        nd_ambient_mix = nt.nodes.new('ShaderNodeMixRGB')
        nd_ambient_mix.blend_type = 'MIX'
        nd_ambient_mix.inputs['Fac'].default_value = 0.0
        nd_ambient_mix.name = 'Ambient'

        # Skybox texture inputs
        nd_northTex = nt.nodes.new('ShaderNodeTexImage')
        nd_eastTex = nt.nodes.new('ShaderNodeTexImage')
        nd_southTex = nt.nodes.new('ShaderNodeTexImage')
        nd_westTex = nt.nodes.new('ShaderNodeTexImage')
        nd_topTex = nt.nodes.new('ShaderNodeTexImage')
        nd_bottomTex = nt.nodes.new('ShaderNodeTexImage')
        nd_northTex.name = 'Texture North'
        nd_eastTex.name = 'Texture East'
        nd_southTex.name = 'Texture South'
        nd_westTex.name = 'Texture West'
        nd_topTex.name = 'Texture Top'
        nd_bottomTex.name = 'Texture Bottom'

        # Skybox mapping
        nds_color = self.setup_skybox(nt, nd_northTex, nd_eastTex, nd_southTex, nd_westTex, nd_topTex, nd_bottomTex)

        # Ambient texture inputs
        nd_northTex = nt.nodes.new('ShaderNodeTexImage')
        nd_eastTex = nt.nodes.new('ShaderNodeTexImage')
        nd_southTex = nt.nodes.new('ShaderNodeTexImage')
        nd_westTex = nt.nodes.new('ShaderNodeTexImage')
        nd_topTex = nt.nodes.new('ShaderNodeTexImage')
        nd_bottomTex = nt.nodes.new('ShaderNodeTexImage')
        nd_northTex.name = 'Ambient North'
        nd_eastTex.name = 'Ambient East'
        nd_southTex.name = 'Ambient South'
        nd_westTex.name = 'Ambient West'
        nd_topTex.name = 'Ambient Top'
        nd_bottomTex.name = 'Ambient Bottom'

        # Ambient mapping
        nds_ambient = self.setup_skybox(nt, nd_northTex, nd_eastTex, nd_southTex, nd_westTex, nd_topTex, nd_bottomTex)

        # Shader mixing links
        nt.links.new(nd_shader_mix.outputs[0], nd_output.inputs[0])
        nt.links.new(nd_light_path.outputs['Is Camera Ray'], nd_shader_mix.inputs['Fac'])
        nt.links.new(nd_bg_ambient.outputs[0], nd_shader_mix.inputs[1])
        nt.links.new(nd_bg_color.outputs[0], nd_shader_mix.inputs[2])

        # Color links
        nt.links.new(nds_color, nd_bg_color.inputs['Color'])
        nt.links.new(nds_ambient, nd_ambient_mix.inputs['Color2'])
        nt.links.new(nd_ambient_mix.outputs[0], nd_bg_ambient.inputs['Color'])

        # Assign generated node tree
        self.node_tree = nt

    def draw_buttons(self, context, layout):
        """Draw node buttons."""
        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="North")
        prop_layout.template_ID(self.node_tree.nodes['Texture North'], 'image', new='image.new', open='image.open')

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="East")
        prop_layout.template_ID(self.node_tree.nodes['Texture East'], 'image', new='image.new', open='image.open')

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="South")
        prop_layout.template_ID(self.node_tree.nodes['Texture South'], 'image', new='image.new', open='image.open')

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="West")
        prop_layout.template_ID(self.node_tree.nodes['Texture West'], 'image', new='image.new', open='image.open')

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Top")
        prop_layout.template_ID(self.node_tree.nodes['Texture Top'], 'image', new='image.new', open='image.open')

        prop_layout = layout.row().split(factor=0.4)
        prop_layout.label(text="Bottom")
        prop_layout.template_ID(self.node_tree.nodes['Texture Bottom'], 'image', new='image.new', open='image.open')

        box = layout.box()
        box.label(text="Ambient Lighting")
        box.prop(self, 'prop_use_map')

        if self.prop_use_map:

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="North")
            prop_layout.template_ID(self.node_tree.nodes['Ambient North'], 'image', new='image.new', open='image.open')

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="East")
            prop_layout.template_ID(self.node_tree.nodes['Ambient East'], 'image', new='image.new', open='image.open')

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="South")
            prop_layout.template_ID(self.node_tree.nodes['Ambient South'], 'image', new='image.new', open='image.open')

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="West")
            prop_layout.template_ID(self.node_tree.nodes['Ambient West'], 'image', new='image.new', open='image.open')

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="Top")
            prop_layout.template_ID(self.node_tree.nodes['Ambient Top'], 'image', new='image.new', open='image.open')

            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="Bottom")
            prop_layout.template_ID(self.node_tree.nodes['Ambient Bottom'], 'image', new='image.new', open='image.open')
        else:
            prop_layout = box.row().split(factor=0.4)
            prop_layout.label(text="Color")
            prop_layout.prop(self, 'prop_ambient', text="")
