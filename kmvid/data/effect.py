import kmvid.data.common as common
import kmvid.data.clip as clip
import kmvid.data.draw as draw
import kmvid.data.variable as variable
import kmvid.data.state as state

import enum
import sys
import PIL.ImageChops
import PIL.ImageOps

class Effect(common.Node, variable.VariableHold):
    def __init__(self, args=None, kwargs=None):
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, args=args, kwargs=kwargs)

    def apply(self, render):
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
class EffectSeq(Effect):
    def __init__(self, effects=None):
        Effect.__init__(self)
        self.effects = []

        if effects is not None:
            for eff in effects:
                self.add(eff)

    def add(self, eff):
        self.effects.append(eff)

    def apply(self, render):
        for eff in self.effects:
            eff.apply(render)

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        s.set('effects', [eff.to_simple() for eff in self.effects])
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = EffectSeq()
        Effect.from_simple(s, obj)
        obj.effects = []
        for eff_data in s.get('effects'):
            eff_simple = common.Simple.from_data(s, eff_data)
            obj.add(Effect.from_simple(eff_simple))
        return obj

@variable.holder
class Pos(Effect):
    """Changes the position of a clip in relation to its parent.

    There are multiple variables relating to positioning along the
    same axis. Relative positioning is applied first. Second absolute
    positioning, which will override relative positioning. Offset is
    applied last.

    """

    x = variable.VariableConfig(
        int, doc="""Absolute x position.""")
    y = variable.VariableConfig(
        int, doc="""Absolute y position.""")
    center = variable.VariableConfig(
        bool, False, doc="""For use with x and y variables.

        When True the center of the clip is aligned with x and y
        rather than the upper left corner.""")

    x_offset = variable.VariableConfig(
        int, 0, doc="""Offset for x position.""")
    y_offset = variable.VariableConfig(
        int, 0, doc="""Offset for y position.""")

    horizontal = variable.VariableConfig(
        float, doc="""Relative horizontal position.

        0 aligns the clip to the left of the parent, 1 aligns it to
        the right.""")
    vertical = variable.VariableConfig(
        float, doc="""Relative vertical position.

        0 aligns the clip to the top of the parent, 1 aligns it to the
        bottom.""")
    weight = variable.VariableConfig(
        float, 1, doc="""For use with horizontal and vertical variables.

        How much of the clip is visible in the parent when horizontal
        and vertical are at 0 or 1. Weight 1 means that the clip is
        contained fully within the parent. Weight 0 means that the
        clip is right outside the parent.""")

    def __init__(self, *args, **kwargs):
        Effect.__init__(self, args=args, kwargs=kwargs)

    def apply(self, render):
        if render.parent_image is not None:
            weight = 1 - self.weight

            if self.horizontal is not None:
                w = render.image.size[0]
                pw = render.parent_image.size[0]
                total_width = pw + w * weight * 2
                start_x = -w * weight

                render.x = (start_x + (total_width - w) * self.horizontal)

            if self.vertical is not None:
                h = render.image.size[1]
                ph = render.parent_image.size[1]
                total_height = ph + h * weight * 2
                start_y = -h * weight

                render.y = (start_y + (total_height - h) * self.vertical)

        if self.x is not None:
            render.x = self.x
            if self.center:
                render.x -= render.image.size[0] // 2

        if self.y is not None:
            render.y = self.y
            if self.center:
                render.y -= render.image.size[1] // 2

        render.x += self.x_offset
        render.y += self.y_offset

class ResizeType(enum.Enum):
    COVER = 0
    CONTAIN = 1
    STRETCH = 2
    FIT = 3

@variable.holder
class Resize(Effect):
    width = variable.VariableConfig(int)
    height = variable.VariableConfig(int)
    strategy = variable.VariableConfig(ResizeType, ResizeType.FIT)

    def __init__(self, *args, **kwargs):
        """Resizes the clip. The clip is repositioned so that the center of
        the clip is the same before and after the resize. Either width
        of height may be omitted.

        width -- New width of the clip.

        height -- New height of the clip.

        strategy -- How to resize the image.

            COVER Maintains aspect ratio. Fit the clip into the
            dimensions so that the entire surface/axis is covered by
            the clip. May leave parts of the clip outside the given
            bounds.

            CONTAIN Maintains aspect ratio. Fit the clip into the
            dimensions/axis so that no part of the clip is outside of
            it. The resulting clip may be smaller than specified along
            one of the axes.

            STRETCH Forcably fits the clip into the given dimensions,
            skewing the aspect ratio as necessary. The resulting clip
            will cover the entire given surface/axis.

            FIT Same as cover but truncates the image to completely
            fit inside the given dimensions.

        """
        Effect.__init__(self, args=args, kwargs=kwargs)

    def apply(self, render):
        img_w = render.image.size[0]
        img_h = render.image.size[1]

        if self.strategy == ResizeType.COVER:
            render.image = PIL.ImageOps.cover(render.image, (self.width or 1,
                                                             self.height or 1))

        elif self.strategy == ResizeType.CONTAIN:
            assert self.width or self.height # sanity check before blowing out the RAM
            render.image = PIL.ImageOps.contain(render.image, (self.width or 1e6,
                                                               self.height or 1e6))

        elif self.strategy == ResizeType.STRETCH:
            render.image = render.image.resize((self.width or img_w,
                                                self.height or img_h))

        elif self.strategy == ResizeType.FIT:
            alt_w, alt_h = render.image.size
            if self.width and not self.height:
                alt_h *= self.width / alt_w
            elif not self.width and self.height:
                alt_w *= self.height / alt_h

            render.image = PIL.ImageOps.fit(render.image, (self.width or int(alt_w),
                                                           self.height or int(alt_h)))

        else:
            raise Exception("Unknown resize strategy: %s" % str(self.strategy))

        render.x -= (render.image.size[0] - img_w) / 2
        render.y -= (render.image.size[1] - img_h) / 2

