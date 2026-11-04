"""
AEGIS Ollama Client

Provides communication with a locally running Ollama model.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaClient:
    """Communicate with a local Ollama language model."""

    def __init__(
        self,
        base_url="http://localhost:11434",
        model="qwen3:4b",
        timeout=600,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate_response(self, prompt):
        """
        Generate a response using the configured local model.

        Args:
            prompt: User's message.

        Returns:
            str: Model-generated response.

        Raises:
            ValueError: If the prompt is empty.
            ConnectionError: If Ollama is unavailable.
            RuntimeError: If Ollama returns an error.
        """

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt.strip(),
                }
            ],
            "stream": False,
        }

        request = Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))

        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {error.code}: {details}"
            ) from error

        except (URLError, TimeoutError) as error:
            raise ConnectionError(
                "Unable to connect to Ollama. "
                "Make sure Ollama is running."
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError(
                "Ollama returned an invalid response."
            ) from error

        content = result.get("message", {}).get("content", "")

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return content.strip()