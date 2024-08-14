import logging
from typing import List, Any, Optional
from langchain_core.pydantic_v1 import root_validator, BaseModel
from pydantic import create_model
from pydantic.fields import FieldInfo
import yagmail

logger = logging.getLogger(__name__)


SMTP_SERVER = "smtp.gmail.com"

NoInput = create_model(
    "NoInput"
)

SendEmail = create_model(
    "GmailSendMessageStep",
    receiver=(str, FieldInfo(description="Email of the person you are going to send the letter to.")),
    message=(str, FieldInfo(description="Email message you going to send.")),
    subject=(str, FieldInfo(description="Email subject.")),
    cc=(List[str], FieldInfo(description="Persons who you are going to share a copy of email to."))
)

class YagmailWrapper(BaseModel):
    username: str
    password: str
    host: Optional[str] = SMTP_SERVER

    @root_validator()
    def validate_toolkit(cls, values):
        username = values['username']
        password = values['password']
        host = values.get("host")
        values['client'] = yagmail.SMTP(user=username, password=password, host=host)
        return values

    def send_gmail_message(self, receiver: str, message: str, subject: str, cc=None):
        """ Send email """
        response = self.client.send(
            to=receiver,
            subject=subject,
            contents=message,
            cc=cc
        )
        return response


    def get_available_tools(self):
        return [
            {
                "name": "send_gmail_message",
                "description": self.send_gmail_message.__doc__,
                "args_schema": SendEmail,
                "ref": self.send_gmail_message,
            }
        ]

    def run(self, mode: str, *args: Any, **kwargs: Any):
        for tool in self.get_available_tools():
            if tool["name"] == mode:
                return tool["ref"](*args, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")