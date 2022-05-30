# GeoJSONs and Euroscope
This folder is where all the GeoJSON files that need to be converted should go. 

## How the Script uses this folder
The script is built so that it searches for .geojson files recursively to the first level, so any subfolder in here will be searched, but anything below that won't. This means thta you can, for example, sort your GeoJSON files into airport folders and read them that way, but you can also have a folder called `Off` or whatever, and any files in subfolders of that won't be read. My folder looks like this currently:
```
Input\GeoJSON
            |
            ---- LSZL
            |       |
            |       ---- LSZL_RWY_SATDRAW.geojson
            |       ...
            |
            ---- LSZC
            |       |
            |       ---- LSZC_APRON_SATDRAW.geojson
            |       ...
            |
            ----- Off
                    |
                    ---- LSGC
                    |       |
                    |       ---- LSGC_BLDGS_SATDRAW.geojson
                    |       ...
                    |
                    --- LSGG
...
```
What this means basically is that in my case the files in the LSZL and LSZC subfolders would be read and converted, the files in the LSGC and LSGG subfolders wouldn't , because they're one recursion level too deep.

## How the GeoJSON files should be formatted
The GeoJSON files should have a normal header and be formatted as a `FeatureCollection`. I have been using CRS84 as a coordinate reference system, however any EGS 84 based Lon/Lat system should work. A sample header would look like this:
```JSON
"type": "FeatureCollection",
"name": "LSZC_APRON_SATDRAW",
"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
```

Each feature then needs to be formatted properly so as to be able to be parsed. In the properties there need to be an `apt` attribute, whose value would be the airport ICAO identifier, a `lbl` attribute, whose value would be whatever name you want to give this feature, or the text you want to appear for a Euroscope freetext point, a `clr` attribute, which can take any color value as described in the definitions file readme, but can also be null if you don't want to overwrite the category assigned color which will be the case most of the time. Lastly you'll need a `cat` where the category will be defined as outlined in the configuration file readme.
A properly formatted feature would look like this:
```JSON
{ 
"type": "Feature", 
"properties": 
    { 
    "apt": "LSZC", 
    "lbl": "LSZC Apron", 
    "clr": null, 
    "cat": "apron" 
    }, 
"geometry":
    { 
    "type": "MultiPolygon",
    "coordinates": 
        [ 
            [ 
                [ 
                    [ 8.408865004498832, 46.978113940654644 ],
                    "..."
                ]
            ]
        ]
    }
}
```