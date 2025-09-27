import requests
from uagents import Agent, Context
from pydantic import BaseModel, Field
import os
from openai import OpenAI

ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")
ASI_ONE_MODEL = "asi1-mini"
THEGRAPH_JWT_TOKEN = os.getenv("THEGRAPH_JWT_TOKEN")

client = OpenAI(
    api_key=ASI_ONE_API_KEY,
    base_url= ASI_ONE_BASE_URL
)


url = "https://token-api.thegraph.com/swaps/evm?network_id=matic&startTime=1735689600&endTime=9999999999&orderBy=timestamp&orderDirection=desc&limit=10&page=1"
headers = {"Authorization": f"Bearer {THEGRAPH_JWT_TOKEN}"}

MAX_TOKENS = 64000  

def approx_token_count(text: str) -> int:
    """Approximate token count from text length."""
    return len(text) // 4   # ~4 chars per token

def safe_prompt(prompt: str) -> str:
    tokens = approx_token_count(prompt)
    if tokens > MAX_TOKENS:
        # Truncate from the start (keep recent context)
        excess = tokens - MAX_TOKENS
        chars_to_trim = excess * 4
        prompt = prompt[chars_to_trim:]
    return prompt

# Define a request model for receiving questions
class AIRequest(BaseModel):
    question: str = Field(
        description="The question that the user wants to have an answer for."
    )
class AIResponse(BaseModel):
    answer: str = Field(
        description="The answer from AI agent to the user agent"
    )

SYSTEM_PROMPT = """
You are a Signal Agent in our DeFi investment/trading platform, and based on the data provided of a particular
asset pair's trading history in a specific direction, you have to forecast a limit order DeFi swap that should be carried out
that would contain the swap amount of the maker token that should be swapped for the taker account, 
as well as expiry in number of hours the limit order should be live for.
Assume that we are capable of placing DeFi swap limit orders.
Your output should be a valid JSON format with the following example's structure:

{
    "maker": "USDT",
    "taker": "wETH",
    "maker_amount": "1.2",
    "expiry": "45"
}

The user input must contain the following:
1. Maker - Taker token pair: is interpreted as maker token is the first mentioned token and taker token second, unless the 
user explicitly states them.
2. How many maximum maker tokens are available to place the limit order
3. Maximum time that they can afford to keep the order open
4. Swap data of the maker and taker tokens

If any of the information is missing from the user input, request it from the user.
"""

# Template for structuring the question before sending it to the chat model
USER_PROMPT_TEMPLATE = """
Answer the following question:
{question}
"""
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
@agent.on_message(model=AIRequest, replies=AIResponse)
async def answer_question(ctx: Context, sender: str, msg: AIRequest):
    """
    Handles incoming questions and responds using OpenAI's chat model.
    Args:
        ctx (Context): The agent's execution context.
        sender (str): The identifier of the sender.
        msg (AIRequest): The received question wrapped in the AIRequest model.
    Returns:
        None
    """
    ctx.logger.info(f"Received question from {sender}: {msg.question}")
    prompt = PROMPT_TEMPLATE.format(question=msg.question)
    response = query_openai_chat(prompt)
    ctx.logger.info(f"Response: {response}")
    await ctx.send(
        'agent1qgesp6djpknf83jltydjwzzzdwg4jm4n2s90yzwl4eua3yjnhwvj6yt30gu', AIResponse(answer=response)
    )
