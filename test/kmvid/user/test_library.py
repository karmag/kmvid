import kmvid.user.library as library

import testbase

class TestResourceLibrary(testbase.Testbase):
    def _get_library(self):
        lib = library.Library()

        for i in range(10):
            item = library.Item()
            item.set_tag('prio', i)
            item.set_tag('always')
            if i % 2 == 0:
                item.set_tag('sometimes')
            if i % 3 == 0:
                item.set_tag('text', "text-%d" % i)
            lib._items[item.id] = item

        return lib

    def test_x(self):
        lib = self._get_library()

        for expected, query in [(10, ".always"),
                                ( 5, ".sometimes"),
                                ( 0, ".never"),

                                ( 1, ("=", ".prio", 4)),
                                ( 9, ("/=", ".prio", 4)),
                                ( 3, ("<", ".prio", 3)),
                                ( 4, ("<=", ".prio", 3)),
                                ( 3, (">", ".prio", 6)),
                                ( 4, (">=", ".prio", 6)),

                                ( 5, ("and", ".always", ".sometimes")),
                                ( 5, ("and", ".sometimes", ".always")),
                                (10, ("or", ".always", ".sometimes")),
                                (10, ("or", ".sometimes", ".always")),
                                ( 9, ("not", ("=", ".prio", 2))),

                                ( 4, ("<", 15, ("+", 10, ".prio"))),

                                ( 1, ("=", "text-0", ".text")),
                                ( 5, ("=", ".sometimes", True)),
                                ]:
            with self.subTest(expected=expected,
                              query=library.query_as_string(query)):
                qf = library.get_query_function(query)
                self.assertEqual(expected,
                                 len([x for x in lib.search_items(qf)]))
