"""Constants for the Daichi integration."""
from __future__ import annotations

DOMAIN = "daichi"

# Configuration keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DAICHI_API = "daichi_api"

# Default values
DEFAULT_DAICHI_API = "https://web.daichicloud.ru/api/v4"
DEFAULT_CLIENT_ID = "sOJO7B6SqgaKudTfCzqLAy540cCuDzpI"

# Update interval
UPDATE_INTERVAL = 60  # seconds

# Логические функции устройства.
# Function ID у разных моделей кондиционеров разные, поэтому реальный id
# определяется по pult конкретного устройства через bleTag/bleOnCommand
# (см. device_control.find_function и FUNCTION_IDS.md).

# Основные функции
FUNC_POWER = "power"
FUNC_TEMPERATURE = "temperature"

# Режимы работы (Mode of operation)
FUNC_COOL = "cool"
FUNC_HEAT = "heat"
FUNC_AUTO = "auto"
FUNC_DRY = "dry"
FUNC_FAN = "fan"

# Скорость вентилятора (Fan speed)
FUNC_FAN_SPEED_AUTO = "fan_speed_auto"
FUNC_FAN_SPEED = "fan_speed"

# Swing (Качание)
FUNC_VERTICAL_SWING = "vertical_swing"
FUNC_HORIZONTAL_SWING = "horizontal_swing"
FUNC_3D_SWING = "3d_swing"

# Дополнительные режимы (Additional modes)
FUNC_ECO = "eco"
FUNC_TURBO = "turbo"
FUNC_SOUND_OFF = "sound_off"
FUNC_SLEEP = "sleep"
FUNC_HEATING_PLUS_8 = "heating_plus_8"

# Логическая функция -> (bleTag, bleOnCommand). None — bleOnCommand не проверяется.
# Для FUNC_FAN_SPEED дополнительно требуется bleOnCommand != "0" (см. find_function).
FUNCTION_BLE_TAGS: dict[str, tuple[str, str | None]] = {
    FUNC_POWER: ("power", None),
    FUNC_TEMPERATURE: ("setTemp", None),
    FUNC_COOL: ("mode", "cool"),
    FUNC_HEAT: ("mode", "heat"),
    FUNC_AUTO: ("mode", "auto"),
    FUNC_DRY: ("mode", "dry"),
    FUNC_FAN: ("mode", "vent"),
    FUNC_FAN_SPEED_AUTO: ("fanSpeed", "0"),
    FUNC_FAN_SPEED: ("fanSpeed", None),
    FUNC_VERTICAL_SWING: ("flow", "vert_on"),
    FUNC_HORIZONTAL_SWING: ("flow", "horizont_on"),
    FUNC_3D_SWING: ("flow", "3d_on"),
    FUNC_ECO: ("economy", "on"),
    FUNC_TURBO: ("powerfull", "on"),
    FUNC_SOUND_OFF: ("beepOff", "on"),
    FUNC_SLEEP: ("sleep", "on"),
    FUNC_HEATING_PLUS_8: ("heat8", "on"),
}

# Исторические Function ID (модель, на которой разрабатывалась интеграция).
# Используются только как запасной вариант, если у функции в pult нет bleTagInfo.
LEGACY_FUNCTION_IDS: dict[str, int] = {
    FUNC_POWER: 350,
    FUNC_TEMPERATURE: 351,
    FUNC_COOL: 352,
    FUNC_HEAT: 353,
    FUNC_AUTO: 354,
    FUNC_DRY: 355,
    FUNC_FAN: 356,
    FUNC_FAN_SPEED_AUTO: 357,
    FUNC_FAN_SPEED: 358,
    FUNC_VERTICAL_SWING: 359,
    FUNC_HORIZONTAL_SWING: 360,
    FUNC_3D_SWING: 361,
    FUNC_ECO: 363,
    FUNC_TURBO: 364,
    FUNC_SOUND_OFF: 365,
    FUNC_SLEEP: 366,
    FUNC_HEATING_PLUS_8: 332,
}

# Маппинг режимов Home Assistant на логические функции
HVAC_MODE_TO_FUNCTION = {
    "off": FUNC_POWER,
    "cool": FUNC_COOL,
    "heat": FUNC_HEAT,
    "dry": FUNC_DRY,
    "fan_only": FUNC_FAN,
    "auto": FUNC_AUTO,
}

# Preset modes (дополнительные режимы работы)
# Note: Comfortable Sleep requires additional parameters (temp, sleepTime)
# so it cannot be activated via simple preset, it's not included here.
PRESET_NONE = "none"
PRESET_ECO = "eco"
PRESET_TURBO = "turbo"
PRESET_SLEEP = "sleep"

PRESET_MODE_TO_FUNCTION = {
    PRESET_ECO: FUNC_ECO,
    PRESET_TURBO: FUNC_TURBO,
    PRESET_SLEEP: FUNC_SLEEP,
}

# Swing modes
SWING_OFF = "off"
SWING_VERTICAL = "vertical"
SWING_HORIZONTAL = "horizontal"
SWING_BOTH = "both"

SWING_MODE_TO_FUNCTION = {
    SWING_VERTICAL: FUNC_VERTICAL_SWING,
    SWING_HORIZONTAL: FUNC_HORIZONTAL_SWING,
    SWING_BOTH: FUNC_3D_SWING,
}

FUNCTION_TO_HVAC_MODE = {
    FUNC_COOL: "cool",
    FUNC_HEAT: "heat",
    FUNC_AUTO: "auto",
    FUNC_DRY: "dry",
    FUNC_FAN: "fan_only",
}

FUNCTION_TO_PRESET = {
    FUNC_ECO: PRESET_ECO,
    FUNC_TURBO: PRESET_TURBO,
    FUNC_SLEEP: PRESET_SLEEP,
}

FUNCTION_TO_SWING = {
    FUNC_VERTICAL_SWING: SWING_VERTICAL,
    FUNC_HORIZONTAL_SWING: SWING_HORIZONTAL,
    FUNC_3D_SWING: SWING_BOTH,
}
