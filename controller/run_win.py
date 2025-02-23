import time

from browser import driver
from browser.processor import update_tab_urls, check_tab


def monitor():
    opened_tabs = {}
    not_found_tabs = set()

    while True:
        update_tab_urls(opened_tabs, not_found_tabs)

        for tab_id, tab_info in list(opened_tabs.items()):
            if not tab_info["visited"]:
                if tab_info["tab"] is None:

                    print(f"Opening {tab_info['page_url']}...")
                    for handle in driver.window_handles:
                        driver.switch_to.window(handle)
                        if driver.current_url == tab_info["page_url"]:
                            tab_info["tab"] = handle
                            break
                    if tab_info["tab"] is None:
                        print("Tab not found.")
                        not_found_tabs.add(tab_id)
                        continue

                if tab_info["tab"]:
                    print(f"Checking {tab_info['page_url']}...")
                    check_tab(tab_info["tab"])
                    tab_info["visited"] = True

        for tab_id in not_found_tabs:
            if tab_id in opened_tabs:
                del opened_tabs[tab_id]

        time.sleep(2)