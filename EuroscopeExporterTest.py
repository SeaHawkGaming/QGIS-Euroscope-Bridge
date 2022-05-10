#===============================================================================================================#
#                                                                                                               #
#                                      VACC Switzerland GeoJSON Exporter                                        #
#                                                                                                               #
#===============================================================================================================#
#                                                                                                               #
# Version 0.01 Alpha                                                                                            #
# Last revision: 2021-11-12                                                                                     #
# Changelog:                                                                                                    #
#   - 0.01                                                                                                      #
#       - New                                                                                                   #
# Known Issues:                                                                                                 #
#   - Polygons parsed to lines do not parse holes                                                               #
# To Do:                                                                                                        #
#   - Colour Listing for Jonas                                                                                  #
#   - Export capable for GNG                                                                                    #
#                                                                                                               #
#===============================================================================================================#
#                                                                                                               #
# This is a basic converter / exporter that takes GeoJSON in a predefined format, applies a ruleset             #
# from a definitions file to it and from that generates a stub sector file that can be used for testing.        #
# In a second step a GNG compatible text file can be generated to easily import the generated data into         #
# an already established sectorfile.                                                                            #
#                                                                                                               #
# For conventions on the format of the input GeoJSON files check out the specification in the Ground Layouts    #
# oneDrive folder, additionally some further configuration of fields and attributes can be made through the     #
# definitions without touching the code.                                                                        #
#                                                                                                               #
# For questions or inquiries contact me at luca.paganini(at)vacc.ch                                             #
#                                                                                                               #
#===============================================================================================================#

from os import path, write, listdir, mkdir, getcwd, scandir
from json import load,dumps
from re import search
from datetime import datetime
import math

# First, to facilitate parsing, create a dictionary that holds all entries, split into the different ES
# categories used. This dict is initialized empty to prevent issues with python variable handling

esData = {
    "geo":{
        "Output String":"",
        "Features":[]
    },
    "freetext":{
        "Output String":"",
        "Features":[]
    },
    "regions":{
        "Output String":"",
        "Features":[]
    }
}

gngData = {
    "geo":{
        "Output String":"",
        "Features":{}
    },
    "freetext":{
        "Output String":"",
        "Features":{}
    },
    "regions":{
        "Output String":"",
        "Features":{}
    }
}


globalDebugging = False
if globalDebugging:
    loggingLevel = "Verbose"
else:
    loggingLevel = "Standard"

log = "Started Logging at " + datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " at logging level " + loggingLevel + "\n"

colorsUsed = []

# I create two strings with the current date, this is important as it's used in the output file name and the .sct and .ese files need to have exactly the same name

dateString = datetime.now().strftime("%Y-%m-%d")
dateStringLong = datetime.now().strftime("%Y%m%d-%H%M%S")

# Here a few file and path definitions.

defFilePath = path.dirname(__file__) + "\\Input\\Configuration\\ES Exporter Definitions.json"               # Definitions file, used to create rules for parsing
geoJSONFolderPath = path.dirname(__file__) + "\\Input\\GeoJSON\\"                                           # Input GeoJSON location
sctHeaderPath = path.dirname(__file__) + "\\Input\\Configuration\\sct_File_Header.txt"                      # Input of the sct Header file used as a basis for building the export
eseHeaderPath = path.dirname(__file__) + "\\Input\\Configuration\\ese_File_Header.txt"                      # Input of the ese Header file used as a basis for building the export
outputFolder = path.dirname(__file__) + "\\Output\\"                                                        # Output folder location

if globalDebugging:
    print("Folder paths:\n  Definitions File: " + defFilePath + "\n  geoJSON Folder: " + geoJSONFolderPath + "\n  .SCT  header File: " + sctHeaderPath + "\n  .ESE  header File: " + eseHeaderPath + "\n  Output Folder: " + outputFolder)

# Here we check whether the output folder exists, if not we create it.

if not path.isdir(outputFolder):
    mkdir(outputFolder)
    log += "Creating output folder at " +  outputFolder + "\n"

# Here we define a function to read the definitions file and then dump it into a global dict for easy access

def readDefinitions ():
    with open (defFilePath) as defFile:
        global definitions
        definitions = load(defFile)

