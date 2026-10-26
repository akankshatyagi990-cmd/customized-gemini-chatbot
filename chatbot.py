import os
import json
import re
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)


# ============================================================
# STEP 12 - CUSTOMIZED GEMINI CHATBOT
#
# FEATURES:
# - Saved user name
# - Persistent chat history
# - Conversation memory
# - Load previous chats locally
# - Clear chat
# - Change name
# - Temporary API retry
# - Daily quota handling
# ============================================================


# ------------------------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# ------------------------------------------------------------

load_dotenv()


# ------------------------------------------------------------
# 2. CHECK API KEY
# ------------------------------------------------------------

api_key = os.getenv("GOOGLE_API_KEY")


if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY was not found in the .env file."
    )


# ------------------------------------------------------------
# 3. CREATE GEMINI MODEL
# ------------------------------------------------------------

llm_obj = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash"
)


# ------------------------------------------------------------
# 4. FILE NAMES
# ------------------------------------------------------------

PROFILE_FILE = "user_profile.json"

CHAT_HISTORY_FILE = "chat_history.json"


# ============================================================
# USER PROFILE FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# 5. LOAD USER NAME
# ------------------------------------------------------------

def load_username():

    if not os.path.exists(PROFILE_FILE):
        return None

    try:

        with open(
            PROFILE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            profile = json.load(file)

        return profile.get("username")

    except Exception:

        return None


# ------------------------------------------------------------
# 6. SAVE USER NAME
# ------------------------------------------------------------

def save_username(username):

    profile = {
        "username": username
    }

    with open(
        PROFILE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            profile,
            file,
            indent=4
        )


# ============================================================
# GEMINI RESPONSE FUNCTION
# ============================================================


# ------------------------------------------------------------
# 7. EXTRACT TEXT FROM RESPONSE
# ------------------------------------------------------------

def get_response_text(result):

    content = result.content

    if isinstance(content, str):
        return content


    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, dict):

                if item.get("type") == "text":

                    text_parts.append(
                        item.get("text", "")
                    )

            else:

                text_parts.append(
                    str(item)
                )

        return "\n".join(text_parts)


    return str(content)


# ============================================================
# CHAT HISTORY FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# 8. SAVE CHAT HISTORY
# ------------------------------------------------------------

def save_chat_history(conversation_history):

    saved_messages = []


    for message in conversation_history:

        if isinstance(message, SystemMessage):

            role = "system"


        elif isinstance(message, HumanMessage):

            role = "human"


        elif isinstance(message, AIMessage):

            role = "ai"


        else:

            continue


        saved_messages.append(
            {
                "role": role,
                "content": message.content,
            }
        )


    with open(
        CHAT_HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            saved_messages,
            file,
            indent=4,
            ensure_ascii=False
        )


# ------------------------------------------------------------
# 9. LOAD CHAT HISTORY
# ------------------------------------------------------------

