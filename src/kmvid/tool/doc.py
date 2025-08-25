import kmvid.data.clip as clip
import kmvid.data.draw as draw
import kmvid.data.effect as effect
import kmvid.data.project as project
import kmvid.data.variable as variable
import kmvid.script as script

import enum

class DocData:
    def __init__(self):
        self.enums = []
        self.variable_holds = []
        self.functions = []

    def read_module(self, module):
        for key in dir(module):
            obj = getattr(module, key)
            if isinstance(obj, enum.EnumType):
                self.enums.append(DocEnum(obj))
            elif (type(obj) is type and
                  issubclass(obj, variable.VariableHold) and
                  getattr(obj, 'get_variable_configs', False)):
                self.variable_holds.append(DocVariableHolder(obj))
            elif callable(obj):
                self.functions.append(DocFunction(key, obj))

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
        self.type = cfg.type
        self.default = cfg.default
        self.doc = cfg.doc

        if type(cfg.type) is type or isinstance(cfg.type, enum.EnumType):
            self.type = cfg.type.__name__

    def get_type(self):
        if self.type is None:
            return ""
        return str(self.type)

    def get_default(self):
        if self.default is None:
            return ""
        if isinstance(self.default, str):
            return '"%s"' % str(self.default)
        if issubclass(type(self.default), enum.Enum):
            return '"%s"' % self.default.name
        return str(self.default)

class DocFunction:
    def __init__(self, sym, fn):
        self._sym = sym
        self._fn = fn

        self.name = sym

#--------------------------------------------------

class Tag:
    def __init__(self, name, *args):
        self.name = name
        self.attributes = {}
        self.content = []

        if len(args) > 0 and type(args[0]) is dict:
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

#--------------------------------------------------

script_css = """
:root {
    --main-border: 5px;

    --col-bg: #333;
    --col-bg-alt: #111;
    --col-text: #eee;
}

body {
    background: var(--col-bg-alt);
    color: var(--col-text);
    font-family: arial;
    font-size: 18px;
}

h1, h2, h3 {
    margin: 0;
    margin-top: 0.2em;
    margin-bottom: 0.5em;
}

h1 {
    font-size: 160%;
    background: #555;
}

h2 {
    font-size: 120%;
    background: #444;
}

h3 {
    font-size: 110%;
    background: rgb(38, 38, 38);
}

a {
    color: var(--col-text);
    text-decoration: none;
}

.indent {
    margin-left: 1.2em;
}

.doc {
    background: rgb(40, 40, 62);
    width: 80%;
}

.code {
    background: #336;
    color: white;
    border: 1px solid white;
    margin-left: 3em;
    padding: 0.2em;
    font-size: 80%;
    width: fit-content;
}

#main {
    background: var(--col-bg);
    margin: var(--main-border);

    display: grid;
    grid-template-columns: max-content 5px 1fr;
}

.divider {
    background: var(--col-bg-alt);
}

#menu, #content {
    height: calc(100vh - (var(--main-border) * 6));
    padding: var(--main-border);
    overflow-y: auto;
}

#menu {
    padding-right: 1em;
}

.menu-item {
    display: block;
}

.menu-sub-item {
    display: block;
    font-size: 90%;
}

.menu-space {
    margin-top: 1em;
}

.variable-table {
    border: 1px solid var(--col-text);
}

.variable-table th {
    background: #336;
    padding: 0.2em;
    padding-left: 0.5em;
    padding-right: 2em;
    text-align: left;
    text-transform: lowercase;
}

.variable-table td {
    background: #112;
    padding-left: 1em;
    padding-right: 1em;
    padding-top: 0.2em;
    padding-bottom: 0.2em;
}

.enum-table td {
    background: var(--col-bg-alt);
}

.variable {
    color: #ff3;
}

.variable-supplement {
    color: #66e;
    font-size: 90%;
}
"""

class Entry:
    def __init__(self, name):
        self.name = name
        self.id = name.lower()
        self.content = Tag('No content')

