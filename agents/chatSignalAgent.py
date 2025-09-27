from datetime import datetime, timezone
from uuid import uuid4
import os
import requests
import json

from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)
from pydantic import BaseModel, Field

ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY","")
MAX_TOKENS = 32000
ASI_ONE_MODEL = "asi1-mini"
THEGRAPH_JWT_TOKEN = os.getenv("THEGRAPH_JWT_TOKEN","")


client = OpenAI(
    base_url=ASI_ONE_BASE_URL,
    api_key=ASI_ONE_API_KEY,
)

agent = Agent()

# We create a new protocol which is compatible with the chat protocol spec. This ensures
# compatibility between agents
protocol = Protocol(spec=chat_protocol_spec)

class UserInput(BaseModel):
    makerToken: str = Field(
        description="The token that the user will put in to be swapped"
    )
    takerToken: str = Field(
        description="The token that the user intends to receive against the maker token"
    )
    # poolAddress: str = Field(
    #     description="The uniswap v4 pool address of the two tokens"
    # )
    makerMaxAmount: float = Field(
        description="Maximum amount of maker tokens the user is willing to swap"
    )
    maxExpiry: float = Field(
        description="Maximum amount of time in hours the user can keep the limit order live"
    )

class AIResponse(BaseModel):
    maker: str = Field(
        description="The token the user is providing in the swap (e.g., USDT)"
    )
    taker: str = Field(
        description="The token the user wants to receive (e.g., wETH)"
    )
    maker_amount: float = Field(
        description="The amount of maker token to be swapped"
    )
    expiry: int = Field(
        description="The expiry time in hours the order should stay live"
    )


SYSTEM_PROMPT_1 = """
Rephrase the user message in the following format.

IMPORTANT: Your response MUST be valid JSON ONLY and match this schema:

{
    "makerToken": "USDTO",
    "takerToken": "WETH",
    "makerMaxAmount": "float (e.g., 1.2)",
    "maxExpiry": "integer (hours, e.g., 45)"
}

If you are uncertain, respond with the following anyway:
{
    "makerToken": "USDTO",
    "takerToken": "WETH",
    "makerMaxAmount": 20,
    "maxExpiry": 15
}

Do not include extra text or explanations. 
"""


# SYSTEM_PROMPT_2 = """
# You are a Signal Agent in our DeFi investment/trading platform.
# Your job: forecast a limit order DeFi swap using technical indicators.

# You will receive history of swaps by general public in JSON sourced from a public API, with fields like:

# {
#     "timestamp": ...,
#     "datetime": ...,
#     "token0": { "symbol": ..., "address": ..., "decimals": ... },
#     "token1": { "symbol": ..., "address": ..., "decimals": ... },
#     "amount0": ...,
#     "amount1": ...,
#     "price0": ...,
#     "price1": ...
# }
# Rules:
# - The token with the negative amount (amount0 or amount1) is the taker in the swap.
# - Study the prices and trade directions to determine if the user should go ahead with the desired swap.
# - If the swap looks like a bad idea according to technical indicators, set maker_amount = 0 and expiry = 0.
# - Else, propose a limit order which can be placed right now that can benefit the user


# Return ONLY valid JSON matching this schema:
# {
#     "maker": string,      // token symbol the user is providing
#     "taker": string,      // token symbol the user wants
#     "maker_amount": float, // amount of maker token to swap
#     "expiry": integer      // hours the order stays live
# }
# """

SYSTEM_PROMPT_2 = """
You are a DeFi Signal Agent. 

steps:
1. Decide upon appropriate trade indicators
2. Implement indicators upon provided swap data
3. Provide a limit order that should be placed within the constraints of the user

Rules:
- The token with the negative amount is the taker.
- If the trade looks bad, set maker_amount = 0 and expiry = 0.
- You MUST return ONLY valid JSON that conforms exactly to the schema as follows:
{
    "maker": string,
    "taker": string,
    "maker_amount": float,
    "expiry": int
}
- Do NOT include code fences, markdown, or explanations.

"""


USER_PROMPT_TEMPLATE = """
User wants to swap {makerToken} for {takerToken}.
- Maximum maker tokens available with the user: {makerMaxAmount}
- Maximum expiry in hours for the limit order: {maxExpiry}

Here is recent pool swap data:
{swap_data}
"""

