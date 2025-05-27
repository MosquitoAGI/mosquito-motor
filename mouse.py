"""Click execution with a settle delay."""


def click(page, settle_ms=150):
    page.mouse.down()
    page.wait_for_timeout(10)
    page.mouse.up()
    page.wait_for_timeout(settle_ms)
    return True
