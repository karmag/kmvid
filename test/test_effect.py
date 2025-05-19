import kmvid.data.clip as clip
import kmvid.data.effect as effect
import kmvid.data.state as state

import testbase

R = (255, 0, 0)
G = (0, 255, 0)
B = (0, 0, 255)

TUPLE_TO_CHAR = {R: 'x', G: 'o', B: '-'}

def to_image_repr(img):
    result = []
    for y in range(img.size[1]):
        row = ""
        for x in range(img.size[0]):
            row += TUPLE_TO_CHAR[img.getpixel((x, y))]
        result.append(row)
    return result

class TestEffect(testbase.Testbase):
    def test_pos(self):
        self.check(clip.color(width=4, height=1, color=G),
                   None,
                   ['oooo--',
                    '------',
                    '------'])

        self.check(clip.color(width=4, height=1, color=G),
                   effect.Pos(x=1, y=1),
                   ['------',
                    '-oooo-',
                    '------'])

        self.check(clip.color(width=4, height=1, color=G),
                   effect.Pos(x=1, y=1, x_offset=1, y_offset=-1),
                   ['--oooo',
                    '------',
                    '------'])

        self.check(clip.color(width=3, height=1, color=G),
                   effect.Pos(x=3, y=2, center=True),
                   ['------',
                    '------',
                    '--ooo-'])

    def test_relative_pos(self):
        self.check(clip.color(width=2, height=1, color=G),
                   effect.Pos(horizontal=0, vertical=0),
                   ['oo----',
                    '------',
                    '------'])

        self.check(clip.color(width=2, height=1, color=G),
                   effect.Pos(horizontal=0.5, vertical=0.5),
                   ['------',
                    '--oo--',
                    '------'])

        self.check(clip.color(width=2, height=1, color=G),
                   effect.Pos(horizontal=1, vertical=1),
                   ['------',
                    '------',
                    '----oo'])

        self.check(clip.color(width=2, height=2, color=G),
                   effect.Pos(horizontal=0, vertical=0, weight=0.5),
                   ['o-----',
                    '------',
                    '------'])

        self.check(clip.color(width=2, height=1, color=G),
                   effect.Pos(vertical=0, weight=0),
                   ['------',
                    '------',
                    '------'])

    def test_resize(self):
        self.check(clip.color(width=2, height=2, color=G),
                   [effect.Resize(width=6, height=3),
                    effect.Pos(x=0, y=0)],
                   ['oooooo',
                    'oooooo',
                    'oooooo'])

        self.check(clip.color(width=2, height=2, color=G),
                   [effect.Resize(width=4,
                                  height=2,
                                  strategy=effect.ResizeType.STRETCH),
                    effect.Pos(x=0, y=0)],
                   ['oooo--',
                    'oooo--',
                    '------'])

        self.check(clip.color(width=2, height=2, color=G),
                   [effect.Resize(width=4),
                    effect.Pos(x=0, y=0)],
                   ['oooo--',
                    'oooo--',
                    'oooo--'])

    def test_resize_all(self):
        base = clip.color(width=700, height=900, color=(100, 100, 100))
        x = 0
        y = 0
        for strategy in effect.ResizeType:
            for w, h in [(50, None),
                         (None, 100),
                         (50, 100)]:
                c = clip.color(width=200, height=200, color=(50, 0, 0))
                c.add_item(effect.Draw()
                           .config(fill=(0, 50, 0), pen_width=0)
                           .rectangle(x=0, y=0, width=100, height=200)
                           .config(fill=(90, 90, 150))
                           .rectangle(x=25, y=25, width=50, height=50))
                c.add_item(effect.Resize(width=w, height=h, strategy=strategy))
                c.add_item(effect.Pos(x=x * 250 + 10, y=y * 250 + 10))
                base.add_item(c)
                base.add_item(effect.Draw()
                              .config(color=(255, 255, 255), pen_width=1)
                              .rectangle(x=x * 250 + 10,
                                         y=y * 250 + 10,
                                         width=50,
                                         height=100))
                x += 1
            x = 0
            y += 1
        self.assertImage("all", base)

    def test_rotate(self):
        self.check(clip.color(width=3, height=2, color=G),
                   effect.EffectSeq(effects=[effect.Rotate(90),
                                             effect.Pos(horizontal=0.5,
                                                        vertical=0.5)]),
                   ['--oo--',
                    '--oo--',
                    '--oo--'])

    def test_border(self):
        c = clip.color(width=6, height=3, color=B)
        self.check(c,
                   effect.Border(width=0, color=R),
                   ['------',
                    '------',
                    '------'])

        c = clip.color(width=4, height=1, color=B)
        self.check(c,
                   [effect.Border(width=1, color=R),
                    effect.Pos(x=0, y=0)],
                   ['xxxxxx',
                    'x----x',
                    'xxxxxx'])

        c = clip.color(width=100, height=100, color=G)
        c.add_item(effect.Border(width=10,
                                 all={'size': 30},
                                 tl={'width': 10},
                                 tr={'type': effect.BorderCornerType.LINE},
                                 bl={'size': None, 'width': None, 'height': None}))

        self.assertImage("mixed", c)

    def test_fade(self):
        size = 50
        c = clip.color(width=size * 10,
                       height=size * 3,
                       color=(0, 0, 0))

        for i in range(10):
            tile = clip.color(width=size, height=size, color=(255, 0, 0))
            tile.add_item(effect.Fade(fade_in=10))
            tile.add_item(effect.Pos(x=i*size))
            tile.start_time = -i
            tile.duration = 10
            c.add_item(tile)

        for i in range(10):
            tile = clip.color(width=size, height=size, color=(0, 255, 0))
            tile.add_item(effect.Fade(fade_out=10))
            tile.add_item(effect.Pos(x=i*size, y=size))
            tile.start_time = -i
            tile.duration = 10
            c.add_item(tile)

        for i in range(10):
            tile = clip.color(width=size, height=size, color=(0, 0, 255))
            tile.add_item(effect.Fade(value=(i+1)/10))
            tile.add_item(effect.Pos(x=i*size, y=2*size))
            c.add_item(tile)

        self.assertImage("fade", c)

    def test_alpha_shape(self):
        size = 150
        pad = 5

        def make(type, **kwargs):
            alpha = clip.color(color="white", width=size, height=size)
            alpha.add_item(effect.AlphaShape(type, **kwargs))

            c = clip.color(color="black", width=size, height=size)
            c.add_item(alpha)
            return c

        images = [
            [
                # horizontal / vertical line
                make("line", x=0, y=size, w=0, h=-size),
                make("line", x=0, y=0, w=size, h=0),
                make("line", x=0, y=0, w=0, h=size),
                make("line", x=size, y=0, w=-size, h=0),
            ], [
                # line diagonals
                make("line", x=0, y=size, w=size, h=-size),
                make("line", x=0, y=0, w=size, h=size),
                make("line", x=size, y=0, w=-size, h=size),
                make("line", x=size, y=size, w=-size, h=-size),
            ], [
                # line modifiers
                make("line", x=size/3, y=size/3, w=size/3, h=size/3),
                make("line", x=size/3, y=size/3, w=size/3, h=size/3, min_value=0.5),
                make("line", x=size/3, y=size/3, w=size/3, h=size/3, max_value=0.5),
                make("line", x=size/3, y=size/3, w=size/3, h=size/3, invert=True),
            ], [
                # basic ellipse
                make("ellipse", x=0, y=0, w=size, h=size),
                make("ellipse", x=0, y=size/3, w=size, h=size/3),
                make("ellipse", x=size/3, y=0, w=size/3, h=size),
            ], [
                # ellipse modifiers
                make("ellipse", x=size/3, y=size/3, w=size/3, h=size/3, size=size/3),
                make("ellipse", x=size/3, y=size/3, w=size/3, h=size/3, size=size/3, min_value=0.5),
                make("ellipse", x=size/3, y=size/3, w=size/3, h=size/3, size=size/3, max_value=0.5),
                make("ellipse", x=size/3, y=size/3, w=size/3, h=size/3, size=size/3, invert=True),
            ],
        ]

        max_width = max([len(row) for row in images])
        master = clip.color(color=(250, 0, 0),
                            width = size*max_width + pad*(max_width + 1),
                            height = size*len(images) + pad*(len(images) + 1))

        for row_num, row in enumerate(images):
            for col_num, img in enumerate(row):
                img.add_item(effect.Pos(x = col_num*size + (col_num + 1)*pad,
                                        y = row_num*size + (row_num + 1)*pad))
                master.add_item(img)

        self.assertImage("alpha_shape", master)

    def check(self, clp, eff, expected_image):
        base = clip.color(width=6, height=3, color=B)
        base.add_item(clp)

        if eff:
            if isinstance(eff, list):
                for e in eff:
                    clp.add_item(e)
            else:
                clp.add_item(eff)

        with state.State():
            render = base.get_frame()
            frame = render.image
        actual_image = to_image_repr(frame)

        self.assertEqual(expected_image, actual_image)
