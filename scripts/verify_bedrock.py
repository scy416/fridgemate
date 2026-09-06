"""One-shot check that Bedrock + credentials + model ids all work.

Usage:
    python scripts/verify_bedrock.py

Prints the model's reply and the token usage for the call. If this fails, the
rest of FridgeMate will too, so run it first when setting up on a new machine.
"""

from __future__ import annotations

import sys

import boto3

# Import the same constants the app uses, so this really tests the app's config.
sys.path.insert(0, "src")
from fridgemate.config import AWS_REGION, MODEL_FAST, MODEL_SMART  # noqa: E402


def _converse(client, model_id: str) -> None:
    resp = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": "Reply with exactly: pong"}]}],
        inferenceConfig={"maxTokens": 20, "temperature": 0.0},
    )
    text = resp["output"]["message"]["content"][0]["text"].strip()
    usage = resp["usage"]
    print(f"  {model_id}")
    print(f"    reply : {text!r}")
    print(f"    tokens: in={usage['inputTokens']} out={usage['outputTokens']}")


def main() -> int:
    print(f"Region: {AWS_REGION}")
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    try:
        _converse(client, MODEL_FAST)
        _converse(client, MODEL_SMART)
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAILED: {exc}")
        return 1
    print("\nOK - Bedrock reachable and both models respond.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
