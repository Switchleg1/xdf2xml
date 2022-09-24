import csv
import re
import uuid
import xml.etree.ElementTree as ET
from xmlwrite import XMLWrite
from os import path
from sys import argv

#globals

DEF_BASE_OFFSET = 0
DEF_BIN_OFFSET = 0
DEF_CATEGORY_OFFSET = 0
DEF_TITLE = ""
DEF_DESCRIPTION = ""

table_def = {
    "title": "",
    "description": "",
    "category": [],
    "x": {},
    "y": {},
    "z": {},
}

data_sizes = {
    "8": 1,
    "16": 2,
    "32": 4,
}

#functions

def resetAxis(a):
    table_def[a]["name"] = a
    table_def[a]["units"] = ""
    table_def[a]["min"] = ""
    table_def[a]["max"] = ""
    table_def[a]["address"] = hex(0)
    table_def[a]["length"] = 0
    table_def[a]["dataSize"] = 1
    table_def[a]["math"] = ""
    table_def[a]["math2"] = ""
    table_def[a]["order"] = "cr"


#begin

categories = {}
resetAxis("x")
resetAxis("y")
resetAxis("z")
xdfRoot = ET.parse(argv[1]).getroot()
for element in xdfRoot:
    if element.tag == "XDFHEADER":
        print("***HEADER***")
        for hdr in element:
            if hdr.tag == "deftitle":
                DEF_TITLE = str(hdr.text)
                xmlOut = XMLWrite(DEF_BASE_OFFSET, DEF_BIN_OFFSET, DEF_CATEGORY_OFFSET, DEF_TITLE, argv[3])
                print("Title: " + DEF_TITLE)
            elif hdr.tag == "description":
                DEF_DESCRIPTION = str(hdr.text)
                print("Description: " + DEF_DESCRIPTION)
            elif hdr.tag == "BASEOFFSET":
                try:
                    DEF_BASE_OFFSET = int(hdr.get("offset").lstrip("0x"), base=16)
                except:
                    DEF_BASE_OFFSET = 0
                print("Base Offset: " + hex(DEF_BASE_OFFSET))
            elif hdr.tag == "CATEGORY":
                try:
                    index = int(hdr.get("index").lstrip("0x"), base=16)
                except:
                    index = 0
                categories[index] = hdr.get("name")
                print("Category [" + hex(index) + "]: " + categories[index])
    elif element.tag == "XDFTABLE":
        table_def["category"] = []
        for hdr in element:
            if hdr.tag == "title":
                table_def["title"] = hdr.text
                print("Table: " + str(table_def["title"]))
            elif hdr.tag == "description":
                if table_def["title"] is None:
                    table_def["title"] = str(hdr.text)
                table_def["description"] = str(hdr.text)
                print("  Description: " + table_def["description"])
            elif hdr.tag == "CATEGORYMEM":
                catName = categories[int(hdr.get("category"))-1]
                table_def["category"].append(catName)
                print("  Category: " + catName)
            elif hdr.tag == "XDFAXIS":
                axisID = hdr.get("id")
                resetAxis(axisID)
                print("  Axis: " + axisID)
                for axis in hdr:
                    if axis.tag == "EMBEDDEDDATA":
                        try:
                            address = int(axis.get("mmedaddress"), base=16)
                        except:
                            address = axis.get("mmedaddress")
                        table_def[axisID]["address"] = hex(address + DEF_BASE_OFFSET)
                        table_def[axisID]["dataSize"] = data_sizes[axis.get("mmedelementsizebits")]
                        table_def[axisID]["order"] = "cr" if axis.get("mmedtypeflags") == "0x02" else "rc"
                        print("    Address: " + str(table_def[axisID]["address"]))
                        print("    Data Type: " + str(table_def[axisID]["dataSize"]))
                        print("    Data Order: " + str(table_def[axisID]["order"]))
                    elif axis.tag == "indexcount":
                        try:
                            table_def[axisID]["length"] = int(float(axis.text))
                        except:
                            table_def[axisID]["length"] = 0
                        print("    Length: " + str(table_def[axisID]["length"]))
                    elif axis.tag == "MATH":
                        table_def[axisID]["math"] = xmlOut.build_equation(axis.get("equation"), False)
                        table_def[axisID]["math2"] = xmlOut.build_equation(axis.get("equation"), True)
                        print("    Equation: " + table_def[axisID]["math"])
                    elif axis.tag == "min":
                        try:
                            table_def[axisID]["min"] = float(axis.text)
                        except:
                            table_def[axisID]["min"] = 0.0
                        print("    Min: " + str(table_def[axisID]["min"]))
                    elif axis.tag == "max":
                        try:
                            table_def[axisID]["max"] = float(axis.text)
                        except:
                            table_def[axisID]["max"] = 0.0
                        print("    Max: " + str(table_def[axisID]["max"]))
        table = xmlOut.table_with_root(table_def)           
xmlOut.write(f"{argv[2]}")
