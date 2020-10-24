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

    ui_definitions = OrderedDict()

    def has_property(self, prop):
        cls = type(self)
        return prop in cls.__annotations__

    def get_property(self, prop):
        if hasattr(self, prop):
            return getattr(self, prop)

        # Search default value
        cls = type(self)

        if prop in cls.__annotations__:
            return cls.__annotations__[prop].default

        return None

    def condition_poll(self, info):
        # No condition set
        if not info.condition:
            return True

        args = []

        # Gather binded property values and invoke condition
        for p in info.bind:
            args.append(self.get_property(p))

        print(args)
        return info.condition(*args)

    @staticmethod
    def _eval_condition(cond):
        if not re.search("(__|eval|exec)", cond):
            return eval(cond, {'__builtins__': None}, {})

        return None

    @classmethod
    def _load_data(cls):
        from os import path
        from xml.dom.minidom import parse
        path = path.join(path.dirname(__file__), cls.DATA_DIR, cls.PROP_SOURCE)
        return parse(path)

    @classmethod
    def initialize(cls):
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
                n_label = n_id
                n_cond = node.getAttribute('condition') if node.hasAttribute('condition') else ""

                if node.hasAttribute('label'):
                    n_label = node.getAttribute('label')
                elif node.firstChild and node.firstChild.nodeValue:
                    n_label = node.firstChild.nodeValue

                # Property and info data arguments
                info_args = {'label': n_label}
                prop_args = {'name': n_label}

                # Property conditions
                if (n_cond.startswith("lambda ")):
                    info_args['condition'] = cls._eval_condition(n_cond)
                    info_args['bind'] = tuple(node.getAttribute('bind').split()) if node.hasAttribute('bind') else ()

                # Integer property
                if n_type == 'int':
                    prop_args['default'] = int(node.getAttribute('default')) if node.hasAttribute('default') else 0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if node.hasAttribute('min'):
                        prop_args['min'] = node.getAttribute('min')

                    if node.hasAttribute('max'):
                        prop_args['max'] = node.getAttribute('max')

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = IntProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Floating point number property
                elif n_type == 'float':
                    prop_args['default'] = float(node.getAttribute('default')) if node.hasAttribute('default') else 0.0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if node.hasAttribute('min'):
                        prop_args['min'] = node.getAttribute('min')

                    if node.hasAttribute('max'):
                        prop_args['max'] = node.getAttribute('max')

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = FloatProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Boolean property
                elif n_type == 'bool':
                    prop_args['default'] = stk_utils.str_to_bool(node.getAttribute('default'))

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = BoolProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # String property
                elif n_type == 'string':
                    prop_args['default'] = node.getAttribute('default')

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = StringProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Color property
                elif n_type == 'color':
                    prop_args['default'] = stk_utils.str_to_color(node.getAttribute('default'))
                    prop_args['subtype'] = 'COLOR'
                    prop_args['min'] = 0.0
                    prop_args['max'] = 1.0

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = FloatVectorProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Enumerator property
                elif n_type == 'enum':
                    prop_args['default'] = node.getAttribute('default')
                    n_items = []

                    # Iterate all enum items
                    for item in node.childNodes:
                        if item.localName is None or item.localName.lower() != 'item' or not item.hasAttribute('value'):
                            continue

                        n_items.append((
                            item.getAttribute('value'),
                            item.getAttribute('label') if item.hasAttribute('label') else item.getAttribute('value'),
                            item.getAttribute('doc') if item.hasAttribute('doc') else ""
                        ))

                    if len(n_items) == 0:
                        n_items.append(('none', "Unassigned", ""))

                    prop_args['items'] = n_items

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    p[n_id] = cls.PropertyInfo(**info_args)
                    props[n_id] = EnumProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Object reference property
                elif n_type == 'object':
                    n_filter = node.getAttribute('filter') if node.hasAttribute('filter') else ""

                    prop_args['type'] = bpy.types.Object

                    if node.hasAttribute('doc'):
                        n_doc = node.getAttribute('doc')
                        info_args['doc'] = n_doc
                        prop_args['description'] = n_doc

                    if n_filter.startswith("lambda "):
                        info_args['filter'] = cls._eval_condition(n_filter)
                        p[n_id] = cls.FilterPropertyInfo(**info_args)
                        prop_args['poll'] = p[n_id].poll
                        print(p[n_id].poll)
                    else:
                        p[n_id] = cls.FilterPropertyInfo(**info_args)

                    props[n_id] = PointerProperty(**prop_args)  # pylint: disable=assignment-from-no-return

                # Label
                elif n_type == 'label':
                    if node.hasAttribute('doc'):
                        p[n_id] = cls.PropertyInfo(n_label, node.getAttribute('doc'))
                    else:
                        p[n_id] = cls.PropertyInfo(n_label, "")

                # Sub-panel
                elif n_type == 'panel':
                    if node.hasAttribute('doc'):
                        info_args['doc'] = node.getAttribute('doc')

                    info_args['properties'] = generate_props(node)

                    p[n_id] = cls.PanelInfo(**info_args)  # pylint: disable=no-value-for-parameter

            return p

        for root in node.childNodes:
            if root.localName.lower() == 'properties':
                cls.ui_definitions = generate_props(root)

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

    class PanelInfo:
        def __init__(self, label, properties, doc="(No documentation was defined for this property)", bind=None,
                     condition=None):
            self.label = label
            self.doc = doc
            self.bind = bind
            self.condition = condition
            self.properties = properties


class STKObjectPropertyGroup(PropertyGroup, STKPropertyGroup):
    PROP_SOURCE = 'stk_object_properties.xml'

    @ classmethod
    def register(cls):
        # if '__annotations__' not in cls.__dict__:
        #     setattr(cls, '__annotations__', {})

        # cls.__annotations__ = cls.initialize()

        cls.initialize()

        bpy.types.Object.supertuxkart = PointerProperty(  # pylint: disable=assignment-from-no-return
            name="SuperTuxKart Object Properties",
            description="SuperTuxKart object properties",
            type=cls,
        )

    @ classmethod
    def unregister(cls):
        del bpy.types.Object.supertuxkart
