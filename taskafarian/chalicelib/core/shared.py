class Shared:
    def __init__(self):
        self.current_user = None
        self.current_request = None

    def clear(self):
        self.current_user = None
        self.current_request = None


g = Shared()
