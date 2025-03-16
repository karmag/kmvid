import kmvid.data.clip as clip
import kmvid.data.draw as draw
import kmvid.data.effect as effect
import kmvid.data.project as project
import kmvid.data.variable as variable

import enum

class DocData:
    def __init__(self):
        self.enums = []
        self.variable_holds = []

    def get_items(self):
        items = []

        items.extend(self.enums)
        items.extend(self.variable_holds)

        mod_order = ['kmvid.data.project',
                     'kmvid.data.clip',
                     'kmvid.data.effect']

        def key_fn(x):
            mod_key = x.module
            for i, mo in enumerate(mod_order):
                if mod_key == mo:
                    mod_key = "%d %s" % (i, x.module)
                    break

            type_key = 0
            if isinstance(x, DocEnum):
                type_key = 1

            return "%s %d %s" % (mod_key, type_key, x.name)

        return sorted(items, key=key_fn)

class DocEnum:
    def __init__(self, cls):
        self._cls = cls

        self.name = cls.__name__
        self.module = cls.__module__
        self.doc = cls.__doc__
        self.values = []

        for val in cls:
            self.values.append(DocEnumValue(val))

class DocEnumValue:
    def __init__(self, value):
        self._value = value
        self.name = value.name
        self.value = value.value

class DocVariableHolder:
    def __init__(self, cls):
        self._cls = cls

        self.name = cls.__name__
        self.module = cls.__module__
        self.doc = cls.__doc__
        self.variables = []

        for cfg in cls.get_variable_configs():
            self.variables.append(DocVariableConfig(cfg))

        if not self.doc:
            init = getattr(cls, '__init__', None)
            if init:
                self.doc = init.__doc__

class DocVariableConfig:
    def __init__(self, cfg):
        self._cfg = cfg

        self.name = cfg.name
        self.type = cfg.type.__name__ if cfg.type else None
        self.default = cfg.default
        self.doc = cfg.doc

    def get_type(self):
        if self.type is None:
            return ""
        return str(self.type)

    def get_default(self):
        if self.default is None:
            return ""
        if isinstance(self.default, str):
            return '"%s"' % str(self.default)
        return str(self.default)

__MODULES__ = [clip, draw, effect, project]

def get_enums():
    result = []
    for mod in __MODULES__:
        for key in dir(mod):
            obj = getattr(mod, key)
            if isinstance(obj, enum.EnumType):
                result.append(DocEnum(obj))
    return result

def get_variableholds():
    result = []
    for mod in __MODULES__:
        for key in dir(mod):
            obj = getattr(mod, key)
            if (type(obj) == type and
                issubclass(obj, variable.VariableHold) and
                getattr(obj, 'get_variable_configs', False)):
                result.append(DocVariableHolder(obj))
    return result

def get_doc_data():
    doc = DocData()
    doc.enums = get_enums()
    doc.variable_holds = get_variableholds()
    return doc

#--------------------------------------------------

class Tag:
    def __init__(self, name, *args):
        self.name = name
        self.attributes = {}
        self.content = []

        if len(args) > 0 and type(args[0]) == dict:
            self.attributes = args[0]
            args = args[1:]

        self.add(*args)

    def add(self, *args):
        for x in args:
            if isinstance(x, list):
                self.add(*x)
            else:
                self.content.append(x)
        return self

    def write(self, f):
        f.write("<%s" % self.name)
        if len(self.attributes) > 0:
            for k in self.attributes:
                f.write(' %s = "%s"' % (k, str(self.attributes[k])))
        f.write(">")

        for element in self.content:
            if isinstance(element, Tag):
                element.write(f)
            else:
                f.write(str(element))

        f.write("</%s>" % self.name)