# Now to initially grab all definitions, we run the function defined above

readDefinitions()

# This is a quick helper function to convert coordinates from QGIS (DDD.ddddd) to EuroScope (DDD.MM.SS.sss) Format 

def decimalDegreesToESNotation(coordinatePair):
    north = coordinatePair[1]
    east = coordinatePair[0]

    northDegrees = math.floor(math.fabs(north))
    northMinutes = math.floor((math.fabs(north) - northDegrees) * 60)
    northSeconds = round((math.fabs(north) - northDegrees - northMinutes / 60) * 3600, 3)

    if northSeconds < 10:
        northSeconds = "0" + str(northSeconds)
    

    formattedNorth = str(northDegrees).rjust(3,"0") + "." + str(northMinutes).rjust(2,"0") + "." + str(northSeconds).ljust(6,"0")
    if north < 0:
        formattedNorth = "S" + formattedNorth
    else:
        formattedNorth = "N" + formattedNorth
    
    eastDegrees = math.floor(math.fabs(east))
    eastMinutes = math.floor((math.fabs(east) - eastDegrees) * 60)
    eastSeconds = round((math.fabs(east) - eastDegrees - eastMinutes / 60) * 3600, 3)

    if eastSeconds < 10:
        eastSeconds = "0" + str(eastSeconds)

    formattedEast = str(eastDegrees).rjust(3,"0") + "." + str(eastMinutes).rjust(2,"0") + "." + str(eastSeconds).ljust(6,"0")
    if east < 0:
        formattedEast = "W" + formattedEast
    else: 
        formattedEast = "E" + formattedEast
    
    return formattedNorth + " " + formattedEast

# This is the function that does most of the heavy lifting, it takes a dictionary that contains all the necessary data read from the geoJSON input file and 
# mapped to more applicable categories through the definitions file and converts it into a multi-line string in the correct format for EuroScope

