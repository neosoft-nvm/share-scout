"""Shared application identity for window titles and packages."""
NAME = 'ShareScout'
VERSION = '0.4.2'


def window_title(detail=None):
    title = f'{NAME} {VERSION}'
    return f'{title} — {detail}' if detail else title
