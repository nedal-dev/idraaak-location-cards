"""Idraaak Location Cards for QGIS."""


def classFactory(iface):
    from .plugin import LocationCardsPlugin

    return LocationCardsPlugin(iface)
