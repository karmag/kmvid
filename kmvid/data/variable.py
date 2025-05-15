import kmvid.data.common as common
import kmvid.data.expression as expression
import kmvid.data.state as state
import scipy.interpolate as interpolate

import enum
import sys

#--------------------------------------------------
# definition

def holder(cls):
    """Decorator for instanciable VariableHold classes."""
    cmap = cls.__dict__

    var_names = []
    for name in cmap:
        if isinstance(cmap[name], VariableConfig):
            var_names.append(name)

    configs = {}
    setattr(cls, "_VariableHold__variable_configs", configs)

    for name in var_names:
        cfg = cmap[name]
        cfg.name = name
        configs[name] = cfg

        setattr(cls, name, property(_default_get_fn(name),
                                    _default_set_fn(name)))

    def get_all():
        configs = [cfg for cfg in getattr(cls, "_VariableHold__variable_configs", {}).values()]
        return sorted(configs, key = lambda cfg: cfg.index)
    cls.get_variable_configs = get_all

    def split_kwargs(kwargs):
        configs = getattr(cls, "_VariableHold__variable_configs", {})
        mine = {}
        other = {}
        for key in kwargs:
            if key in configs:
                mine[key] = kwargs[key]
            else:
                other[key] = kwargs[key]
        return (mine, other)
    cls.split_kwargs = split_kwargs

    return cls

def _default_get_fn(name):
    return lambda self: self.get_value(name)

def _default_set_fn(name):
    return lambda self, value: self.set_value(name, value)

class VariableHold(common.Simpleable):
    def __init__(self, args=None, kwargs=None):
        self.__variables = {}

        for k in self.__variable_configs:
            cfg = self.__variable_configs[k]
            self.add_variable(Variable(cfg))

        if args:
            variables = self.get_all_variables()
            for i, v in enumerate(args):
                self.set_value(variables[i].name, v)

        if kwargs:
            self.set_all_values(kwargs)

    def add_variable(self, var):
        """Adds the given variable to this VariableHold.

        var -- The variable to add. Name of the variable must be
        unique for this VariableHold instance.

        """
        assert var.name not in self.__variables

        var.parent = self
        var.__index = len(self.__variables)
        self.__variables[var.name] = var

    def get_variable(self, name):
        return self.__variables.get(name, None)

    def get_all_variables(self):
        result = [var for var in self.__variables.values()]
        result.sort(key = lambda v: v.__index)
        return result

    def get_value(self, var_name):
        var = self.get_variable(var_name)
        return var.get_value()

    def set_value(self, var_name, value):
        var = self.get_variable(var_name)
        var.set_value(value)
        return self

    def set_all_values(self, kvs):
        for k in kvs:
            self.get_variable(k).set_value(kvs[k])
        return self

    def to_simple(self):
        s = common.Simple(self)
        variables = {}
        for var in self.get_all_variables():
            variables[var.name] = var.to_simple()
        s.set('variables', variables)
        return s

    @staticmethod
    def from_simple(s, obj):
        obj.__variables = {}

        var_data = s.get_simple('variables')

        for k in obj.__variable_configs:
            cfg = obj.__variable_configs[k]
            var = Variable.from_simple(var_data.get_simple(k), Variable(cfg))
            obj.add_variable(var)

        return obj

__VARIABLE_CONFIG_INDEX_COUNTER__ = 0

class VariableConfig(common.Simpleable):
    def __init__(self,
                 type=None,
                 default=None,
                 doc=None,
                 value_transform_fn=None):
        global __VARIABLE_CONFIG_INDEX_COUNTER__
        __VARIABLE_CONFIG_INDEX_COUNTER__ += 1
        self.index = __VARIABLE_CONFIG_INDEX_COUNTER__
        self.name = None
        self.type = type
        self.default = default
        self.doc = doc

        force = None
        if type and issubclass(type, enum.Enum):
            def force(value):
                return value if value is None else common.to_enum(value, type)

        elif type in (int, float, str):
            def force(value):
                if value is None:
                    return value
                return type(value)

        self.value_transform_fn = value_transform_fn or force

class Variable(common.Node):
    def __init__(self, config):
        """Variable class.

        config -- VariableConfig defining this variable.

        """
        common.Node.__init__(self)

        self.config = config
        self.name = config.name

        self._values = []
        self._default = None

        self.value_transform_fn = config.value_transform_fn or (lambda x: x)
        self._set_default(config.default)

    def set_value(self, value):
        """Sets the current value of the variable. Removes any other values
        current present.

        """
        self._values = []
        self.add_value(value)

    def add_value(self, value):
        if value is None:
            return

        for vv in _to_variable_values(value, self.config.value_transform_fn):
            if vv.start_time is None:
                vv.start_time = 0

            remove = []
            for old_vv in self._values:
                if vv.start_time == old_vv.start_time:
                    remove.append(old_vv)

            for old_vv in remove:
                self._values.remove(old_vv)

            vv.parent = self
            self._values.append(vv)

        self._values.sort(key = lambda vv: vv.start_time)

    def _set_default(self, value):
        if value is None:
            self._default = None
        else:
            varval = _to_variable_values(value, self.config.value_transform_fn)
            if len(varval) != 1:
                raise Exception("Can't set default value to a value series")
            self._default = varval[0]
            self._default.parent = self

    def get_value(self, external_lookup=True):
        """Returns the value. If value is not set the default value is used
        instead. If the default value is not set a _get_{name}
        function will be looked for in the parent node and called
        without arguments. If no function is found None is returned.

        If external_lookup is False this method will not attempt to
        find _get_{name} functions in parent objects. This is to allow
        non-recursive calls from within those methods.

        """
        val = None

        if len(self._values) == 1:
            val = self._values[0].get_value()

        elif len(self._values) > 1:
            val = _get_value(self, state.local_time)

        elif self._default is not None:
            val = self._default.get_value()

        elif self.parent is not None and external_lookup:
            f = getattr(self.parent, '_get_' + self.config.name, None)
            if f is not None:
                val = f()

        return self.value_transform_fn(val)

    def get_all_variable_values(self):
        return self._values

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.set('values', [varval.to_simple() for varval in self._values])
        return s

    @staticmethod
    def from_simple(s, obj):
        common.Node.from_simple(s, obj)
        obj._values = [VariableValue.from_simple(common.Simple.from_data(s, varval_data))
                       for varval_data in s.get('values')]
        return obj

