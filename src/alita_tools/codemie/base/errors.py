class TruncatedOutputError(Exception):
    message: str = "Output was truncated."

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class InvalidCredentialsError(Exception):
    message: str = "Invalid credentials"

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message