def reduce_swaps(ctx: Context, raw_data: dict, interval_minutes: int = 5):

    ctx.logger.info("reducing swaps count")
    swaps = raw_data.get("data", [])
    if not swaps:
        ctx.logger.info("returning empty")
        return []

    # Sort by timestamp ascending
    swaps.sort(key=lambda x: x["timestamp"])
    reduced = []
    interval_map = {}  # interval_start -> (trade, distance)
    try:
        for swap in swaps:
            ts = swap["timestamp"]
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            # Round down to nearest interval mark
            interval_start = dt.replace(
                minute=(dt.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0
            )

            # Distance from interval start
            distance = abs((dt - interval_start).total_seconds())

            if interval_start not in interval_map or distance < interval_map[interval_start][1]:
                interval_map[interval_start] = (swap, distance)
        ctx.logger.info(f"Done with interval map")
        # Keep only the nearest trade per interval
        for swap, _ in sorted(interval_map.values(), key=lambda x: x[0]["timestamp"]):
            cleaned = {
                "timestamp": swap["timestamp"],
                "datetime": swap.get("datetime") or datetime.fromtimestamp(swap["timestamp"], tz=timezone.utc).isoformat(),
                "token0": {
                    "symbol": swap["token0"]["symbol"],
                    "address": swap["token0"]["address"],
                    "decimals": swap["token0"]["decimals"],
                },
                "token1": {
                    "symbol": swap["token1"]["symbol"],
                    "address": swap["token1"]["address"],
                    "decimals": swap["token1"]["decimals"],
                },
                "amount0": float(swap["amount0"]) / 10 ** int(swap["token0"]["decimals"]),
                "amount1": float(swap["amount1"]) / 10 ** int(swap["token1"]["decimals"]),
                "price0": swap["price0"],
                "price1": swap["price1"],
            }
            reduced.append(cleaned)

    except Exception as e:
        ctx.logger.info(f"ran into some error when reducing ")
        ctx.logger.error(e)
    return reduced

def approx_token_count(text: str) -> int:
    """Approximate token count from text length."""
    return len(text) // 4

def safe_prompt(prompt: str) -> str:
    tokens = approx_token_count(prompt)
    if tokens > MAX_TOKENS:
        excess = tokens - MAX_TOKENS
        chars_to_trim = excess * 4
        prompt = prompt[chars_to_trim:]
    return prompt

def fetch_swaps(ctx: Context,poolAddress: str, network: str = "matic", startTime: int = 1735689600, endTime: int = 9999999999, swaps_interval_minutes: int = 5, limit: int = 100):
    url = f"https://token-api.thegraph.com/swaps/evm?network_id={network}&pool={poolAddress}&startTime={startTime}&endTime={endTime}&orderBy=timestamp&orderDirection=desc&limit={limit}"
    headers = {"Authorization": f"Bearer {THEGRAPH_JWT_TOKEN}"}
    response = requests.get(url, headers=headers)
    ctx.logger.info("response got from The Graph")
    # ctx.logger.info(str(response.json()))

    response.raise_for_status()

    graph_response = response.json()
    

    return reduce_swaps(ctx,graph_response, swaps_interval_minutes)


# We define the handler for the chat messages that are sent to your agent
@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    # send the acknowledgement for receiving the message
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    # collect up all the text chunks
    text = ''
    for item in msg.content:
        if isinstance(item, TextContent):
            text += item.text

    # query the model based on the user question
    response = ""
    try:
        r = client.chat.completions.create(
            model=ASI_ONE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_1},
                {"role": "user", "content": text},
            ],
        )

        response = r.choices[0].message.content
        ctx.logger.info(f"Raw LLM response: {response}")

        try:
            # Parse the JSON string into your Pydantic model
            tradeInput = UserInput.model_validate_json(response)
        except Exception as e:
            ctx.logger.error(f"Failed to parse LLM response into UserInput: {e}")
            return

        ctx.logger.info(f"Parsed trade input: {tradeInput}")

        if tradeInput.makerMaxAmount > 0:
            ctx.logger.info(f"Received trade input")
            swap_data = fetch_swaps(ctx,"0x4ccd010148379ea531d6c587cfdd60180196f9b1");
            ctx.logger.info(f"Fetched data from TheGraph")
           
            prompt = USER_PROMPT_TEMPLATE.format(
                makerToken=tradeInput.makerToken,
                takerToken=tradeInput.takerToken,
                makerMaxAmount=tradeInput.makerMaxAmount,
                maxExpiry=tradeInput.maxExpiry,
                swap_data=json.dumps(swap_data, indent=2)
            )
            prompt = safe_prompt(prompt)
            # ctx.logger.info(f"prompt: {str(prompt)}")
            chat_completion = client.chat.completions.create(
                model=ASI_ONE_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_2},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_schema", "json_schema": AIResponse.model_json_schema()},
                max_completion_tokens= 64000
            )
            ctx.logger.info(f"JSON LLM response: {chat_completion.choices[0]}")
            json_response_str = chat_completion.choices[0].message.content
            

            try:
                ai_response = AIResponse.model_validate_json(json_response_str)
            except Exception as e:
                ctx.logger.error(f"Failed to parse LLM response into AIResponse: {e}")
                return

            if ai_response.expiry > tradeInput.maxExpiry:
                ai_response.expiry = int(tradeInput.maxExpiry)

            response = ai_response
    except Exception as e:
        ctx.logger.error(f"Swap fetch failed: {e}")
        await ctx.send(sender, ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            # we send the contents back in the chat message
            TextContent(type="text", text="Error"),
            # we also signal that the session is over, this also informs the user that we are not recording any of the
            # previous history of messages.
            EndSessionContent(type="end-session"),
        ]
        ))
        return


    # send the response back to the user
    await ctx.send(sender, ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            # we send the contents back in the chat message
            TextContent(type="text", text=str(response)),
            # we also signal that the session is over, this also informs the user that we are not recording any of the
            # previous history of messages.
            EndSessionContent(type="end-session"),
        ]
    ))


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    # we are not interested in the acknowledgements for this example, but they can be useful to
    # implement read receipts, for example.
    pass


# attach the protocol to the agent
agent.include(protocol, publish_manifest=True)

