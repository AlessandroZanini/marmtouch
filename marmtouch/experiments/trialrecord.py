class TrialRecord:
    def __init__(self, keys, **data):
        self.keys = keys
        for key in data:
            if key not in keys:
                raise ValueError(f"{key} is not a valid key")
        self.data = data
    def dump(self, sep=','):
        return sep.join([str(self.data.get(key, 'nan')) for key in self.keys])