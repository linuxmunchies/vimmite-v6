"""Small standard-library action picker; terminal setup never executes an action."""

import os
import sys
import textwrap

from .config import LauncherError, MANAGED_ACTIONS, SERVICE_ACTIONS


def rows(manifest):
    result = [(name, action.get("description", "")) for name, action in manifest["actions"].items()]
    result.extend((("doctor", "Check declared prerequisites without starting the app."),
                   ("help", "Show all commands and preparation requirements.")))
    if manifest["adapter"] == "server":
        for name in MANAGED_ACTIONS:
            if name[len("managed-"):] not in manifest["actions"]:
                result.append((name, "Control this checkout's temporary background server."))
        descriptions = {
            "service-install": "Preview an optional persistent Linux user service. Apply from the command line.",
            "service-start": "Start the installed user service; no setup or build.",
            "service-stop": "Stop the installed user service.",
            "service-restart": "Restart the installed user service.",
            "service-status": "Show systemd state; application readiness is reported separately.",
            "service-logs": "Show the last 80 journal lines.",
            "service-enable": "Enable startup with your user manager; does not start the app now.",
            "service-disable": "Disable automatic startup; does not stop a running app.",
            "service-remove": "Preview removal of a stopped, disabled user service. Apply from the command line.",
        }
        result.extend((name, descriptions[name]) for name in SERVICE_ACTIONS)
    return result


def plain(manifest, choices):
    while True:
        print("\n" + manifest["name"])
        for index, (name, description) in enumerate(choices, 1):
            print("{}) {} - {}".format(index, name, description))
        try:
            choice = input("Choose an action, or q to quit: ").strip()
        except EOFError:
            return None
        if choice.lower() in ("q", "quit"):
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(choices):
            return choices[int(choice) - 1][0]
        print("Choose a listed action.")


def draw(screen, manifest, choices):
    import curses
    screen.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    selected = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()

        def put(y, value, attr=0):
            if 0 <= y < height and width > 1:
                value = "".join(c if c.isprintable() else " " for c in value)
                try:
                    screen.addnstr(y, 1, value, max(0, width - 2), attr)
                except curses.error:
                    pass

        if height < 12 or width < 48:
            put(0, "Resize to at least 48 x 12. Escape or Q exits.")
        else:
            put(0, manifest["name"] + " - launcher", curses.A_BOLD)
            put(1, "Up/Down: select   Enter: run   Escape/Q: exit")
            count = height - 8
            first = max(0, min(selected - count + 1, len(choices) - count))
            for offset, index in enumerate(range(first, min(len(choices), first + count))):
                put(3 + offset, ("> " if index == selected else "  ") + choices[index][0],
                    curses.A_REVERSE if index == selected else 0)
            for offset, line in enumerate(textwrap.wrap(choices[selected][1], max(1, width - 3))[:2]):
                put(height - 4 + offset, line)
            put(height - 1, "{}/{}  Actions return to the shell; run menu again to choose another.".format(selected + 1, len(choices)))
        screen.refresh()
        key = screen.getch()
        if key in (27, ord("q"), ord("Q")):
            return None
        if height < 12 or width < 48:
            continue
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(choices)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            selected = len(choices) - 1
        elif key in (10, 13, curses.KEY_ENTER):
            return choices[selected][0]


def pick(manifest):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise LauncherError("menu needs a terminal; use an explicit action (over SSH, use ssh -t for the menu)")
    choices = rows(manifest)
    if os.getenv("TERM", "dumb") != "dumb":
        try:
            import curses
        except ImportError:
            pass
        else:
            try:
                return curses.wrapper(draw, manifest, choices)
            except curses.error:
                print("Terminal capabilities unavailable; using the numbered menu.", file=sys.stderr)
    return plain(manifest, choices)