def get_overview_entries(data):
    entries = []

    entry = Entry("Setup")
    entry.content = Tag('div')
    entries.append(entry)

    def h(name):
        entry.content.add(Tag('h3', name))
        entry.content.add(Tag('div', {'class': 'indent'}))

    def p(*items):
        entry.content.content[-1].add(Tag('p', *items))

    def code(text):
        entry.content.content[-1].add(Tag('pre', {'class': 'code'}, text))

    def add(*xs):
        for x in xs:
            entry.content.content[-1].add(x)

    entry.content.add(Tag('div'))
    p('Get ffmpeg and ffprobe into your path from ',
      Tag('a', {'href': 'https://ffmpeg.org/download.html'}, 'https://ffmpeg.org/download.html'))
    code("""from kmvid.script import *

p = Project(width=800, height=400, fps=60, filename="video.mp4", duration=5)

circle = Clip("black", width=300, height=300)
circle.add(Draw()
           .config(color="white", pen_width=3, fill=(50, 50, 50))
           .ellipse(radius=150))
circle.add(Pos(horizontal={0: 0, 5: 1}, vertical=0.5, weight=0))
p.add(circle)

line = Clip("cyan", width=250, height=25)
line.add(Rotate(angle={0: 0, 5: 360*3}))
line.add(Pos(horizontal=0.5, vertical=0.5))
circle.add(line)

p.write()""")

    entry = Entry("Concepts")
    entry.content = Tag('div')
    entries.append(entry)

    h('Building blocks')
    p('The core components are projects, clips and effects. ',
      'Projects provides functionality to render videos and images. ',
      'Clips can contain other clips and effects, projects can only contain clips.')
    code("""from kmvid.script import *

p = Project(duration=3)
c = Clip("red", width=200, height=100)
c.add(Pos(x=50, y=90))
c.add(Rotate(45))
p.add(c)
p.write() # creates output.mp4

# Can also be chained giving the same result
Project(duration=3).add(
    Clip("red", width=200, height=100).add(
        Pos(x=50, y=90),
        Rotate(45),
    )
).write()""")

    p('Clips and effects are applied in the same order that they are added, each applying any transformation to the output of the previous item. ',
      'This means that, for instance, Crop+Rotate is not the same as Rotate+Crop. ')

    h('Variables')
    p('The variables on clips and effects can be set either through keywords in the constructor or through regular attribute access. ')
    code("""pos = Pos(x=100)
pos.x = 200""")

    p('Variable values are coerced when possible. ')
    add(Tag('table',
            {'class': 'variable-table'},
            Tag('tr',
                Tag('th', 'Variable type'),
                Tag('th', 'Value'),
                Tag('th', 'Examples')),
            Tag('tr',
                Tag('td', 'int,&nbsp;float,&nbsp;str'),
                Tag('td', 'Coerced as if being passed to the corresponding class.'),
                Tag('td', '25<br>12.75<br>"10.5"')),
            Tag('tr',
                Tag('td', 'enum'),
                Tag('td', 'Strings are enum names (ignores case). int for the corresponding ordinal.'),
                Tag('td', 'TimeValueType.LINEAR<br>"linear"<br>1')),
            Tag('tr',
                Tag('td', 'time'),
                Tag('td', 'Defaults to seconds as a float value. String values allows for suffix to indicate the time unit. Time units are [h]our [m]inute [s]econd [ms]illisecond. Strings also allow for multiple values in a row which will be added up.'),
                Tag('td', '5.75<br>"1h40m12s"<br>"40m 1h -50000ms"'))))
    code("""fade = Fade(value          = "0.75",
            fade_in        = 2.5,
            fade_out       = "450ms",
            alpha_strategy = "overwrite")""")

    p('Variables can be set to change over time by using a dict that maps times to values. '
      'By default the transition between values will be linear. '
      'To change the way values moves between points use Val to explicitly set the TimeValueType. ')
    p('NONE means no transition so values are held until the next value is encountered causing a sharp cut between values. '
      'LINEAR makes a simple linear move from one value to the next. '
      'CURVE, BOUNDED_CURVE, and LOOSE_CURVE makes increasingly loose curves between the given points, these require at least three points to function properly. ')
    code("""# Moves from left to right over 3 seconds
pos = Pos(horizontal = {0: 0, 3: 1})

# Stay still to the left, at 3 seconds jumps to the right
pos = Pos(horizontal = {0: Val(0, "none"), 3: 1})""")

    return entries

