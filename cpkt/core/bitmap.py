BITMASK = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]
BIT_CNT = [bin(i).count("1") for i in range(256)]


class BitMap(object):
    """
    BitMap class
    """

    def __init__(self, bitmap, max_bit_num=None):
        """
        Create a BitMap
        """
        self.bitmap = bitmap
        self.max_bit_num = max_bit_num if max_bit_num else len(bitmap) * 8
        self.max_bytes_num = (self.max_bit_num + 7) // 8
        assert self.max_bytes_num >= (self.max_bit_num + 7) // 8
        self.bit_in_last_byte = self.max_bit_num % 8  # 0 表示正好字节对齐，非0表示最后一个字节中仅有前 n 个位有意义

    def __del__(self):
        """
        Destroy the BitMap
        """
        pass

    def set(self, pos):
        """
        Set the value of bit@pos to 1
        """
        self.bitmap[pos // 8] |= BITMASK[pos % 8]

    def reset(self, pos):
        """
        Reset the value of bit@pos to 0
        """
        self.bitmap[pos // 8] &= ~BITMASK[pos % 8]

    def flip(self, pos):
        """
        Flip the value of bit@pos
        """
        self.bitmap[pos // 8] ^= BITMASK[pos % 8]

    def count(self):
        """
        Count bits set
        """
        count = 0
        if self.bit_in_last_byte:
            for x in self.bitmap[:self.max_bytes_num - 1]:
                count += BIT_CNT[x]
            x = self.bitmap[self.max_bytes_num - 1]
            for i in range(8):
                if i >= self.bit_in_last_byte:
                    x = ~BITMASK[i]
            count += BIT_CNT[x]
        else:
            for x in self.bitmap[:self.max_bytes_num]:
                count += BIT_CNT[x]
        return count

    def size(self):
        """
        Return size
        """
        return len(self.bitmap) * 8

    def test(self, pos):
        """
        Return bit value
        """
        return (self.bitmap[pos // 8] & BITMASK[pos % 8]) != 0

    def any(self):
        """
        Test if any bit is set
        """
        if self.bit_in_last_byte:
            for x in self.bitmap[:self.max_bytes_num - 1]:
                if x:
                    return True
            x = self.bitmap[self.max_bytes_num - 1]
            for i in range(8):
                if i < self.bit_in_last_byte:
                    if (x & BITMASK[i]) != 0:
                        return True
        else:
            for x in self.bitmap[:self.max_bytes_num]:
                if x:
                    return True
        return False

    def none(self):
        """
        Test if no bit is set
        """
        if self.bit_in_last_byte:
            for x in self.bitmap[:self.max_bytes_num - 1]:
                if x:
                    return False
            x = self.bitmap[self.max_bytes_num - 1]
            for i in range(8):
                if i < self.bit_in_last_byte:
                    if (x & BITMASK[i]) != 0:
                        return False
        else:
            for x in self.bitmap[:self.max_bytes_num]:
                if x:
                    return False
        return True

    def all(self):
        """
        Test if all bits are set
        """
        if self.bit_in_last_byte:
            for x in self.bitmap[:self.max_bytes_num - 1]:
                if x != 0xFF:
                    return False
            x = self.bitmap[self.max_bytes_num - 1]
            for i in range(8):
                if i < self.bit_in_last_byte:
                    if (x & BITMASK[i]) == 0:
                        return False
        else:
            for x in self.bitmap[:self.max_bytes_num]:
                if x != 0xFF:
                    return False
        return True

    def enum_nonzero(self):
        """
        Get all non-zero bits
        """
        for byte_offset in range(self.max_bytes_num):
            if not self.bitmap[byte_offset]:
                continue

            x = self.bitmap[byte_offset]
            for i in range(8):
                if (x & BITMASK[i]) != 0:
                    bit_offset = byte_offset * 8 + i
                    if bit_offset >= self.max_bit_num:
                        break
                    else:
                        yield bit_offset

    def __getitem__(self, item):
        """
        Return a bit when indexing like a array
        """
        return self.test(item)

    def __setitem__(self, key, value):
        """
        Sets a bit when indexing like a array
        """
        if value is True:
            self.set(key)
        elif value is False:
            self.reset(key)
        else:
            raise Exception("Use a boolean value to assign to a bitfield")
