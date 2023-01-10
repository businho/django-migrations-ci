class DumpError(RuntimeError):
    @classmethod
    def from_stderr(cls, err):
        return cls(err.decode().strip())
