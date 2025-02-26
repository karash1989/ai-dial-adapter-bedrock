from typing import List, Optional, Union

from aidial_sdk.chat_completion import (
    CustomContent,
    FunctionCall,
    Message,
    Role,
    ToolCall,
)
from pydantic import BaseModel

from aidial_adapter_bedrock.llm.errors import ValidationError


class SystemMessage(BaseModel):
    content: str

    def to_message(self) -> Message:
        return Message(role=Role.SYSTEM, content=self.content)


class HumanRegularMessage(BaseModel):
    content: str
    custom_content: Optional[CustomContent] = None

    def to_message(self) -> Message:
        return Message(
            role=Role.USER,
            content=self.content,
            custom_content=self.custom_content,
        )


class HumanToolResultMessage(BaseModel):
    id: str
    content: str

    def to_message(self) -> Message:
        return Message(
            role=Role.TOOL,
            tool_call_id=self.id,
            content=self.content,
        )


class HumanFunctionResultMessage(BaseModel):
    name: str
    content: str

    def to_message(self) -> Message:
        return Message(
            role=Role.FUNCTION,
            name=self.name,
            content=self.content,
        )


class AIRegularMessage(BaseModel):
    content: str
    custom_content: Optional[CustomContent] = None

    def to_message(self) -> Message:
        return Message(
            role=Role.ASSISTANT,
            content=self.content,
            custom_content=self.custom_content,
        )


class AIToolCallMessage(BaseModel):
    calls: List[ToolCall]
    content: Optional[str] = None

    def to_message(self) -> Message:
        return Message(
            role=Role.ASSISTANT,
            content=self.content,
            tool_calls=self.calls,
        )


class AIFunctionCallMessage(BaseModel):
    call: FunctionCall
    content: Optional[str] = None

    def to_message(self) -> Message:
        return Message(
            role=Role.ASSISTANT,
            content=self.content,
            function_call=self.call,
        )


BaseMessage = Union[SystemMessage, HumanRegularMessage, AIRegularMessage]

ToolMessage = Union[
    HumanToolResultMessage,
    HumanFunctionResultMessage,
    AIToolCallMessage,
    AIFunctionCallMessage,
]


def _parse_assistant_message(
    content: Optional[str],
    function_call: Optional[FunctionCall],
    tool_calls: Optional[List[ToolCall]],
    custom_content: Optional[CustomContent],
) -> BaseMessage | ToolMessage:
    if content is not None and function_call is None and tool_calls is None:
        return AIRegularMessage(content=content, custom_content=custom_content)

    if function_call is not None and tool_calls is None:
        return AIFunctionCallMessage(call=function_call, content=content)

    if function_call is None and tool_calls is not None:
        return AIToolCallMessage(calls=tool_calls, content=content)

    raise ValidationError("Unknown type of assistant message")


def parse_dial_message(msg: Message) -> BaseMessage | ToolMessage:
    match msg:
        case Message(role=Role.SYSTEM, content=content) if content is not None:
            return SystemMessage(content=content)
        case Message(
            role=Role.USER, content=content, custom_content=custom_content
        ) if content is not None:
            return HumanRegularMessage(
                content=content, custom_content=custom_content
            )
        case Message(
            role=Role.ASSISTANT,
            content=content,
            function_call=function_call,
            tool_calls=tool_calls,
            custom_content=custom_content,
        ):
            return _parse_assistant_message(
                content, function_call, tool_calls, custom_content
            )
        case Message(
            role=Role.FUNCTION, name=name, content=content
        ) if content is not None and name is not None:
            return HumanFunctionResultMessage(name=name, content=content)
        case Message(
            role=Role.TOOL, tool_call_id=id, content=content
        ) if content is not None and id is not None:
            return HumanToolResultMessage(id=id, content=content)
        case _:
            raise ValidationError("Unknown message type or invalid message")
