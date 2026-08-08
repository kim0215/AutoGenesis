# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import time
import json
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tools.appium_driver_tool import simplify_page_source
from tools.harmonyos_helpers import resolve_locator
from utils.logger import log_tool_call
from utils.response_format import format_tool_response, init_tool_response
from utils.gen_code import record_calls


logger = logging.getLogger(__name__)


def register_harmonyos_driver_tools(mcp, driver_manager):
    """Register HarmonyOS-specific driver tools to MCP server."""

    @mcp.tool()
    @log_tool_call
    @record_calls(driver_manager)
    async def press_key(caller: str, text: str, step: str = "", scenario: str = "", step_raw: str = "") -> str:
        """press keyboard key to the HarmonyOS device.

        Args:
            caller: Caller name
            text: keycode to send (e.g., '1' for Home)
            step: Step name
            step_raw: Raw original step text
            scenario: Scenario name
        """
        resp = init_tool_response()
        driver = driver_manager._driver
        try:
            driver.press_keycode(int(text))
            resp["status"] = "success"
        except Exception as e:
            logger.error(f"press key code error: {e}")
            resp["status"] = "error"
            resp["error"] = f"press key code error: {str(e)}"
        page_source = driver.page_source
        resp["data"] = {"page_source": simplify_page_source(page_source)}
        return json.dumps(format_tool_response(resp))

    @mcp.tool()
    @log_tool_call
    @record_calls(driver_manager)
    async def long_press_element(
        caller: str,
        locator_value: str,
        locator_strategy: str = "",
        duration: int = 2000,
        step: str = "",
        scenario: str = "",
        step_raw: str = "",
    ) -> str:
        """Long press on a HarmonyOS element by its locator.

        Args:
            caller: Caller name
            locator_value: Value of the locator (e.g., visible text)
            locator_strategy: Locator strategy (e.g., 'text', 'key', 'HypiumBy')
            duration: Duration of the long press in milliseconds (default is 2000ms)
            step: Step name
            scenario: Scenario name
            step_raw: Raw original step text
        """
        resp = init_tool_response()
        driver = driver_manager._driver
        try:
            locator = resolve_locator(locator_strategy, locator_value)
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(locator))
            driver.execute_script(
                "mobile: longClickGesture",
                {"elementId": element.id, "duration": duration},
            )
            resp["status"] = "success"
        except Exception as e:
            logger.error(f"Error long pressing element {locator_value}: {e}")
            resp["status"] = "error"
            resp["error"] = f"Error long pressing element {locator_value}: {str(e)}"
        if resp["status"] == "success":
            time.sleep(2)

        page_source = driver.page_source
        resp["data"] = {"page_source": simplify_page_source(page_source)}
        return json.dumps(format_tool_response(resp))

    @mcp.tool()
    @log_tool_call
    @record_calls(driver_manager)
    async def swipe_back(caller: str, step: str = "", scenario: str = "", step_raw: str = "") -> str:
        """Perform HarmonyOS side-swipe back gesture."""
        resp = init_tool_response()
        driver = driver_manager._driver
        try:
            driver.execute_script("mobile: swipeBack")
            resp["status"] = "success"
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error performing swipeBack: {e}")
            resp["status"] = "error"
            resp["error"] = f"Error performing swipeBack: {str(e)}"
        page_source = driver.page_source
        resp["data"] = {"page_source": simplify_page_source(page_source)}
        return json.dumps(format_tool_response(resp))

    @mcp.tool()
    @log_tool_call
    @record_calls(driver_manager)
    async def swipe_home(caller: str, step: str = "", scenario: str = "", step_raw: str = "") -> str:
        """Perform HarmonyOS swipe-up home gesture."""
        resp = init_tool_response()
        driver = driver_manager._driver
        try:
            driver.execute_script("mobile: swipeHome")
            resp["status"] = "success"
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error performing swipeHome: {e}")
            resp["status"] = "error"
            resp["error"] = f"Error performing swipeHome: {str(e)}"
        page_source = driver.page_source
        resp["data"] = {"page_source": simplify_page_source(page_source)}
        return json.dumps(format_tool_response(resp))
