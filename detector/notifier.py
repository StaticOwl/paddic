from plyer import notification


def show_warning(page_url):
    notification.notify(
        title="Warning!",
        message=f"{page_url} contains explicit content and has been blocked.",
        timeout=5
    )