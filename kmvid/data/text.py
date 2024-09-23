import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

import os
import os.path

font_cache = None
__default_font__ = None

class FontCache:
    def __init__(self):
        self.unresolved_paths = set()
        self.font_data = {}

    def get_font(self, name, size=16, variant="Regular"):
        data = self.font_data.get(name, None)
        if data is None:
            self.load(name)
            data = self.font_data.get(name, None)
            if data is None:
                raise Exception("No font with name: %s" % name)
        return data.get_font(size, variant)

    def register_path(self, path):
        """Add a path used to search for font file."""
        path = os.path.abspath(path)

        if os.path.isdir(path):
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                self.unresolved_paths.add(filepath)
        else:
            self.unresolved_paths.add(path)

    def load(self, name):
        """Loads all font information that can be found for the given name."""
        remove = set()

        for path in self.unresolved_paths:
            font = self._load_font(path)
            if not font:
                remove.add(path)
            else:
                if font.getname()[0] == name:
                    self._add_font(font)
                    remove.add(path)

        self.unresolved_paths.difference_update(remove)

    def preload(self, path=None):
        """Loads all fonts that can be found in registered paths."""
        if path is None:
            while len(self.unresolved_paths) > 0:
                path = self.unresolved_paths.pop()
                self.preload(path)
        else:
            font = self._load_font(path)
            if font:
                self._add_font(font)

    def _load_font(self, path, size=16):
        try:
            return PIL.ImageFont.truetype(path, size=size)
        except OSError:
            pass

    def _add_font(self, font):
        name = font.getname()[0]
        if name not in self.font_data:
            self.font_data[name] = FontData(font)
        else:
            self.font_data[name].add(font)

    def pprint(self):
        """Prints font information."""
        self.preload()

        max_len = 0
        for fname in self.font_data.keys():
            for vname in self.font_data[fname].get_variants():
                max_len = max(max_len, len(vname))
        fmt = "    %%-%ds %%s" % max_len

        for fname in sorted(self.font_data.keys()):
            print(fname)

            data = self.font_data[fname]
            variant_names = sorted(data.get_variants())
            if "Regular" in variant_names:
                variant_names.remove("Regular")
                variant_names = ["Regular"] + variant_names

            for vname in variant_names:
                font = data.get_font(variant=vname)
                print(fmt % (vname, font.path))

            print()

class FontData:
    def __init__(self, font):
        self.name = font.getname()[0]
        self.font_by_variant = {}
        self.cache = {}

        self.add(font)

    def add(self, font):
        name, variant = font.getname()
        assert name == self.name
        self.font_by_variant[variant] = font

    def get_font(self, size=16, variant="Regular"):
        key = (size, variant)
        if key not in self.cache:
            font = self.font_by_variant.get(variant, None)
            if font is None:
                raise Exception("No variant '%s' for font '%s'" % (variant, self.name))
            self.cache[key] = font.font_variant(size = size)
        return self.cache[key]

    def get_variants(self):
        return self.font_by_variant.keys()

font_cache = FontCache()
font_cache.register_path("c:\\windows\\fonts")

def get_font(name, size=16, variant="Regular"):
    """Returns a font according to the given specifications. The name
    "default" calls get_default_font.

    """
    if name == "default":
        return get_default_font()
    return font_cache.get_font(name,
                               size or 16,
                               variant or "Regular")

def get_default_font():
    global __default_font__
    if __default_font__ is None:
        __default_font__ = PIL.ImageFont.load_default()
    return __default_font__

def _split_on_space(text):
    index = 0
    while True:
        index = text.find(" ", index+1)

        if index >= len(text) or index == -1:
            return

        yield (text[:index], text[index+1:])

def wrap_text(font, text, width, split_fn=_split_on_space):
    """Attempts to wrap the text to fit within width. Wrapping is adviced
    by the split_fn. If results given from split_fn are not able to
    fit the smallest result is taken.

    font -- Font to use.

    text -- Text to wrap. Linebreaks in the text are respected.

    width -- Width to wrap text at.

    split_fn -- A function returning a generator. The function is
    passed a line from text and returns pair of strings suggesting
    ways to split the line. The yielded values must be ordered with
    the smallest suggestion first.

        gen = split_fn("abc def ghi")
        next(gen) ;; ("abc", "def ghi")
        next(gen) ;; ("abc def", "ghi")

    """
    result = []
    lines = text.split("\n")

    while len(lines) > 0:
        single_line = lines[0]
        length = font.getlength(single_line)

        last_ok = (single_line, "")
        if length > width:
            gen = split_fn(single_line)
            last_ok = next(gen, (single_line, ""))
            for head, tail in gen:
                length = font.getlength(head)
                if length <= width:
                    last_ok = (head, tail)
                else:
                    break

        result.append(last_ok[0])
        if len(last_ok[1]) == 0:
            lines = lines[1:]
        else:
            lines = [last_ok[1]] + lines[1:]

    return "\n".join(result)

def fit_font(font, text, width):
    """Returns the font that is as large as possible while still fitting
    the text into width.

    font -- Font name and variant is taken from this font.

    text -- The text to measure with.

    width -- The width in pixels that the text is to be fitted into.

    """
    length = 0
    for part in text.split("\n"):
        part_length = font.getlength(part)
        if part_length > length:
            text = part
            length = part_length

    size = font.size * (width / length)

    while length > width:
        size *= 0.9
        font = font.font_variant(size = size)
        length = font.getlength(text)

    best_size = size
    while length < width:
        best_size = size
        size += 1
        font = font.font_variant(size = size)
        length = font.getlength(text)

    return get_font(font.getname()[0],
                    best_size,
                    font.getname()[1])
