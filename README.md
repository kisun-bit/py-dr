## 公共包
* 数据定义（from cpkt.data import define as dd）
* 基础封装
    * 打印调试日志（from cpkt.core import xlogging as lg）
    * 异常相关(from cpkt.core import exc)
    * 获取运行时信息（from cpkt.core import rt）
    * 调试支持（from cpkt.core import xdebug as dbg）
    * 读写锁（from cpkt.core import rwlock）
* 远程调用接口定义（from cpkt.rpc import ice）
* 临时文件管理
    * 客户端( from cpkt.tmpfile import client as tf )
    * 服务端( from cpkt.tmpfile import server as tmpfile\_server )
* ice封装
    * 提供ICE服务的程序框架（from cpkt.icehelper import application）

## 公司网络中安装
* `/usr/local/python3.6/bin/pip3 install -U cpkt --index http://172.16.1.65:8080 --trusted-host 172.16.1.65 -v --disable-pip-version-check`  
* `pip install -U cpkt --index http://172.16.1.65:8080 --trusted-host 172.16.1.65 -v --disable-pip-version-check`
* `\Python36\Scripts\pip.exe install -U cpkt --index http://172.16.1.65:8080 --trusted-host 172.16.1.65 -v --disable-pip-version-check`

## 编码规范
* 兼容py3.4 与 3.6
* 必要时兼容windows
* 完善的接口注释
* 使用统一的异常基类
* 原则上不输出调试信息
    * 如果需要输出关键路径上的调试信息，需要调用者传入日志输出对象

## 使用者规范
导入包，必须使用本文档中的格式；包括缩写也一样

## 代码片段
* `snippets` 目录