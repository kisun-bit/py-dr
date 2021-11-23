class ClwErrorStatus(object):
    # 0和正数为保留错误，不得使用。因为可能是以前抛异常时，没有抛错误代码。
    # 为了跟系统抛的异常错误码区分。我们的错误码全是0x10000000之后的。32位系统也能使用。

    UNKNOW_BUG = 0x12345678

    # dss模块的错误码 0x10010001 - 0x10020000：
    DSS_WRITE_TWINCE            = 0x10010001    # 居然对一个文件写2次。
    DSS_NO_FREE_PORT            = 0x10010002    # 没有可用的端口资源，等待重试。
    DSS_CREATE_NEW_SNAPSHOT_ERR = 0x10010003    # 创建快照文件失败。原因未知，后面会细化原因。
    DSS_NO_IMGIO_TO_CONNECT     = 0x10010004    # imgio进程无法连接。
    DSS_SAME_RAW_HANDLE         = 0x10010005    # imgio返回了相同的 raw_handle，内部错误。
    DSS_STORE_OFFLINE           = 0x10010006    # 存储节点已经超时离线。
    DSS_CAN_NOT_ACCESS_STORE    = 0x10010007    # 无法访问到存储节点，或存储节点已经移除。
    DSS_UPDATE_QEMU_IMG_VER     = 0x10010008    # 备份数据文件句柄无效，请检查镜像服务版本
    DSS_CLOSE_INVALID_HANDLE    = 0X10010009    # 尝试关闭一个无效句柄。
    
    

    # ice 相关错误 0x10020001 - 0x10030000:
    ICE_RPC_FAILED = 0x10020001  # ice rpc 调用失败，发生非自定义的ICE异常，一般为网络问题
    ICE_RPC_FAILED_MSG = '内部异常，网络通信失败'
    ROUTER_RELAY_FAILED = 0x10020002  # router rpc 转发时，发生非自定义的ICE异常，一般为网络问题
    ROUTER_RELAY_FAILED_MSG = '内部异常，网络通信失败'
    ROUTER_ANALYZE_TARGET_FAILED = 0x10020003  # router rpc 无法解析转发目标，一般为转发目标不在定义中
    ROUTER_ANALYZE_TARGET_FAILED_MSG = '内部异常，服务定义无效'
    ROUTER_ANALYZE_CALL_FAILED = 0x10020004  # router rpc 无法解析需要调用的方法
    ROUTER_ANALYZE_CALL_FAILED_MSG = '内部异常，方法定义无效'

    # dashboard 相关错误 0x10030001 - 0x10040000:
    DASHBOARD_TOKEN_INVALID = 0x10030001  # token 无效，不应该重试
