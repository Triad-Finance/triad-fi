import requests
from uagents import Agent, Context
from pydantic import BaseModel, Field
import os
from openai import OpenAI
import json
from datetime import datetime, timedelta, timezone

ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY","")
MAX_TOKENS = 64000  
ASI_ONE_MODEL = "asi1-extended"
THEGRAPH_JWT_TOKEN = os.getenv("THEGRAPH_JWT_TOKEN","")

client = OpenAI(
    api_key=ASI_ONE_API_KEY,
    base_url= ASI_ONE_BASE_URL
)



class UserInput(BaseModel):
    makerToken: str = Field(
        description="The token that the user will put in to be swapped"
    )
    takerToken: str = Field(
        description="The token that the user intends to receive against the maker token"
    )
    poolAddress: str = Field(
        description="The uniswap v4 pool address of the two tokens"
    )
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


SYSTEM_PROMPT = """
You are a Signal Agent in our DeFi investment/trading platform.
Your job: forecast a limit order DeFi swap.

IMPORTANT: Your response MUST be valid JSON ONLY and match this schema:

{
    "maker": "string (token symbol, e.g., USDT)",
    "taker": "string (token symbol, e.g., wETH)",
    "maker_amount": "float (e.g., 1.2)",
    "expiry": "integer (hours, e.g., 45)"
}

Do not include extra text or explanations.
"""

# Template for structuring the question before sending it to the chat model
USER_PROMPT_TEMPLATE = """
Answer the following question:
{question}
"""

def reduce_swaps(raw_data: dict, interval_minutes: int = 5):
    """
    Reduce swaps to one per interval and drop irrelevant fields.
    
    Args:
        raw_data (dict): JSON response from token-api
        interval_minutes (int): interval size in minutes
    Returns:
        list[dict]: reduced swaps
    """
    swaps = raw_data.get("data", [])
    if not swaps:
        return []

    reduced = []
    last_interval = None

    for swap in swaps:
        ts = swap["timestamp"]
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        # Round timestamp down to nearest interval
        interval = dt - timedelta(
            minutes=dt.minute % interval_minutes,
            seconds=dt.second,
            microseconds=dt.microsecond,
        )

        # Only take the first swap in each interval
        if last_interval == interval:
            continue
        last_interval = interval

        # Keep only useful fields
        cleaned = {
            "timestamp": ts,
            "datetime": swap["datetime"],
            # "pool": swap["pool"],
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
            "amount0": swap["amount0"],
            "amount1": swap["amount1"],
            "price0": swap["price0"],
            "price1": swap["price1"],
        }
        reduced.append(cleaned)

    return reduced


def safe_parse_response(response_text: str) -> AIResponse:
    try:
        data = json.loads(response_text.strip())
        return AIResponse(**data)
    except Exception as e:
        raise ValueError(f"Invalid response format: {e}\nResponse: {response_text}")
    
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

def fetch_swaps(poolAddress: str, network: str = "matic", startTime: int = 1735689600, endTime: int = 9999999999, swaps_interval_minutes: int = 5, limit: int = 100):
    url = f"https://token-api.thegraph.com/swaps/evm?network_id={network}&pool={poolAddress}&protocol=uniswap_v4&&startTime={startTime}&endTime={endTime}&orderBy=timestamp&orderDirection=desc&limit={limit}"
    headers = {"Authorization": f"Bearer {THEGRAPH_JWT_TOKEN}"}
    response = requests.get(url, headers=headers)

    response.raise_for_status()

    graph_response = response.json()

    return reduce_swaps(graph_response, swaps_interval_minutes)


def query_openai_chat(prompt: str):
    """
    Sends a chat request to OpenAI's API and retrieves the response.
    Args:
        prompt (str): The input prompt/question formatted for the model.
    Returns:
        str: The response from the OpenAI chat model.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ],
        model=ASI_ONE_MODEL,
    )
    return (chat_completion.choices[0].message.content)
        
# Define a message handler for the agent
@agent.on_message(model=UserInput, replies=AIResponse)
async def generate_limit_order(ctx: Context, sender: str, tradeInput: UserInput):
    """
    Handles incoming questions and responds using OpenAI's chat model.
    Args:
        ctx (Context): The agent's execution context.
        sender (str): The identifier of the sender.
        tradeInput (UserInput): The received interested swap.
    Returns:
        None
    """
    ctx.logger.info(f"Received question from {sender}: {tradeInput}")

    prompt = PROMPT_TEMPLATE.format(question=msg.question)
    response = query_openai_chat(prompt)
    ctx.logger.info(f"Response: {response}")
    await ctx.send(
        'agent1qgesp6djpknf83jltydjwzzzdwg4jm4n2s90yzwl4eua3yjnhwvj6yt30gu', AIResponse(answer=response)
    )
