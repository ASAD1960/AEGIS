
"""
AEGIS Cloudflare Workers AI Client

Connects AEGIS to a cloud-hosted language model
through the Cloudflare Workers AI REST API.

Supports bounded conversation history for contextual responses.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_HISTORY_MESSAGES = 20


class CloudflareClient:
    """Communicate with Cloudflare Workers AI."""

    def __init__(
        self,
        account_id=None,
        api_token=None,
        model="@cf/zai-org/glm-4.7-flash",
        timeout=120,
    ):
        self.account_id = (
            account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")
        )
        self.api_token = (
            api_token or os.getenv("CLOUDFLARE_API_TOKEN")
        )
        self.model = model
        self.timeout = timeout

        if not self.account_id:
            raise ValueError("Cloudflare Account ID is missing.")

        if not self.api_token:
            raise ValueError("Cloudflare API token is missing.")

    @staticmethod
    def _prepare_history(conversation_history):
        """
        Prepare previous conversation messages.

        Only valid user and assistant messages are included.
        System messages and malformed records are ignored.
        """

        if conversation_history is None:
            return []

        if not isinstance(conversation_history, (list, tuple)):
            raise ValueError(
                "Conversation history must be a list or tuple."
            )

        prepared_messages = []

        for message in conversation_history:
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")

            if role not in ("user", "assistant"):
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            prepared_messages.append(
                {
                    "role": role,
                    "content": content.strip(),
                }
            )

        return prepared_messages[-MAX_HISTORY_MESSAGES:]

    def generate_response(self, prompt, conversation_history=None):
        """
        Generate a response using Cloudflare Workers AI.

        Args:
            prompt: Current user's message.
            conversation_history: Optional previous user/assistant messages.

        Returns:
            str: Model-generated response.
        """

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        history = self._prepare_history(conversation_history)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are AEGIS, a helpful and reliable "
                    "AI assistant. Give clear, accurate, "
                    "and useful answers. Use previous conversation "
                    "messages when relevant to understand context "
                    "and maintain continuity. Never invent memories "
                    "or claim to remember information that is not "
                    "present in the supplied conversation."
                ),
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": prompt.strip(),
            }
        )

        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )

        payload = {
            "messages": messages
        }

        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as error:
            details = error.read().decode(
                "utf-8", errors="replace"
            )
            raise RuntimeError(
                f"Cloudflare returned HTTP {error.code}: {details}"
            ) from error

        except (URLError, TimeoutError) as error:
            raise ConnectionError(
                "Unable to connect to Cloudflare Workers AI."
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError(
                "Cloudflare returned an invalid response."
            ) from error

        if result.get("success") is False:
            raise RuntimeError(
                f"Cloudflare API error: {result.get('errors')}"
            )

        response_data = result.get("result", {})
        choices = response_data.get("choices", [])

        if not choices:
            raise RuntimeError(
                "Cloudflare returned no response choices."
            )

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Cloudflare returned an empty response."
            )

        return content.strip()
