import json
from typing import assert_never

from aidial_sdk.chat_completion import FunctionCall, ToolCall
from anthropic.types import ToolUseBlock

from aidial_adapter_bedrock.llm.consumer import Consumer
from aidial_adapter_bedrock.llm.errors import ValidationError
from aidial_adapter_bedrock.llm.message import (
    AIFunctionCallMessage,
    AIToolCallMessage,
    BaseMessage,
    HumanFunctionResultMessage,
    HumanRegularMessage,
    HumanToolResultMessage,
    ToolMessage,
)
from aidial_adapter_bedrock.llm.tools.tools_config import ToolsMode


def to_dial_function_call(block: ToolUseBlock) -> FunctionCall:
    return FunctionCall(name=block.name, arguments=json.dumps(block.input))


def to_dial_tool_call(block: ToolUseBlock) -> ToolCall:
    return ToolCall(
        index=None,
        id=block.id,
        type="function",
        function=to_dial_function_call(block),
    )


def process_tools_block(
    consumer: Consumer, block: ToolUseBlock, tools_mode: ToolsMode | None
):
    match tools_mode:
        case ToolsMode.TOOLS:
            consumer.create_function_tool_call(to_dial_tool_call(block))
        case ToolsMode.FUNCTIONS:
            consumer.create_function_call(to_dial_function_call(block))
        case None:
            raise ValidationError(
                "A model has called a tool, but no tools were given to the model in the first place."
            )
        case _:
            raise Exception(f"Unknown {tools_mode} during tool use!")


def process_with_tools(
    message: BaseMessage | ToolMessage, tools_mode: ToolsMode | None
) -> BaseMessage | HumanToolResultMessage | AIToolCallMessage:
    """
    1. Validates, that no Functions or Tools messages are used without config
    2. Validates, that client don't use Functions messages with tools config
    3. Validates, that client don't use Tools messages with functions config
    4. Convert Functions messages to Tools messages (Claude supports only Tools).
        For tool id we just use function name
    """
    if tools_mode is None:
        if not isinstance(message, BaseMessage):
            raise ValidationError(
                "You cannot use messages with functions or tools without config. Please change your messages."
            )
        return message
    elif tools_mode == ToolsMode.TOOLS:
        if isinstance(message, HumanFunctionResultMessage) or isinstance(
            message, AIFunctionCallMessage
        ):
            raise ValidationError(
                "You cannot use function messages with tools config."
            )
        return message
    elif tools_mode == ToolsMode.FUNCTIONS:
        match message:
            case HumanRegularMessage():
                return message
            case HumanToolResultMessage() | AIToolCallMessage():
                raise ValidationError(
                    "You cannot use tools messages with functions config."
                )
            case AIFunctionCallMessage():
                return AIToolCallMessage(
                    content=message.content,
                    calls=[
                        ToolCall(
                            index=None,
                            id=message.call.name,
                            type="function",
                            function=message.call,
                        )
                    ],
                )
            case HumanFunctionResultMessage():
                return HumanToolResultMessage(
                    id=message.name, content=message.content
                )
            case _:
                raise ValueError(f"Unknown message type {type(message)}")

    else:
        assert_never(tools_mode)