@variable.holder
class Rotate(Effect):
    angle = variable.VariableConfig(float, 0)

    def __init__(self, *args, **kwargs):
        """Rotate clockwise by the given angle amount of degrees. The clip is
        rotated around it's center point.

        """
        Effect.__init__(self, args=args, kwargs=kwargs)

    def apply(self, render):
        render.image = render.image.convert("RGBA")
        old = render.image.size
        render.image = render.image.rotate(-self.angle,
                                           #resample=PIL.Image.Resampling.BICUBIC,
                                           expand=True,
                                           fillcolor="#0000")
        new = render.image.size

        render.x += int((old[0] - new[0]) / 2)
        render.y += int((old[1] - new[1]) / 2)

@variable.holder
class Fade(Effect):
    """Fade the clip by applying a uniform alpha value.

    If multiple values are set only the lowest will apply.

    """

    value = variable.VariableConfig(
        float, 1, doc="""Alpha value as a float between 0 and 1.""")
    fade_in = variable.VariableConfig(
        float, doc="""Duration of fade transition at the start of the clip.""")
    fade_out = variable.VariableConfig(
        float, doc="""Duration of fade transition at the end of the clip.""")
    alpha_strategy = variable.VariableConfig(
        common.AlphaStrategyType, common.AlphaStrategyType.MIN)

    def __init__(self, **kwargs):
        Effect.__init__(self, kwargs=kwargs)

    def apply(self, render):
        value = self.value
        fade_in_value = 1
        fade_out_value = 1
        time = state.local_time

        if self.fade_in is not None and self.fade_in >= time:
            fade_in_value = time / self.fade_in

        if self.fade_out is not None:
            clp = self.get_parent_node(clip.Clip)
            duration = clp.duration
            if duration:
                fade_start = duration - self.fade_out
                if time < fade_start:
                    fade_out_value = 1
                else:
                    fade_out_value = 1 - (time - fade_start) / self.fade_out

        render.image = common.merge_alpha(
            render.image,
            max(0, min(1, value, fade_in_value, fade_out_value)),
            self.alpha_strategy)

@variable.holder
class Crop(Effect):
    left = variable.VariableConfig(int, 0)
    top = variable.VariableConfig(int, 0)
    right = variable.VariableConfig(int, 0)
    bottom = variable.VariableConfig(int, 0)

    def __init__(self, **kwargs):
        """Crops the clip by removing the given number of pixels from each
        edge. The clip is repositioned so that the center is the same
        before and after the crop.

        """
        Effect.__init__(self, kwargs=kwargs)

    def apply(self, render):
        w, h = render.image.size

        left = self.left
        top = self.top
        right = self.right
        bottom = self.bottom

        render.image = render.image.crop((left, top, w - right, h - bottom))
        render.x -= (left + right) / 2
        render.y -= (top + bottom) / 2

@variable.holder
class Draw(Effect):
    def __init__(self, **kwargs):
        Effect.__init__(self)

        self.draw = draw.Draw(**kwargs)

    def config(self, **kwargs):
        self.draw.config(**kwargs)
        return self

    def rectangle(self, *args, **kwargs):
        self.draw.rectangle(*args, **kwargs)
        return self

    def ellipse(self, *args, **kwargs):
        self.draw.ellipse(*args, **kwargs)
        return self

    def text(self, *args, **kwargs):
        self.draw.text(*args, **kwargs)
        return self

    def line(self, *args, **kwargs):
        self.draw.line(*args, **kwargs)
        return self

    def apply(self, render):
        self.draw.apply(render.image)

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Effect, self)
        s.set('draw', self.draw.to_simple())
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Draw()

        Effect.from_simple(s, obj)
        obj.draw = draw.Draw.from_simple(s.get_simple('draw'))
        return obj

