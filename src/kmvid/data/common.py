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

def to_enum(value, enum_type):
    """Converts the value to an enum of the given type. If the value is
    already of type it is returned as is. String and integers are
    treated as name and ordinal respectively.

    If no conversion can be performed a ValueError is raised.

    """
    if isinstance(value, enum_type):
        return value

    value_str = str(value).lower()
    for entry in enum_type:
        if entry.name.lower() == value_str or entry.value == value:
            return entry

    raise ValueError("Unable to interpret '%s' as enum of type %s" % (
        str(value), enum_type.__name__))

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

class AlphaStrategyType(enum.Enum):
    MIN = 0
    MAX = 1
    OVERWRITE = 2

def merge_alpha(image, alpha, strategy=AlphaStrategyType.MIN):
    """Merge image with the given alpha value. Returns the image.

    image --

    alpha -- If an image use the its alpha channel as the alpha layer.
    If a float treat it as an alpha value and construct a uniform
    image from that value.

    strategy --

    """

    if isinstance(alpha, (int, float)):
        alpha = PIL.Image.new(mode = "L",
                              size = image.size,
                              color = min(255, max(0, int(alpha * 255))))
    else:
        if not alpha.mode == "L":
            alpha = alpha.getchannel("A")

    if image.has_transparency_data:
        if strategy == AlphaStrategyType.MIN:
            alpha = PIL.ImageChops.darker(image.getchannel("A"), alpha)

        elif strategy == AlphaStrategyType.MAX:
            alpha = PIL.ImageChops.lighter(image.getchannel("A"), alpha)

        elif strategy == AlphaStrategyType.OVERWRITE:
            pass

        else:
            raise ValueError("Unknown alpha strategy: %s" % str(strategy))

    image.putalpha(alpha)
    return image
