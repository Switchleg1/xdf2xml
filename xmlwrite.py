import re
import uuid
import decimal
import xml.etree.ElementTree as ET

data_sizes = {
    1: 'uint8',
    2: 'uint16',
    4: 'float',
}

class XMLWrite:
    def __init__(self, baseOffset, binOffset, categoryOffset, title, ID):
        self.categories = []
        self.tables = {}
        self.baseOffset = baseOffset
        self.categoryOffset = categoryOffset
        self.binOffset = binOffset

        # create a new context for this task
        self.ctx = decimal.Context()
        self.ctx.prec = 20

        self.root = ET.Element("ecus")
        self.xmlheader = ET.SubElement(self.root, "ecu_struct")
        self.xmlheader.set('id',str(ID).rstrip(".a2l").lstrip(".\\"))
        self.xmlheader.set('type',str(title).rstrip(".a2l").lstrip(".\\"))
        self.xmlheader.set('include',"")
        self.xmlheader.set('desc_size',"#400000")
        self.xmlheader.set('reverse_bytes',"False")
        self.xmlheader.set('ecu_type',"vag")
        self.xmlheader.set('flash_template',"")
        self.xmlheader.set('checksum',"")

    def write(self, filename):
        tree = ET.ElementTree(self.root)
        ET.indent(tree, space="  ", level=0)
        tree.write(filename)

    def table_with_root(self, table_def):
        axis_count = 1
        has_x = False
        has_y = False

        #check for x axis
        if "x" in table_def and table_def['x']['address'].lstrip("0x") != "":
            axis_count += 1
            has_x = True

        #check for y axis 
        if "y" in table_def and table_def['y']['address'].lstrip("0x") != "":
            axis_count += 1
            has_y = True

        #ensure title doesn't match existing table, if so add spaces
        while table_def["title"] in self.tables:
            table_def["title"] += " "
        self.tables[table_def["title"]] = True
        
        table = ET.SubElement(self.xmlheader, "map")
        table.set('name',table_def["title"])
        table.set("type",str(axis_count))
        table.set("help",table_def["description"])
        table.set("class","|".join(table_def["category"]))

        data = ET.SubElement(table,"data")
        data.set("offset","#"+table_def['z']['address'].lstrip("0x"))
        data.set("storagetype",str(data_sizes[table_def['z']["dataSize"]]))
        data.set("func_2val",table_def['z']['math'])
        data.set("func_val2",table_def['z']['math2'])
        data.set("format","%0.2f")
        data.set("metric",table_def['z']['units'])
        data.set("min",str(table_def['z']['min']))
        data.set("max",str(table_def['z']['max']))
        data.set("order", str(table_def['z']['order']))

        if has_x == True:
            rows = ET.SubElement(table,"cols")
            rows.set("count",str(table_def['x']['length']))
            rows.set("offset","#"+table_def['x']['address'].lstrip("0x"))
            rows.set("storagetype",str(data_sizes[table_def['x']["dataSize"]]))
            rows.set("func_2val",table_def['x']['math'])
            rows.set("func_val2",table_def['x']['math2'])
            rows.set("format","%0.2f")
            rows.set("metric",table_def['x']['units'])

        if has_y == True:
            cols = ET.SubElement(table,"rows")
            cols.set("count",str(table_def['y']['length']))
            cols.set("offset","#"+table_def['y']['address'].lstrip("0x"))
            cols.set("storagetype",str(data_sizes[table_def['y']["dataSize"]]))
            cols.set("func_2val",table_def['y']['math'])
            cols.set("func_val2",table_def['y']['math2'])
            cols.set("format","%0.2f")
            cols.set("metric",table_def['y']['units'])
  
        return table

    def adjust_address(self, address):
        return address - self.baseOffset + self.binOffset

# A2L to "normal" conversion methods

    def fix_degree(self, bad_string):
        return re.sub("\uFFFD", "\u00B0", bad_string)  # Replace Unicode "unknown" with degree sign

    def coefficients_to_equation(self, coefficients, inverse):
        a, b, c, d, e, f = (
            self.float_to_str(coefficients["a"]),
            self.float_to_str(coefficients["b"]),
            self.float_to_str(coefficients["c"]),
            self.float_to_str(coefficients["d"]),
            self.float_to_str(coefficients["e"]),
            self.float_to_str(coefficients["f"]),
        )

        s1 = '+'
        s2 = '-'
        if c[0] == '-':
            c = c[1:]
            s1 = '-'
            s2 = '+'
        
        operation = ""
        if inverse is True:
            operation = f"({b} * ([x] / {f})) {s1} {c}"
        else:  
            operation = f"(({f} * [x]) {s2} {c}) / {b}"
        
        if a == "0.0" and d == "0.0" and e=="0.0" and f!="0.0":  # Polynomial is of order 1, ie linear original: f"(({f} * [x]) - {c} ) / ({b} - ({e} * [x]))"
            return operation
        else:
            return "Cannot handle polynomial ratfunc because we do not know how to invert!"

    def build_equation(self, s, inv):
        p = re.compile("\d+\.\d+")
        l = p.findall(s)
        if len(l) < 3:
            return "[x]"
        ce = {
            "a": 0.0,
            "b": float(l[2]),
            "c": float(l[1]),
            "d": 0.0,
            "e": 0.0,
            "f": float(l[0])
        }
        return self.coefficients_to_equation(ce, inv)

    def float_to_str(self, f):
        """
        Convert the given float to a string,
        without resorting to scientific notation
        """
        d1 = self.ctx.create_decimal(repr(f))
        return format(d1, 'f')

