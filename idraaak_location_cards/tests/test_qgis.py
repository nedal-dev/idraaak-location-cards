"""Integration checks: run with real QGIS Python bindings and offscreen Qt."""

import math
import os
from pathlib import Path
import tempfile
import unittest

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QWidget

if os.environ.get("QGIS_PREFIX_PATH"):
    QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
application = QgsApplication([], True)
application.initQgis()

from idraaak_location_cards.plugin import (  # noqa: E402
    LocationCardsDialog,
    LocationCardsPlugin,
    collect_locations,
)


def make_layer(crs="EPSG:4326", geometries=None):
    layer = QgsVectorLayer(
        f"Point?crs={crs}&field=name:string", "Test points", "memory"
    )
    geometries = geometries or [("POINT(4.8936 52.3731)", "Amsterdam")]
    for wkt, name in geometries:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        feature["name"] = name
        layer.dataProvider().addFeatures([feature])
    QgsProject.instance().addMapLayer(layer)
    return layer


class Interface:
    def __init__(self, layer):
        self.layer = layer
        self.window = QWidget()
        self.menu = []
        self.toolbar = []

    def mainWindow(self):
        return self.window

    def activeLayer(self):
        return self.layer

    def addPluginToMenu(self, name, action):
        self.menu.append(action)

    def addToolBarIcon(self, action):
        self.toolbar.append(action)

    def removePluginMenu(self, name, action):
        self.menu.remove(action)

    def removeToolBarIcon(self, action):
        self.toolbar.remove(action)


class QgisIntegration(unittest.TestCase):
    def tearDown(self):
        QgsProject.instance().removeAllMapLayers()

    def test_empty_selection_does_not_export_all(self):
        layer = make_layer()
        with self.assertRaisesRegex(ValueError, "Select at least one"):
            collect_locations(layer, "name", True)
        locations, skipped = collect_locations(layer, "name", False)
        self.assertEqual(len(locations), 1)
        self.assertEqual(skipped, [])
        self.assertFalse(layer.isModified())

    def test_projected_layer_to_wgs84_and_selected_subset(self):
        x = 6378137 * math.radians(10)
        y = 6378137 * math.log(math.tan(math.pi / 4 + math.radians(50) / 2))
        layer = make_layer(
            "EPSG:3857",
            [
                (f"POINT({x} {y})", "Projected point"),
                ("POINT(0 0)", "Unselected"),
            ],
        )
        feature_id = next(layer.getFeatures()).id()
        layer.selectByIds([feature_id])
        places, skipped = collect_locations(layer, "name", True)
        self.assertEqual(len(places), 1)
        self.assertAlmostEqual(places[0].latitude, 50, places=6)
        self.assertAlmostEqual(places[0].longitude, 10, places=6)
        self.assertEqual(skipped, [])
        self.assertEqual(layer.featureCount(), 2)

    def test_null_name_fallback_and_invalid_coordinate_skip(self):
        layer = make_layer(
            geometries=[("POINT(1 2)", None), ("POINT(1 100)", "Bad")]
        )
        places, skipped = collect_locations(layer, "name", False)
        self.assertTrue(places[0].name.startswith("Point "))
        self.assertEqual(len(places), 1)
        self.assertEqual(len(skipped), 1)

    def test_multipart_is_not_silently_reduced(self):
        layer = QgsVectorLayer(
            "MultiPoint?crs=EPSG:4326", "Multipart", "memory"
        )
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt("MULTIPOINT((1 2),(3 4))"))
        layer.dataProvider().addFeatures([feature])
        with self.assertRaisesRegex(ValueError, "No valid single-point"):
            collect_locations(layer, "", False)

    def test_dialog_export_and_plugin_lifecycle(self):
        layer = make_layer(
            geometries=[("POINT(4.4695 51.9244)", "محطة روتردام")]
        )
        layer.selectAll()
        iface = Interface(layer)
        plugin = LocationCardsPlugin(iface)
        plugin.initGui()
        self.assertEqual(len(iface.menu), 1)
        plugin.run()
        dialog = plugin.dialog
        self.assertIsInstance(dialog, LocationCardsDialog)
        self.assertTrue(dialog.selected.isChecked())
        self.assertEqual(dialog.layers.currentLayer(), layer)
        dialog.open_after.setChecked(False)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "actual-export.html"
            old_picker, old_info = (
                QFileDialog.getSaveFileName,
                QMessageBox.information,
            )
            try:
                QFileDialog.getSaveFileName = staticmethod(
                    lambda *a, **k: (str(path), "")
                )
                QMessageBox.information = staticmethod(
                    lambda *a, **k: QMessageBox.Ok
                )
                dialog.export_cards()
            finally:
                QFileDialog.getSaveFileName, QMessageBox.information = (
                    old_picker,
                    old_info,
                )
            exported = path.read_text(encoding="utf-8")
            self.assertIn("محطة روتردام", exported)
            self.assertIn("51.924400%2C4.469500", exported)
        if os.environ.get("LOCATION_CARDS_TEST_SCREENSHOT"):
            dialog.grab().save(os.environ["LOCATION_CARDS_TEST_SCREENSHOT"])
        plugin.unload()
        self.assertEqual(iface.menu, [])
        self.assertEqual(iface.toolbar, [])


if __name__ == "__main__":
    print("Real QGIS runtime:", Qgis.QGIS_VERSION, flush=True)
    unittest.main(verbosity=2)