def formatFeatureForES (featureObject,featureType,debugging=False):

    global log

    # Initially we need to check which category of ES object we're writing to as the formatting conventions in EuroScope / VRC aren't exactly standardized
    # First step is to format the color of the object for Euroscope, as at least this part is common to all object formats

    color = featureObject["Color"]
    if not color.isdecimal():
        color = "COLOR_" + color

    # Secondly we check what kind of a feature type we're dealing with and extracting the coordinate list accordingly, this is necessary due to a nesting 
    # quirk of GeoJSON where polygons are nested deeper than lines, which are nested deeper than points. The check for holes in polygons has already been
    # implemented, however they are currently not yet processed.

    if debugging:
        print("Feature Type of working feature is: " + featureObject["Feature Type"])

    if len(featureObject["Coordinates"]) == 0:
        log += "Found an empty feature of group " + featureObject["Group"] + ", skipping."
        return -1
    if featureObject["Feature Type"] == "Polygon":
        if not featureType == "MultiPolygon":
            log += "Tried mapping a feature of group " + featureObject["Group"] + " that isn't a polygon to a Euroscope region.\n"
            return -1
        coordinates = featureObject["Coordinates"][0]
    elif featureObject["Feature Type"] == "Line":
        if not featureType == "MultiLineString":
            if featureType == "MultiPolygon":
                log += "Mapping a polygon feature of group " + featureObject["Group"] + " to a Euroscope geo line, holes may be lost in the process.\n"
                coordinates = featureObject["Coordinates"][0]
            elif featureType == "LineString":
                coordinates = [featureObject["Coordinates"]]
            else:
                log += "Tried mapping a point feature or a feature of unknown type of group " + featureObject["Group"] + " to a Euroscope geo line.\n"
                return -1
        else:
            coordinates = featureObject["Coordinates"]

            
    elif featureObject["Feature Type"] == "Point":
        if not featureType == "Point":
            if featureType == "MultiPolygon":
                log += "Mapping a polygon feature of group " + featureObject["Group"] + " to a Euroscope freetext point, only the first coordinate will be considered.\n"
                coordinates = featureObject["Coordinates"][0][0]
            if featureType == "MultiLineString":
                log += "Mapping a line feature of group " + featureObject["Group"] + " to a Euroscope freetext point, only the first coordinate will be considered.\n"
                coordinates = featureObject["Coordinates"][0]
        else:
            coordinates = featureObject["Coordinates"]
    else:
        print("Something went wrong with a feature object at " + featureObject["Group"] + " which has an invalid feature type (" + featureObject["Feature Type"] + ")")
        return -1
    if "Priority" in featureObject:
        priority = featureObject["Priority"]

    # Initially I deal with the regions as they are the most complex feature

    if featureObject["ES Category"] == 'regions':

        # I create an empty dict with the priority and the formatted region to be filled by the subsequent functions

        featureDict = {
                "Priority":priority,
                "Formatted Region":""
            }
        if debugging:
            print("This Region Feature has a length of " + str(len(coordinates)))

        # I have to make sure I catch any possible holes in the polygon, those would be a second item in the enclosing 
        # list for the multipolygon feature in the geoJSON, so I iterate over the list containing the coordinate lists

        for i in range(len(coordinates)):
            if debugging:
                print("  Currently working on layer " + str(i + 1) + "/" + str(len(coordinates)))

            # Defining the current coordinate list as the current item in the list of all coordinate lists

            currentCoordsList = coordinates[i]

            # Set the color for all objects except for the base layer object to grass

            if not i == 0:
                if debugging:
                    print("    Setting Color to grass for hole")
                #color = "11823615"    # Hot Pink for debugging purposes
                color = "COLOR_AoRground1"
            
            # Figure out what the first set of coordinates is as those are prefixed with the color for the entire region

            firstCoords = decimalDegreesToESNotation(currentCoordsList[0])

            # Create the string with the feature, initializing by creating the region name header and the first line with the color prefix

            coordinateText = "REGIONNAME " + featureObject["Group"] + "\n" + (color).ljust(27) + firstCoords + "\n"

            # For all further coordinates I can just chuck them into the string after justifying them according to the convention

            for coordinatePair in currentCoordsList[1:-1]:
                formattedCoords = decimalDegreesToESNotation(coordinatePair)
                coordString = formattedCoords.rjust(56) + "\n"
                coordinateText += coordString

            # Finally, I can append the created string to the feature dict

            featureDict["Formatted Region"] += coordinateText

        # And then return that feature dict to the calling function

        return featureDict

    # in a second step I deal with all the lines which are categorized as GEO by EuroScope

    elif featureObject["ES Category"] == 'geo':

        # Same principle as above, I need the first coordinate pair to prefix the feature name

        # Again here I initialize the string to be written into the sector file

        coordinateText = ""
        for element in coordinates:
            firstCoords = decimalDegreesToESNotation(element[0]) + " " + decimalDegreesToESNotation(element[1])

            coordinateText += featureObject["Group"].ljust(41) + firstCoords + " " + color + "\n"

            # Now I iterate over all the elements in the coordinate list of the feature. As 
            # EuroScope treats all lines as a group of individual line segments I need to draw each 
            # segment, consisting of two coordinates, separately.

            for i in range(len(element) - 2):
                thisCoord = decimalDegreesToESNotation(element[i + 1])
                nextCoord = decimalDegreesToESNotation(element[i + 2])
                coordinateText += (thisCoord + " " + nextCoord).rjust(100) + " " + color + "\n"

        # Here I'm doing the lazy thing and only return the coordinate string, but I'll catch that in the next function

        return coordinateText

    elif featureObject["ES Category"] == "freetext":
        if "Label" in featureObject:
            outputText = decimalDegreesToESNotation(coordinates).replace(" ",":") + ":" + featureObject["Group"] + ":" + featureObject["Label"] + "\n"
            return outputText
        else:
            log += "Missing label attribute for a freetext feature of group " + featureObject["Group"] + ", skipping feature.\n"
            return -1


    # If we're dealing with any other feature type (currently freetext falls into this) I return -1 to prevent the function calling this from complaining.

    return -1

