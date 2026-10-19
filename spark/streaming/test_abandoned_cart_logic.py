def process_cart_events(events, active=False, latest_activity=None):
    """Test cart state transitions without connecting to Kafka or HBase."""
    for event in sorted(events, key=lambda item: item["timestamp"]):
        event_type = event["event_type"]

        if event_type == "add_to_cart":
            active = True
            latest_activity = event["timestamp"]

        elif event_type in ("remove_from_cart", "checkout", "purchase"):
            active = False
            latest_activity = event["timestamp"]

    return active, latest_activity


def test_added_cart_remains_active():
    active, _ = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"}
    ])
    assert active is True


def test_checkout_deactivates_cart():
    active, _ = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"},
        {"event_type": "checkout", "timestamp": "2026-10-19T10:02:00"},
    ])
    assert active is False


def test_purchase_deactivates_cart():
    active, _ = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"},
        {"event_type": "purchase", "timestamp": "2026-10-19T10:02:00"},
    ])
    assert active is False


def test_remove_deactivates_cart():
    active, _ = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"},
        {"event_type": "remove_from_cart", "timestamp": "2026-10-19T10:02:00"},
    ])
    assert active is False

def test_cart_stays_active_after_another_add():
    active, latest = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"},
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:05:00"},
    ])
    assert active is True
    assert latest == "2026-10-19T10:05:00"


def test_checkout_remains_inactive_after_later_time():
    active, latest = process_cart_events([
        {"event_type": "add_to_cart", "timestamp": "2026-10-19T10:00:00"},
        {"event_type": "checkout", "timestamp": "2026-10-19T10:02:00"},
    ])
    assert active is False
    assert latest == "2026-10-19T10:02:00"


if __name__ == "__main__":
    tests = [
        test_added_cart_remains_active,
        test_checkout_deactivates_cart,
        test_purchase_deactivates_cart,
        test_remove_deactivates_cart,
        test_cart_stays_active_after_another_add,
        test_checkout_remains_inactive_after_later_time,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nAll {len(tests)} cart-state tests passed.")
