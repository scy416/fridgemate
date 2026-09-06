"""Thin factory around ``ChatBedrockConverse``.

Every agent gets its model from here so there is a single seam for region,
credentials, and structured-output wiring. Nothing else in the codebase should
import ``langchain_aws`` directly.
"""

from __future__ import annotations

from typing import TypeVar

from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel

from fridgemate.config import AWS_REGION, MODEL_FAST

TSchema = TypeVar("TSchema", bound=BaseModel)


def get_chat(
    model_id: str = MODEL_FAST,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> ChatBedrockConverse:
    """Return a Bedrock chat client for ``model_id``.

    Credentials come from the standard AWS chain (the ``AWS_PROFILE`` named in
    ``.env`` for local dev). ``temperature`` defaults to 0 because most steps
    here are extraction / judgement, where we want repeatable output.
    """
    return ChatBedrockConverse(
        model=model_id,
        region_name=AWS_REGION,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def structured(schema: type[TSchema], model_id: str = MODEL_FAST):
    """Return a chat client that is forced to answer as ``schema``.

    LangChain drives Bedrock's tool-use API under the hood, so the model must
    return JSON that validates against ``schema`` or the call raises.
    """
    return get_chat(model_id).with_structured_output(schema)