def formatFeatureForGng (featureObject,featureType,debugging=False):

    global log

    # Initially we need to check which category of ES object we're writing to as the formatting conventions in EuroScope / VRC aren't exactly standardized
    # First step is to format the color of the object for Euroscope, as at least this part is common to all object formats

    color = featureObject["Color"]
    if not color.isdecimal():
        color = "COLOR_" + color

    # Secondly we check what kind of a feature type we're dealing with and extracting the coordinate list accordingly, this is necessary due to a nesting 
    # quirk of GeoJSON where polygons are nested deeper than lines, which are nested deeper than points. The check for holes in polygons has already been
    # implemented, however they are currently not yet processed.

    if debugging:
        print("Feature Type of working feature is: " + featureObject["Feature Type"])

    if len(featureObject["Coordinates"]) == 0:
        log += "Found an empty feature of group " + featureObject["Group"] + ", skipping."
        return -1
    if featureObject["Feature Type"] == "Polygon":
        if not featureType == "MultiPolygon":
            log += "Tried mapping a feature of group " + featureObject["Group"] + " that isn't a polygon to a Euroscope region.\n"
            return -1
        coordinates = featureObject["Coordinates"][0]
    elif featureObject["Feature Type"] == "Line":
        if not featureType == "MultiLineString":
            if featureType == "MultiPolygon":
                log += "Mapping a polygon feature of group " + featureObject["Group"] + " to a Euroscope geo line, holes may be lost in the process.\n"
                coordinates = featureObject["Coordinates"][0]
            elif featureType == "LineString":
                coordinates = [featureObject["Coordinates"]]
            else:
                log += "Tried mapping a point feature or a feature of unknown type of group " + featureObject["Group"] + " to a Euroscope geo line.\n"
                return -1
        else:
            coordinates = featureObject["Coordinates"]
    elif featureObject["Feature Type"] == "Point":
        if not featureType == "Point":
            if featureType == "MultiPolygon":
                log += "Mapping a polygon feature of group " + featureObject["Group"] + " to a Euroscope freetext point, only the first coordinate will be considered.\n"
                coordinates = featureObject["Coordinates"][0][0]
            if featureType == "MultiLineString":
                log += "Mapping a line feature of group " + featureObject["Group"] + " to a Euroscope freetext point, only the first coordinate will be considered.\n"
                coordinates = featureObject["Coordinates"][0]
        else:
            coordinates = featureObject["Coordinates"]
    else:
        print("Something went wrong with a feature object at " + featureObject["Group"] + " which has an invalid feature type (" + featureObject["Feature Type"] + ")")
        return -1
    if "Priority" in featureObject:
        priority = featureObject["Priority"]

    # Initially I deal with the regions as they are the most complex feature

    if featureObject["ES Category"] == 'regions':

        # I create an empty dict with the priority and the formatted region to be filled by the subsequent functions

        featureDict = {
                "Priority":priority,
                "RegionName":featureObject["Group"],
                "Formatted Region":""
            }
        if debugging:
            print("This Region Feature has a length of " + str(len(coordinates)))

        # I have to make sure I catch any possible holes in the polygon, those would be a second item in the enclosing 
        # list for the multipolygon feature in the geoJSON, so I iterate over the list containing the coordinate lists

        for i in range(len(coordinates)):
            if debugging:
                print("  Currently working on layer " + str(i + 1) + "/" + str(len(coordinates)))

            # Defining the current coordinate list as the current item in the list of all coordinate lists

            currentCoordsList = coordinates[i]

            # Set the color for all objects except for the base layer object to grass

            if not i == 0:
                if debugging:
                    print("    Setting Color to grass for hole")
                #color = "11823615"    # Hot Pink for debugging purposes
                color = "COLOR_AoRground1"
            

            # Create the string with the feature, initializing by creating the region name header and the first line with the color prefix

            coordinateText = color + "\n"

            # For all further coordinates I can just chuck them into the string after justifying them according to the convention

            for coordinatePair in currentCoordsList:
                formattedCoords = decimalDegreesToESNotation(coordinatePair)
                coordString = formattedCoords + "\n"
                coordinateText += coordString

            # Finally, I can append the created string to the feature dict

            featureDict["Formatted Region"] += coordinateText

        # And then return that feature dict to the calling function

        return featureDict

    # in a second step I deal with all the lines which are categorized as GEO by EuroScope

    elif featureObject["ES Category"] == 'geo':

        # Same principle as above, I need the first coordinate pair to prefix the feature name

        # Again here I initialize the string to be written into the sector file
        airportICAO = featureObject["Group"][:4]
        restOfGroup = featureObject["Group"][5:].rsplit(" ")
        featureDict = {"Group":featureObject["Group"],"Airport":airportICAO,"Category":restOfGroup[0],"Name":" ".join(restOfGroup[1:]),"Code":""}
        for element in coordinates:
            
            # Now I iterate over all the elements in the coordinate list of the feature. As 
            # EuroScope treats all lines as a group of individual line segments I need to draw each 
            # segment, consisting of two coordinates, separately.

            for i in range(len(element) - 1):
                thisCoord = decimalDegreesToESNotation(element[i])
                nextCoord = decimalDegreesToESNotation(element[i + 1])
                featureDict["Code"] += (thisCoord + " " + nextCoord) + " " + color + "\n"

        # Here I'm doing the lazy thing and only return the coordinate string, but I'll catch that in the next function

        return featureDict

    elif featureObject["ES Category"] == "freetext":
        if "Label" in featureObject:
            airportICAO = featureObject["Group"][:4]
            labelgroup = featureObject["Group"][5:]
            outputText = decimalDegreesToESNotation(coordinates).replace(" ",":") + "::" + featureObject["Label"]
            featureDict = {"Group":featureObject["Group"],"Airport":airportICAO,"Labelgroup":labelgroup,"Code":outputText}
            return featureDict
        else:
            log += "Missing label attribute for a freetext feature of group " + featureObject["Group"] + ", skipping feature.\n"
            return -1


    # If we're dealing with any other feature type (currently freetext falls into this) I return -1 to prevent the function calling this from complaining.

    return -1


