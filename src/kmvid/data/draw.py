import kmvid.data.common as common
import kmvid.data.text
import kmvid.data.variable as variable

import enum
import sys

import PIL.ImageChops
import PIL.ImageDraw

class FinishType(enum.Enum):
    MERGE = 0
    MERGE_ALPHA = 1
    RETURN = 2
    DIRECT = 3

@variable.holder
class Draw(common.Node, variable.VariableHold):
    background = variable.VariableConfig()
    mode = variable.VariableConfig(str, "RGBA")
    finish = variable.VariableConfig(FinishType, FinishType.MERGE)

    def __init__(self, **kwargs):
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, kwargs=kwargs)

        self.instructions = []

    def add_instruction(self, ins):
        self.instructions.append(ins)
        ins.parent = self

    def apply(self, image):
        original_image = image

        if self.finish == FinishType.DIRECT:
            image = original_image
        else:
            image = PIL.Image.new(mode = self.mode,
                                  size = original_image.size,
                                  color = (0, 0, 0, 0))

        draw = PIL.ImageDraw.Draw(image)

        if self.background:
            draw.rectangle((0, 0) + image.size, fill = self.background)

        data = Data()
        data.image = image
        data.draw = draw

        for ins in self.instructions:
            ins.apply(data)

        final_image = None
        if self.finish == FinishType.MERGE:
            original_image.paste(image,
                                 (image if image.has_transparency_data else None))
            final_image = original_image

        elif self.finish == FinishType.MERGE_ALPHA:
            alpha = None
            if original_image.has_transparency_data:
                alpha = PIL.ImageChops.darker(
                    image.getchannel("A"),
                    original_image.getchannel("A"))
            else:
                alpha = image.getchannel("A")

            original_image.putalpha(alpha)
            final_image = original_image

        elif self.finish == FinishType.RETURN:
            final_image = image

        elif self.finish == FinishType.DIRECT:
            final_image = image

        else:
            raise Exception(f"Unknown FinishType value: {self.finish}")

        return final_image

    def config(self, **kwargs):
        self.add_instruction(Config(**kwargs))
        return self

    def rectangle(self, *args, **kwargs):
        self.add_instruction(Rectangle(*args, **kwargs))
        return self

    def ellipse(self, *args, **kwargs):
        self.add_instruction(Ellipse(*args, **kwargs))
        return self

    def text(self, *args, **kwargs):
        self.add_instruction(Text(*args, **kwargs))
        return self

    def line(self, *args, **kwargs):
        self.add_instruction(Line(*args, **kwargs))
        return self

    def to_simple(self):
        s = common.Simple()
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        s.set('instructions', [ins.to_simple() for ins in self.instructions])
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Draw()

        common.Node.from_simple(s, obj)
        variable.VariableHold.from_simple(s, obj)
        obj.instructions = []
        for ins_data in s.get('instructions'):
            ins = Instruction.from_simple(common.Simple.from_data(s, ins_data))
            obj.instructions.append(ins)
        return obj

class Data:
    def __init__(self):
        self.image = None
        self.draw = None

        self.color = None
        self.fill = None
        self.pen_width = None

        self.font_name = None
        self.font_size = None
        self.font_variant = None

class Instruction(common.Node, variable.VariableHold):
    def __init__(self, args=None, kwargs=None):
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, args=args, kwargs=kwargs)

    def apply(self, data):
        raise NotImplementedError()

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            if cls.__dict__.get('from_simple', None):
                obj = cls.from_simple(s)
            else:
                obj = cls()

        common.Node.from_simple(s, obj)
        variable.VariableHold.from_simple(s, obj)
        return obj

@variable.holder
class Config(Instruction):
    color = variable.VariableConfig()
    fill = variable.VariableConfig()
    pen_width = variable.VariableConfig(int, default=0)

    font_name = variable.VariableConfig(str)
    font_size = variable.VariableConfig(int)
    font_variant = variable.VariableConfig(str)

    def __init__(self, **kwargs):
        Instruction.__init__(self, kwargs=kwargs)

        self._is_set = set(kwargs.keys())

    def apply(self, data):
        if 'color' in self._is_set:
            data.color = self.color
        if 'fill' in self._is_set:
            data.fill = self.fill
        if 'pen_width' in self._is_set:
            data.pen_width = self.pen_width

        if 'font_name' in self._is_set:
            data.font_name = self.font_name
        if 'font_size' in self._is_set:
            data.font_size = self.font_size
        if 'font_variant' in self._is_set:
            data.font_variant = self.font_variant

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Instruction, self)
        s.set('is_set', self._is_set)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Config()

        Instruction.from_simple(s, obj)
        obj._is_set = s.get('is_set', set())
        return obj

