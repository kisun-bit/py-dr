# -*- coding: utf-8 -*-
import os

import pytest

from cpkt.core import rt
from cpkt.tmpfile import server
from cpkt.tmpfile import common

current_dir = os.path.split(os.path.realpath(__file__))[0]


@pytest.fixture(scope='module', autouse=True)
def init_assert_rollback():
    """校验每次测试前，测试环境是干净的;测试完回滚日志文件"""

    tmp_txt_path = os.path.join(current_dir, 'test.txt')
    rt.delete_file(tmp_txt_path)
    common.MAX_INDEX = 128
    server.init_persistence(tmp_txt_path)  # 初始化server
    assert server.persistence_manager.is_logfile_empty()  # 校验日志文件为空
    try:
        yield
    finally:
        server.persistence_manager = None
        server.index_allocator = None
        server.background_thread = None
