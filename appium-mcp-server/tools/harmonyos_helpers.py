# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""HarmonyOS helpers shared by MCP driver tools."""

from __future__ import annotations

import logging
import time

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)


def is_harmonyos_session(driver_manager, driver=None) -> bool:
    if getattr(driver_manager, "device", None) == "harmonyos":
        return True
    if driver is None:
        driver = getattr(driver_manager, "_driver", None)
    if not driver:
        return False
    platform = str(driver.capabilities.get("platformName", "")).lower()
    return platform in ("harmonyos", "harmony")


def resolve_locator(locator_strategy: str, locator_value: str):
    """Default empty strategy to Hypium text locator on HarmonyOS."""
    from tools.appium_driver_tool import get_appium_locator

    strategy = (locator_strategy or "").strip() or "text"
    return get_appium_locator(strategy, locator_value)


def locator_for_session(driver_manager, locator_strategy: str, locator_value: str):
    """Pick HarmonyOS-aware locator resolution when on harmonyos platform."""
    from tools.appium_driver_tool import get_appium_locator

    if is_harmonyos_session(driver_manager):
        return resolve_locator(locator_strategy, locator_value)
    return get_appium_locator(locator_strategy, locator_value)


def find_element(driver, locator_strategy: str, locator_value: str, timeout: int = 5):
    locator = resolve_locator(locator_strategy, locator_value)
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))


def click_element_harmonyos(
    driver,
    locator_value: str,
    locator_strategy: str = "",
) -> None:
    element = find_element(driver, locator_strategy, locator_value)
    try:
        element.click()
        return
    except Exception as click_error:
        logger.warning(f"HarmonyOS element.click failed, fallback to clickGesture: {click_error}")
        driver.execute_script("mobile: clickGesture", {"elementId": element.id})


def send_keys_harmonyos(
    driver,
    locator_value: str,
    locator_strategy: str,
    text: str,
) -> None:
    element = find_element(driver, locator_strategy, locator_value)
    try:
        element.click()
    except Exception:
        driver.execute_script("mobile: clickGesture", {"elementId": element.id})

    try:
        element.clear()
    except Exception as clear_error:
        logger.warning(f"HarmonyOS element.clear failed (continuing): {clear_error}")

    try:
        element.send_keys(text)
        return
    except Exception as send_error:
        logger.warning(f"HarmonyOS send_keys failed, fallback to inputText: {send_error}")
        driver.execute_script("mobile: inputText", {"text": text})


def double_click_element_harmonyos(
    driver,
    locator_value: str,
    locator_strategy: str = "",
) -> None:
    element = find_element(driver, locator_strategy, locator_value)
    driver.execute_script("mobile: doubleClickGesture", {"elementId": element.id})


def swipe_harmonyos(
    driver,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int = 1000,
) -> None:
    """Map coordinate swipe to HarmonyOS swipeGesture direction."""
    dx = end_x - start_x
    dy = end_y - start_y
    if abs(dx) >= abs(dy):
        direction = "right" if dx > 0 else "left"
    else:
        direction = "down" if dy > 0 else "up"

    size = driver.get_window_size()
    left = min(start_x, end_x)
    top = min(start_y, end_y)
    width = max(abs(dx), int(size["width"] * 0.1))
    height = max(abs(dy), int(size["height"] * 0.1))
    percent = min(0.95, max(0.1, max(abs(dx) / max(size["width"], 1), abs(dy) / max(size["height"], 1))))

    try:
        driver.execute_script(
            "mobile: swipeGesture",
            {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "direction": direction,
                "percent": percent,
            },
        )
    except Exception as gesture_error:
        logger.warning(f"HarmonyOS swipeGesture failed, fallback to driver.swipe: {gesture_error}")
        driver.swipe(start_x, start_y, end_x, end_y, duration)

    time.sleep(0.5)
