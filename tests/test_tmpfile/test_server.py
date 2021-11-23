# -*- coding: utf-8 -*-
import os
import time
from unittest.mock import patch, MagicMock

import pytest

from cpkt.core import rt
from cpkt.tmpfile import client
from cpkt.tmpfile import common
from cpkt.tmpfile import server
from . import test_client

# 临时(测试)文件路径
current_dir = os.path.split(os.path.realpath(__file__))[0]
DIR_FOR_TEST = os.path.join(current_dir, 'TestFiles')


def _add_task(pid: int, pid_create_timestamp: int, status: int, file_path: str, delete_timestamp):
    """创建任务"""

    # 添加文件
    open(file_path, "w")
    assert os.path.exists(file_path)

    # 添加日志记录
    return server.ApiForClient().add(
        pid=pid,
        status=status,
        file_path=file_path,
        caller_msg="caller_msg",
        delete_timestamp=delete_timestamp,
        pid_create_timestamp=pid_create_timestamp,
    )


# 记录是否擦除
def _is_record_erased(index: int) -> bool:
    return server.persistence_manager.is_empty(index)


# 文件是否删除
def _is_file_deleted(file_path: str) -> bool:
    return not os.path.exists(file_path)


# 处理任务
def _deal_task(index: int):
    record = server.persistence_manager.read(index)
    server.Worker(idx=index, record=record, pm=server.persistence_manager).work()


# 测试夹具
def _test_box(file_path, status, caller_msg, pid, pid_create_timestamp, del_timestamp, is_record_erased: bool,
              is_file_deleted: bool):
    with open(file_path, "w"):
        pass

    # 创建任务
    index, _ = server.ApiForClient().add(
        pid=pid,
        status=status,
        file_path=file_path,
        caller_msg=caller_msg,
        delete_timestamp=del_timestamp,
        pid_create_timestamp=pid_create_timestamp,
    )

    # 处理任务
    assert not server.persistence_manager.is_logfile_empty()
    _deal_task(index)

    # 校验结果
    assert _is_record_erased(index) == is_record_erased
    assert _is_file_deleted(file_path) == is_file_deleted

    # 回滚测试环境
    test_client.rollback(file_path, index)


def test_status_not_delete():
    """测试处理状态为 STATUS_NOT_DELETE 的情况"""

    _test_box(
        caller_msg=' ' * 510,  # 伪造的caller_msg，为了测试字符串超长的情况
        pid=client.pid,
        is_file_deleted=False,
        is_record_erased=True,
        del_timestamp=int(time.time()),
        status=common.STATUS_NOT_DELETE,
        pid_create_timestamp=client.pid_create_timestamp,
        file_path=os.path.join(DIR_FOR_TEST, 'test_status_not_delete.txt'),
    )


def test_status_wait_delete_and_time_to_delete():
    """测试处理状态为 STATUS_WAIT_DELETE，且已设置删除时间，且删除时间已到的情况"""

    _test_box(
        caller_msg='',
        pid=client.pid,
        is_file_deleted=True,
        is_record_erased=True,
        del_timestamp=int(time.time()),
        status=common.STATUS_WAIT_DELETE,
        pid_create_timestamp=client.pid_create_timestamp,
        file_path=os.path.join(DIR_FOR_TEST, 'test_status_wait_delete_and_time_to_delete.txt'),
    )


def test_status_unknown_pid_not_exist_2():
    """测试状态为 UNKNOWN，且调用者进程已死的情况"""

    _test_box(
        caller_msg='',
        pid=10000000,
        is_file_deleted=True,
        is_record_erased=True,
        status=common.STATUS_UNKNOWN,
        del_timestamp=int(time.time()),
        pid_create_timestamp=int(time.time()),
        file_path=os.path.join(DIR_FOR_TEST, 'test_status_unknown_pid_not_exist_2.txt'),
    )


def test_status_unknown_pid_not_exist_1():
    """测试状态为 UNKNOWN，且调用者进程未死，但进程创建时间不一致的情况"""

    _test_box(
        caller_msg='',
        pid=client.pid,
        is_file_deleted=True,
        is_record_erased=True,
        status=common.STATUS_UNKNOWN,
        del_timestamp=int(time.time()),
        pid_create_timestamp=int(time.time()),
        file_path=os.path.join(DIR_FOR_TEST, 'test_status_unknown_pid_not_exist_1.txt'),
    )


@patch.object(target=rt.PathInMount, attribute="is_in_not_mount", new=MagicMock(return_value=True))
def test_is_in_not_mount():
    """测试文件所在目录为挂载目录，但未挂载"""

    _test_box(
        caller_msg='',
        pid=client.pid,
        is_file_deleted=False,  # 文件不应该删除
        is_record_erased=False,  # 记录不应该擦除
        status=common.STATUS_UNKNOWN,
        del_timestamp=int(time.time()),
        pid_create_timestamp=int(time.time()),
        file_path=os.path.join(DIR_FOR_TEST, 'test_is_in_not_mount.txt'))


def test_write_error():
    """测试写入异常"""

    with pytest.raises(Exception):
        wrong_record = "wrong record".encode('utf-8')  # 错误的 record
        available_index, pm = server.index_allocator.get_available_index()
        server.persistence_manager.write(available_index, wrong_record)


def test_not_find_available_index():
    """测试获取可用index失败"""

    with pytest.raises(server.index_allocator.NotFindAvailableIndex):
        for i in range(1, common.MAX_INDEX + 1):
            record = (common.RECORD_VERSION + common.ERASE_STR[1:]).encode('utf-8')
            server.persistence_manager.write(i, record)
        server.index_allocator.get_available_index()
