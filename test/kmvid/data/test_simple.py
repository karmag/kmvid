import kmvid.data.clip as clip
import kmvid.data.draw as draw
import kmvid.data.effect as effect
import kmvid.data.expression as expression
import kmvid.data.project as project
import kmvid.data.resource as resource
import kmvid.data.variable as variable
import kmvid.user.library as library

import unittest

class TestSimple(unittest.TestCase):
    def test_to_from_simple(self):
        test_data = [
            project.Project(),

            clip.color(),
            clip.image("/path"),
            clip.video("/path"),

            draw.Config(color=(1, 2, 3), fill=(4, 5, 6), pen_width=10),
            draw.Ellipse(x=1, y=2, width=3, height=4, radius=5),
            draw.Rectangle(x=10, y=20, width=30, height=40),

            effect.EffectSeq(effects = [effect.Pos(), effect.Resize()]),
            effect.Pos(),
            effect.Resize(),
            effect.Rotate(),
            effect.Fade(),
            effect.Crop(),
            effect.Draw(),
            effect.Border(all={'size': 10, 'width': 20, 'height': 30}),
            effect.AlphaShape(x=5, y=10, w=200, h=50, min_value=0.2, max_value=0.9, alpha_strategy="MAX"),

            expression.Function("+"),
            expression.Symbol("time"),
            expression.Value(100),

            resource.ColorResource(),
            resource.ImageResource("a.jpg"),
            resource.VideoResource("a.mp4"),
            resource.MappingEntry(2, 3, 5),
            resource.TimeMap(5),

            variable.StaticValue(100),
            variable.ExpressionValue(expression.Value('a')),

            library.Library(),
            library.FileItem(),

            self._big_test(),
        ]

        for index, obj in enumerate(test_data):
            with self.subTest(index = index, type_name = type(obj).__name__):
                first = obj.to_simple()
                second = type(obj).from_simple(first).to_simple()
                self.assertEqual(first.data, second.data)
                self.assertTrue(first.get('_type', False))

    def _big_test(self):
        p = project.Project(width = 800, height = 600, fps = 10)
        p.set_value("duration", 5)

        img = clip.image("img.jpg")
        img.add(effect.Resize(width=700))
        img.add(effect.Rotate(180))
        img.add(effect.Pos(x = 10, y = 10))
        p.add(img)

        rot = clip.color((600, 400), (150, 20, 20), mode="RGBA")
        img = clip.image("img.jpg", mode="RGBA")
        img.add(effect.Resize(width=580, height=380))
        img.add(effect.Pos(x = 10, y = 10))
        rot.add(img)
        rot.add(effect.Rotate(35))
        rot.add(effect.Resize(width=500))
        img.add(effect.Pos(x = 10, y = 10))
        p.add(rot)

        vid = clip.video("video.mp4")
        vid.add(effect.Resize(width=400))
        img.add(effect.Pos(x = 10, y = 10))
        p.add(vid)

        return p
