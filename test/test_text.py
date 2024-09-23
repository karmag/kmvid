import testbase

import kmvid.data.text as text

class TestText(testbase.Testbase):
    def test_split_fn(self):
        self.assertEqual([x for x in text._split_on_space("a b c")],
                         [("a", "b c"),
                          ("a b", "c")])

        self.assertEqual([x for x in text._split_on_space("a bc  ")],
                         [("a", "bc  "),
                          ("a bc", " "),
                          ("a bc ", "")])
