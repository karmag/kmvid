import kmvid.data.clip as clip
import kmvid.data.effect as effect
import kmvid.data.state as state

import testbase

class TestClip(testbase.Testbase):
    def test_start_time(self):
        root = clip.color(color=(20, 20, 20), width=150, height=150)

        offset = clip.color(color=(200, 200, 200), width=50, height=150)
        offset.start_time = 5
        offset.duration = 10
        offset.add(effect.Pos(x=50))

        r = clip.color(color=(255, 0, 0), width=50, height=50)
        g = clip.color(color=(0, 255, 0), width=50, height=50)
        b = clip.color(color=(0, 0, 255), width=50, height=50)

        r.duration = 10
        g.duration = 10
        b.duration = 10

        r.start_time = -8
        g.start_time = 0
        b.start_time = 8

        g.add(effect.Pos(y=50))
        b.add(effect.Pos(y=100))

        offset.add(r)
        offset.add(g)
        offset.add(b)

        root.add(offset)

        with state.State():
            state.set_time(10)
            render = root.get_frame()
            self.assertImage("clip_start_time", render.image)