# This is just a helper function to assign a feature its attributes from the definitions file

def categoryMapping(category,airport,debugging = False):

    global log

    # If the category is not defined it can obviously not be mapped so we write to the log file and skip out of the function
    if category == None:
        log += "Skipping feature because of missing category in file "
        return -1

    # First I split the category string into the main category and the suffixes

    splitCat = category.split("_")
    mainCategory = splitCat[0]

    # Then I try mapping the object through the definitions to get the default state of the main category. If the category isn't defined in the 
    # definitions file we once again skip out of the function

    if not mainCategory in definitions["Category Mapping"]:
        log += "Unknown category " + mainCategory + " found in file "
        return -1
    mappedObject = definitions["Category Mapping"][mainCategory]
    outputObject = dict(mappedObject["default"])

    if debugging:
        print ("Input Category: " + category + "\n  Default Group: " + outputObject["Group"])

    # If I have found any suffixes I'll iterate through them and look for them in the definitions file, if they're defined we overwrite the default
    # info with the suffix info where it differs.
    if len(splitCat) > 1:
        if "gr" in splitCat and debugging:
            print("Found a Grass feature for airport " + airport + str(splitCat))
        suffix = splitCat[1]
        if debugging:
            print("  Now working on suffix " + suffix)
        if not suffix in mappedObject["suffixes"]:
            log += "Unknown suffix " + suffix + " to category " + mainCategory + " found in file "
            return -1
        suffixDescription = mappedObject["suffixes"][suffix]
        for key in suffixDescription:
            if not key =="Additional Suffixes":
                outputObject[key] = suffixDescription[key]
                if len(splitCat) > 2:
                    if search("([0-3]{1}[0-9]{1}[LCR]?)",splitCat[2]):
                        outputObject["Group"] = outputObject["Group"].replace("$1",splitCat[-1])
                    else:
                        log += "Unmappable additional suffix " + splitCat[2] + " found in " + category
            elif len(splitCat) > 2:
                if not search("([0-3]{1}[0-9]{1}[LCR]?)",suffix):
                    for additionalSuffix in suffixDescription["Additional Suffixes"]:
                        if additionalSuffix in splitCat:
                            for additionalKey in suffixDescription["Additional Suffixes"][additionalSuffix]:
                                outputObject[additionalKey] = suffixDescription["Additional Suffixes"][additionalSuffix][additionalKey]
                else:
                    outputObject["Group"] = outputObject["Group"].replace("$1",splitCat[-1])

    # The Group attribute often contains an airport tag so we replace it in here already
    outputObject["Group"] = outputObject["Group"].replace("$airport",airport)

    if debugging:
        print("Output:\n  Group: " + outputObject["Group"] + "\n  ES Category: " + outputObject["ES Category"])

    # If everything worked fine we can now return the object we just created wit the mapped info

    return outputObject

