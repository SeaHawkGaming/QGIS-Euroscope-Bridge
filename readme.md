# VACC Switzerland Sectorfile Tools
Bridging the gap between GIS and EuroScope
## What are the sectorfile tools?
Basically it's, well, a toolbox that allows you to convert  geoJSON  files from a GIS application such as QGIS into either a sectorfile stub for testing in EuroScope or into GNG-importable text files that allow for easy distribution to controllers.
## How do they work?
As this is still an early "proof of concept" version, these tools currently only consist of a Python script with no dedicated user interface, however a GUI is in the works, expect two weeks™.

The conversion from a geoJSON into Euroscope format depends heavily on the definitions file found [here](Input/Configuration/ES%20Exporter%20Definitions.json).
Information on how to work with that file can be found in the [readme](Input/Configuration).

The script then reads the definitions and tries to match the `cat` label in the GeoJSON data to predefined maps from those definitions, and then distributes the geoJSON features into the respective euroscope categories, with the correct colors, feature type and group.

In theory it is also possible with this script to override the category defined color for a single feature either by using a color name as in the GNG or by by using a hex color code in the `color` tag in GeoJSON, however as the latter is not supported by GNG it is not recommended, instead we recommend to use more diverse definitions.

The folder structure is hard coded into the script, so unless you want to modify the script to suit your needs in that regard you must use the given folder structure.

## To Do:
- Currently the formatting functions for Euroscope stub files and GNG texts are two separate and independent functions, however most of what they're doing is identical to each other so I'd like to integrate them into each other and only split the processing where required.
- Continuing to build the UI.
