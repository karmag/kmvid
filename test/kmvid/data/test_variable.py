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

def quick_variable(value):
    cfg = variable.VariableConfig(vartype=int)
    var = variable.Variable(cfg)
    var.set_value(value)
    return var

class TestVariable(testbase.Testbase):
    def test_multivalue_variable(self):
        var = quick_variable({0: 10, 1: 20, 2: 100})

        self.assertEqual(10, var.get_value())

        with state.State():
            self.assertEqual(10, var.get_value())
            state.set_time(1)
            self.assertEqual(20, var.get_value())
            state.set_time(2)
            self.assertEqual(100, var.get_value())

    def test_override_old_value(self):
        # single
        var = quick_variable(5)
        var.add_value(10)
        self.assertEqual(10, var.get_value())

        # multi
        var = quick_variable({0: 10, 1: 20})
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
        var = quick_variable({0: 0, 1: 10, 2: 100})

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

    def test_setting_values(self):
        def getval(type, value):
            cfg = variable.VariableConfig(vartype=type)
            var = variable.Variable(cfg)
            var.set_value(value)
            return var.get_value()

        test_data = [
            ((int, 5), 5),
            ((int, 7.5), 7),
            ((int, "6"), 6),
            ((int, None), None),
            ((float, 1), 1),
            ((float, 2.5), 2.5),
            ((float, "3"), 3),
            ((float, None), None),
            ((str, "hello"), "hello"),
            ((str, 123), "123"),
            ((str, None), None),
            (("time", 10), 10),
            (("time", 15.2), 15.2),
            (("time", "11ms"), 0.011),
            (("time", "12s"), 12),
            (("time", "1m"), 60),
            (("time", "1h"), 60*60),
            (("time", " 2 4m 1.5 500ms"), 2 + 4*60 + 1.5 + 0.5),
            (("time", "1h3s"), 60*60+3),
            (("time", "4-3m"), 4-3*60),
            ((EnumTest, EnumTest.DEF), EnumTest.DEF),
            ((EnumTest, "def"), EnumTest.DEF),
            ((EnumTest, 2), EnumTest.DEF),
        ]

        for args, expected in test_data:
            with self.subTest(args=args, expected=expected):
                self.assertEqual(getval(*args), expected)

    def test_make_val(self):
        var = variable.make_val("abc", 5, "linear")
        self.assertEqual(var.get_value(), "abc")
        self.assertEqual(var.start_time, 5)
        self.assertEqual(var.time_type, variable.TimeValueType.LINEAR)

        var = variable.make_val(45, None, 10)
        self.assertEqual(var.get_value(), 45)
        self.assertEqual(var.start_time, 10)
        self.assertEqual(var.time_type, variable.TimeValueType.NONE)

        var = variable.make_val(('+', 'time', 22), "none", 5, "linear", 10)
        self.assertEqual(var.get_value(), 22)
        self.assertEqual(var.start_time, 10)
        self.assertEqual(var.time_type, variable.TimeValueType.LINEAR)

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
