from cpkt.core import xpopen as xp


def _test_cmd(cmd, timeout=None, shell=True, input_string=None):
    print('\n', '-' * 30, "cmd:【{}】".format(cmd), '-' * 30, '\n')
    r_1, out_1, err_1 = xp.execute_cmd(cmd, timeout, shell, input_string)
    print('ret_code:\t', r_1)
    print('out_type:\t', type(out_1))
    print('out:\t', out_1)
    print('err:\t', err_1)
    print('\n')


def x(a, b=None, **kwargs):
    print('x ---- begin')
    print(a)
    print(b)
    print(kwargs)
    print('x ---- end')


if __name__ == '__main__':

    # windows
    _test_cmd('ping')
    # test_cmd('ping www.baidu.com', timeout=1)
    # test_cmd('ping www.baidu.com', shell=False)  # 修正shell=True
    _test_cmd(['dir', ])
    # test_cmd('echo input_some_data_2_this_file>./test.txt')
    # test_cmd('mysql -u root -p root', timeout=3, input_string='123456\r\n')  # 错误，输入的字符串并定向到了mysql进程

    # linux
    # test_cmd('gdisk', input_string='/home\n')

    import time
    x('1')
    x('2', 'n')
    x('3', 'n', yyy='k')
    x('4', 'n', yyy='k', zzz='q')
    _timer = xp.delay_execute_cmd(1, r'mkdir C:\temp\test', )
    time.sleep(5)
