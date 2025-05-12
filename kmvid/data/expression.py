import kmvid.data.common as common
import kmvid.data.state as state

import functools
import operator
import sys

def parse(expression):
    if isinstance(expression, str):
        if __SYMBOL_MAPPING__.get(expression, None):
            return Symbol(expression)

    elif isinstance(expression, (tuple, list)):
        if len(expression) > 0:
            if __FUNCTION_MAPPING__.get(expression[0], None):
                return Function(expression[0],
                                [parse(x) for x in expression[1:]])
            else:
                raise ValueError(f"Function '{expression[0]}' doesn't exist")
        else:
            raise ValueError("Sequences can not be empty")

    return Value(expression)

#--------------------------------------------------
# data

class FnDef:
    def __init__(self, name, function=None, ftype=None):
        self.name = name
        self.function = function
        self.ftype = ftype

    def call(self, args):
        if self.ftype is None:
            return self.function(*args)
        elif self.ftype == "binary":
            return functools.reduce(self.function, args)
        else:
            raise Exception(f"Unknown function type '{self.ftype}'")

class SymDef:
    def __init__(self, name, function=None):
        self.name = name
        self.function = function
        self.takes_arg = True

    def get(self, node):
        return self.function()

__FUNCTION_MAPPING__ = {}
__SYMBOL_MAPPING__ = {}

for fdef in [FnDef('+', operator.add,     ftype="binary"),
             FnDef('-', operator.sub,     ftype="binary"),
             FnDef('*', operator.mul,     ftype="binary"),
             FnDef('/', operator.truediv, ftype="binary"),
             ]:
    __FUNCTION_MAPPING__[fdef.name] = fdef

for sdef in [SymDef('time', lambda: state.local_time),
             SymDef('global-time', lambda: state.global_time),
             SymDef('width', lambda: state.render.image.size[0]),
             SymDef('height', lambda: state.render.image.size[1]),
             ]:
    __SYMBOL_MAPPING__[sdef.name] = sdef

#--------------------------------------------------
# types

class Expression(common.Node):
    def __init__(self):
        common.Node.__init__(self)

    def evaluate(self):
        raise NotImplementedError()

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            return cls.from_simple(s)
        else:
            common.Node.from_simple(s, obj)
            return obj

class Function(Expression):
    def __init__(self, name=None, args=None):
        Expression.__init__(self)
        self.name = name
        self.args = []

        args = args or []
        self.add_arg(*args)

    def add_arg(self, *args):
        for arg in args:
            arg.parent = self
            self.args.append(arg)

    def evaluate(self):
        fdef = __FUNCTION_MAPPING__.get(self.name, None)
        if fdef is None:
            raise Exception(f"No function with name '{self.name}'")
        return fdef.call([arg.evaluate() for arg in self.args])

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Expression, self)
        s.set('name', self.name)
        s.set('args', [arg.to_simple() for arg in self.args])
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Function()
        Expression.from_simple(s, obj)
        obj.name = s.get('name')
        obj.args = []
        for arg_data in s.get('args'):
            obj.add_arg(Expression.from_simple(s, common.Simple.from_data(arg_data)))
        return obj

class Symbol(Expression):
    def __init__(self, name=None):
        Expression.__init__(self)
        self.name = name

    def evaluate(self):
        sym = __SYMBOL_MAPPING__.get(self.name, None)
        if sym is None:
            raise Exception(f"No symbol with name '{self.name}'")
        return sym.get(self)

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Expression, self)
        s.set('name', self.name)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Symbol()
        Expression.from_simple(s, obj)
        obj.name = s.get('name')
        return obj

class Value(Expression):
    def __init__(self, value=None):
        Expression.__init__(self)
        self.value = value

    def evaluate(self):
        return self.value

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(Expression, self)
        s.set('value', self.value)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Value()
        Expression.from_simple(s, obj)
        obj.value = s.get('value')
        return obj
