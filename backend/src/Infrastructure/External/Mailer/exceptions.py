class MailerSendError(Exception):
    """Raised when the email provider rejects or fails to deliver the message."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
