import io

from cpkt.core import xdebug as dbg


def test_func():
    s = io.StringIO()
    dbg.XDebugHelper.all_thread_stack(s)
    s.seek(0)
    print(s.read())


test_func()
