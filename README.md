# Stacked Scenes
[![hacs_badge](https://img.shields.io/badge/HACS-Default-gren.svg)](https://github.com/custom-components/hacs)
![version](https://img.shields.io/github/v/release/njlangley/stacked_scenes)
![GitHub all releases](https://img.shields.io/github/downloads/njlangley/stacked_scenes/total)
![GitHub release (latest by SemVer)](https://img.shields.io/github/downloads/njlangley/stacked_scenes/latest/total)

> Have you tried Stacked Scenes, but you have an open-plan area with entities that belong to multiple scenes and it doesn't quite work?

Stacked Scenes was built because although Stacked Scenes is awesome (this integration wouldn't exist without me trying that first), it just didn't work for my setup in a large multi-use open-plan family room. If you need to be able to use an entity in multiple scenes, have it work out what the state should be as those overlap and and turned on and off, this integration **might** help. If you don't need any of that, just use Stacked Scenes - really, its awesome!

Stacked scenes works by creating switch object for scenes (just like stateful scenes), but the states of the entities are calculated by applying the scenes as layers. It can be helpful to think of the layers like those in a image editor; an entity that is defined in two (or more) scenes that are both 'on' will work ot the value to use from the values defined in those scenes (based on an adjustable option per device). When one of the scenes is turned off, the layers are re-evaluated to set the new entity values. Changing an entity to another value directly makes the scene turn 'off', as nothing in the stack of scenes matches any more.

> ***Note:*** *External scenes (eg Hue) are not supported at the moment, as I don't use them and have no way of testing the logic used to set entity states.*

> ***Note 2:*** *Stacked Scenes and Stacked Scenes won't play nice together, so just use one of the other. If you have both installed, Stacked Scenes will generate a Home Assistant Repair asking you to remove one of them, and then won't load any further to avoid any weird behaviour.*


## Installation
### HACS
Install via [HACS](https://hacs.xyz) by searching for `Stacked Scenes` in the integrations section, or simply click the button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=njlangley&repository=stacked_scenes&category=integration)

### Manual
Clone the repository and copy the custom_components folder to your home assistant config folder.

```bash
git clone https://github.com/njlangley/stacked_scenes.git
cp -r stacked_scenes/custom_components config/
```

## Configuration
This integration is now configured via the config flow. After you have installed and restarted Home Assistant, go to Devices and Services, Add Integration, and search for Stacked Scenes. Alternatively, just click this button:

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=stacked_scenes)

![Config flow screenshot](media/config-flow.png)

### Scene path
If your configuration has a different location for scenes you can change the location by changing the `Scene path` variable. By default, Home Assistant places all scenes inside `scenes.yaml` which is where this integration retrieves the scenes.

### Rounding tolerance
Some attributes such as light brightness will be rounded off. Therefore, to assess whether the scene is active a tolerance will be applied. The default tolerance of 1 will work for rounding errors of ±1. If this does not work for your setup consider increasing this value.

### Restore on deactivation
You can set up Stacked Scenes to restore the state of the entities when you want to turn off a scene. This can also be configured per Stacked Scene by going to the device page.

### Transition time
Furthermore, you can specify the default transition time for applying scenes. This will gradually change the lights of a scene to the specified state. It does need to be supported by your lights.

### Debounce time

After activating a scene by turning on a stacked scene switch, entities may need some time to achieve their desired states. When first turned on, the scene state switch will be assumed to be 'on'; the debounce time setting controls how long this integration will wait after observing a member entity state update event before reevaluating the entity state to determine if the scene is still active. If you're having issues with scenes immediately deactivating/reactivating, consider increasing this debounce time.

This setting is measured in seconds, but sub-second values (e.g '0.1' for 100ms delay) can be provided such that the delay is not perceptible to humans viewing a dashboard, for example.

## Scene configurations
For each scene you can specify the individual transition time and whether to restore on deactivation by changing the variables on the scene's device page.

### Supported Domains / Attributes
Note that while all entity states are supported only some entity attributes are supported at the moment. For the entities listed in the table the state is supported as well as the attributes in the table. Please open an issue, if you want support for other entity attributes.

| Entity Domain  | Attributes                               |
|----------------|------------------------------------------|
| `light`        | `brightness`, `rgb_color`, `effect`      |
| `cover`        | `position`                               |
| `media_player` | `volume_level`, `source`                 |
| `fan`          | `direction`, `oscillating`, `percentage` |

Entities from other domains might give behave a little weird - this has not been tested yet.


### Scene Priority
Each scene can also have a priority set from it's device page. This is the default way that the logic decides which scene to use as the value of an entity, picking the scene with the highest priority.


### Device Level Value Priority
For each device used by a scene, and new drop-down entity is added allowing the user to select the priority mode for entities of that device.
- Pick a value based on the priority of a scene (Default)
- Pick the attribute value from the first (oldest) scene 'on' using its value (datetime)
- Pick the attribute value from the last (latest) scene 'on' using its value (datetime)
- Pick the minimum value from the scenes that are 'on' using its value
- Pick the maximum value from the scenes that are 'on' using its value

First/last are supported for all attributes, but min/max are only appropriate for some attributes as shown in the table below. Only supported values will be shown in the drop-down entity for a device.

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


> ***Note:*** *RGB Color support is experimental. Some lights don't support all RGB values, and will return a different value once they are turned on. This will break the logic used to test if the value is the same. This typically happens when a light is using a different color mode such as HSL, and the conversion back and forth is not very accurate.*

### Logic

The following logic is used to determine if a scene is on:
- All entities in the scene have the state required by the scene.
- At least one entity in the scene has the exact attributes required by the scene.
- Some entities may match the scene definition in state, but their attributes match a different scene that is also 'on' (If the attributes don't match another scene that is also 'on', then the scene is off).

### Limitations
Here are some known limitations of the existing logic. Some of these are being worked on, some won't be fixed but a Home Assistant repair will be raised for them in the future.

- Scenes that overlap must have at least one entity with the same attributes and state. If all the attributes (brightness, color, volume etc) are different, then the scenes don't overlap.
- Scenes that are a subset of another scene (eg. all of their entities are in another scene, regardless of differences in attribute values) cannot be turned off when the superset scene is turned on. This would lead to an invalid state.
- Scenes with a single entity will cause weird issues, like not being able to turn that scene off (same as subset issue above).
- Setting RGB color values for lights that only support color temp will cause problems.
- Some RGB lights won't set to the exact color you specify, leading to issues determining scene state. This will hopefully be addressed in the future by comparing different RGB values to allow a color closeness threshold to be set.
- Scenes that set an entity to off are not supported. This is because working out the required state between two scenes with opposite desired states is impossible.
- For devices with multiple entities in the same domain (e.g. WLED with multiple light entities), all the entities have the same device level priority mode.

## HomeKit configuration
Once you have configured this integration, you can add the scenes to HomeKit. I assume that you already set up and configured the HomeKit integration. Expose the newly added switches to HomeKit. Then, in HomeKit define scenes for each Stacked Scenes switch.



## FAQ

#### Why is scene priority mode for entities set using a dropdown entity on the device
Because we can't set this in the scene YAML, as it would make the YAML invalid. The simplest option was to add it as a per device drop-down entity. However I use WLED and I know this can be a bit annoying for multi-channel WLED installs, and assume there are other similar niche use-cases where it could cause an issue. It might get addressed in the  future.

#### I can't turn one of my scenes off when another scene is on.
You have a scene that is is wholly a subset of another, that is another scene contains all the entities in the scene you can't turn off, and the attributes are identical for at least one of the entities.

#### I have two scene with overlapping entities. When I turn one on the other turns off.
You don't have any entities with exactly the same attributes; this is required for the logic to work. Or you have more than two scenes with the same entities defined, and the entities in the scene turning off are getting attributes prioritized from the other scenes, so no given entity matches on state and all attributes.

#### I turned off an entity belonging to a scene manually, and the scene turned off.
If the states of entities in the scene don't match, then the scene is off.

#### I changed an attribute (brightness, color etc.) of entity belonging to a scene manually, and the scene turned off.
for a scene to be on:
- The state and attributes of at least one entity in a scene must match exactly.
- The state of all other entities must be on, and the attributes must match those in another scene that is also on.