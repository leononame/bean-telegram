from dataclasses import dataclass, field
from typing import List

from telegram.ext import CallbackContext

import beans


@dataclass
class ConversationState:
    """ConversationState is the single state representation in a conversation.
    All state is bundled into one object, this way the state is easily removeable from 
    memory when the conversation is over."""

    id: int  # The id of the original message
    accounts: List[str] = field(default_factory=lambda: [])
    current_path: str = ""
    tx: beans.Transaction = None


def save_state(context: CallbackContext, c: ConversationState):
    """Save a conversation's state in the chat context. This way, it can be retrieved by a callback."""
    data = context.chat_data.get("states")
    if data == None:
        context.chat_data["states"] = {}
        data = context.chat_data["states"]
    data[str(c.id)] = c


def get_state(context: CallbackContext, cid: str) -> ConversationState:
    """Retrieve a conversation's state for the current chat context."""
    data = context.chat_data.get("states")
    if data == None:
        return None
    return data.get(cid)


def pop_state(context: CallbackContext, cid: str) -> ConversationState:
    """Retrieve a conversation's state for the current chat context and delete it from the storage."""
    data = context.chat_data.get("states")
    if data == None:
        return
    if data.get(cid):
        return data.pop(cid)
    return None


def delete_state(context: CallbackContext, cid: str):
    """Delete a conversation's state from storage."""
    data = context.chat_data.get("states")
    if data == None:
        return
    if data.get(cid):
        del data[cid]


def get_narration_account(context: CallbackContext, narration: str) -> str:
    """Get the account last used with the same narration."""
    data = context.user_data.get("narrations")
    if data == None:
        return ""
    return data.get(narration)


def save_narration_account(context: CallbackContext, narration: str, account: str):
    """Save the account the user chose to use in combination with the narration."""
    data = context.user_data.get("narrations")
    if data == None:
        context.user_data["narrations"] = {}
        data = context.user_data.get("narrations")
    data[narration] = account
