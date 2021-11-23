from cpkt.icehelper import ice_interface


def main():
    execute_dict = ice_interface.fetch_ice_interface(['tests.test_ice_interface.foo1'])
    i_checker, f, o_checker = execute_dict['foo_func_ice']
    assert i_checker == 'inputchecker'
    assert o_checker == 'outputchecker'
    assert f() == 'hello world'


main()
