# Dummy objects to allow saliweb.build to import objects from SCons.Script.

class File: pass

class Mkdir: pass

class Chmod(object):
    def __init__(self, target, mode):
        self.target = target
        self.mode = mode

class Value: pass

class Action: pass

class Builder: pass

class EnumVariable(object):
    def __init__(self, key, help, default, allowed_values, map=None,
                 ignorecase=None):
        self.key = key
        self.help = help
        self.default = default
        self.allowed_values = allowed_values
        self.map = map
        self.ignorecore = ignorecase
