from focus_engine import check_focus


def start_focus_session(domain, title, snippet):
    return check_focus(domain, title, snippet)


def stop_focus_session():
    return {"status": "stopped"}