def get_effect_entries(data):
    entries = []

    for varhold in [x for x in data.variable_holds if x.name != 'Project']:
        entry = Entry(varhold.name)
        entry.content = get_variable_hold_tag(varhold)
        entries.append(entry)

    return entries

def get_draw_entries(data):
    entries = []

    entry = Entry("About")
    entries.append(entry)
    entry.content = Tag('div',
                        Tag('p',
                            'Draw is an effect that provides functionality to render shapes and text. ',
                            'Instructions are added to the Draw effect and are executed in sequence. '),
                        Tag('pre', {'class': 'code'},
                            """draw = (Draw()
        .config(color="gray", fill="white", pen_width=5)
        .rectangle(x=50, y=100, width=400, height=100)
        .config(font_name="Arial", fill="green", pen_width=0)
        .text(text="Sample text", x=250, y=150, width=300, anchor="mm"))

proj = Project(width=500, height=300).add(draw)

proj.get_frame(0).show()"""))

    for varhold in data.variable_holds:
        entry = Entry(varhold.name.lower())
        entry.content = get_variable_hold_tag(varhold)
        entries.append(entry)

    return entries

def get_variable_hold_tag(varhold):
    root = Tag('div')

    table = Tag('table', {'class': 'variable-table'})
    table.add(Tag('tr',
                  Tag('th', 'Name'),
                  Tag('th', 'Type'),
                  Tag('th', 'Default')))
    for var in varhold.variables:
        table.add(Tag('tr'),
                  Tag('td', var.name),
                  Tag('td', var.get_type()),
                  Tag('td', var.get_default()))
    root.add(table)

    root.add(Tag('div', format_doc_string(varhold.doc)))

    details = Tag('div', {'class': 'indent'})
    for var in varhold.variables:
        details.add(Tag('span', {'class': 'variable'}, var.name, " "))
        details.add(Tag('span',
                        {'class': 'variable-supplement'},
                        ("%s = %s" % (var.get_type(), var.get_default())
                         if var.get_default()
                         else var.get_type())))
        details.add(Tag('div', {'class': 'indent'}, format_doc_string(var.doc)))
    root.add(details)

    return root

def get_script_tag():
    data = DocData()
    data.read_module(script)

    draw_data = DocData()
    draw_data.read_module(draw)

    for varhold in data.variable_holds:
        if varhold.name == 'Draw':
            data.variable_holds.remove(varhold)
            break

    for varhold in draw_data.variable_holds:
        if varhold.name == 'Draw':
            draw_data.variable_holds.remove(varhold)
            break

    overview = get_overview_entries(data)
    effects = get_effect_entries(data)
    draw_entries = get_draw_entries(draw_data)

    menu = Tag('div', {'id': 'menu'})
    for name, entries in [('Overview', overview),
                          ('Effect', effects),
                          ('Draw', draw_entries)]:
        menu.add(Tag('div',
                     {'class': 'menu-item'},
                     Tag('a', {'href': f"#{name.lower()}"}, name)))
        submenu = Tag('div', {'class': 'indent'})
        for entry in entries:
            submenu.add(Tag('div',
                            {'class': 'menu-sub-item'},
                            Tag('a', {'href': f"#{entry.id}"}, entry.name)))
        menu.add(submenu)
        menu.add(Tag('div', {'class': 'menu-space'}))

    content = Tag('div', {'id': 'content'})
    for name, entries in [('Overview', overview),
                          ('Effect', effects),
                          ('Draw', draw_entries)]:
        content.add(Tag('h1', {'id': name.lower()}, name))
        subcontent = Tag('div', {'class': 'indent'})
        for entry in entries:
            subcontent.add(Tag('h2', {'id': entry.id}, entry.name))
            subcontent.add(Tag('div', {'class': 'indent'}, entry.content))
            subcontent.add(Tag('div', {'style': 'height: 2em;'}))
        content.add(subcontent)

    html = Tag('html',
               Tag('head',
                   Tag('title', 'kmvid script'),
                   Tag('style', script_css)),
               Tag('body',
                   Tag('div', {'id': 'main'},
                       menu,
                       Tag('div', {'class': 'divider'}),
                       content)))

    return html

#--------------------------------------------------

def write_html(path, tag):
    with open(path, "w") as f:
        tag.write(f)

def run():
    write_html("doc/script.html", get_script_tag())

if __name__ == '__main__':
    run()
