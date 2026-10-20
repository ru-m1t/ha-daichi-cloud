"""Climate platform for Daichi integration."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FUNC_POWER,
    FUNC_TEMPERATURE,
    FUNC_FAN_SPEED_AUTO,
    FUNC_FAN_SPEED,
    FUNC_VERTICAL_SWING,
    FUNC_HORIZONTAL_SWING,
    FUNC_3D_SWING,
    FUNC_ECO,
    FUNC_TURBO,
    FUNC_SLEEP,
    FUNCTION_TO_HVAC_MODE,
    FUNCTION_TO_PRESET,
    FUNCTION_TO_SWING,
    HVAC_MODE_TO_FUNCTION,
    PRESET_NONE,
    PRESET_MODE_TO_FUNCTION,
    SWING_OFF,
    SWING_BOTH,
    SWING_MODE_TO_FUNCTION,
)
from .coordinator import DaichiDataUpdateCoordinator
from .device_control import find_function, get_function_state
from .entity import DaichiEntity, parse_temperature

_LOGGER = logging.getLogger(__name__)


def _detect_value_range(
    device_data: dict[str, Any], function: str, default: tuple[float, float]
) -> tuple[float, float]:
    """Detect min/max value of a numeric function from pult config."""
    func = find_function(device_data, function)
    if not func:
        return default

    min_val = func.get("minValue") or func.get("min")
    max_val = func.get("maxValue") or func.get("max")
    value_range = (func.get("state") or {}).get("valueRange")
    if isinstance(value_range, list) and len(value_range) == 2:
        min_val = min_val if min_val is not None else value_range[0]
        max_val = max_val if max_val is not None else value_range[1]

    try:
        lo = float(min_val) if min_val is not None else default[0]
        hi = float(max_val) if max_val is not None else default[1]
        return (lo, hi)
    except (ValueError, TypeError):
        return default


class DaichiClimateEntity(DaichiEntity, ClimateEntity):
    """Representation of a Daichi climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0

    def __init__(
        self,
        coordinator: DaichiDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, device_id, device_data)
        self._attr_unique_id = f"{DOMAIN}_{device_id}"

        def has(function: str) -> bool:
            return find_function(device_data, function) is not None

        self._attr_hvac_modes = [HVACMode.OFF]
        for function, mode_str in FUNCTION_TO_HVAC_MODE.items():
            if has(function):
                self._attr_hvac_modes.append(HVACMode(mode_str))
        if len(self._attr_hvac_modes) == 1:
            self._attr_hvac_modes = [
                HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT,
                HVACMode.FAN_ONLY, HVACMode.DRY, HVACMode.AUTO,
            ]

        has_fan = has(FUNC_FAN_SPEED) or has(FUNC_FAN_SPEED_AUTO)
        if has_fan:
            _, max_speed = _detect_value_range(device_data, FUNC_FAN_SPEED, (1, 5))
            self._attr_fan_modes = ["auto"] + [str(i) for i in range(1, int(max_speed) + 1)]
        else:
            self._attr_fan_modes = []

        preset_list: list[str] = []
        for function, preset_name in FUNCTION_TO_PRESET.items():
            if has(function):
                preset_list.append(preset_name)
        if preset_list:
            self._attr_preset_modes = [PRESET_NONE] + preset_list
        else:
            self._attr_preset_modes = []

        swing_list: list[str] = []
        for function, swing_name in FUNCTION_TO_SWING.items():
            if has(function):
                swing_list.append(swing_name)
        if swing_list:
            self._attr_swing_modes = [SWING_OFF] + swing_list
        else:
            self._attr_swing_modes = []

        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if has(FUNC_TEMPERATURE):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if has_fan:
            features |= ClimateEntityFeature.FAN_MODE
        if preset_list:
            features |= ClimateEntityFeature.PRESET_MODE
        if swing_list:
            features |= ClimateEntityFeature.SWING_MODE
        self._attr_supported_features = features

        min_t, max_t = _detect_value_range(device_data, FUNC_TEMPERATURE, (16.0, 30.0))
        self._attr_min_temp = min_t
        self._attr_max_temp = max_t

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        dd = self.device_data
        if not dd:
            return None

        cur_temp = dd.get("curTemp")
        if cur_temp is not None:
            try:
                return float(cur_temp)
            except (ValueError, TypeError):
                pass

        for key in ("currentStateDetailed", "currentState"):
            items = dd.get(key, [])
            if items:
                temp = parse_temperature(items[0].get("text", ""))
                if temp is not None:
                    return temp

        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        dd = self.device_data
        if not dd:
            return None

        state = dd.get("state", {})
        if not state:
            return None

        info = state.get("info", {})
        temp = parse_temperature(info.get("text", ""))
        if temp is not None:
            return temp

        val = get_function_state(dd, FUNC_TEMPERATURE).get("value")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        dd = self.device_data
        state = dd.get("state", {})
        if not state or not state.get("isOn", False):
            return HVACMode.OFF

        icon_names = state.get("info", {}).get("iconNames", [])

        icon_to_mode = {
            "modeCool_active": HVACMode.COOL,
            "modeHeat_active": HVACMode.HEAT,
            "modeDry_active": HVACMode.DRY,
            "modeFan_active": HVACMode.FAN_ONLY,
            "modeAuto_active": HVACMode.AUTO,
        }
        for icon, mode in icon_to_mode.items():
            if icon in icon_names:
                return mode

        for function, mode_str in FUNCTION_TO_HVAC_MODE.items():
            if get_function_state(dd, function).get("isOn", False):
                return HVACMode(mode_str)

        return HVACMode.AUTO

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        dd = self.device_data
        if not dd:
            return "auto"

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])

        if "fanSpeedAuto_active" in icon_names:
            return "auto"

        for icon_name in icon_names:
            if icon_name.startswith("fanSpeed") and icon_name.endswith("_active"):
                match = re.search(r"fanSpeedM\d+V(\d+)_active", icon_name)
                if match:
                    return match.group(1)
                speed_str = icon_name.replace("fanSpeed", "").replace("_active", "")
                if speed_str.isdigit():
                    return speed_str

        if get_function_state(dd, FUNC_FAN_SPEED_AUTO).get("isOn", False):
            return "auto"
        val = get_function_state(dd, FUNC_FAN_SPEED).get("value")
        if val is not None:
            return str(val)

        return "auto"

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        dd = self.device_data
        if not dd:
            return PRESET_NONE

        for function, preset in FUNCTION_TO_PRESET.items():
            if get_function_state(dd, function).get("isOn", False):
                return preset

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])
        icon_to_preset = {
            "eco_active": FUNCTION_TO_PRESET[FUNC_ECO],
            "turbo_active": FUNCTION_TO_PRESET[FUNC_TURBO],
            "sleep_active": FUNCTION_TO_PRESET[FUNC_SLEEP],
        }
        for icon, preset in icon_to_preset.items():
            if icon in icon_names:
                return preset

        return PRESET_NONE

    @property
    def swing_mode(self) -> str | None:
        """Return the current swing mode."""
        dd = self.device_data
        if not dd:
            return SWING_OFF

        vertical_on = get_function_state(dd, FUNC_VERTICAL_SWING).get("isOn", False)
        horizontal_on = get_function_state(dd, FUNC_HORIZONTAL_SWING).get("isOn", False)
        swing_3d_on = get_function_state(dd, FUNC_3D_SWING).get("isOn", False)

        if swing_3d_on or (vertical_on and horizontal_on):
            return SWING_BOTH
        if vertical_on:
            return FUNCTION_TO_SWING[FUNC_VERTICAL_SWING]
        if horizontal_on:
            return FUNCTION_TO_SWING[FUNC_HORIZONTAL_SWING]

        icon_names = dd.get("state", {}).get("info", {}).get("iconNames", [])
        if "swing3D_active" in icon_names:
            return SWING_BOTH
        if "swingVertical_active" in icon_names:
            return FUNCTION_TO_SWING[FUNC_VERTICAL_SWING]
        if "swingHorizontal_active" in icon_names:
            return FUNCTION_TO_SWING[FUNC_HORIZONTAL_SWING]

        return SWING_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if temperature < self._attr_min_temp or temperature > self._attr_max_temp:
            _LOGGER.warning(
                "Temperature %s is out of range [%s, %s]",
                temperature, self._attr_min_temp, self._attr_max_temp,
            )
            return

        try:
            await self.coordinator.async_control_device_with_retry(
                int(self._device_id), FUNC_TEMPERATURE, int(temperature),
            )
        except Exception as err:
            _LOGGER.error("Failed to set temperature for device %s: %s", self._device_id, err)
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            try:
                await self.coordinator.async_control_device_with_retry(
                    int(self._device_id), FUNC_POWER, False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn off device %s: %s", self._device_id, err)
                raise
        else:
            # Отправляем Power только если устройство выключено — иначе одна команда (режим)
            current_mode = self.hvac_mode
            if current_mode == HVACMode.OFF:
                try:
                    await self.coordinator.async_control_device_with_retry(
                        int(self._device_id), FUNC_POWER, True,
                    )
                except Exception as err:
                    _LOGGER.warning("Failed to turn on device %s: %s", self._device_id, err)

            function = HVAC_MODE_TO_FUNCTION.get(hvac_mode.value)
            if function:
                try:
                    await self.coordinator.async_control_device_with_retry(
                        int(self._device_id), function, None,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to set HVAC mode %s for device %s: %s",
                        hvac_mode.value, self._device_id, err,
                    )
                    raise
            else:
                _LOGGER.warning("Unknown HVAC mode: %s", hvac_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in (self._attr_fan_modes or []):
            _LOGGER.warning("Invalid fan mode: %s", fan_mode)
            return

        try:
            if fan_mode == "auto":
                await self.coordinator.async_control_device_with_retry(
                    int(self._device_id), FUNC_FAN_SPEED_AUTO, True,
                )
            else:
                speed_value = int(fan_mode)
                await self.coordinator.async_control_device_with_retry(
                    int(self._device_id), FUNC_FAN_SPEED, speed_value,
                )
        except ValueError:
            _LOGGER.warning("Invalid fan mode value: %s", fan_mode)
        except Exception as err:
            _LOGGER.error("Failed to set fan mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in (self._attr_preset_modes or []):
            _LOGGER.warning("Invalid preset mode: %s", preset_mode)
            return

        try:
            current = self.preset_mode
            if current and current != PRESET_NONE and current != preset_mode:
                function = PRESET_MODE_TO_FUNCTION.get(current)
                if function:
                    try:
                        await self.coordinator.async_control_device_with_retry(
                            int(self._device_id), function, False,
                        )
                    except Exception:
                        _LOGGER.debug("Failed to turn off preset %s", current)

            if preset_mode != PRESET_NONE:
                function = PRESET_MODE_TO_FUNCTION.get(preset_mode)
                if function:
                    await self.coordinator.async_control_device_with_retry(
                        int(self._device_id), function, True,
                    )
        except Exception as err:
            _LOGGER.error("Failed to set preset mode for device %s: %s", self._device_id, err)
            raise

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        if swing_mode not in (self._attr_swing_modes or []):
            _LOGGER.warning("Invalid swing mode: %s", swing_mode)
            return

        try:
            current = self.swing_mode
            if current and current != SWING_OFF and current != swing_mode:
                function = SWING_MODE_TO_FUNCTION.get(current)
                if function:
                    try:
                        await self.coordinator.async_control_device_with_retry(
                            int(self._device_id), function, False,
                        )
                    except Exception:
                        _LOGGER.debug("Failed to turn off swing %s", current)

            if swing_mode != SWING_OFF:
                function = SWING_MODE_TO_FUNCTION.get(swing_mode)
                if function:
                    await self.coordinator.async_control_device_with_retry(
                        int(self._device_id), function, True,
                    )
        except Exception as err:
            _LOGGER.error("Failed to set swing mode for device %s: %s", self._device_id, err)
            raise

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daichi climate entities from a config entry."""
    coordinator: DaichiDataUpdateCoordinator = entry.runtime_data

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities = []
    for device_id, device_data in (coordinator.data or {}).items():
        entities.append(
            DaichiClimateEntity(coordinator, str(device_id), device_data)
        )

    async_add_entities(entities, update_before_add=True)
