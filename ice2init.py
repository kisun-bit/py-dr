import os

ice_path = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'cpkt', 'rpc', 'ice')
init_path = os.path.join(os.path.join(os.path.abspath(os.path.dirname(__name__)), 'cpkt', 'rpc', 'ice'), '__init__.py')
dirs = os.listdir(ice_path)


with open(init_path, 'w', encoding='utf-8') as f:
    for i in dirs:
        path = os.path.join(ice_path, i)
        if os.path.isdir(path):
            f.write('import {}\n'.format(i))

