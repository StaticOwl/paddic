from browser.devtools import is_browser_running, is_debugging_active, restart_browser_with_devtools
from controller.run_win import monitor as win_monitor


def monitor(system: str = "Windows"):
    browser_process = is_browser_running()
    if browser_process and not is_debugging_active():
        restart_browser_with_devtools(browser_process)

    if is_debugging_active():
        print(f"Monitoring browser activity on {system}...")
        match system:
            case "Darwin":
                pass
            case "Windows":
                win_monitor()