#--------------------------------------------------
# variable values

def _to_variable_values(value, value_transform_fn=None):
    if isinstance(value, VariableValue):
        if value_transform_fn:
            value.value = value_transform_fn(value.value)
        return [value]

    elif isinstance(value, expression.Expression):
        return [ExpressionValue(value)]

    elif isinstance(value, dict):
        varvals = []
        for k in value:
            new_varvals = _to_variable_values(value[k], value_transform_fn)
            for nvv in new_varvals:
                nvv.start_time = k
            varvals.extend(new_varvals)
        return varvals

    else:
        if value_transform_fn:
            value = value_transform_fn(value)
        return [StaticValue(value)]

def make_val(value, *args):
    kwargs = {}

    for x in args:
        if isinstance(x, (str, TimeValueType)):
            kwargs['time_type'] = common.to_enum(x, TimeValueType)

        elif isinstance(x (int, float)):
            kwargs['time'] = x

    varval = None
    if isinstance(value, expression.Expression):
        varval = ExpressionValue(value, **kwargs)
    else:
        varval = StaticValue(value, **kwargs)

    return varval

class TimeValueType(enum.Enum):
    NONE = 0
    LINEAR = 1
    CURVE = 2
    BOUNDED_CURVE = 3
    LOOSE_CURVE = 4

class VariableValue(common.Node):
    def __init__(self, time=None, time_type=None):
        common.Node.__init__(self)
        self.start_time = time
        self.time_type = time_type or TimeValueType.LINEAR

    def get_value(self):
        raise NotImplementedError()

    def to_simple(self):
        s = common.Simple()
        s.merge_super(common.Node, self)
        s.set('start_time', self.start_time)
        s.set('time_type', self.time_type)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            return cls.from_simple(s)
        else:
            common.Node.from_simple(s, obj)
            obj.start_time = s.get('start_time')
            obj.time_type = TimeValueType.__members__[s.get('time_type')]
            return obj

class StaticValue(VariableValue):
    def __init__(self, value, **kwargs):
        VariableValue.__init__(self, **kwargs)
        self.value = value

    def get_value(self):
        return self.value

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(VariableValue, self)
        s.set('value', self.value)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = StaticValue(None)
        VariableValue.from_simple(s, obj)
        obj.value = s.get('value')
        return obj

class ExpressionValue(VariableValue):
    def __init__(self, expression, **kwargs):
        VariableValue.__init__(self, **kwargs)
        self.expression = expression

    def get_value(self):
        return self.expression.evaluate()

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(VariableValue, self)
        s.set('expression', self.expression.to_simple())
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = ExpressionValue(None)
        VariableValue.from_simple(s, obj)
        obj.expression = expression.Expression.from_simple(
            s.get_simple('expression'))
        return obj

#--------------------------------------------------
# continuous values

def _get_value(var, time=0):
    values = var._values
    index = _get_varval_index_at_time(values, time)

    if index == -1:
        return values[0].get_value()

    varval = values[index]
    tt = values[index].time_type

    if tt == TimeValueType.NONE:
        return varval.get_value()

    elif tt == TimeValueType.LINEAR:
        return _get_linear_value(values, index, time)

    elif (tt == TimeValueType.CURVE or
          tt == TimeValueType.BOUNDED_CURVE or
          tt == TimeValueType.LOOSE_CURVE):
        return _get_curve_value(values, index, time)

    else:
        raise Exception(f"Unknown time_type value {tt}")

def _get_varval_index_at_time(values, time):
    """Returns the index of the varval active at the given time. Returns
    -1 if the time is before any varval."""
    if time < values[0].start_time:
        return -1

    result = 0
    for index, varval in enumerate(values):
        if varval.start_time > time:
            break
        else:
            result = index

    return result

def _get_linear_value(values, index, time):
    if index == len(values) - 1:
        return values[index].get_value()

    varval = values[index]
    right = values[index + 1]

    duration = right.start_time - varval.start_time
    factor = (time - varval.start_time) / duration
    start_value = varval.get_value()
    change = right.get_value() - start_value

    return start_value + change * factor

def _get_curve_value(values, index, time):
    if index == len(values) - 1:
        return values[index].get_value()

    xs = []
    ys = []
    for varval in values:
        xs.append(varval.start_time)
        # TODO getting value like this wont work for dynamic values;
        # time used will be current time
        ys.append(varval.get_value())

    varval = values[index]

    if varval.time_type == TimeValueType.CURVE:
        ip = interpolate.Akima1DInterpolator(xs, ys)
    elif varval.time_type == TimeValueType.BOUNDED_CURVE:
        ip = interpolate.PchipInterpolator(xs, ys)
    elif varval.time_type == TimeValueType.LOOSE_CURVE:
        ip = interpolate.CubicSpline(xs, ys)
    else:
        raise ValueError("Unknown TimeValueType for curve function: %s" % str(varval.time_type))

    return ip(time)
