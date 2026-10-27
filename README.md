# Idraaak Location Cards — 0.1.1 preview

Export selected QGIS point features to a self-contained, printable HTML page. Each card has a place name, WGS84 latitude/longitude, a Google Maps link and its written URL. Choose an Arabic RTL or English card layout. Work locally and print to PDF using the browser.

This is a **preview**, not an approved QGIS repository release. QGIS 3.34–3.x is the intended target. Six rendering tests and five integration tests passed using real QGIS 3.34.4 bindings and offscreen Qt. See `VALIDATION.md` for the scope and remaining desktop checks. No QGIS 4 compatibility is claimed.

## Install and try

1. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
2. Choose `idraaak_location_cards-0.1.1.zip` and install it.
3. Load `examples/demo-points.geojson` from this package, or use your own valid point layer.
4. Select the features you want to share. Open **Plugins → Idraaak Location Cards** or use the toolbar icon.
5. Choose the point layer and optional name field. **Selected features only** is on by default. Disable it deliberately to export the whole layer, up to 1,000 features.
6. Choose Arabic or English, set a title, then **Export HTML cards**.
7. Open the local HTML file. Use **Print or save PDF** for a printable copy. Share the HTML or PDF only with intended recipients.

The dialog uses English labels; exported cards support Arabic and English. Sample landmarks have approximate coordinates and are for testing only.

## Behavior and limits

- Coordinates are transformed from the layer CRS to EPSG:4326 using the current QGIS project transform context.
- Only single-point features are supported. Empty and multipart geometries, failed transformations and coordinates outside WGS84 bounds are skipped and counted.
- An empty selection never silently exports all features. Choose a valid CRS before exporting; the tool cannot infer one.
- Displayed coordinates have six decimal places; that does not imply survey accuracy.
- Up to 1,000 features per export. Source layers and attributes are never modified.
- The HTML has no external scripts, fonts, images or automatic network calls. Printing uses the browser. There is no basemap, QR generator, routing engine or live tracking.
- For a multipoint layer, convert it to single parts using QGIS before using this tool.
- Page titles and feature names are HTML-escaped.

## Privacy

No account, API key, upload or telemetry. The exported file contains precise selected coordinates. Opening a Google Maps link sends those coordinates to Google under its policies. Opening the explanatory Idraaak link makes a normal website request. Local HTML includes `noindex,nofollow` as a precaution, but this does not make a publicly uploaded file private.

## Context

The Arabic article [static and live location sharing](https://idraaak.com/share-live-location-whatsapp-google-maps/) explains the difference between sharing a fixed point and live tracking. The cards always share fixed points. The article includes installation and export instructions for the preview.

Existing QGIS plugins already create online-map links and QR codes. This preview focuses on batch, printable Arabic/English cards. It does not claim to introduce map-link generation.

## Before repository submission

- The dialog, export and coordinate handling passed tests on QGIS 3.34.4 bindings with offscreen Qt. A full interactive desktop ZIP-install check remains unverified; see VALIDATION.md.
- The homepage article contains the installation and export steps.
- The source repository and issue tracker are public at https://github.com/nedal-dev/idraaak-location-cards and https://github.com/nedal-dev/idraaak-location-cards/issues. The metadata points to these real URLs.
- Verify the repository source and uploaded ZIP match. Obtain a real QGIS desktop screenshot.
- Recheck current repository rules and submit once. Publication and link attributes are subject to review and must be checked on the eventual public page.

License: GPL-3.0-or-later. Copyright 2026 Idraaak / Nedal Sh. See LICENSE.
