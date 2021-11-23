## 单元测试指导：
   * 启动项配置：
        参见：tmpfile覆盖率配置.JPG
    1、配置测试环境变量:
        删除test目录下：DelayDelLog.txt
        linux：export TEST_MODE=1
        windows：pycharm启动项设置参数 export TEST_MODE=1
        
    2、执行测试
        1)切换到测试代码所在路径：/root/.pyenv/versions/3.4.4/lib/python3.4/site-packages/cpkt/tmpfile/test
        2)执行测试命令：pytest --cov-report term-missing --cov=/root/.pyenv/versions/3.4.4/lib/python3.4/site-packages/cpkt/tmpfile/
