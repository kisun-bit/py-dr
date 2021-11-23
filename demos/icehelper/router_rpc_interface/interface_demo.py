import threading
import time

from marshmallow import Schema, fields, post_load, validate

from cpkt.icehelper import ice_interface
from cpkt.icehelper import router_rpc as rr

Length = validate.Length


##########################################
# 简单调用
@ice_interface.register('hello_world')
def hello_world_func(params: dict, sender):
    """没有序列化器检查器就需要加入详细的文档说明输入与输出

    :param params:
        {
            'in': str
        }
    :param sender:
    :return:
        {
            'out': str
        }
    """
    print('\n--------\ni am in hello_world_func\nsender: {}\n--------\n'.format(sender))
    return {'out': 'hello world: {}'.format(params['in'])}


##########################################
# 递归调用 + 输入数据反序列化器 + 返回数据序列化器

class RecursiveCallbackParams(object):
    def __init__(self, count):
        self.count = count  # 递归调用剩余次数


class RecursiveCallbackSchema(Schema):
    count = fields.Integer(required=True)

    @post_load
    def make_params(self, data):
        return RecursiveCallbackParams(**data)


class RecursiveCallbackResultSchema(Schema):
    count = fields.Integer(required=True)  # 递归调用剩余次数


@ice_interface.register('recursive_callback', RecursiveCallbackSchema, RecursiveCallbackResultSchema)
def recursive_callback(params: RecursiveCallbackParams, sender):
    """递归 callback : 每次调用 count 都减1， 直到小于等于0
    """
    count = params.count
    print('\n--------\ni am in recursive_callback count: {}\n--------\n'.format(count))
    count -= 1
    if count > 0:
        rr.rpc.op(sender, 'recursive_callback', {'count': count})


#########################################
# 异步回调 + 输入数据反序列化器
class HelloWorldCallbackParams(object):
    def __init__(self, msg, delay):
        self.msg = msg
        self.delay = delay


class HelloWorldCallbackSchema(Schema):
    msg = fields.String(required=True, validate=Length(max=512, min=1))
    delay = fields.Integer(required=True)

    @post_load
    def make_params(self, data):
        return HelloWorldCallbackParams(**data)


@ice_interface.register('hello_world_callback', HelloWorldCallbackSchema)
def hello_world_callback(params: HelloWorldCallbackParams, sender):
    threading.Thread(target=hello_world_report, args=(params.msg, params.delay, sender,)).start()
    print('\n--------\ni am in hello_world_callback\nsender: {}\n--------\n'.format(sender))


def hello_world_report(msg, delay, sender):
    time.sleep(delay)
    rr.rpc.op(sender, 'hello_world_report', {'out': msg})
