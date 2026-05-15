class CircuitBreaker:
    def __init__(self, name):
        self.name = name
        self.state = "closed"
    def call(self, fn):
        return fn()
