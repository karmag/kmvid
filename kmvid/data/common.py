import collections
import enum
import json
import math

import PIL.ImageChops

__ID_COUNTER__ = 0

def gen_id():
    global __ID_COUNTER__
    __ID_COUNTER__ += 1
    return __ID_COUNTER__

def is_implemented(cls, method_name):
    if type(cls) is not type:
        cls = type(cls)
    return cls.__dict__.get(method_name, None) is not None

#--------------------------------------------------
# simple

__SIMPLE_BASE_TYPES__ = set([
    "Clip",
    "Effect",
    "Expression",
    "Instruction",
    "Item",
    "Project",
    "Resource",
    "Variable",
    "VariableValue",
])

def _clean_simple_data(x):
    if isinstance(x, (int, str, float, bool, type(None))):
        return x

    elif isinstance(x, dict):
        result = {}
        for k in x:
            result[k] = _clean_simple_data(x[k])
        return result

    elif isinstance(x, (list, tuple)):
        return [_clean_simple_data(y) for y in x]

    elif isinstance(x, set):
        return set([_clean_simple_data(y) for y in x])

    elif isinstance(x, Simple):
        return x.data

    elif isinstance(x, enum.Enum):
        return x.name

    else:
        raise Exception('Unknown data to clean for simple: %s' % str(type(x)))

class Simple:
    def __init__(self, obj=None):
        self.data = collections.OrderedDict()
        if obj is not None:
            type_name = type(obj).__qualname__
            base_type_name = None
            for cls in type(obj).mro():
                if cls.__qualname__ in __SIMPLE_BASE_TYPES__:
                    base_type_name = cls.__qualname__
                    break

            if base_type_name and type_name != base_type_name:
                self.data['_type'] = base_type_name
                self.data['_sub_type'] = type_name
            else:
                self.data['_type'] = type_name

        self.node_store = {}

    @staticmethod
    def from_data(root_simple, data):
        s = Simple()
        s.data = data
        s.node_store = root_simple.node_store
        return s

    def set(self, key, value):
        assert key not in self.data
        self.data[key] = _clean_simple_data(value)

    def get(self, key, default='__nothing__'):
        if default == '__nothing__':
            return self.data[key]
        return self.data.get(key, default)

    def merge(self, other):
        for k in other.data:
            if not (k == '_type' or k == '_sub_type'):
                if k in self.data:
                    raise Exception(f"Can't merge, key '{k}' already exists")
                else:
                    self.set(k, other.data[k])

    def merge_super(self, cls, inst):
        s = cls.to_simple(inst)
        self.merge(s)

    def register_node(self, node):
        self.node_store[node.global_id] = node

    def populate_node(self, node_id, obj, key):
        if node_id is not None:
            assert node_id in self.node_store
            setattr(obj, key, self.node_store[node_id])

    def get_simple(self, key):
        """Returns a Simple object by wrapping the given key."""
        s = Simple()
        s.data = self.data[key]
        s.node_store = self.node_store
        return s

    def get_json(self, indent=None):
        return json.dumps(self.data, indent=indent)

    def pprint(self, indent=4):
        print(self.get_json(indent=indent))

    def save_file(self, path):
        with open(path, 'w', encoding="utf-8") as f:
            json.dump(self.data, f)

    @staticmethod
    def load_file(path):
        with open(path, 'r', encoding="utf-8") as f:
            s = Simple()
            s.data = json.load(f)
            return s

class Simpleable:
    def to_simple(self):
        raise NotImplementedError()

    @staticmethod
    def from_simple(simple, obj):
        raise NotImplementedError()

#--------------------------------------------------
# data

class Node(Simpleable):
    def __init__(self):
        Simpleable.__init__(self)
        self.global_id = gen_id()
        self.parent = None

    def get_parent_node(self, type):
        node = self

        while node.parent:
            if isinstance(node.parent, type):
                return node.parent
            node = node.parent

        return None

    def to_simple(self):
        s = Simple(self)
        s.set('global_id', self.global_id)
        s.set('parent', (self.parent.global_id if self.parent else None))
        return s

    @staticmethod
    def from_simple(s, obj):
        obj.global_id = s.get('global_id')
        s.populate_node(s.get('parent'), obj, 'parent')
        s.register_node(obj)

