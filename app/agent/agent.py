"""
AEGIS Agent Core

Main agent connecting tools, tool selection,
task parsing, strategies, execution and feedback.

Supports persistent conversational context through
conversation history and personal memories.
"""

import os

from app.agent.identity import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_CAPABILITIES,
)

from app.tools.text_tool import TextAnalysisTool
from app.tools.calculator_tool import CalculatorTool
from app.tools.data_analysis_tool import DataAnalysisTool
from app.tools.registry import ToolRegistry

from app.agent.tool_selector import ToolSelector
from app.agent.task_parser import TaskParser

from app.learning.selector import StrategySelector
from app.learning.feedback import FeedbackSystem
from app.agent.executor import TaskExecutor

from app.llm.ollama_client import OllamaClient
from app.llm.cloudflare_client import CloudflareClient


class Agent:

    def __init__(self):

        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.capabilities = AGENT_CAPABILITIES
        self.status = "Initialized"

        # Register available tools.
        self.tool_registry = ToolRegistry()

        self.tool_registry.register(TextAnalysisTool())
        self.tool_registry.register(CalculatorTool())
        self.tool_registry.register(DataAnalysisTool())

        # Keep the existing text-analysis interface.
        self.text_tool = self.tool_registry.get("text_analysis")

        # Initialize tool selection and task parsing.
        self.tool_selector = ToolSelector()
        self.task_parser = TaskParser()

        self.strategy_selector = StrategySelector()
        self.feedback_system = FeedbackSystem()

        # Preserve the existing research execution engine.
        self.executor = TaskExecutor()

        # Initialize the local language model.
        self.llm_client = OllamaClient()

        # Select the language model provider.
        # Cloudflare is the default provider.
        # Ollama remains available for local development.
        self.llm_provider = os.getenv(
            "AEGIS_LLM_PROVIDER",
            "cloudflare"
        ).strip().lower()

        self.last_execution = None

    def get_status(self):
        return self.status

    def introduce(self):

        print(f"My name is {self.name}.")
        print(self.role)
        print(f"My current status is: {self.status}")

    def list_tools(self):
        """Return metadata for all registered tools."""

        return self.tool_registry.list_tools()

    def select_tool(self, task):
        """Select an appropriate registered tool for a task."""

        selected_tool = self.tool_selector.select(task)

        if not self.tool_registry.has_tool(selected_tool):
            raise RuntimeError(
                f"Selected tool is not registered: {selected_tool}"
            )

        return selected_tool

    def execute_tool(self, tool_name, **kwargs):
        """Execute a registered tool by its name."""

        self.status = "Working"

        try:

            tool = self.tool_registry.get(tool_name)

            return tool.execute(**kwargs)

        finally:
            self.status = "Initialized"

    def process_request(
        self,
        task,
        file_path=None,
        filter_column=None,
        filter_operator=None,
        filter_value=None,
        conversation_history=None,
        personal_memories=None,
    ):
        """
        Unified entry point for processing user requests.

        Handles simple conversation directly and delegates
        supported tasks to their registered tools.

        General questions are handled by the configured
        language model provider with optional conversation history
        and persistent personal memories.

        CSV requests require file_path. Optional CSV filtering
        arguments are forwarded to the data-analysis tool.

        Args:
            task: Current user request.
            file_path: Optional CSV file path.
            filter_column: Optional CSV filter column.
            filter_operator: Optional CSV filter operator.
            filter_value: Optional CSV filter value.
            conversation_history: Previous conversation messages.
            personal_memories: Authenticated user's active personal memories.

        Returns:
            dict: Tool name, arguments and execution result.
        """

        if not isinstance(task, str) or not task.strip():
            raise ValueError(
                "Task must be a non-empty string."
            )

        # Normalize the message for conversational matching.
        normalized_task = " ".join(task.casefold().split())
        normalized_task = normalized_task.strip(" .,!?")

        # Handle simple greetings without requiring a tool.
        greetings = {
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "how are you doing",
        }

        if normalized_task in greetings:
            return {
                "tool_name": "conversation",
                "arguments": {},
                "result": (
                    "Hello! I'm AEGIS, your local intelligent assistant. "
                    "I can help you with calculations, text analysis, "
                    "and CSV data analysis. What would you like to work on?"
                ),
            }

        # Handle identity questions.
        if normalized_task in {
            "who are you",
            "what are you",
            "what is your name",
        }:
            return {
                "tool_name": "conversation",
                "arguments": {},
                "result": (
                    "I'm AEGIS, an intelligent assistant. "
                    "I currently support calculations, text analysis, "
                    "and CSV data analysis through my registered tools."
                ),
            }

        # Handle capability questions.
        if normalized_task in {
            "what can you do",
            "help",
            "show me your capabilities",
        }:
            return {
                "tool_name": "conversation",
                "arguments": {},
                "result": (
                    "I can perform calculations, analyze text, and "
                    "analyze CSV datasets. Give me a supported task "
                    "and I'll route it to the appropriate registered tool."
                ),
            }

        # Identify the appropriate tool for supported tasks.
        # Unrecognized requests are handled by the language model.
        try:
            tool_name = self.select_tool(task)

        except ValueError:
            return self.process_general_chat(
                task,
                conversation_history=conversation_history,
                personal_memories=personal_memories,
            )

        # Route calculation requests.
        if tool_name == "calculator":
            return self.process_calculation(task)

        # Route text-analysis requests.
        if tool_name == "text_analysis":
            return self.process_text_analysis(task)

        # Route CSV data-analysis requests.
        if tool_name == "data_analysis":

            if not file_path:
                raise ValueError(
                    "A file_path is required for CSV data analysis."
                )

            return self.process_data_analysis(
                task=task,
                file_path=file_path,
                filter_column=filter_column,
                filter_operator=filter_operator,
                filter_value=filter_value,
            )

        raise ValueError(
            f"Unsupported task type: {tool_name}"
        )

    def process_general_chat(
        self,
        task,
        conversation_history=None,
        personal_memories=None,
    ):
        """
        Generate a response using the configured language model.

        Cloudflare is the default provider.
        Ollama remains available as a local alternative.

        Args:
            task: Current user message.
            conversation_history: Previous conversation messages.
            personal_memories: Authenticated user's active personal memories.

        Returns:
            dict: Provider information and generated response.
        """

        self.status = "Working"

        try:

            if self.llm_provider == "cloudflare":

                client = CloudflareClient()

                result = client.generate_response(
                    task,
                    conversation_history=conversation_history,
                    personal_memories=personal_memories,
                )

                return {
                    "tool_name": "cloudflare",
                    "arguments": {
                        "model": client.model,
                        "provider": "cloudflare",
                    },
                    "result": result,
                }

            elif self.llm_provider == "ollama":

                result = self.llm_client.generate_response(
                    task,
                    conversation_history=conversation_history,
                    personal_memories=personal_memories,
                )

                return {
                    "tool_name": "ollama",
                    "arguments": {
                        "model": self.llm_client.model,
                        "provider": "ollama",
                    },
                    "result": result,
                }

            else:
                raise ValueError(
                    f"Unsupported LLM provider: {self.llm_provider}"
                )

        finally:
            self.status = "Initialized"

    def process_calculation(self, task):
        """
        Parse and execute a natural-language calculation request.

        Returns:
            dict: Selected tool, parsed arguments and execution result.
        """

        self.status = "Working"

        try:

            parsed = self.task_parser.parse(task)

            tool_name = parsed["tool_name"]
            arguments = parsed["arguments"]

            # Confirm that the intended tool is registered.
            registered_tool = self.select_tool(task)

            if registered_tool != tool_name:
                raise RuntimeError(
                    "Selected tool does not match the parsed request."
                )

            # Execute using the existing registered tool.
            tool = self.tool_registry.get(tool_name)
            result = tool.execute(**arguments)

            return {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
            }

        finally:
            self.status = "Initialized"

    def process_text_analysis(self, task):
        """
        Process a natural-language text-analysis request.

        Supported formats:
            Analyze this text: <text>
            Count the words and characters in this text: <text>

        Returns:
            dict: Selected tool, extracted text and analysis results.
        """

        self.status = "Working"

        try:

            # Confirm that this request belongs to text analysis.
            tool_name = self.select_tool(task)

            if tool_name != "text_analysis":
                raise ValueError(
                    "This request is not a text-analysis task."
                )

            # Extract the text after the first colon.
            _, separator, content = task.partition(":")

            if not separator:
                raise ValueError(
                    "Provide the text after a colon."
                )

            content = content.strip()

            if not content:
                raise ValueError(
                    "Text content cannot be empty."
                )

            # Execute through the registered text-analysis tool.
            tool = self.tool_registry.get(tool_name)
            result = tool.execute(text=content)

            return {
                "tool_name": tool_name,
                "arguments": {
                    "text": content,
                },
                "result": result,
            }

        finally:
            self.status = "Initialized"

    def process_data_analysis(
        self,
        task,
        file_path,
        filter_column=None,
        filter_operator=None,
        filter_value=None,
    ):
        """
        Process a natural-language CSV analysis request.

        Optional filtering requires all three filter arguments.

        Returns:
            dict: Selected tool, execution arguments and analysis results.
        """

        self.status = "Working"

        try:

            # Confirm that this request belongs to data analysis.
            tool_name = self.select_tool(task)

            if tool_name != "data_analysis":
                raise ValueError(
                    "This request is not a CSV data-analysis task."
                )

            # Prepare the arguments for the registered CSV tool.
            arguments = {
                "file_path": file_path,
            }

            # Filtering must be supplied as a complete set.
            filter_options = (
                filter_column,
                filter_operator,
                filter_value,
            )

            if any(value is not None for value in filter_options):

                if not all(value is not None for value in filter_options):
                    raise ValueError(
                        "Filtering requires filter_column, "
                        "filter_operator and filter_value."
                    )

                arguments.update({
                    "filter_column": filter_column,
                    "filter_operator": filter_operator,
                    "filter_value": filter_value,
                })

            # Execute through the registered data-analysis tool.
            tool = self.tool_registry.get(tool_name)
            result = tool.execute(**arguments)

            return {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
            }

        finally:
            self.status = "Initialized"

    def analyze_text(self, text):

        self.status = "Working"

        try:
            return self.text_tool.analyze(text)

        finally:
            self.status = "Initialized"

    def choose_strategy(self):
        return self.strategy_selector.select_strategy()

    def perform_task(self, text, strategy_id=None):

        self.status = "Working"
        self.last_execution = None

        try:

            if strategy_id is None:

                strategy = self.choose_strategy()

                strategy_id = next(
                    key
                    for key, value in
                    self.strategy_selector.strategy_system
                    .get_all_strategies().items()
                    if value == strategy
                )

            result = self.executor.execute(
                text,
                strategy_id
            )

            result["strategy_id"] = strategy_id

            self.last_execution = {
                "task": text,
                "strategy_id": strategy_id,
            }

            return result

        finally:
            self.status = "Initialized"

    def record_feedback(self, rating, comment=""):

        if self.last_execution is None:
            raise RuntimeError(
                "Execute a task before recording feedback."
            )

        return self.feedback_system.record_feedback(
            task=self.last_execution["task"],
            rating=rating,
            comment=comment,
            strategy_id=self.last_execution["strategy_id"],
        )
