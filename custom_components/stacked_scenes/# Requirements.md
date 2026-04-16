# Requirements

## Applying scenes
Once we have identified the actions we need to take (turning on/off, setting attributes), we construct a dictionary of desired states, and them call the scene service to apply a dynamic scene.
```
service_data = {"entities": entities_dict}
self.hass.services.call(
            domain="scene", service="apply", service_data=service_data
        )
```

This is used by stacked scenes on deactivation to set all of the entities for a scene to off, or to restore to the saved state.

## Restore
- We should save state when:
  - The entity is not part of another scene that is 'on'

- We should restore state when:
  - The entity is not part of another scene that is 'on'

## Apply
When applying the scene, we should work out what to do with any entities that are a part of overlapping scenes that are 'on'. Depending on the attribute, there are a number of strategies:

- Pick the attribute value from the first (oldest) scene 'on' using its value (datetime)
- Pick the attribute value from the last (latest) scene 'on' using its value (datetime)
- Pick the minimum value from the scenes that are 'on' using its value
- Pick the maximum value from the scenes that are 'on' using its value
- Pick a value based on the priority of a scene
  - Could be overridable at scene/entity level?
  - Where is this set? The scene object is pretty fixed and doesn't allow extra items

First/last are supported for all attributes, but min/max are only appropriate for some attributes as shown in the table below.

| Domain       | Attribute   | Type       | Min | Max | First | Last | Priority |
| ------------ | ----------- | ---------- | :-: | :-: | :---: | :--: |   :--:   |
| Light        | Brightness  | int        | ✓   | ✓   | ✓     | ✓    | ✓        |
| Light        | RGB Color   | array[int] | ✗   | ✗   | ✓     | ✓    | ✓        |
| Light        | Effect      | string     | ✗   | ✗   | ✓     | ✓    | ✓        |
| Cover        | Position    | int        | ✓   | ✓   | ✓     | ✓    | ✓        |
| Media Player | Volume      | float      | ✓   | ✓   | ✓     | ✓    | ✓        |
| Media Player | Source      | string     | ✗   | ✗   | ✓     | ✓    | ✓        |
| Fan          | Direction   | string     | ✗   | ✗   | ✓     | ✓    | ✓        |
| Fan          | Oscillating | bool       | ✓   | ✓   | ✓     | ✓    | ✓        |
| Fan          | Percentage  | int        | ✓   | ✓   | ✓     | ✓    | ✓        |

The way we choose the value should really be customisable, but it needs to be at the entity level as inconsistency across scenes would be difficult to understand in use. For example we may want a light to be the dimmest or brightest of the applied overlapping scenes. However this may lead to issues identifying if a scene is active or not.

## Is the Scene On
The base code just tests each entity/attribute to see if it matches the state desired for the scene.

For overlapping scenes we have shortcut this - for entities that belong to two active scenes, of the initial state match fails, we fall back to assuming that if an overlapping scene is active, then the entity mush match it's state. TODO: change this to just check the state of overlapping scenes too.

### Problems
However, this approach may cause issues where we are picking a minimum brightness for a light from two overlapping scenes that each specify a different colour - we could end up with a combo which is not either actual scenes setting!

Also what happens is all entities are on, but none re exactly as set in the scene (eg TV is on in the demo as soon as chill is on - this is because TV is only a single entity)






# TODO
  - A scene is on if:
    - DONE- At least on entity has the exact properties required

    - All of the entities that should be on/off, open/closed etc are, even if the exact amount or color is different (see matrix)
        - Tolerance for RGB values, as they are not always exact depending on the accuracy of the light
 
    - We do not support scenes that define an entity as off. This is because it introduces the possibility that two overlapping scenes could have the opposite states. Turning one scene on would turn the other off, but wouldn't turn off any entities that only applied because of that scene, leaving things in a weird state...
        - Is that a problem for things that are not really on/off, such as covers? Covers have a position, we could just ignore state for them and only compare the position attribute? Or just go with closed is not possible as a state, given the state is open for even 1% open

    - DONE - Setting an RBG color in a scene for alight that only supports color temp causes issues - the color is never as expected! We need to check if a feature is supported, and exclude it if not. We could also raise warnings (Bubble up as HA issues to be fixed) as we load the scene.

    - Any scene that is wholly a subset of another scene (all entities exist in the superset, and all attributes are the same), causes some weird behaviour. When enabling the superset scene, the subset scene is then evaluated and enabled, when means it's applied date ends up after the superset scene. When turning off the superset scene, the subset scene stays on, as even though it was never manually turned on, as it has a greater applied date. How can we work around this? Issue/Repair and/or some logic to identify full subsets?
        - This is also why we can't turn off TV - the chill one stays on, which keeps the TV scene on, even if you try and turn it off!

    - Scenes with exactly one entity are always problematic as they are only on if there is an exact match for that one entity. You then can turn them on if another scene has higher priority (or depending on the entity scene strategy, higher/lower brightness, or the priority is first)


    - Check if at least one entity in the scene is exactly right (DONE)
        - Then if the rest are the right state, the scene is on (DONE)
            - Except covers? (ignore initially) - (NOT DONE)