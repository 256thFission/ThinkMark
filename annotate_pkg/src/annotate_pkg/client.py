from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import Any, Dict, List, Optional

load_dotenv()

class LLMClient:
    """Utility class to interact with OpenRouter chat endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize OpenRouter client and default model."""
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set in environment or argument")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )

        self.model = model or os.getenv(
            "OPENROUTER_MODEL",
            "google/gemini-2.0-flash-lite-001"
        )


    def summarize_markdown(
        self,
        markdown_object: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Summarize a markdown object via OpenRouter."""
        model_to_use = model or self.model
        messages = [{"role": "system",
         "content": "Describe this doccumentation page in 1-2 sentance summary for an index. If it does not contain useful information for a developer agent, respond with FAIL."},
                    {"role": "user", "content": markdown_object}]
        return self.client.chat.completions.create(
            messages=messages,
            model=model_to_use,
            **kwargs
        )

    