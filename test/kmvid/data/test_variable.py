import kmvid.data.clip as clip
import kmvid.data.effect as effect
import kmvid.data.expression as expression
import kmvid.data.variable as variable
import kmvid.data.state as state

import enum
import testbase

class EnumTest(enum.Enum):
    ABC = 1
    DEF = 2

@variable.holder
class ClassTest(variable.VariableHold):
    x = variable.VariableConfig(int)
    enumerati = variable.VariableConfig(EnumTest, EnumTest.ABC)
    def __init__(self, *args, **kwargs):
        variable.VariableHold.__init__(self, args=args, kwargs=kwargs)

def make_variable(name, value):
    cfg = variable.VariableConfig(type=int)
    var = variable.Variable(cfg)
    var.name = name
    var.set_value(value)
    return var

class TestVariable(testbase.Testbase):
    def test_setting_variable(self):
        expected = 5

        for var in [make_variable("static value", expected),
                    make_variable("expression", expression.Value(expected))]:
            self.assertEqual(expected, var.get_value())

    def test_multivalue_variable(self):
        var = make_variable("x", {0: 10, 1: 20, 2: 100})

        self.assertEqual(10, var.get_value())

        with state.State():
            self.assertEqual(10, var.get_value())
            state.set_time(1)
            self.assertEqual(20, var.get_value())
            state.set_time(2)
            self.assertEqual(100, var.get_value())

    def test_override_old_value(self):
        # single
        var = make_variable("x", 5)
        var.add_value(10)
        self.assertEqual(10, var.get_value())

        # multi
        var = make_variable("x", {0: 10, 1: 20})
        var.add_value(30)
        self.assertEqual(2, len(var.get_all_variable_values()))

        self.assertEqual(30, var.get_value())
        with state.State():
            state.set_time(1)
            self.assertEqual(20, var.get_value())

        # add with time
        var.add_value({1: 60, 2: 100})
        self.assertEqual(30, var.get_value())
        with state.State():
            state.set_time(1)
            self.assertEqual(60, var.get_value())
            state.set_time(2)
            self.assertEqual(100, var.get_value())

    def test_time_value_type(self):
        var = make_variable("x", {0: 0, 1: 10, 2: 100})

        # linear (default)
        with state.State():
            for time, expected in [(0, 0),
                                   (0.2, 2),
                                   (0.5, 5),
                                   (1, 10),
                                   (1.5, 55),
                                   (2, 100)]:
                state.set_time(time)
                self.assertEqual(expected, var.get_value())

        # discrete / instant
        for vv in var.get_all_variable_values():
            vv.time_type = variable.TimeValueType.NONE

        with state.State():
            for time, expected in [(0, 0),
                                   (0.2, 0),
                                   (0.5, 0),
                                   (1, 10),
                                   (1.5, 10),
                                   (2, 100)]:
                state.set_time(time)
                self.assertEqual(expected, var.get_value())

    def test_enum_values(self):
        self.assertEqual(EnumTest.DEF, ClassTest(enumerati=EnumTest.DEF).enumerati)
        self.assertEqual(EnumTest.DEF, ClassTest(enumerati="def").enumerati)
        self.assertEqual(EnumTest.DEF, ClassTest(enumerati=2).enumerati)

    def test_expression_values(self):
        with state.State():
            c = clip.color(color=(30, 30, 30), width=100, height=100)
            c.add(
                effect.Draw()
                .config(fill=(255, 255, 255))
                .rectangle(
                    x = expression.parse(('*', 'width', 0.25)),
                    y = expression.parse(('*', 'height', 0.5)),
                    width = expression.parse(('*', 'width', 0.5)),
                    height = expression.parse(('*', 'height', 0.25)),
                )
            )
            self.assertImage("expression_values", c)