def load_chat_history():

    if not os.path.exists(CHAT_HISTORY_FILE):
        return []


    try:

        with open(
            CHAT_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            saved_messages = json.load(file)


        conversation = []


        for item in saved_messages:

            role = item.get("role")

            content = item.get(
                "content",
                ""
            )


            if role == "system":

                conversation.append(
                    SystemMessage(
                        content=content
                    )
                )


            elif role == "human":

                conversation.append(
                    HumanMessage(
                        content=content
                    )
                )


            elif role == "ai":

                conversation.append(
                    AIMessage(
                        content=content
                    )
                )


        return conversation


    except Exception:

        return []


# ------------------------------------------------------------
# 10. GET PREVIOUS CHAT TURNS
# ------------------------------------------------------------

def get_chat_turns(conversation_history):

    turns = []

    current_question = None


    for message in conversation_history:

        if isinstance(message, HumanMessage):

            current_question = message.content


        elif (
            isinstance(message, AIMessage)
            and current_question is not None
        ):

            turns.append(
                {
                    "user": current_question,
                    "bot": message.content,
                }
            )

            current_question = None


    return turns


# ------------------------------------------------------------
# 11. DISPLAY LAST N CHAT TURNS
# ------------------------------------------------------------

def show_previous_chats(
    conversation_history,
    number_of_chats
):

    chat_turns = get_chat_turns(
        conversation_history
    )


    if not chat_turns:

        print(
            "\nBot: No previous chats are saved yet."
        )

        return


    number_of_chats = min(
        number_of_chats,
        len(chat_turns)
    )


    selected_chats = chat_turns[
        -number_of_chats:
    ]


    print(
        "\n" + "=" * 70
    )

    print(
        f"LAST {number_of_chats} CHAT(S)"
    )

    print(
        "=" * 70
    )


    for index, chat in enumerate(
        selected_chats,
        start=1
    ):

        print(
            f"\nChat {index}"
        )

        print(
            "-" * 70
        )

        print(
            f"You: {chat['user']}"
        )

        print(
            f"\nBot: {chat['bot']}"
        )


    print(
        "\n" + "=" * 70
    )


# ============================================================
# COMMAND PARSING
# ============================================================


# ------------------------------------------------------------
# 12. CHECK HISTORY COMMAND
# ------------------------------------------------------------

def get_requested_history_count(
    command
):

    command = command.lower().strip()


    patterns = [

        r"load previous (\d+) chat",

        r"load previous (\d+) chats",

        r"show previous (\d+) chat",

        r"show previous (\d+) chats",

        r"show last (\d+) chat",

        r"show last (\d+) chats",

        r"history (\d+)",
    ]


    for pattern in patterns:

        match = re.fullmatch(
            pattern,
            command
        )


        if match:

            return int(
                match.group(1)
            )


    return None


# ============================================================
# API ERROR HANDLING
# ============================================================


# ------------------------------------------------------------
# 13. CHECK DAILY QUOTA ERROR
# ------------------------------------------------------------

def is_daily_quota_error(error):

    error_text = str(error).upper()


    quota_terms = [

        "PER DAY LIMIT EXCEEDED",

        "GENERATE_CONTENT_FREE_TIER_REQUESTS",

        "GENERATEREQUESTSPERDAY",

        "REQUESTS PER DAY LIMIT EXCEEDED",

    ]


    return any(
        term in error_text
        for term in quota_terms
    )


# ------------------------------------------------------------
# 14. CHECK TEMPORARY ERROR
# ------------------------------------------------------------

def is_temporary_error(error):

    error_text = str(error).upper()


    temporary_terms = [

        "503",

        "UNAVAILABLE",

        "500",

        "INTERNAL",

        "504",

        "DEADLINE_EXCEEDED",

        "429",

    ]


    return any(
        term in error_text
        for term in temporary_terms
    )


# ------------------------------------------------------------
# 15. SEND REQUEST WITH RETRIES
# ------------------------------------------------------------

def invoke_with_retry(
    messages,
    max_attempts=3
):

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            return llm_obj.invoke(
                messages
            )


        except Exception as error:

            # Daily quota errors should NOT be retried.
            if is_daily_quota_error(error):

                raise


            # Other non-temporary errors
            if not is_temporary_error(error):

                raise


            # No retries left
            if attempt == max_attempts:

                raise


            wait_seconds = 2 ** attempt


            print(
                "\nBot: Gemini is temporarily busy."
            )

            print(
                f"Retrying in {wait_seconds} seconds..."
            )


            time.sleep(
                wait_seconds
            )


# ============================================================
# START APPLICATION
# ============================================================


# ------------------------------------------------------------
# 16. WELCOME MESSAGE
# ------------------------------------------------------------

print(
    "\n" + "=" * 70
)

print(
    "WELCOME TO YOUR CUSTOMIZED AI LEARNING ASSISTANT"
)

print(
    "=" * 70
)


# ------------------------------------------------------------
# 17. LOAD USER NAME
# ------------------------------------------------------------

username = load_username()


if username is None:

    username = input(
        "\nMay I know your name please? "
    ).strip()


    while not username:

        username = input(
            "Please enter your name: "
        ).strip()


    save_username(
        username
    )


    print(
        f"\nBot: Nice to meet you, {username}!"
    )


else:

    print(
        f"\nBot: Welcome back, {username}!"
    )


# ------------------------------------------------------------
# 18. SYSTEM PROMPT
# ------------------------------------------------------------

system_prompt = f"""
You are a customized AI Learning Assistant.

The user's name is {username}.

Your role is to help the user understand technical
and general topics in a simple, practical,
and beginner-friendly way.

Follow these rules:

1. Address the user by name when appropriate.

2. Explain difficult topics step by step.

3. Use beginner-friendly language.

4. Explain technical terms clearly.

5. Give practical examples when useful.

6. For programming questions, explain what
   the code is doing.

7. Use previous conversation context when relevant.

8. Keep answers organized and easy to understand.

9. Be friendly and professional.

10. Do not make simple answers unnecessarily long.
"""


# ------------------------------------------------------------
# 19. LOAD PREVIOUS HISTORY
# ------------------------------------------------------------

conversation_history = load_chat_history()


if not conversation_history:

    conversation_history = [

        SystemMessage(
            content=system_prompt
        )

    ]


else:

    if isinstance(
        conversation_history[0],
        SystemMessage
    ):

        conversation_history[0] = (
            SystemMessage(
                content=system_prompt
            )
        )

    else:

        conversation_history.insert(
            0,
            SystemMessage(
                content=system_prompt
            )
        )


# ------------------------------------------------------------
# 20. DISPLAY MEMORY STATUS
# ------------------------------------------------------------

chat_turns = get_chat_turns(
    conversation_history
)


print(
    f"Bot: I have {len(chat_turns)} "
    "saved chat(s)."
)


# ------------------------------------------------------------
# 21. DISPLAY COMMANDS
# ------------------------------------------------------------

print(
    "\nCommands:"
)

print(
    "exit / quit"
)

print(
    "clear chat"
)

print(
    "change name"
)

print(
    "load previous 2 chat"
)

print(
    "show last 5 chats"
)


# ============================================================
# CHAT LOOP
# ============================================================


while True:

    print()


    user_question = input(
        f"{username}: "
    ).strip()


    command = user_question.lower()


    # --------------------------------------------------------
    # 22. EXIT
    # --------------------------------------------------------

    if command in [
        "exit",
        "quit",
    ]:

        save_chat_history(
            conversation_history
        )


        print(
            f"\nBot: Goodbye {username}! "
            "Your conversation has been saved."
        )

        break


    # --------------------------------------------------------
    # 23. LOAD PREVIOUS CHATS
    # --------------------------------------------------------

    requested_history = (
        get_requested_history_count(
            user_question
        )
    )


    if requested_history is not None:

        show_previous_chats(
            conversation_history,
            requested_history
        )

        continue


    # --------------------------------------------------------
    # 24. CLEAR CHAT
    # --------------------------------------------------------

    if command == "clear chat":

        conversation_history = [

            SystemMessage(
                content=system_prompt
            )

        ]


        save_chat_history(
            conversation_history
        )


        print(
            "\nBot: Your saved conversation "
            "has been cleared."
        )

        continue


    # --------------------------------------------------------
    # 25. CHANGE NAME
    # --------------------------------------------------------

    if command == "change name":

        new_username = input(
            "\nBot: What name should I remember? "
        ).strip()


        if new_username:

            username = new_username


            save_username(
                username
            )


            print(
                f"\nBot: Got it! "
                f"I will remember you as {username}."
            )


        else:

            print(
                "\nBot: Name was not changed."
            )


        continue


    # --------------------------------------------------------
    # 26. EMPTY INPUT
    # --------------------------------------------------------

    if not user_question:

        print(
            "\nBot: Please enter a question."
        )

        continue


    # --------------------------------------------------------
    # 27. ADD USER MESSAGE
    # --------------------------------------------------------

    conversation_history.append(

        HumanMessage(
            content=user_question
        )

    )


    # --------------------------------------------------------
    # 28. CALL GEMINI
    # --------------------------------------------------------

    try:

        result = invoke_with_retry(
            conversation_history
        )


        response_text = get_response_text(
            result
        )


        conversation_history.append(

            AIMessage(
                content=response_text
            )

        )


        save_chat_history(
            conversation_history
        )


        print(
            f"\nBot: {response_text}"
        )


    except Exception as error:

        # Remove unanswered user message.
        if (
            conversation_history
            and isinstance(
                conversation_history[-1],
                HumanMessage
            )
        ):

            conversation_history.pop()


        # Daily quota exhausted
        if is_daily_quota_error(error):

            print(
                "\nBot: Your Gemini API daily quota "
                "has been exhausted."
            )

            print(
                "Your saved profile and chat history "
                "are still available locally."
            )

            print(
                "Commands such as 'load previous 2 chat' "
                "will continue to work."
            )


        # Other temporary error
        elif is_temporary_error(error):

            print(
                "\nBot: Gemini is temporarily unavailable."
            )

            print(
                "Please try the question again later."
            )


        # Other error
        else:

            print(
                "\nBot: Something went wrong."
            )

            print(
                f"Error: {error}"
            )


# ------------------------------------------------------------
# 29. PROGRAM END
# ------------------------------------------------------------

print(
    "\nChatbot stopped successfully."
)