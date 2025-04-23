from kmvid.script import *
import kmvid.data.text as text

import random

width = 1920
height = 1080
fps = 60

class Tiles:
    def __init__(self, shape, padding = None, font_name = "Courier New"):
        self.shape = shape
        self.padding = padding or width/100
        self.font_name = font_name

        self.w = len(shape[0])
        self.h = len(shape)

        self.size = (width - (self.w + 1) * padding) / (self.w + 2)
        self.size = min(self.size, (height - (self.h + 1) * padding) / (self.h + 2))
        self.size = int(self.size)

        block_x_size = self.size * self.w + padding * (self.w - 1)
        block_y_size = self.size * self.h + padding * (self.h - 1)

        self.x_offset = (width - block_x_size) / 2
        self.y_offset = (height - block_y_size) / 2

    def get_position(self, x, y):
        return (x * self.size + x * self.padding + self.x_offset,
                y * self.size + y * self.padding + self.y_offset)

    def get_color(self, x, y):
        return "#222255"

    def get_text(self, x, y):
        char = self.shape[y][x]
        if char != " ":
            return char
        return None

    def get_tile(self, x, y):
        c = Clip(self.get_color(x, y), width=self.size, height=self.size)

        char = self.get_text(x, y)
        if char:
            c.add(Draw()
                  .config(fill = "#ffffff")
                  .text(x = self.size / 2,
                        y = self.size / 2,
                        text = char,
                        width = self.size / 2,
                        font_name = self.font_name,
                        anchor = "mm"))
        c.add(Border(width=1, all={"size": self.size/5}))

        return c

def slide_1():
    tiles = Tiles(["              ",
                   "  GAME  OVER  ",
                   "              ",
                   ],
                  padding=width/100)

    master = Clip("#111111", width=width, height=height)

    time_travel = 0.2
    time_duration = 3

    time_offset = 0
    time_increase = 0.05

    rng = random.Random(1)

    for x in range(tiles.w):
        for y in range(tiles.h):
            t = tiles.get_tile(x, y)
            t.start_time = time_offset
            t.duration = time_duration + time_travel * 2

            (xx, yy) = tiles.get_position(x, y)
            t.add(Pos(x = {0: width + tiles.size,
                           time_travel: xx,
                           time_travel + time_duration: xx,
                           time_duration + time_travel * 2: -tiles.size},
                      y = {0: rng.randint(0, height),
                           time_travel: yy,
                           time_travel + time_duration: yy,
                           time_duration + time_travel * 2: rng.randint(0, height)}))

            master.add(t)

            time_offset += time_increase

    return master

def run():
    p = Project(width=width, height=height, fps=fps, filename="example_text_block.mp4")

    p.add(slide_1())

    #p.get_frame(2).show()
    p.write()

if __name__ == '__main__':
    run()
