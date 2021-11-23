from cpkt.icehelper import ice_interface


@ice_interface.register('foo_func_ice', 'inputchecker', 'outputchecker')
def foo_func():
    return 'hello world'
