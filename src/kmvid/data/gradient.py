def line_gradient(line):
    """Line is ((x1, y1), (x2, y2)). Returns (x_diff, y_diff) indicating
    the percentage change that should occur per pixel to create a
    gradient between the two points in line. (x1, y1) starts at 0 and
    goes to 1 at (x2, y2).

    The value for a specific coordinate (x, y) can be found by using
    the formula:

        value = (x - x1)*x_diff + (y - y1)*y_diff
        value = max(value, 0)
        value = min(value, 1)

    """
    (x1, y1), (x2, y2) = line

    # deal with horizontal/vertical lines as the algorithm can't handle those
    if x1 == x2:
        return (0, 1 / (y2 - y1))
    if y1 == y2:
        return (1 / (x2 - x1), 0)

    perpendicular = _get_perpendicular_line(line)

    x_intersection = _get_intersection_point(perpendicular, ((0, y1), (10, y1)))
    y_intersection = _get_intersection_point(perpendicular, ((x1, 0), (x1, 10)))

    x_diff = 1 / (x_intersection[0] - x1)
    y_diff = 1 / (y_intersection[1] - y1)

    return x_diff, y_diff

def _get_perpendicular_line(line):
    """Returns a line that is perpendicular to the given line. The
    returned perpendicular line goes through the endpoint of the given
    line.

    Doesn't work with vertical/horizontal lines.

    """
    (x1, y1), (x2, y2) = line

    m = (y2 - y1) / (x2 - x1) # line formula: y = m*x - m*x1 + y1
    m2 = -1 / m # perpendicular formula: y = m2*x - m2*x2 + y2

    x3 = x2 + 10
    y3 = m2*x3 - m2*x2 + y2

    return ((x2, y2), (x3, y3))

def _get_intersection_point(line_a, line_b):
    """Returns (x, y) indicating where the two lines intersect. If the
    lines don't intersect the behavior is undefined.

    """
    (x1, y1), (x2, y2) = line_a
    (x3, y3), (x4, y4) = line_b

    x = (
        ( (x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4) ) /
        ( (x1 - x2)*(y3 - y4) - (y1 - y2)*(x3 - x4) )
    )

    y = (
        ( (x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4) ) /
        ( (x1 - x2)*(y3 - y4) - (y1 - y2)*(x3 - x4) )
    )

    return x, y
