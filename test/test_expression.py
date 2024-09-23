import kmvid.data.expression as expression
import kmvid.data.state as state

import testbase

class TestExpression(testbase.Testbase):
    def test_math(self):
        for expected, form in [(15, ('+', 5, 10)),
                               (10, ('-', 40, 10, 15, 5)),
                               (20, ('*', 2, 10)),
                               (5, ('/', 50, 10)),
                               ]:
            with self.subTest(expected=expected, form=form):
                self.assertEqual(expected,
                                 expression.parse(form).evaluate())

    def test_time(self):
        with state.State():
            state.time = 5
            self.assertEqual(5, expression.parse('global-time').evaluate())
            self.assertEqual(5, expression.parse('time').evaluate())
