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
import collections
from . import stk_utils

SceneCollection = collections.namedtuple('SceneCollection', [
    'objects',              # List objects that represent the kart model (chassis)
    'wheels',               # List of 4 wheel objects
    'speed_weighted',       # List of speed weighted objects
    'nitro_emitters',       # List of nitro emitter transforms (max 2)
    'headlights',           # List of objects that represents the headlights (bpy.types.Object)
    'hat'                   # The karts hat positioner object (bpy.types.Object)
])

SpeedWeighted = collections.namedtuple('SpeedWeighted', [
    'name',                 # Name identifier of the speed-weighted object
    'object',               # The speed-weighted object (bpy.types.Object)
    'strength',             # How much the kart speed affects the distance from the animation to the static pose
    'speed',                # The factor that controls the speed of the animation (multiplier)
    'uv_speed_u',           # UV texture speed u
    'uv_speed_v'            # UV texture speed v
])

Instanced = collections.namedtuple('Instanced', [
    'name',                 # Name identifier of the object
    'object',               # The object (bpy.types.Object)
])


def collect_scene(context: bpy.context, report=print):
    """Collect all relevant objects from the Blender scene relevant for kart exporting.
    This method of parsing the Blender scene is straightforward and simple. Much overhead is not really necessary as
    kart data is (for historic reasons) fundamentally different to track data. So there is no benefit in using e.g.
    NumPy structures. The scenes are not that complex (it's a kart after all) and code from track/library export cannot
    really be reused.

    Parameters
    ----------
    context : bpy.context
        The Blender context object
    report : callable, optional
        A function used for reporting warnings or errors for this operation, by default 'print()'

    Returns
    -------
    SceneCollection
        A (named) tuple that describes the scene collection; it consists of all relevant data (or references) necessary
        for the export
    """
    objects = []

    # Gather all objects from enabled collections
    # If collections are hidden in viewport or render, all their objects should get ignored
    for col in stk_utils.iter_enabled_collections(context.scene.collection):
        objects.extend(col.objects)

    used_identifiers = set()
    kart_objects = []
    wheels = []
    speed_weighted = []
    nitro_emitters = []
    headlights = []
    hat = None

    # Categorize all objects that need to get exported
    for obj in objects:
        # Ignore disabled or direct library references (only accept proxies)
        if obj.hide_viewport or obj.hide_render:
            continue

        if (obj.type == 'MESH' or obj.type == 'EMPTY') and hasattr(obj, 'stk_kart'):
            # Categorize objects
            props = obj.stk_kart
            t = props.type

            # Library object proxies
            if obj.proxy:
                continue

            # Unassigned model (defaults to static kart model)
            elif obj.type != 'EMPTY' and t == 'none':
                kart_objects.append(obj)

            # Wheels
            elif obj.type != 'EMPTY' and t == 'wheel':
                # Skip if already more than two nitro emitters specified
                if len(wheels) >= 4:
                    report({'WARNING'}, "More than four wheels found in scene! A kart can only use 4 wheels. The wheel "
                           f"'{obj.name}' has been ignored!")
                    continue

                wheels.append(obj)

            # Speed weighted objects
            elif obj.type != 'EMPTY' and t == 'speed_weighted':
                # Name identifier
                name = props.name if len(props.name) > 0 else obj.data.name

                # Skip if already an object with this identifier
                if obj.data.users < 2 and name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{name}' is already staged for export and will be "
                           "ignored! Check if different objects have the same name identifier.")
                    continue

                strength = 0.05
                speed = 1.0

                # Get strength value (this is the calculated speed-weight strength based on the animation
                # -> only used on older devices)
                if props.strength != 'default':
                    strength = -1.0 if props.strength == 'disable' else props.strength_factor

                # Get speed factor value (multiplier for the animation speed)
                if props.speed != 'default':
                    strength = -1.0 if props.speed == 'disable' else props.speed_factor

                speed_weighted.append(SpeedWeighted(
                    name=name,
                    object=obj,
                    strength=strength,
                    speed=speed,
                    uv_speed_u=props.uv_speed_u,
                    uv_speed_v=props.uv_speed_v
                ))

                used_identifiers.add(name)

            # Nitro emitters
            elif t == 'nitro_emitter':
                # Skip if already more than two nitro emitters specified
                if len(nitro_emitters) >= 2:
                    report({'WARNING'}, "More than two nitro emitters found in scene! A kart can only contain two "
                           f"particle emitters for the nitro boost. The emitter '{obj.name}' has been ignored!")
                    continue

                nitro_emitters.append(stk_utils.object_get_transform(obj))

            # Headlight fx object
            elif obj.type != 'EMPTY' and t == 'headlight':
                # Name identifier
                name = props.name if len(props.name) > 0 else obj.data.name

                # Skip if already an object with this identifier
                if obj.data.users < 2 and name in used_identifiers:
                    report({'WARNING'}, f"The object with the name '{name}' is already staged for export and will be "
                           "ignored! Check if different objects have the same name identifier.")
                    continue

                headlights.append(Instanced(name, obj))
                used_identifiers.add(name)

            # Hat positioner
            elif t == 'hat':
                # Skip if already a hat positioner specified
                if hat:
                    report({'WARNING'}, f"Multiple hat positioners found in scene! The object '{obj.name}' has been "
                           "ignored!")
                    continue

                hat = obj

    # Check if the scene has 4 wheels specified for the kart
    if len(wheels) != 4:
        report({'ERROR'}, "A kart must have 4 wheels specified! Select the 'Wheel' object property on the wheels.")

    # Return the scene collection
    return SceneCollection(kart_objects, wheels, speed_weighted, nitro_emitters, headlights, hat)
