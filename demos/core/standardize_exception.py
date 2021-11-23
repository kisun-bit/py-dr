from cpkt.core import exc

try:
    raise exc.generate_exception_and_logger('msg to user', 'msg to rd', 9)
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))

try:
    assert 1 == 0, ('msg to user', 'msg to rd', 8)
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))

try:
    assert 1 == 0, ('msg to user', 'msg to rd',)
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))

try:
    assert 1 == 0, 'msg to rd'
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))

try:
    assert 1 == 0
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))

try:
    assert 1 / 0
except Exception as e:
    ee = exc.standardize_exception(e)
    print('{} | {} | {}'.format(ee.description, ee.debug, ee.rawCode))
