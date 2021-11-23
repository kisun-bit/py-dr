from cpkt.core import bitmap

data = b'\x00\xF1\x8F'

b = bitmap.BitMap(data, 19)

for i in b.enum_nonzero():
    print('{}'.format(i))