@variable.holder
class Rectangle(Instruction):
    x = variable.VariableConfig(int, 0)
    y = variable.VariableConfig(int, 0)
    width = variable.VariableConfig(int)
    height = variable.VariableConfig(int)
    center = variable.VariableConfig(bool)

    def __init__(self, *args, **kwargs):
        Instruction.__init__(self, args=args, kwargs=kwargs)

    def apply(self, data):
        x = self.x
        y = self.y

        if self.center:
            x -= int(self.width / 2)
            y -= int(self.height / 2)

        data.draw.rectangle((x, y, x + self.width, y + self.height),
                            fill = data.fill,
                            outline = data.color,
                            width = data.pen_width)

@variable.holder
class Ellipse(Instruction):
    x = variable.VariableConfig(int, 0)
    y = variable.VariableConfig(int, 0)
    width = variable.VariableConfig(int)
    height = variable.VariableConfig(int)
    radius = variable.VariableConfig(float)
    center = variable.VariableConfig(bool)

    def __init__(self, *args, **kwargs):
        Instruction.__init__(self, args=args, kwargs=kwargs)

    def apply(self, data):
        x = self.x
        y = self.y
        w = self.width
        h = self.height

        if self.radius is not None:
            w = self.radius * 2
            h = self.radius * 2

        if self.center:
            x -= int(w / 2)
            y -= int(h / 2)

        data.draw.ellipse((x, y, x + w, y + h),
                          fill = data.fill,
                          outline = data.color,
                          width = data.pen_width)

@variable.holder
class Text(Instruction):
    text = variable.VariableConfig(str, "no text")
    x = variable.VariableConfig(int, 0)
    y = variable.VariableConfig(int, 0)
    font_name = variable.VariableConfig(str)
    size = variable.VariableConfig(int)
    variant = variable.VariableConfig(str)
    width = variable.VariableConfig(int)
    anchor = variable.VariableConfig(str)

    def __init__(self, *args, **kwargs):
        """Draw text.

        text -- Text to draw. If the text contains linebreak
        characters multiple lines are drawn.

        x -- Left coordinate to place text.

        y -- Top coordinate to place text.

        font_name -- Name of the font.

        size -- Size of the font.

        variant -- Variant of the font.

        width -- The width at which point text wrapping occurs. If set
        to None no wrapping takes place. If parts of the text can't
        fit it will be truncated. If size (or font_size from config,
        if size is not set) is None then the font size is adapted so
        that text fits into width.

        anchor -- Where to place the text in relation to x and y
        coordinates. By default top left is used.

            Horizontal
                l - left
                m - middle
                r - right
                s - baseline (vertical text only)

            Vertical
                a - ascender / top (horizontal text only)
                t - top (single-line text only)
                m - middle
                s - baseline (horizontal text only)
                b - bottom (single-line text only)
                d - descender / bottom (horizontal text only)

            https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html

        """
        Instruction.__init__(self, args=args, kwargs=kwargs)

    def apply(self, data):
        font_size = self.size or data.font_size
        font = None
        text = self.text

        font = kmvid.data.text.get_font(
            self.font_name or data.font_name,
            size = font_size,
            variant = self.variant or data.font_variant)

        if self.width and font_size:
            text = kmvid.data.text.wrap_text(font, text, self.width)
        elif self.width:
            font = kmvid.data.text.fit_font(font, text, self.width)

        data.draw.text((self.x, self.y),
                       text,
                       fill = data.fill,
                       font = font,
                       stroke_width = data.pen_width,
                       stroke_fill = data.color,
                       anchor = self.anchor)

@variable.holder
class Line(Instruction):
    path = variable.VariableConfig()
    close = variable.VariableConfig(bool, False)

    def __init__(self, *args, **kwargs):
        """Draw lines or a polygon.

        path -- A list of (x, y) pairs indicating.

        close -- When true an additional line from the last point to
        the first point will be drawn. This turns the lines into a
        polygon which can be filled.

        """
        Instruction.__init__(self, args=args, kwargs=kwargs)

    def apply(self, data):
        path = self.path

        if self.close:
            data.draw.polygon(path,
                              fill = data.fill,
                              outline = data.color,
                              width = data.pen_width)
        else:
            data.draw.line(path,
                           fill = data.color,
                           width = data.pen_width)
