import os
from unittest.mock import patch

from cpkt.core import rt
from cpkt.tmpfile import client
from cpkt.tmpfile import common
from cpkt.tmpfile import server

# 临时(测试)文件路径
current_dir = os.path.split(os.path.realpath(__file__))[0]
DIR_FOR_TEST = os.path.join(current_dir, 'TestFiles')
tmp_file_path = os.path.join(DIR_FOR_TEST, 'test_client.txt')

# 三种测试情况
OPERATIONS = {
    'DoNothing': 0,
    'Cancel': 1,
    'Confirm': 2
}


# 获取记录
def get_record_dict_by_index(index: int) -> dict:
    record = server.persistence_manager.read(index)
    return common.RecordManipulate.record_parse(record)


# mock 函数, 获取 server 返回值
def get_server_return(*params):

    _ = params
    return server.ApiForClient().add(
        file_path=tmp_file_path,
        pid=client.pid,
        caller_msg='',
        pid_create_timestamp=client.pid_create_timestamp,
        delete_timestamp=common.EMPTY_TIMESTAMP_STR
    )


# 测试环境回滚: 清理临时文件, 擦除 record
def rollback(file_path, index):
    rt.delete_file(file_path)
    server.persistence_manager.erase(index)


# 测试夹具, 通过参数operation, 区分测试情况
def _test_box(operation, caller_msg=None):
    assert operation in OPERATIONS.values()

    # 添加临时文件
    with open(tmp_file_path, "w"):
        pass

    # with 上下文中，校验 status、change_timestamp
    with client.TmpFile(tmp_file_path, 0, caller_msg) as task:
        record_dict = get_record_dict_by_index(task.index)
        assert record_dict['status'] == common.STATUS_UNKNOWN
        assert record_dict['change_timestamp'] == common.EMPTY_TIMESTAMP_STR

        # 取消删除，校验 status 以及文件确实未被删除
        if operation == OPERATIONS['Cancel']:
            task.cancel_delete()
            record_dict = get_record_dict_by_index(task.index)
            assert record_dict['status'] == common.STATUS_NOT_DELETE
            assert os.path.exists(tmp_file_path)

        # 确认删除
        elif operation == OPERATIONS['Confirm']:
            task.confirm_delete()
            record_dict = get_record_dict_by_index(task.index)
            assert record_dict['status'] == common.STATUS_WAIT_DELETE
        else:
            pass

    # 回滚测试环境
    rollback(tmp_file_path, task.index)
    server.persistence_manager.erase(task.index)


@patch.object(target=client.TmpFile, attribute="_parse_server_return", new=get_server_return)
def test_auto_set_delete():
    """测试：取消删除"""

    _test_box(OPERATIONS['DoNothing'], caller_msg='msg')


@patch.object(target=client.TmpFile, attribute="_parse_server_return", new=get_server_return)
def test_cancel_delete():
    """测试：取消删除"""

    _test_box(OPERATIONS['Cancel'])


@patch.object(target=client.TmpFile, attribute="_parse_server_return", new=get_server_return)
def test_confirm_delete():
    """测试:确认删除"""

    _test_box(OPERATIONS['Confirm'])
