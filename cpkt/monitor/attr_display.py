

class AttrDisplay(object):
    def gather_attrs(self):
        return "\n".join("  {}={}".format(k, getattr(self, k)) for k in self.__dict__.keys())

    def __str__(self):
        return "{}:\n [\n{}\n ]\n".format(self.__class__.__name__, self.gather_attrs())