# Another helper function to transform hex codes into Euroscope decimal 24bit color integers. Because I'm only working with strings to build the output
# file I return the integer as a string

def esColorCode(colorHex,debugging = False):
    hexString = colorHex[1:]
    red = int(hexString[0:2],16)
    green = int(hexString[2:4],16)
    blue = int(hexString[4:],16)
    decString = str(blue * 65536 + green * 256 + red)
    if debugging:
        print("Red: " + str(red) + ", Green: " + str(green) + ", Blue: " + str(blue))
    return decString

# This is one of the big bois, it reads a single GeoJSON file and parses it into the respective categories

def readGeoJSONFile(path,debugging = False):

    global log

    # The first and most obvious step is to actually open and load the file into a dict courtesy of the json library

    with open (path) as JSONFile:
        data = load(JSONFile)

    # Next we step through each feature in the data we loaded. We can safely discard the header as all the information in there is not necessary for our purposes

    for feature in data['features']:

        # If there is no geometry defined for the feature it's not relevant for us, we can skip that.

        if feature["geometry"] == None:
            continue

        # I noticed that QGIS sometimes decides to capitalize the keys so here I make them all lowercase so that I can access them easily

        feature["properties"] = {key.lower(): value for key, value in feature["properties"].items()}

        # Load a few key properties as easily accessed variables

        airport = feature['properties']['apt']
        label = feature['properties']['lbl']
        color = feature['properties']['clr']
        category = feature['properties']['cat']
        featureType = feature["geometry"]["type"]

        # If attributes are missing we cannot parse the feature so we log that and skip the feature

        if airport == None:
            log += "Skipping feature because of missing \"apt\" attribute in file " + path + "\n"
            continue
        
        if "_dis" in category:
            log += "Skipping disabled feature in file " + path + "\n"
            continue

        # Now let's use that helper function to map category of the current feature to the attributes found in the definitions

        featureObject = categoryMapping(category,airport,debugging)

        # If the function fails it will append the log with how it failed but it doesn't know what file it failed on so we write that into the log here.

        if featureObject == -1:
            log += path + "\n"
            continue

        # Some features aren't intended for use in EuroScope so we ignore them.

        if "Ignore" in featureObject:
            if featureObject["Ignore"]:
                continue
        
        # Next, let's extract the coordinates of the feature as well. I only do this now to prevent issues with null items

        coordinates = feature['geometry']['coordinates']

        # Now we can add a few additional attributes to the feature object that are needed for some subfunctions

        featureObject["Label"] = label
        featureObject["Coordinates"] = coordinates
        
        # If we have a color assigned in the feature we'll have to overwrite the default colour from the definition

        if not color == None:
            if debugging:
                print("Setting custom color " + color)

            # First let's deal with anything that isn't a hex code as we need to look those up.

            if not search("#[0-9a-fA-F]{6}",color):

                # This checks for custom defined two letter color codes specified in the definitions, this is used as a 
                # shortcut to create new colors not yet defined in the sectorfile
                if search("^[a-z]{2}$",color):
                    for defColor in definitions["Colors"]["Additional Colors"]:
                        if defColor["Tag"] == color:
                            featureObject["Color"] = defColor["Color"]
                            if debugging:
                                print("  Custom Color " + featureObject["Color"] + " set!")
                
                # Any other color *should* be one already defined in the sector file so we can just write it into field

                else:
                    featureObject["Color"] = color
                    if debugging:
                        print("  Custom Color " + featureObject["Color"] + " set!")
            
            # Here we deal with the hex code defined colors, they're just passed to the appropriate function.
            
            else:
                featureObject["Color"] = esColorCode(color)
                if debugging:
                    print("  Custom Color " + featureObject["Color"] + " set!")

        # This is a little bit of a special case, there's a few definitions that use hex codes by default, we need to catch those

        elif search("#[0-9a-fA-F]{6}",featureObject["Color"]):
            featureObject["Color"] = esColorCode(featureObject["Color"])
        
        # And now that we have dealt with all the preparation we can pass the feature to the formatter

        if not featureObject["Color"] in colorsUsed:
            colorsUsed.append(featureObject["Color"])

        formattedFeature = formatFeatureForES(featureObject,featureType,debugging)
        gngFormattedFeature = formatFeatureForGng(featureObject,featureType,debugging)
        global esData
        global gngData

        # After the feature has been formatted it is then sorted into the correct category

        if not formattedFeature == -1:
            # print("Key: " + gngFormattedFeature["RegionName"] + "\nObject: " + dumps(gngData[featureObject["ES Category"]]["Features"],indent=1))
            if featureObject["ES Category"] == "regions":
                esData[featureObject["ES Category"]]["Features"].append(formattedFeature)
                if gngFormattedFeature["RegionName"] in gngData[featureObject["ES Category"]]["Features"]:
                    gngData[featureObject["ES Category"]]["Features"][gngFormattedFeature["RegionName"]].append(gngFormattedFeature)
                else:
                    gngData[featureObject["ES Category"]]["Features"][gngFormattedFeature["RegionName"]] = [gngFormattedFeature]
            else: 
                esData[featureObject["ES Category"]]["Output String"] += formattedFeature
                if gngFormattedFeature["Group"] in gngData[featureObject["ES Category"]]["Features"]:
                    gngData[featureObject["ES Category"]]["Features"][gngFormattedFeature["Group"]]["Code"] += "\n" + gngFormattedFeature["Code"]
                else:
                    gngData[featureObject["ES Category"]]["Features"][gngFormattedFeature["Group"]] = gngFormattedFeature
        else:
            log += "Skipping feature due to error in formatting from file " + path + "\n"
            

