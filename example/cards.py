from kmvid.script import *

import math
import random

def make_suit(suit, size):
    n = suit % 3
    width = max(1, size/20)

    if n == 0:
        return (Clip((0, 0, 0, 0), width=size, height=size)
                .add(
                    Draw()
                    .config(fill="#ff5555ff", color="#501616ff", pen_width=width)
                    .ellipse(0, 0, size, size)
                ))

    elif n == 1:
        return (Clip((0, 0, 0, 0), width=size, height=size)
                .add(
                    Draw()
                    .config(fill="#5fd35fff", color="#165016ff", pen_width=width)
                    .rectangle(0, 0, size, size)
                ))

    elif n == 2:
        return (Clip((0, 0, 0, 0), width=size, height=size)
                .add(
                    Draw()
                    .config(fill="#5f8dd3ff", color="#162d50ff", pen_width=width)
                    .line([(0, 0), (size, 0), (size/2, size)], close=True)
                ))

def make_card(suit, amount, size):
    card = Clip("#c8beb7ff", width=size*0.7, height=size)

    suit_size = size/5
    vert_factor = 0.3
    vert_offset = 0.5 - vert_factor * (amount/2) + vert_factor/2

    card.add(Draw()
             .config(color="#ac9d93ff", pen_width=size/4)
             .line([(0, 0), (size*0.7, size)])
             .line([(0, size), (size*0.7, 0)]))

    for n in range(amount):
        card.add(
            make_suit(suit, suit_size).add(
                Pos(horizontal=0.5,
                    vertical=vert_factor * n + vert_offset)))

    card.add(Border(width=size/40,
                    color="#333333ff",
                    all=dict(size=size/10)))

    return card

def run():
    w = 1280
    h = 720

    proj = Project(w, h, 30, filename="example_cards.mp4")
    rng = random.Random(3)
    deck = [make_card(suit, amount+1, w/4)
            for suit in range(3)
            for amount in range(3)]

    card_interval = 0.1 # time delay between cards
    fan_tilt = 10 # degrees change per card

    for i, card in enumerate(deck):
        # (x, y, rotation) for resting and fan positions
        resting = (rng.random(), rng.random(), rng.randint(-360, 360))
        fan = (1 / (len(deck) + 1) * (i + 1),
               1 - math.sin((i+0.5) / len(deck) * math.pi) * 0.9,
               -(len(deck) / 2 * fan_tilt) + i * fan_tilt)

        card.start_time = i * card_interval
        card.add(
            Pos(horizontal={0: rng.choice([-2, 2]),
                            1: resting[0],
                            3: resting[0],
                            4: fan[0],
                            5.3: fan[0],
                            6: rng.choice([-2, 2]),
                            },
                vertical={0: rng.choice([-2, 2]),
                          1: resting[1],
                          3: resting[1],
                          4: fan[1],
                          5.3: fan[1],
                          6: rng.choice([-2, 2]),
                          }),
            Rotate({0: rng.randint(0, 360),
                    1: resting[2],
                    3: resting[2],
                    4: fan[2],
                    5.3: fan[2],
                    6: rng.randint(0, 360),
                    }),
        )

        proj.add(card)

    proj.duration = 6 + len(deck) * card_interval
    proj.write()

if __name__ == '__main__':
    run()
