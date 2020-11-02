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

import re
import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    IntProperty,
    FloatProperty,
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty
)
from collections import OrderedDict
from . import stk_utils


class STKPropertyGroup:
    DATA_DIR = 'stkdata'
    PROP_SOURCE = 'stk_properties.xml'

    def condition_poll(self, info):
        # No condition set
        if not info.condition:
            return True

        args = []

        # Gather binded property values and invoke condition
        for p in info.bind:
            args.append(getattr(self, p, None))

        return info.condition(*args)

    @staticmethod
    def _eval_condition(cond):
        ALLOWED_BUILTINS = ('abs', 'all', 'any', 'ascii', 'bin', 'bool', 'chr', 'complex', 'dict', 'dir', 'divmod',
                            'enumerate', 'filter', 'float', 'format', 'frozenset', 'hash', 'hex', 'id', 'int',
                            'isinstance', 'issubclass', 'iter', 'len', 'list', 'max', 'memoryview', 'min', 'next',
                            'object', 'oct', 'open', 'ord', 'pow', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
                            'sorted', 'str', 'sum', 'tuple', 'type', 'zip')
        if not re.search("(__|eval|exec)", cond):
            context = {x: __builtins__[x] for x in __builtins__ if x in ALLOWED_BUILTINS}
            context['bpy'] = bpy
            return eval(cond, {'__builtins__': context}, {})

        return None

    @classmethod
    def _load_data(cls):
        from os import path
        from xml.dom.minidom import parse
        path = path.join(path.dirname(__file__), cls.DATA_DIR, cls.PROP_SOURCE)
        return parse(path)

    @classmethod
    def initialize(cls):
        cls.ui_definitions = OrderedDict()
        props = {}
        node = cls._load_data()

        def generate_props(panel):
            p = OrderedDict()

            for node in panel.childNodes:
                if node.localName is None or not node.hasAttribute('id'):
                    continue

                # Global node attributes
                n_type = node.localName.lower()
                n_id = node.getAttribute('id')
                n_cond = node.getAttribute('condition') if node.hasAttribute('condition') else ""

                # Property and info data arguments
                info_args = {}
                prop_args = {'options': set()}

                # Property conditions
                if (n_cond.startswith("lambda ")):
                    info_args['condition'] = cls._eval_condition(n_cond)
                    info_args['bind'] = tuple(node.getAttribute('bind').split()) if node.hasAttribute('bind') else ()

                # Integer property
                if n_type == 'int':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = int(node.getAttribute('default')) if node.hasAttribute('default') else 0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if node.hasAttribute('min'):
                        prop_args['min'] = int(node.getAttribute('min'))

                    if node.hasAttribute('max'):
                        prop_args['max'] = int(node.getAttribute('max'))

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = IntProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Floating point number property
                elif n_type == 'float':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = float(node.getAttribute('default')) if node.hasAttribute('default') else 0.0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if node.hasAttribute('min'):
                        prop_args['min'] = float(node.getAttribute('min'))

                    if node.hasAttribute('max'):
                        prop_args['max'] = float(node.getAttribute('max'))

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = FloatProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Boolean property
                elif n_type == 'bool':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = stk_utils.str_to_bool(node.getAttribute('default'))

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = BoolProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # String property
                elif n_type == 'string':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = node.getAttribute('default')

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = StringProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Color property
                elif n_type == 'color':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = stk_utils.str_to_vector(node.getAttribute('default'))
                    prop_args['subtype'] = 'COLOR'
                    prop_args['min'] = 0.0
                    prop_args['max'] = 1.0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = FloatVectorProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Coordinates (float vector) property
                elif n_type == 'coordinates':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    prop_args['default'] = stk_utils.str_to_vector(node.getAttribute('default'))
                    prop_args['subtype'] = 'XYZ'

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if node.hasAttribute('min'):
                        prop_args['min'] = float(node.getAttribute('min'))

                    if node.hasAttribute('max'):
                        prop_args['max'] = float(node.getAttribute('max'))

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = FloatVectorProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Enumerator property
                elif n_type == 'enum':
                    n_label = node.getAttribute('label') if node.hasAttribute('label') else n_id
                    info_args['label'] = n_label
                    prop_args['name'] = n_label
                    n_items = []

                    # Flags enum
                    if node.hasAttribute('flags'):
                        prop_args['options'].add('ENUM_FLAG')
                        prop_args['default'] = set(node.getAttribute('default').split())
                    else:
                        prop_args['default'] = node.getAttribute('default')

                    # Iterate all enum items
                    for i in node.childNodes:
                        if i.localName is None:
                            continue

                        cn_type = i.localName.lower()

                        # Basic enum item
                        if cn_type == 'item' and i.hasAttribute('value'):
                            n_items.append((
                                i.getAttribute('value'),
                                i.getAttribute('label') if i.hasAttribute('label') else i.getAttribute('value'),
                                i.getAttribute('doc') if i.hasAttribute('doc') else ""
                            ))

                        # Enum separator
                        elif cn_type == 'separator':
                            n_items.append(None)

                        # Sub-category
                        elif cn_type == 'category':
                            n_items.append(('', i.getAttribute('label') if i.hasAttribute('label') else "", ""))

                            # Iterate child nodes of category
                            for ci in i.childNodes:
                                if ci.localName is None:
                                    continue

                                ci_type = ci.localName.lower()

                                # Category enum item
                                if ci_type == 'item' and ci.hasAttribute('value'):
                                    n_items.append((
                                        ci.getAttribute('value'),
                                        ci.getAttribute('label')
                                        if ci.hasAttribute('label')
                                        else ci.getAttribute('value'),
                                        ci.getAttribute('doc') if ci.hasAttribute('doc') else ""
                                    ))

                                # Category enum separator
                                elif ci_type == 'separator':
                                    n_items.append(None)

                    if len(n_items) == 0:
                        n_items.append(('none', "Unassigned", ""))
                        prop_args['default'] = 'none'

                    prop_args['items'] = n_items
                    prop_args['attr'] = n_id

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = EnumProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Object or collection reference property
                elif n_type == 'object' or n_type == 'collection' or n_type == 'material':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    prop_args['name'] = n_label

                    # Specify pointer type
                    if n_type == 'collection':
                        prop_args['type'] = bpy.types.Collection
                    elif n_type == 'material':
                        prop_args['type'] = bpy.types.Material
                    else:
                        prop_args['type'] = bpy.types.Object

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    n_filter = node.getAttribute('filter') if node.hasAttribute('filter') else ""

                    if n_filter.startswith("lambda "):
                        info_args['filter'] = cls._eval_condition(n_filter)
                        p[n_id] = cls.FilterPropertyInfo(**info_args)
                        prop_args['poll'] = p[n_id].poll
                    else:
                        p[n_id] = cls.FilterPropertyInfo(**info_args)

                    props[n_id] = PointerProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Image
                elif n_type == 'image':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    info_args['operator_new'] = 'image.new'
                    info_args['operator_open'] = 'image.open'
                    prop_args['name'] = n_label
                    prop_args['type'] = bpy.types.Image

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.IDPropertyInfo(**info_args)
                    props[n_id] = PointerProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Label
                elif n_type == 'label':
                    n_label = n_id

                    if node.hasAttribute('label'):
                        n_label = node.getAttribute('label')
                    elif node.firstChild and node.firstChild.nodeValue:
                        n_label = node.firstChild.nodeValue

                    info_args['label'] = n_label
                    info_args['doc'] = node.getAttribute('doc') if node.hasAttribute('doc') else ""

                    p[n_id] = cls.PropertyInfo(**info_args)

                # Box
                elif n_type == 'box':
                    info_args['properties'] = generate_props(node)

                    p[n_id] = cls.BoxInfo(**info_args)  # pylint: disable=unexpected-keyword-arg

                # Sub-panel
                elif n_type == 'panel':
                    info_args['label'] = node.getAttribute('label') if node.hasAttribute('label') else None
                    info_args['expanded'] = node.hasAttribute('expanded')
                    info_args['properties'] = generate_props(node)

                    p[n_id] = cls.PanelInfo(**info_args)

                # Separator
                elif n_type == 'separator':
                    if node.hasAttribute('factor'):
                        info_args['factor'] = node.getAttribute('factor')

                    p[n_id] = cls.SeparatorInfo(**info_args)

            return p

        for root in node.childNodes:
            if root.localName.lower() == 'properties':
                cls.ui_definitions = generate_props(root)

        # Assign property annotations
        cls.__annotations__ = props

    class PropertyInfo:
        def __init__(self, label, doc="(No documentation was defined for this property)", bind=None, condition=None):
            self.label = label
            self.doc = doc
            self.bind = bind
            self.condition = condition

    class FilterPropertyInfo(PropertyInfo):
        def __init__(self, label, filter, doc="(No documentation was defined for this property)", bind=None,
                     condition=None):
            super().__init__(label, doc, bind, condition)
            self.filter = filter

            def poll(p_self, p_obj):
                return self.filter(p_obj)

            self.poll = poll if poll is not None else lambda p_self, p_obj: True

    class IDPropertyInfo(PropertyInfo):
        def __init__(self, label, operator_new='', operator_open='', operator_unlink='',
                     doc="(No documentation was defined for this property)", bind=None, condition=None):
            super().__init__(label, doc, bind, condition)
            self.operator_new = operator_new
            self.operator_open = operator_open
            self.operator_unlink = operator_unlink

    class BoxInfo:
        def __init__(self, properties, bind=None, condition=None):
            self.bind = bind
            self.condition = condition
            self.properties = properties

    class PanelInfo:
        def __init__(self, label, properties, bind=None, condition=None, expanded=False):
            self.label = label
            self.properties = properties
            self.bind = bind
            self.condition = condition
            self.expanded = expanded

    class SeparatorInfo:
        def __init__(self, factor=1.0, bind=None, condition=None):
            self.factor = factor
            self.bind = bind
            self.condition = condition


class STKScenePropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_scene_properties.xml'

    @classmethod
    def register(cls):
        bpy.types.Scene.stk = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Scene Properties",
            description="SuperTuxKart scene properties",
            type=cls
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.stk


class STKKartObjectPropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_kart_object_properties.xml'

    @classmethod
    def register(cls):
        # Create an RNA property specifically for karts (not just a general object property) to prevent false-sharing
        # between properties of different scene types. Every property group has its own data access.
        bpy.types.Object.stk_kart = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Object Properties",
            description="SuperTuxKart object properties",
            type=cls
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Object.stk_kart


class STKTrackObjectPropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_track_object_properties.xml'

    @classmethod
    def register(cls):
        # Create an RNA property specifically for tracks (not just a general object property) to prevent false-sharing
        # between properties of different scene types. Every property group has its own data access.
        bpy.types.Object.stk_track = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Object Properties",
            description="SuperTuxKart object properties",
            type=cls
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Object.stk_track


class STKLibraryObjectPropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_library_object_properties.xml'

    @classmethod
    def register(cls):
        # Create an RNA property specifically for library nodes (not just a general object property) to prevent
        # false-sharing between properties of different scene types. Every property group has its own data access.
        bpy.types.Object.stk_library = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Object Properties",
            description="SuperTuxKart object properties",
            type=cls
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Object.stk_library


class STKMaterialPropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_material_properties.xml'

    @classmethod
    def register(cls):
        bpy.types.Material.stk = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Material Properties",
            description="SuperTuxKart material properties",
            type=cls
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Material.stk