def format_doc_string(docstr):
    if not docstr:
        return ""

    docstr = docstr.lstrip()
    lines = docstr.split("\n")

    indent = 0
    for line in lines[1:] if len(lines) > 0 else []:
        indent = min(indent, len(line) - len(line.lstrip()))

    for n, line in enumerate(lines[1:]):
        if len(line) >= indent:
            lines[n + 1] = line[indent:].rstrip()

    div = Tag('div', {'class': 'doc'})

    while len(lines) > 0:
        if not lines[0]:
            lines = lines[1:]
            continue

        p = Tag('p')
        while len(lines) > 0 and lines[0]:
            p.add(lines[0])
            lines = lines[1:]

        div.add(p)

    return div

def generate_index(data):
    index = Tag('div', {'id': 'index'})

    prev_module = "qweqwe"

    for item in data.get_items():
        if prev_module != item.module:
            index.add(Tag('div', {'class': 'index module'}, item.module))
            prev_module = item.module

        htmlclass = 'index item '
        if isinstance(item, DocEnum):
            htmlclass += 'enum'
        else:
            htmlclass += 'varhold'

        index.add(Tag('div', {'class': htmlclass}, item.name))

    return index

def generate_details(data):
    details = Tag('div', {'id': 'details'})

    for item in data.get_items():
        details.add(Tag("hr"))

        tag = Tag('vid')

        if isinstance(item, DocEnum):
            tag.add(Tag('span', {'class': 'details enum header'}, item.name),
                    " ",
                    Tag('span', {'class': 'details module header'}, item.module))

            table = Tag('table')
            for val in item.values:
                table.add(Tag('tr',
                              Tag('td', val.name),
                              Tag('td', val.value)))
            tag.add(table)

            tag.add(format_doc_string(item.doc))

        elif isinstance(item, DocVariableHolder):
            tag.add(Tag('span', {'class': 'details varhold header'}, item.name),
                    " ",
                    Tag('span', {'class': 'details module header'}, item.module))

            table = Tag('table',
                        Tag('tr',
                            Tag('th', 'name'),
                            Tag('th', 'type'),
                            Tag('th', 'default')))
            for cfg in item.variables:
                table.add(Tag('tr',
                              Tag('td', cfg.name),
                              Tag('td', cfg.get_type()),
                              Tag('td', cfg.get_default())))
            tag.add(table)

            tag.add(format_doc_string(item.doc))

            for cfg in item.variables:
                div = Tag('div', {'class': 'indent'})

                type_line = " "
                if cfg.get_type():
                    type_line += cfg.get_type()
                if cfg.get_default():
                    type_line += ' = %s' % cfg.get_default()

                div.add(Tag('div',
                            Tag('span', {'class': 'details var header'}, cfg.name),
                            Tag('span', {'class': 'minor'}, type_line)))

                div.add(Tag('div', {'class': 'indent'}, format_doc_string(cfg.doc)))

                tag.add(div)

        else:
            raise Exception("Unknown item type %s" % type(item))

        details.add(tag)

    return details

def generate_tags():
    data = get_doc_data()

    root = Tag('html',
               Tag('head',
                   Tag('link', {'rel': 'stylesheet',
                                'href': 'style.css'}),
                   Tag('title', 'kmvid documentation')),
               Tag('body',
                   Tag('div', {'id': 'main'},
                       generate_index(data),
                       generate_details(data))))

    return root

def write_html(path):
    with open(path, "w") as f:
        generate_tags().write(f)

def printit():
    old_module = "qweqwe"
    for cls in get_variableholds():
        if old_module != cls.module:
            print(cls.module)
            print()
            old_module = cls.module

        print("    %s" % cls.name)

        for var in cls.variables:
            print("        %-12s %s %s" % (
                var.name,
                var.type if var.type is not None else "_",
                ("= %s" % str(var.default)) if var.default is not None else ""))

        print()

    for e in get_enums():
        print("%s.%s" % (e.module, e.name))
        for val in e.values:
            print("    %s = %d" % (val.name, val.value))
        print()

def run():
    #printit()
    write_html("doc/doc.html")

if __name__ == '__main__':
    run()
