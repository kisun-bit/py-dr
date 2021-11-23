import os
import sys

# 将PRC接口模块加入加载模块路径
current_dir = os.path.split(os.path.realpath(__file__))[0]
ice_dir = os.path.join(current_dir, 'ice')
sys.path.append(ice_dir)
