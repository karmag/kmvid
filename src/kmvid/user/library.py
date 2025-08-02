import kmvid.data.common as common
import kmvid.data.resource as resource

import enum
import logging
import operator
import os
import os.path
import sys
import threading
import time
import uuid

logger = logging.getLogger(__name__)

class StepType(enum.Enum):
    LIGHT = 1
    HEAVY = 2

class Library(common.Simpleable, threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self._items = {} # id -> Item
        self._root_entry = FolderEntry(name="root")

        # worker variables
        self._running = False
        self._queue_light = []
        self._queue_heavy = []

    def get_item(self, id):
        """Returns the item or None if no corresponding item exits."""
        return self._items.get(id, None)

    def add_item(self, item):
        """Adds the item to the library. If a corresponding item already
        exists the item is not added. Returns the item that is stored
        in the library.

        """
        self._items[item.id] = item
        self._queue_light.append(item)
        return item

    def get_root(self):
        """Returns the entry representing the root for this library."""
        return self._root_entry

    def add_file(self, path, recursive=True):
        """Adds the file(s) to the library. Returns an Entry representing the
        files added. If no useable files are found None is returned.
        Descends recursively into directories if specified. If path is
        a directory and recursive is false only the directory and
        files directly under it are included.

        """
        assert os.path.exists(path)

        entry = None

        if os.path.isdir(path):
            name = os.path.basename(path)
            if name == '':
                head, _ = os.path.split(path)
                _, name = os.path.split(head)

            entry = FolderEntry(name)
            for filename in os.listdir(path):
                sub_path = os.path.join(path, filename)
                if os.path.isdir(sub_path) and not recursive:
                    continue

                sub_entry = self.add_file(sub_path, recursive=recursive)
                if sub_entry:
                    entry.add_entry(sub_entry)

        elif resource.is_recognized_format(path):
            item = FileItem(path)
            item = self.add_item(item)
            entry = ItemEntry(item=item)

        if entry and entry.is_branch() and len(entry.get_entries()) == 0:
            return None
        else:
            return entry

    def search_items(self, query):
        """Returns an iterator of items that match the given query. Query
        function takes an item and returns true/false. If query is
        None all items are returned.

        """
        if query is None:
            return self._items.values()
        return filter(get_query_function(query), self._items.values())

    def await_all(self, report=False):
        """Blocks until all queued items have finished processing. If the
        thread is running, wait for all items to be processed.
        Otherwise processes the items itself.

        """
        def report_fn():
            if report:
                print("Light:", len(self._queue_light),
                      "  Heavy:", len(self._queue_heavy))

        while (self._running and
               len(self._queue_light) > 0 and
               len(self._queue_heavy) > 0):
            time.sleep(1)
            report_fn()

        t = time.time()
        while self._step_one():
            now = time.time()
            if now - t > 1:
                t += 1
                report_fn()
        report_fn()

    def _step_one(self, force=False):
        """Takes in step in processing available items. Returns True if an
        item was processed or False if there was no work to be done.

        """
        if len(self._queue_light) > 0:
            item = self._queue_light.pop()
            self._queue_heavy.append(item)
            item.run_step(StepType.LIGHT, force)
            return True

        elif len(self._queue_heavy) > 0:
            item = self._queue_heavy.pop()
            item.run_step(StepType.HEAVY, force)
            return True

        else:
            return False

    def run(self):
        while self._running:
            try:
                if not self._step_one():
                    time.sleep(1)
            except Exception as e:
                logger.warn("Library item processing error: %s", e)

    def __enter__(self):
        self._running = True
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._running = False
        self.join(timeout=10)

    def to_simple(self):
        s = common.Simple(self)
        s.set('items', [item.to_simple() for item in self._items.values()])
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Library()

        for item in s.get('items', []):
            item_simple = common.Simple.from_data(s, item)
            obj._items[item['id']] = Item.from_simple(item_simple)

        return obj

class FromFile:
    """FromFile provides convenience functionality for creating a library
    that is stored on file for scripts. Populating the library may be
    a slow operation. FromFile creates a save file and performs all
    the necessary computations on the first invokation, but will just
    read the file on sub-sequent invokations.

    FromFile mimics certain methods from Library which should be used
    for setting it up. Since these are dummy implementations they will
    not contain proper data when reading from file and setup code
    should be written with this in mind.

    Once 'get' is called to retrieve the actual library it is stored
    as such and further changes are not reflected on sub-sequent
    invokations.

    To re-setup the library to account for changes: delete the file.

        import kmvid.user.library as library

        ff = library.FromFile("my_project_library.json")
        ff.add_path("path/to/media/1")
        ff.add_path("path/to/media/2")
        for item in ff.search_items(...):
            item.set_tag('key', 'value')

        lib = ff.get()

    """

    def __init__(self, path="library.json"):
        self._path = path
        self._library = None
        self._exists = False

        if os.path.exists(self._path):
            self._library = Library.from_simple(common.Simple.load_file(self._path))
            self._exists = True
        else:
            self._library = Library()

    def add_item(self, item):
        if self._exists:
            return Item()
        else:
            return self._library.add_item(item)

    def get_root(self):
        if self._exists:
            return FolderEntry()
        else:
            return self._library.get_root()

    def add_file(self, path, recursive=True):
        if self._exists:
            return FolderEntry()
        else:
            return self._library.add_file(path, recursive)

    def search_items(self, query_fn):
        if self._exists:
            return []
        else:
            return self._library.search_items(query_fn)

    def await_all(self, report=False):
        if self._exists:
            return
        else:
            return self._library.await_all(report)

    def get(self, report=False):
        """Returns the library."""
        if not self._exists:
            self._library.await_all(report)
            self._library.to_simple().save_file(self._path)
        return self._library

def __operator_wrapper(op, default=None):
    def wrapper(item, *args):

        old_args = args
        args = []
        for a in old_args:
            value = a(item)
            if value is None:
                value = default
            args.append(value)

        if len(args) <= 2:
            return op(*args)

        value = op(args[0], args[1])
        for more in args[2:]:
            value = op(value, more)
        return value

    return wrapper

__QUERY_MAPPING__ = {
    # logical operators
    "="   : __operator_wrapper(operator.eq),
    "/="  : __operator_wrapper(operator.ne),
    "<"   : __operator_wrapper(operator.lt, 0),
    "<="  : __operator_wrapper(operator.le, 0),
    ">"   : __operator_wrapper(operator.gt, 0),
    ">="  : __operator_wrapper(operator.ge, 0),
    "not" : __operator_wrapper(operator.not_),
    "and" : __operator_wrapper(lambda a, b: a and b),
    "or"  : __operator_wrapper(lambda a, b: a or b),

    # math operators
    "+"   : __operator_wrapper(operator.add, 0),
    "-"   : __operator_wrapper(operator.sub, 0),
    "*"   : __operator_wrapper(operator.mul, 0),
    "/"   : __operator_wrapper(operator.truediv, 0),
    "abs" : __operator_wrapper(operator.abs, 0),
    "pow" : __operator_wrapper(operator.pow, 0),
    "mod" : __operator_wrapper(operator.mod, 0),

    "contains" : __operator_wrapper(
        lambda string, search: string.lower().find(search.lower()) != -1)
}

def get_query_function(expression):
    if callable(expression):
        return expression

    if isinstance(expression, (list, tuple)):
        if len(expression) == 0:
            raise ValueError("Expression sequence containing 0 elements")

        f = None
        args = []

        if expression[0] in __QUERY_MAPPING__:
            f = __QUERY_MAPPING__[expression[0]]
        else:
            raise ValueError("First element in expression sequence must be a function reference: %s" % str(expression))

        args = [get_query_function(x) for x in expression[1:]]

        return lambda item: f(item, *args)

    elif isinstance(expression, (int, float)):
        return lambda item: expression

    elif isinstance(expression, str):
        if expression.startswith("."):
            return lambda item: item.get_tag(expression[1:])
        else:
            return lambda item: expression

    else:
        raise ValueError("Unknown expression value: %s" % str(expression))

def query_as_string(expression):
    result = ""
    if isinstance(expression, (list, tuple)):
        result += "("
        for i, x in enumerate(expression):
            if i > 0:
                result += " "
            result += query_as_string(x)
        result += ")"
    elif (isinstance(expression, str) and
          not expression.startswith(".") and
          expression not in __QUERY_MAPPING__):
        result += '"' + expression + '"'
    else:
        result += str(expression)
    return result

class Item(common.Simpleable):
    def __init__(self, id=None, name=""):
        common.Simpleable.__init__(self)

        self.id = id or uuid.uuid4()
        self._tags = {}
        self._static_tags = {}

        self.set_tag('name', name)

    def set_tag(self, name, value=True):
        self._tags[name] = value

    def remove_tag(self, name):
        del self._tags[name]

    def get_tag(self, name):
        if name in self._static_tags:
            return self._static_tags[name]
        return self._tags.get(name, None)

    def run_step(self, step, force=False):
        pass

    def to_simple(self):
        s = common.Simple(self)
        s.set('id', self.id.hex)
        s.set('tags', self._tags)
        s.set('static_tags', self._static_tags)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            if cls.__dict__.get('from_simple', None):
                obj = cls.from_simple(s)
            else:
                obj = cls()

        obj.id = uuid.UUID(s.get('id'))
        obj._tags = s.get('tags')
        obj._static_tags = s.get('static_tags')
        return obj

class FileItem(Item):
    def __init__(self, path=None):
        Item.__init__(self)

        if path:
            self.set_tag('name', os.path.basename(path))
            self._static_tags['path'] = path

        self._resource = None

    def run_step(self, step, force=False):
        if step == StepType.LIGHT:
            if force or 'width' not in self._static_tags:
                if self._resource is None:
                    self._resource = resource.from_file(self.get_tag('path'))
                info = self._resource.get_info()
                for name in ['width', 'height', 'duration', 'fps']:
                    self._static_tags[name] = info.__dict__[name]

            if force or 'size' not in self._static_tags:
                self._static_tags['size'] = os.path.getsize(self.get_tag('path'))

        if step == StepType.HEAVY:
            # TODO hash
            pass

class Entry(common.Simpleable):
    def __init__(self):
        self._name = "unnamed"
        self._parent = None

    def _initialize(self, library):
        pass

    def get_name(self):
        return self._name

    def get_parent(self):
        return self._parent

    def is_branch(self):
        return False

    def get_entries(self):
        return []

    def add_entry(self, entry):
        raise NotImplementedError()

    def remove_entry(self, entry):
        raise NotImplementedError()
    
    def get_item(self):
        return None

    def pprint(self, indent = 0):
        ind = "    " * indent
        print("%s%s%s" % (ind,
                          self.get_name(),
                          " (branch)" if self.is_branch() else ""))
        for entry in self.get_entries():
            entry.pprint(indent + 1)

class FolderEntry(Entry):
    def __init__(self, name="folder"):
        Entry.__init__(self)
        self._name = name
        self._entries = []

    def _initialize(self, library):
        pass

    def is_branch(self):
        return True

    def get_entries(self):
        return self._entries

    def add_entry(self, entry):
        assert entry._parent is None
        entry._parent = self
        self._entries.append(entry)

    def remove_entry(self, entry):
        self._entries.remove(entry)
        entry._parent = None

class ItemEntry(Entry):
    def __init__(self, name=None, item=None):
        Entry.__init__(self)
        self._name = name
        self._item_id = item.id if item else None
        self._item = item

    def _initialize(self, library):
        if self._item_id:
            self._item = library.get_item(self._item_id)

    def get_name(self):
        if self._name is None and self._item:
            return self._item.get_tag('name')
        return self._name

    def get_item(self):
        return self._item
