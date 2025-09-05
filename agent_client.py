# langgraph_agent.py
import os
from typing import Optional, Tuple
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

DEFAULT_AGENT_URL   = os.getenv("AGENT_URL", "http://localhost:2024")
DEFAULT_ASSISTANT_ID = os.getenv("ASSISTANT_ID", "react_planner")


class LangGraphAgent:
    """
    Thin async wrapper around the LangGraph SDK client.
    Usage
    -----
        agent = LangGraphAgent()
        thread_id, ai_text = await agent.chat("Hello!")
    """

    def __init__(
        self,
        agent_url: str = DEFAULT_AGENT_URL,
        assistant_id: str = DEFAULT_ASSISTANT_ID,
        *,
        webhook_url: Optional[str] = 'https://langgraph.free.beeceptor.com',
    ):
        self.client = get_client(url=agent_url)
        self.assistant_id = assistant_id
        self.webhook_url = webhook_url

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    async def chat(
        self, user_message: str, thread_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Send a user message to the agent.
        Returns
        -------
        (thread_id, ai_message_text)
        """
        thread_id = await self._get_or_create_thread(thread_id)
        ai_text = await self._run_agent(user_message, thread_id)
        return thread_id, ai_text

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    async def _get_or_create_thread(self, thread_id: Optional[str]) -> str:
        thread = await self.client.threads.create(
            thread_id=thread_id, if_exists="do_nothing"
        )
        return thread["thread_id"]

    async def _run_agent(self, user_message: str, thread_id: str) -> str:
        run_result = await self.client.runs.wait(
            thread_id,
            assistant_id=self.assistant_id,
            input={"messages": [{"role": "user", "content": user_message}]},
            webhook=self.webhook_url,
        )

        # last AI message
        messages = run_result.get("messages", [])
        ai_msg = next((m for m in reversed(messages) if m.get("type") == "ai"), None)
        if ai_msg is None:
            raise RuntimeError("No AI message returned by agent")
        return ai_msg["content"]
    
    
import asyncio

async def main():
    agent = LangGraphAgent()
    tid, reply = await agent.chat("Plan a 3-day trip to Tokyo")
    print("Thread:", tid)
    print("AI   :", reply)

if __name__ == "__main__":
    asyncio.run(main())