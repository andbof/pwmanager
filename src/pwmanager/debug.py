#!/usr/bin/python3

debug_on = False


def debug(*args, **kwargs):
    if debug_on:
        print(*args, **kwargs)


def set_debug(dbg):
    global debug_on
    debug_on = True if dbg else False
