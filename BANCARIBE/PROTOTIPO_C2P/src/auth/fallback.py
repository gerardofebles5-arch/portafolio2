class FallbackAuth:
    def __init__(self):
        self.methods = ["biometric", "sms", "password"]
    def authenticate(self, method="biometric"):
        return {"success": True, "method": method}
