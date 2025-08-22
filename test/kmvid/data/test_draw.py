import kmvid.data.clip as clip
import kmvid.data.effect as effect

import testbase

class TestDraw(testbase.Testbase):
    def test_draw(self):
        c = clip.color(width=300, height=260, color=(255, 255, 255))

        c.add(effect.Draw()
              # rectangle
              .config(fill=(200, 0, 0))
              .rectangle(10, 10, 100, 100)
              .config(fill=None, color=(100, 0, 0), pen_width=5)
              .rectangle(75, 75, 100, 100, center=True)
              .config(fill=(50, 0, 0))
              .rectangle(75, 75, 50, 50, center=True)
              # ellipse
              .config(fill=(0, 200, 0), color=None, pen_width=None)
              .ellipse(150, 10, 100, 100)
              .config(fill=None, color=(0, 100, 0), pen_width=5)
              .ellipse(225, 75, 100, 100, center=True)
              .config(fill=(0, 50, 0))
              .ellipse(225, 75, 50, 50, center=True)
              # line
              .config(fill=None, color=(0, 0, 200), pen_width=3)
              .line([(10, 150), (110, 250), (110, 150), (10, 250)])
              .config(fill=(0, 0, 150), color=(50, 50, 250))
              .line([(150, 150), (150, 250), (250, 150)], close=True)
              )

        self.assertImage("draw", c)
