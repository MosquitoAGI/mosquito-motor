"""Click execution with a settle delay."""


def click(page, settle_ms=150):
    """Click only makes sense once the cursor stopped moving.

    If the position is not settled the click is skipped; a click mid-drift
    lands somewhere nobody aimed at.
    """
    if hasattr(page, "cursor") and not page.cursor.settled:
        return False
    page.mouse.down()
    page.wait_for_timeout(10)
    page.mouse.up()
    page.wait_for_timeout(settle_ms)
    return True
