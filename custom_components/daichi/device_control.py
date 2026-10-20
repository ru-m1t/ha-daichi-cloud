"""Поиск функций в pult устройства и проверка применения команд управления."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .const import (
    FUNCTION_BLE_TAGS,
    LEGACY_FUNCTION_IDS,
    FUNC_POWER,
    FUNC_TEMPERATURE,
    FUNC_COOL,
    FUNC_HEAT,
    FUNC_AUTO,
    FUNC_DRY,
    FUNC_FAN,
    FUNC_FAN_SPEED_AUTO,
    FUNC_FAN_SPEED,
)


def iter_pult_functions(device_data: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Перебрать все функции pult, включая вложенные linkedFunction."""
    for section in device_data.get("pult") or []:
        for func in section.get("functions") or []:
            while isinstance(func, dict):
                yield func
                func = func.get("linkedFunction")


def _get_ble_info(func: dict[str, Any]) -> tuple[str | None, str | None]:
    """Вернуть (bleTag, bleOnCommand) функции."""
    info = (func.get("metaData") or {}).get("bleTagInfo") or {}
    tag = info.get("bleTag")
    on_command = info.get("bleOnCommand")
    return tag, (str(on_command) if on_command is not None else None)


def find_function(device_data: dict[str, Any], function: str) -> dict[str, Any] | None:
    """
    Найти функцию устройства по логическому имени (FUNC_*).

    Function ID зависят от модели устройства, поэтому функция ищется по
    bleTag/bleOnCommand из metaData. Исторический id используется только
    если у функции с этим id нет bleTagInfo.
    """
    if not device_data:
        return None

    functions = list(iter_pult_functions(device_data))
    tag, on_command = FUNCTION_BLE_TAGS[function]

    for func in functions:
        func_tag, func_on_command = _get_ble_info(func)
        if func_tag != tag:
            continue
        if on_command is not None and func_on_command != on_command:
            continue
        # Ручная скорость вентилятора имеет тот же bleTag, что и авто ("0")
        if function == FUNC_FAN_SPEED and func_on_command == "0":
            continue
        return func

    legacy_id = LEGACY_FUNCTION_IDS.get(function)
    for func in functions:
        if func.get("id") == legacy_id and _get_ble_info(func)[0] is None:
            return func

    return None


def get_function_id(device_data: dict[str, Any], function: str) -> int | None:
    """Вернуть id функции устройства по логическому имени или None."""
    func = find_function(device_data, function)
    return func.get("id") if func else None


def get_function_state(device_data: dict[str, Any], function: str) -> dict[str, Any]:
    """Вернуть state функции из pult или пустой dict."""
    return (find_function(device_data, function) or {}).get("state") or {}


# Иконки режимов в state.info.iconNames
HVAC_FUNCTION_TO_ICON = {
    FUNC_COOL: "modeCool_active",
    FUNC_HEAT: "modeHeat_active",
    FUNC_AUTO: "modeAuto_active",
    FUNC_DRY: "modeDry_active",
    FUNC_FAN: "modeFan_active",
}


def verify_control_applied(
    device_data: dict[str, Any],
    function: str,
    value: Any,
) -> bool:
    """
    Проверить, что команда применилась по актуальному состоянию устройства.
    Возвращает True, если состояние совпадает с ожидаемым.
    """
    if not device_data:
        return False

    state = device_data.get("state", {})
    icon_names = state.get("info", {}).get("iconNames", [])

    if function == FUNC_POWER:
        is_on = state.get("isOn", False)
        expected = bool(value) if value is not None else True
        return is_on == expected

    if function in (FUNC_TEMPERATURE, FUNC_FAN_SPEED):
        current_val = get_function_state(device_data, function).get("value")
        if current_val is None:
            return False
        try:
            return int(current_val) == int(value)
        except (TypeError, ValueError):
            return False

    if function in HVAC_FUNCTION_TO_ICON:
        # Режим работы (applyable): устройство включено и режим активен
        if not state.get("isOn", False):
            return False
        if HVAC_FUNCTION_TO_ICON[function] in icon_names:
            return True
        return bool(get_function_state(device_data, function).get("isOn", False))

    if function == FUNC_FAN_SPEED_AUTO:
        return bool(get_function_state(device_data, function).get("isOn", False))

    # Переключаемые функции (swing, preset, sound off и т.д.)
    current = bool(get_function_state(device_data, function).get("isOn", False))
    expected = bool(value) if value is not None else True
    return current == expected
