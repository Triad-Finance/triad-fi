from datetime import datetime
from uuid import uuid4
import os

from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)


ASI_ONE_BASE_URL = "https://api.asi1.ai/v1"
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY","")
# MAX_TOKENS = 64000  
ASI_ONE_MODEL = "asi1-extended"
# THEGRAPH_JWT_TOKEN = os.getenv("THEGRAPH_JWT_TOKEN","")


client = OpenAI(
    base_url=ASI_ONE_BASE_URL,

    api_key=ASI_ONE_API_KEY,
)

agent = Agent()

# We create a new protocol which is compatible with the chat protocol spec. This ensures
# compatibility between agents
protocol = Protocol(spec=chat_protocol_spec)

SYSTEM_PROMPT = """
You are a Signal Agent in our DeFi investment/trading platform.
Your job: forecast a limit order DeFi swap using technical indicators used in trading.
Read the following intent from user message:

- User wants to swap "makerToken" for "takerToken".
- Maximum maker tokens available: "makerMaxAmount"
- Maximum expiry in hours: "maxExpiry"

IMPORTANT: Your response MUST be valid JSON ONLY and match this schema:

{
    "maker": "string (token symbol, e.g., USDT)",
    "taker": "string (token symbol, e.g., wETH)",
    "maker_amount": "float (e.g., 1.2)",
    "expiry": "integer (hours, e.g., 45)"
}

Do not include extra text or explanations. 
"""



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
    response = 'I am afraid something went wrong and I am unable to answer your question at the moment'
    try:
        r = client.chat.completions.create(
            model=ASI_ONE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )

        response = str(r.choices[0].message.content)
    except:
        ctx.logger.exception('Error querying model')

    # send the response back to the user
    await ctx.send(sender, ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            # we send the contents back in the chat message
            TextContent(type="text", text=response),
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