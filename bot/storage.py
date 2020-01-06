import shelve
from dataclasses import dataclass, field
from os.path import join
from typing import List, Optional

from telegram.ext import CallbackContext

import beans
import config


def get_shelve():
    """Get a single shelve. This function should not be called concurrently,
    but since telegram handlers never run concurrently, we will be fine."""
    return shelve.open(join(config.db_dir, "users.pickle"), writeback=True)


@dataclass
class ConversationState:
    """State is the single state representation in a conversation.
    All state is bundled into one object, this way the state is easily removeable from 
    memory when the conversation is over. This class serves the purpose of
    saving the state when someone is selecting an expense account through
    multiple menus (aka, multiple messages). The current path is stored along
    the list of accounts for the current path.
    
    Attributes:
        id (:obj: int): The ID. The message_id of the chat should be used.
        tx (:class: beans.Transaction): The transaction added to the account
        acounts (:obj: List[str]): List of accounts for the current search path.
        current_path (:obj: str): The current search path
    """

    id: int  # The id is the telegram message_id
    tx: beans.Transaction
    accounts: List[str] = field(default_factory=lambda: [])
    current_path: str = ""


def save_state(context: CallbackContext, s: ConversationState):
    """Save a conversation's state in the chat context. This way, it can be retrieved by a callback.
    
    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context in which to save the state.
        state (:class: State): The state to persist.
    """
    data = context.chat_data.get("states")
    if data == None:
        context.chat_data["states"] = {}
        data = context.chat_data["states"]
    data[str(s.id)] = s


def get_state(context: CallbackContext, id: str) -> Optional[ConversationState]:
    """Retrieve a conversation's state for the current chat context.
    
    Returns:
        The State if found, otherwise None.

    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context from which to retrieve the state.
        id (:obj: str): The ID of the state to retrieve.
    """
    data = context.chat_data.get("states")
    if data == None:
        return None
    return data.get(id)


def pop_state(context: CallbackContext, id: str) -> Optional[ConversationState]:
    """Retrieve a conversation's state for the current chat context and delete it from the storage.
    
    Returns:
        The State if found, otherwise None.

    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context from which to retrieve the state.
        id (:obj: str): The ID of the state to retrieve.
    """
    data = context.chat_data.get("states")
    if data == None:
        return None
    if data.get(id):
        return data.pop(id)
    return None


def delete_state(context: CallbackContext, id: str):
    """Retrieve a conversation's state for the current chat context and delete it from the storage.
    
    Returns:
        The State if found, otherwise None.

    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context from which to retrieve the state.
        id (:obj: str): The ID of the state to retrieve.
    """
    data = context.chat_data.get("states")
    if data == None:
        return None

    if data.get(id):
        del data[id]


def get_narration_account(context: CallbackContext, narration: str) -> str:
    """Get the account last used with the same narration.

    Returns:
        The account as string.

    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context from which to retrieve the narration.
        narration (:obj: str): The narration to check for.
    """
    data = context.user_data.get("narrations")
    if data == None:
        return ""
    return data.get(narration)


def save_narration_account(context: CallbackContext, narration: str, account: str):
    """Save the account the user chose to use in combination with the narration.

    Args:
        context (:class: telegram.ext.CallbackContext): The conversation's context that stores the narration and account.
        narration (:obj: str): The narration.
        account (:obj: str): The account.
    """
    data = context.user_data.get("narrations")
    if data == None:
        context.user_data["narrations"] = {}
        data = context.user_data.get("narrations")
    data[narration] = account
