from cpkt.core import xdebug as dbg


class C(object):

    @staticmethod
    def sf():
        print('when flag on. sf') if dbg.flag_on() else None

    def f(self):
        _ = self
        print('when flag on. C.f') if dbg.flag_on() else None


def func():
    print('when flag on. func') if dbg.flag_on() else None
    print('always')


t = dbg.XDebugHelper('/home')
t.load_flags()

func()
C.sf()
C().f()