# Regions need to be sorted so that the layering is correct, this is accomplished by sorting the array on the priority attribute 
# from the definitions file

def sortRegions(target="euroscope",debugging=False):
    global esData
    global gngData
    if target == "euroscope":
        sortedList = []
        for feature in esData["regions"]["Features"]:
            if len(sortedList) == 0:
                sortedList.append(feature)
            else:
                for i in range(len(sortedList)):
                    if feature["Priority"] < sortedList[i]["Priority"]:
                        if debugging:
                            print("Inserting because " + str(feature["Priority"]) + " is less than " + str(sortedList[i]["Priority"]))
                        sortedList.insert(i, feature)
                        break
                    elif i == len(sortedList) - 1:
                        if debugging:
                            print("Inserting because I've reached the end of the list")
                        sortedList.append(feature)
        esData["regions"]["Features"] = list(sortedList)

        for feature in sortedList:
            esData["regions"]["Output String"] += feature["Formatted Region"]
    elif target == "gng":
        for key in gngData["regions"]["Features"]:
            gngSortedList = []
            for feature in gngData["regions"]["Features"][key]:
                if len(gngSortedList) == 0:
                    gngSortedList.append(feature)
                else:
                    for i in range(len(gngSortedList)):
                        if feature["Priority"] < gngSortedList[i]["Priority"]:
                            if debugging:
                                print("Inserting because " + str(feature["Priority"]) + " is less than " + str(gngSortedList[i]["Priority"]))
                            gngSortedList.insert(i, feature)
                            break
                        elif i == len(gngSortedList) - 1:
                            if debugging:
                                print("Inserting because I've reached the end of the list")
                            gngSortedList.append(feature)
            gngData["regions"]["Features"][key] = {"Output String":"","Features":list(gngSortedList)}

            for feature in gngSortedList:
                gngData["regions"]["Features"][key]["Output String"] += feature["Formatted Region"] + "\n"
    else:
        print("Something broke while sorting, check target " + target + " is correct, because the code is stukkie wukkie, mss could you better sort by hand owo.")

# This is the function that reads the entire folder and finds all the readable files in there, then reads them one by one

def readFolder(folderPath,debugging=False):
    subdirs = [f.path for f in scandir(folderPath) if f.is_dir()]
    subdirs.append(folderPath)
    if debugging:
        print(subdirs)
    for subdir in subdirs:
        for fileName in listdir(subdir):
            if path.isfile(path.join(subdir,fileName)) and search(".*\.geojson$",fileName):
                filePath = path.join(subdir, fileName)
                if debugging:
                    print("Reading file " + fileName + " in folder " + subdir)
                readGeoJSONFile(filePath,debugging)

