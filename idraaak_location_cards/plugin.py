"""QGIS integration. Layer geometry is read only; nothing is uploaded."""

from pathlib import Path

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    NULL,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsWkbTypes,
)
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox

from .cards import ARTICLE_URL, MAX_CARDS, Location, render_cards


def collect_locations(layer, name_field, selected_only=True):
    """Transform single-point features to WGS84 and report skipped records."""
    if layer is None or not layer.isValid():
        raise ValueError("Choose a valid point layer.")
    if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.PointGeometry:
        raise ValueError("Only point layers are supported.")
    if not layer.crs().isValid():
        raise ValueError(
            "The layer needs a valid coordinate reference system."
        )
    if selected_only and layer.selectedFeatureCount() == 0:
        raise ValueError(
            "Select at least one point, or disable Selected features only."
        )
    if name_field and layer.fields().indexFromName(name_field) < 0:
        raise ValueError("The chosen name field no longer exists.")
    features = (
        layer.getSelectedFeatures() if selected_only else layer.getFeatures()
    )
    transform = QgsCoordinateTransform(
        layer.crs(),
        QgsCoordinateReferenceSystem("EPSG:4326"),
        QgsProject.instance().transformContext(),
    )
    output, skipped = [], []
    for count, feature in enumerate(features, start=1):
        if count > MAX_CARDS:
            raise ValueError(
                f"Limit exceeded: select at most {MAX_CARDS} features."
            )
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty() or geometry.isMultipart():
            skipped.append(
                f"Feature {feature.id()}: empty or multipart geometry"
            )
            continue
        try:
            point = transform.transform(geometry.asPoint())
            raw_name = feature[name_field] if name_field else None
            name = (
                f"Point {feature.id()}"
                if raw_name is None
                or raw_name == NULL
                or not str(raw_name).strip()
                else str(raw_name).strip()
            )
            output.append(Location(name, point.y(), point.x()))
        except (QgsCsException, ValueError, OverflowError):
            skipped.append(
                f"Feature {feature.id()}: "
                "invalid coordinates or transformation"
            )
    if not output:
        raise ValueError("No valid single-point features were found.")
    return output, skipped


class LocationCardsDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle("Idraaak Location Cards — preview 0.1.1")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Export printable cards from point features. Coordinates are "
            "converted to WGS84. Static points only, without live tracking."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.layers = QgsMapLayerComboBox()
        self.layers.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.names = QgsFieldComboBox()
        self.names.setAllowEmptyFieldName(True)
        self.layers.layerChanged.connect(self.change_layer)
        form.addRow("Point layer", self.layers)
        form.addRow("Place name field (optional)", self.names)
        self.selected = QCheckBox("Selected features only")
        self.selected.setChecked(True)
        form.addRow("Features", self.selected)
        self.title = QLineEdit("بطاقات مشاركة المواقع")
        self.title.setMaxLength(180)
        form.addRow("Page title", self.title)
        self.language = QComboBox()
        self.language.addItem("العربية — Arabic cards", "ar")
        self.language.addItem("English cards", "en")
        form.addRow("Card language", self.language)
        layout.addLayout(form)
        self.open_after = QCheckBox(
            "Open the saved local HTML file after export"
        )
        self.open_after.setChecked(True)
        layout.addWidget(self.open_after)
        privacy = QLabel(
            f"Up to {MAX_CARDS} features. No uploads or external assets. "
            "The exported file contains the selected locations. "
            "A recipient who opens a map link sends that point to Google Maps."
        )
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        help_button = QPushButton(
            "About static vs live location sharing (Arabic)"
        )
        help_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(ARTICLE_URL))
        )
        layout.addWidget(help_button)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        export_button = buttons.addButton(
            "Export HTML cards", QDialogButtonBox.ActionRole
        )
        export_button.clicked.connect(self.export_cards)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if iface.activeLayer() is not None:
            self.layers.setLayer(iface.activeLayer())
        self.change_layer(self.layers.currentLayer())

    def change_layer(self, layer):
        self.names.setLayer(layer)
        if layer is not None:
            fields = [field.name() for field in layer.fields()]
            self.names.setField("name" if "name" in fields else "")

    def export_cards(self):
        try:
            locations, skipped = collect_locations(
                self.layers.currentLayer(),
                self.names.currentField(),
                self.selected.isChecked(),
            )
            document = render_cards(
                locations,
                self.title.text().strip() or "Location cards",
                self.language.currentData(),
            )
        except (ValueError, QgsCsException) as error:
            QMessageBox.warning(self, "Cannot export cards", str(error))
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save printable cards",
            "location-cards.html",
            "HTML files (*.html)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".html"):
            filename += ".html"
        try:
            Path(filename).write_text(document, encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, "Cannot save file", str(error))
            return
        summary = f"Exported {len(locations)} location cards."
        if skipped:
            summary += f"\nSkipped {len(skipped)} features:\n" + "\n".join(
                skipped[:20]
            )
        QMessageBox.information(self, "Cards saved", summary)
        if self.open_after.isChecked():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(Path(filename).resolve()))
            )


class LocationCardsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon = QIcon(str(Path(__file__).parent / "icon.svg"))
        self.action = QAction(
            icon, "Idraaak Location Cards", self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("Idraaak Location Cards", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action is not None:
            self.iface.removePluginMenu("Idraaak Location Cards", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def run(self):
        if self.dialog is None:
            self.dialog = LocationCardsDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