@variable.holder
class Border(Effect):
    width = variable.VariableConfig(int, 5)
    color = variable.VariableConfig(default=(255, 255, 255))

    def __init__(self, all=None, tl=None, tr=None, bl=None, br=None, **kwargs):
        """Add border and stylized corners.

        width -- The width of the border. The image grows by width
        pixels in all directions. Use a width of 0 to disable drawing
        a border.

        color -- Color of the border.

        all -- Configuration applied to all corners. A dict with keys
        matching keywords in BorderCorner constructor. all is applied
        first to all corners. Individual corners can be configured
        through tl, tr, bl, br. Individual configuration overrides
        all.

        tl -- Top left corner configuration.

        tr -- Top right corner configuration.

        bl -- Bottom left corner configuration.

        br -- Bottom right corner configuration.

        """
        Effect.__init__(self, kwargs=kwargs)

        self.tl = BorderCorner()
        self.tr = BorderCorner()
        self.bl = BorderCorner()
        self.br = BorderCorner()
        self.tl.parent = self
        self.tr.parent = self
        self.bl.parent = self
        self.br.parent = self

        if all:
            self.all(**all)
        if tl:
            self.tl.set_all_values(tl)
        if tr:
            self.tr.set_all_values(tr)
        if bl:
            self.bl.set_all_values(bl)
        if br:
            self.br.set_all_values(br)

    def all(self, **kwargs):
        if 'border' in kwargs:
            self.border.set_value(kwargs.get('border'))
            del kwargs['border']

        self.tl.set_all_values(kwargs)
        self.tr.set_all_values(kwargs)
        self.bl.set_all_values(kwargs)
        self.br.set_all_values(kwargs)
        return self

    def apply(self, render):
        width = int(self.width + 0.5)

        common.merge_alpha(
            render.image,
            self._get_alpha_channel(render.image))

        if width > 0:
            bg = PIL.Image.new(
                mode="RGBA",
                size=(render.image.size[0] + width * 2,
                      render.image.size[1] + width * 2),
                color=self.color)

            common.merge_alpha(
                bg,
                # TODO need to account for the extra size of the border or the corners look wonky
                self._get_alpha_channel(bg))

            bg.paste(render.image, (width, width), render.image)
            render.image = bg

            render.x -= width
            render.y -= width

    def _get_alpha_channel(self, image):
        alpha = PIL.Image.new(mode="L", size=image.size, color=255)
        draw = PIL.ImageDraw.Draw(alpha)

        self._apply_corner(alpha, draw, self.tl)
        self._apply_corner(alpha, draw, self.tr)
        self._apply_corner(alpha, draw, self.bl)
        self._apply_corner(alpha, draw, self.br)

        return alpha

    def _apply_corner(self, alpha, draw, corner):
        w = corner.width
        h = corner.height

        if w is None:
            w = corner.size or 0
        if h is None:
            h = corner.size or 0

        if w == 0 or h == 0:
            return

        fx = None
        fy = None
        pie_start = 0

        if corner == self.tl:
            fx = lambda x: x
            fy = lambda y: y
            pie_start = 180
        elif corner == self.tr:
            fx = lambda x: alpha.size[0] - x
            fy = lambda y: y
            pie_start = 270
        elif corner == self.bl:
            fx = lambda x: x
            fy = lambda y: alpha.size[1] - y
            pie_start = 90
        else:
            fx = lambda x: alpha.size[0] - x
            fy = lambda y: alpha.size[1] - y
            pie_start = 0

        def fix_box(x0, y0, x1, y1):
            if x0 > x1:
                x0, x1 = x1, x0
            if y0 > y1:
                y0, y1 = y1, y0
            return (x0, y0, x1, y1)

        if corner.type == BorderCornerType.CURVE:
            draw.rectangle(fix_box(fx(0), fy(0), fx(w), fy(h)), fill=0)
            draw.pieslice(fix_box(fx(0), fy(0), fx(w*2), fy(h*2)),
                          pie_start,
                          pie_start + 90,
                          fill=255)

        elif corner.type == BorderCornerType.LINE:
            draw.polygon(((fx(0), fy(h)),
                          (fx(0), fy(0)),
                          (fx(w), fy(0))),
                         fill=0)

        else:
            raise Exception("Unknown corner type: %s" % str(corner.type))

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Effect, self)
        s.set('tl', self.tl.to_simple())
        s.set('tr', self.tr.to_simple())
        s.set('bl', self.bl.to_simple())
        s.set('br', self.br.to_simple())
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Border()

        Effect.from_simple(s, obj)
        obj.tl = BorderCorner.from_simple(s.get_simple('tl'))
        obj.tr = BorderCorner.from_simple(s.get_simple('tr'))
        obj.bl = BorderCorner.from_simple(s.get_simple('bl'))
        obj.br = BorderCorner.from_simple(s.get_simple('br'))
        return obj

class BorderCornerType(enum.Enum):
    CURVE = 0
    LINE = 1

@variable.holder
class BorderCorner(common.Node, variable.VariableHold):
    type = variable.VariableConfig(BorderCornerType, BorderCornerType.CURVE)
    size = variable.VariableConfig(int)
    width = variable.VariableConfig(int)
    height = variable.VariableConfig(int)

    def __init__(self, **kwargs):
        """Corner configuration for borders.

        type -- General shape of the corner.

        size -- Convenience for setting both width and height.

        width -- Horizontal anchor point for the corner. Uses size if
        not set.

        height -- Vertical anchor point for the corner. Uses size if
        not set.

        """
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, kwargs=kwargs)

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = BorderCorner()

        common.Node.from_simple(s, obj)
        variable.VariableHold.from_simple(s, obj)
        return obj
