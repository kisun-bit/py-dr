from cpkt.core import rt


def func_name():
    print('{2} {0} {1}'.format(*rt.get_back_function_info(0)))


func_name()