readFolder(geoJSONFolderPath,globalDebugging)

sortRegions()

def hexColorCode(decimalColor):
    blue = int(decimalColor / 65536)
    green = int((decimalColor - (blue * 65536)) / 256)
    red = decimalColor - (blue * 65536) - (green * 256)
    colorHex = '#' + hex(red)[2:].ljust(2,"0") + hex(green)[2:].ljust(2,"0") + hex(blue)[2:].ljust(2,"0")
    return colorHex

# Once all the major operations are completed we can write all the collected errors into a log file

with open (outputFolder + "log_" + dateStringLong + ".txt","w") as logFile:
    colorString = "\nFollowing color codes were used in the generation of this sectorfile:\n"
    for color in colorsUsed:
        if color == "":
            continue
        try:
            if int(color):
                color = hexColorCode(int(color))
        except:
            pass
        colorString += "    " + str(color) + "\n"
    log += colorString
    logFile.write(log)

# From here on out we just need to write the files, first the sct file which also needs the color definitions from the definitions file

def writeSctFile():

    global dateString
    global dateStringLong

    sctFilePath = outputFolder + "QGIS_Generated_Sectorfile-" + dateStringLong + ".sct"

    geo = esData["geo"]["Output String"]
    regions = esData["regions"]["Output String"]
    colors = ""

    for color in definitions["Colors"]["Sector File Colors"]:
        colors += ("#define COLOR_" + color["Name"]).ljust(30) + esColorCode(color["Hex"]).rjust(9) + "\n"

    with open (sctHeaderPath) as sctHeader:
        contents = sctHeader.read().replace("$date     ", dateString).replace("$date", dateString).replace("$regions",regions).replace("$geo",geo).replace("$colors",colors)
    
    with open (sctFilePath,'w') as generatedSectorfile:
        generatedSectorfile.write(contents)

# And finally we write the ese file as a last step

def writeEseFile():

    global dateString
    global dateStringLong

    eseFilePath = outputFolder + "QGIS_Generated_Sectorfile-" + dateStringLong + ".ese"

    freetext = esData["freetext"]["Output String"]

    with open (eseHeaderPath) as eseHeader:
        contents = eseHeader.read().replace("$date     ", dateString).replace("$date", dateString).replace("$freetext",freetext)

    with open (eseFilePath,'w') as generatedSectorfile:
        generatedSectorfile.write(contents)

def writeGngFile(filetype,string):
    global dateStringLong
    gngRegionsFilePath = outputFolder + "GNG_" + filetype + "_Export-" + dateStringLong + ".txt"
    with open (gngRegionsFilePath, 'w') as gngRegionsFile:
        gngRegionsFile.write(string)

def formatForGng():
    global gngData
    sortRegions("gng",globalDebugging)
    for layer in gngData["regions"]["Features"]:
        airport = layer[:4]
        layername = layer[5:]
        header = "AERONAV:" + airport + ":" + layername + ":ES,VRC:QGIS 2205\n"
        gngData["regions"]["Output String"] += header + gngData["regions"]["Features"][layer]["Output String"] + "\n"
    for layerName in gngData["geo"]["Features"]:
        layer = gngData["geo"]["Features"][layerName]
        airport = layer["Airport"]
        category = layer["Category"]
        name = layer["Name"]
        header = ":".join(["AERONAV",airport,category,name,"","GEO","","QGIS 2205\n"])
        gngData["geo"]["Output String"] += header + layer["Code"] + "\n"
    for layerName in gngData["freetext"]["Features"]:
        layer = gngData["freetext"]["Features"][layerName]
        airport = layer["Airport"]
        labelgroup = layer["Labelgroup"]
        header = ":".join(["AERONAV",airport,labelgroup,"ES-ESE","QGIS 2205\n"])
        gngData["freetext"]["Output String"] += header + layer["Code"] + "\n\n"
    for fileType in gngData:
        writeGngFile(fileType,gngData[fileType]["Output String"])

writeSctFile()
writeEseFile()
formatForGng()

for color in colorsUsed:
    found = False
    for entry in definitions["Colors"]["Sector File Colors"]:
        if entry["Name"] == color:
            found = True
    if not found:
        print("Color " + color + " either misspelled or not defined!")