class Render:
    def __init__(self, parent_image, image):
        self.parent_image = parent_image
        self.image = image
        self.x = 0
        self.y = 0

#--------------------------------------------------
# util

def merge_alpha_layer(image, alpha_channel):
    if image.has_transparency_data:
        alpha_channel = PIL.ImageChops.darker(image.getchannel("A"), alpha_channel)
    image.putalpha(alpha_channel)

class Vector:
    """2 dimensional vector going from origin -> target.

    Methods that set/change values can be chained.

    'coord' arguments expects x and y values and can be either two
    positional arguments or a tuple/list with two values.

    """

    def __init__(self, origin=None, target=None):
        self._origin = origin or (0, 0)
        self._target = target or (0, 0)

    def get_x(self):
        return self._origin[0]

    def set_x(self, n):
        self._origin = (n, self._origin[1])
        return self

    def get_y(self):
        return self._origin[1]

    def set_y(self, n):
        self._origin = (self._origin[0], n)
        return self

    def get_origin(self):
        return self._origin

    def set_origin(self, *coord):
        self._origin = self._parse_coordinates(coord)
        return self

    def get_target(self):
        return self._target

    def set_target(self, *coord):
        self._target = self._parse_coordinates(coord)
        return self

    def get_delta_x(self):
        return self._target[0] - self._origin[0]

    def set_delta_x(self, n):
        self._target = (self._origin[0] + n, self._target[1])
        return self

    def get_delta_y(self):
        return self._target[1] - self._origin[1]

    def set_delta_y(self, n):
        self._target = (self._target[0], self._origin[1] + n)
        return self

    def get_magnitude(self):
        return math.hypot(self.delta_x, self.delta_y)

    def set_magnitude(self, magnitude):
        self.delta_x = self.delta_x / self.magnitude * magnitude
        self.delta_y = self.delta_y / self.magnitude * magnitude
        return self

    x = property(get_x, set_x)
    y = property(get_y, set_y)
    origin = property(get_origin, set_origin)
    target = property(get_target, set_target)
    delta_x = property(get_delta_x, set_delta_x)
    delta_y = property(get_delta_y, set_delta_y)
    magnitude = property(get_magnitude, set_magnitude)

    def _parse_coordinates(self, args):
        x = None
        y = None

        if len(args) == 1:
            v = args[0]
            if isinstance(v, (list, tuple)) and len(v) == 2:
                x = v[0]
                y = v[1]

        elif len(args) == 2:
            x = args[0]
            y = args[1]

        if x is None or y is None:
            raise ValueError(f"Can't parse coordinate: {args}")

        return (x, y)

    def swap(self):
        """Switch place of origin and target."""
        self.origin, self.target = self.target, self.origin
        return self

    def invert(self):
        """Rotates target by 180 degrees."""
        self.delta_x *= -1
        self.delta_y *= -1
        return self

    def transpose(self, *coord):
        """Moves both origin and target by the given amount."""
        diff = self._parse_coordinates(coord)
        self._origin = (self._origin[0] + diff[0], self._origin[1] + diff[1])
        self._target = (self._target[0] + diff[0], self._target[1] + diff[1])
        return self

    def move_to(self, *coord):
        """Move origin to the given position while maintaining the distance
        and direction to target.

        """
        xy = self._parse_coordinates(coord)
        self.transpose(xy[0] - self._origin[0],
                       xy[1] - self._origin[1])
        return self

    def at_ratio(self, ratio):
        """Returns (x, y) for the position along origin -> target
        corresponding to ratio. Ratio should be between 0 and 1.

        """
        return (self._origin[0] + self.delta_x * ratio,
                self._origin[1] + self.delta_y * ratio)

    def __str__(self):
        def fmt(n): return int(n) if int(n) == n else "%.2f" % n
        return "(%s %s) --%s--> (%s %s)" % (
            fmt(self._origin[0]),
            fmt(self._origin[1]),
            fmt(self.magnitude),
            fmt(self._target[0]),
            fmt(self._target[1]))
