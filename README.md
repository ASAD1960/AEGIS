# AEGIS 

**An intelligent agent platform designed to execute tasks, use tools, maintain conversational memory, and improve its decision-making through feedback and evaluation.**

AEGIS is a research-oriented AI agent project that explores how an AI system can move beyond simple question-and-answer interactions toward structured task execution, tool selection, persistent memory, and feedback-driven adaptation.

The project combines a Python-based agent engine, a FastAPI backend, a web interface, language model integrations, a persistent memory system, and a benchmarking framework.

Rather than focusing only on generating responses, AEGIS is designed around a broader question:

**Can feedback-driven adaptation improve an AI agent's task success while reducing repeated errors?**

The project provides a foundation for investigating this question through modular agent components, persistent records, evaluation datasets, and repeatable experiments.

---

## Technology Stack

AEGIS uses the following technologies and tools.

### Backend and Agent Engine

| Technology | Purpose |
|---|---|
| Python | Core agent implementation and application logic |
| FastAPI | Backend API and communication layer |
| Pydantic | Request validation and data models |
| SQLite | Persistent storage for conversations, memory, and application records |
| Uvicorn | ASGI server for running the API |

### Frontend

| Technology | Purpose |
|---|---|
| Next.js 16 | Web application framework |
| React 19 | User interface components |
| TypeScript | Type-safe frontend development |
| Tailwind CSS 4 | Interface styling |
| Lucide | Interface icons |

### Language Model Integrations

| Technology | Purpose |
|---|---|
| Cloudflare Workers AI | Cloud-based language model integration |
| Ollama | Local language model integration |

### Data Processing and Evaluation

- Custom benchmark datasets and scenario generation
- Dataset validation and splitting
- Agent response evaluation
- Benchmark execution and analytics
- Experiment result storage
- Feedback analysis and strategy selection

### Development and Testing

- Git and GitHub for version control
- Visual Studio Code for development
- Pytest for automated testing
- TypeScript compiler for frontend type checking
- Next.js production build for frontend verification

---

## Features

### 1. Intelligent Task Processing

AEGIS accepts user requests and processes them through its agent engine.

Implemented capabilities include:

- User task interpretation
- Task routing and tool selection
- General conversational responses
- Structured task execution
- Separation of agent logic and tool execution

### 2. Tool Execution System

AEGIS uses a modular tool architecture that allows the agent to select and execute supported tools.

Currently implemented tools include:

- **Calculator Tool:** Performs mathematical calculations.
- **Text Tool:** Handles supported text-processing and analysis tasks.
- **Data Analysis Tool:** Processes supported structured data and analysis requests.

The tool registry provides a centralized way to organize available tools.

### 3. Persistent Conversational Memory

AEGIS includes a SQLite-based conversation memory system.

Implemented capabilities include:

- Creating conversations
- Saving user messages
- Saving assistant responses
- Retrieving conversation history
- Listing previous conversations
- Restoring conversations through the frontend
- Deleting conversations
- Maintaining conversation identifiers
- Supplying previous messages to the Cloudflare language model integration

This allows users to continue previous conversations rather than treating every interaction as an entirely separate session.

### 4. Language Model Integration

AEGIS supports two language model integration paths:

**Cloudflare Workers AI**
- Cloud-based model communication
- Configurable model selection
- API authentication
- Conversation-history support
- Response processing and error handling

**Ollama**
- Local language model integration
- Support for running compatible models locally

The architecture separates language model communication from the main agent engine.

### 5. Feedback and Learning System

AEGIS includes a learning subsystem designed to record and analyze feedback.

Implemented components include:

- Feedback collection
- Feedback analysis
- Performance-based selection
- Strategy-related components
- Integration between agent execution and feedback records

The learning architecture provides a foundation for studying how previous outcomes can inform future agent decisions.

### 6. Benchmarking and Research Framework

AEGIS includes a dedicated benchmarking subsystem for evaluating agent behavior.

Implemented components include:

- Benchmark dataset generation
- Scenario families
- Dataset validation
- Dataset splitting
- Dataset pipelines
- Benchmark execution
- Evaluation
- Analytics
- Experiment result storage

This subsystem is intended to support repeatable evaluation rather than relying only on subjective impressions of response quality.

### 7. Web Application

AEGIS includes a Next.js-based frontend connected to the FastAPI backend.

Implemented interface capabilities include:

- Chat interface
- Backend connection status
- Conversation history
- Opening previous conversations
- Deleting conversations
- Starting new conversations
- Tool and system information sections
- Assistant response display

### 8. Backend API

The FastAPI application exposes endpoints for communication with the agent and its supporting features.

Current endpoints include:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend health |
| POST | `/api/tasks` | Submit a task to the agent |
| GET | `/api/conversations` | Retrieve conversation history |
| GET | `/api/conversations/{conversation_id}/messages` | Retrieve messages from a conversation |
| DELETE | `/api/conversations/{conversation_id}` | Delete a conversation |

The API also includes a CSV upload endpoint for supported data-analysis workflows.

---

## How AEGIS Works

The application follows a modular architecture.

A typical user interaction follows this process:

1. The user submits a request through the web interface.
2. The frontend sends the request to the FastAPI backend.
3. The backend identifies or creates the conversation.
4. Previous conversation messages are retrieved when available.
5. The agent processes the request and determines the appropriate execution path.
6. A supported tool or language model integration handles the request.
7. The agent produces a response.
8. The backend saves the user message and assistant response.
9. The frontend displays the result and refreshes the conversation history.

This separation makes it possible to develop and evaluate individual components without placing the entire application inside one large module.

---

## Project Architecture

AEGIS is organized into separate modules for agent execution, API communication, benchmarking, learning, language model integrations, memory, and tools.

### Project Structure

```text
AEGIS/
|
|-- app/
|   |
|   |-- agent/
|   |   |-- agent.py
|   |   |-- executor.py
|   |   |-- identity.py
|   |   |-- task_parser.py
|   |   |-- tool_selector.py
|   |
|   |-- api/
|   |   |-- main.py
|   |
|   |-- benchmark/
|   |   |-- analytics.py
|   |   |-- dataset.py
|   |   |-- dataset_generator.py
|   |   |-- dataset_pipeline.py
|   |   |-- dataset_splitter.py
|   |   |-- dataset_validator.py
|   |   |-- evaluator.py
|   |   |-- runner.py
|   |   |-- scenario_families.py
|   |   |-- storage.py
|   |
|   |-- core/
|   |   |-- config.py
|   |
|   |-- learning/
|   |   |-- analyzer.py
|   |   |-- feedback.py
|   |   |-- selector.py
|   |   |-- strategy.py
|   |
|   |-- llm/
|   |   |-- cloudflare_client.py
|   |   |-- ollama_client.py
|   |
|   |-- memory/
|   |   |-- database.py
|   |
|   |-- tools/
|   |   |-- base.py
|   |   |-- calculator_tool.py
|   |   |-- data_analysis_tool.py
|   |   |-- registry.py
|   |   |-- text_tool.py
|   |
|   |-- main.py
|
|-- frontend/
|   |-- src/
|   |   |-- app/
|   |       |-- globals.css
|   |       |-- layout.tsx
|   |       |-- page.tsx
|   |
|   |-- package.json
|
|-- tests/
|   |-- conftest.py
|   |-- test_agent_data_analysis.py
|   |-- test_agent_integration.py
|   |-- test_agent_request_routing.py
|   |-- test_agent_text_analysis.py
|   |-- test_analyzer.py
|   |-- test_api.py
|   |-- test_benchmark_analytics.py
|   |-- test_benchmark_runner.py
|   |-- test_calculator_tool.py
|   |-- test_character_symbol_scenarios.py
|   |-- test_conversation_memory.py
|   |-- test_dataset_generator.py
|   |-- test_dataset_pipeline.py
|   |-- test_dataset_splitter.py
|   |-- test_dataset_validator.py
|   |-- test_data_analysis_tool.py
|   |-- test_evaluator.py
|   |-- test_executor.py
|   |-- test_feedback.py
|   |-- test_feedback_integration.py
|   |-- test_memory.py
|   |-- test_research_runner_persistence.py
|   |-- test_research_storage.py
|   |-- test_selector.py
|   |-- test_sentence_boundary_scenarios.py
|   |-- test_strategy.py
|   |-- test_task_parser.py
|   |-- test_text_tool.py
|   |-- test_tool_registry.py
|   |-- test_tool_selector.py
|
|-- requirements.txt
|-- test_agent.py
|-- verify_database.py
|-- .gitignore
|-- README.md
```

---

## Benchmarking and Evaluation

A central part of AEGIS is its research and evaluation framework.

The benchmark subsystem is designed to support structured experiments involving agent tasks, execution outcomes, and performance analysis.

Its components cover:

- Dataset generation
- Scenario organization
- Dataset validation
- Dataset splitting
- Benchmark execution
- Result evaluation
- Performance analytics
- Experiment persistence

The project also includes tests for benchmark execution, analytics, dataset processing, evaluation, and research-result storage.

### Research Objective

The primary research direction is to investigate whether feedback-driven adaptation can improve task success and reduce repeated errors.

Future experiments will compare different agent configurations under controlled conditions, using consistent datasets and evaluation procedures.

---

## Installation and Setup

### Requirements

- Python development environment
- Node.js and npm
- Git
- Visual Studio Code (recommended)
- Cloudflare Workers AI credentials for cloud model usage
- Ollama and a compatible model for local model usage

### 1. Clone the Repository

```bash
git clone https://github.com/ASAD1960/AEGIS.git
cd AEGIS
```

### 2. Create a Python Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install Backend Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

For Cloudflare Workers AI, configure the following variables in your backend terminal:

```powershell
$env:CLOUDFLARE_ACCOUNT_ID="YOUR_ACCOUNT_ID"
$env:CLOUDFLARE_API_TOKEN="YOUR_API_TOKEN"
```

Replace the placeholders with your own credentials.

**Security:** Never commit API tokens, passwords, or private environment files to GitHub.

### 5. Install Frontend Dependencies

Open another terminal:

```powershell
cd frontend
npm install
```

---

## Running AEGIS

The backend and frontend run in separate terminals.

### Start the Backend

From the project root:

```powershell
python -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

Backend address:

```text
http://127.0.0.1:8000
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

### Start the Frontend

In a separate terminal:

```powershell
cd frontend
npm run dev
```

Frontend address:

```text
http://localhost:3000
```

Open the frontend address in your browser to use AEGIS.

---

## Testing and Verification

AEGIS includes an automated test suite covering the main application components.

The tests are organized around:

| Area | Testing coverage |
|---|---|
| Agent | Integration, routing, and request processing |
| Tools | Calculator, text processing, data analysis, and registry |
| Memory | Database operations and conversation persistence |
| API | Backend endpoints and request handling |
| Learning | Feedback, analysis, selection, and strategy |
| Benchmarking | Dataset generation, validation, execution, and analytics |
| Research | Evaluation and experiment-result persistence |

### Run the Complete Backend Test Suite

From the project root:

```powershell
python -m pytest
```

### Run Tests with Detailed Output

```powershell
python -m pytest -v
```

### Run a Specific Test File

For example:

```powershell
python -m pytest tests/test_conversation_memory.py -v
```

### Verify the Database

```powershell
python verify_database.py
```

### Check Frontend TypeScript

From the frontend directory:

```powershell
npx tsc --noEmit
```

### Build the Frontend

```powershell
npm run build
```

The automated suite covers the implemented backend functionality. Test results should be generated from the current repository state when reporting a release or research experiment.

---

## Current Limitations

AEGIS is an actively developed research-oriented project. Its current implementation provides an agent engine, memory, tool integrations, learning components, and benchmarking infrastructure, but it is not yet a fully autonomous general-purpose intelligence system.

Current limitations and areas requiring further development include:

- Learning and feedback components need more extensive controlled evaluation.
- Persistent memory is currently based on SQLite.
- Cloudflare and Ollama integrations have different execution capabilities.
- The agent's planning and reasoning capabilities require further development.
- Tool execution requires stronger permission and safety controls.
- Benchmark results need broader experiments and reproducibility analysis.
- Production deployment requires appropriate hosting, security, and database configuration.

These limitations are important considerations when interpreting the current capabilities of the system.

---

## Future Development Roadmap

The following items represent planned improvements, not claims about features already completed.

### 1. Advanced Agent Planning

- Multi-step task planning
- Task decomposition
- Dependency-aware execution
- Dynamic plan adjustment
- Execution-state tracking

### 2. Improved Memory Architecture

- Structured long-term memory
- Memory retrieval and relevance ranking
- User preference memory
- Context summarization
- Memory management and retention policies

### 3. Feedback-Driven Adaptation

- More advanced feedback analysis
- Learning from previous execution outcomes
- Strategy adaptation
- Error-pattern identification
- Reduction of repeated execution failures

### 4. Expanded Tool Ecosystem

- More external tool integrations
- File-processing tools
- Research and information-retrieval tools
- Tool chaining
- Tool execution monitoring

### 5. Safety and Controlled Autonomy

- Permission-based tool execution
- Human approval for sensitive actions
- Execution limits
- Input and output validation
- Audit trails
- Failure recovery

### 6. Advanced Benchmarking

- Larger benchmark datasets
- More diverse task scenarios
- Baseline agent comparisons
- Ablation studies
- Success-rate analysis
- Repeated-error measurement
- Reproducible experiment reports

### 7. Frontend and Deployment

- Improved monitoring and analytics
- Better visualization of agent execution
- Deployment-ready configuration
- Production database integration
- Authentication and access control
- More comprehensive operational logging

---

## Research Direction

AEGIS is intended to develop beyond a conventional chatbot by investigating the relationship between memory, feedback, tool use, and agent performance.

The primary research question is:

**Can feedback-driven adaptation improve task success while reducing repeated errors in an AI agent?**

Potential research experiments include:

1. Comparing an agent with feedback adaptation against a baseline without adaptation.
2. Measuring task success across repeated benchmark runs.
3. Investigating whether stored feedback reduces recurring execution errors.
4. Evaluating the effect of conversation memory on multi-turn task completion.
5. Studying how different tool-selection strategies affect execution outcomes.

The benchmarking framework provides the foundation for developing these experiments and documenting their results.

---

## Author

**Asad Yar**

AEGIS — Self-Learning AI Agent

GitHub: [ASAD1960](https://github.com/ASAD1960)

Project Repository: [github.com/ASAD1960/AEGIS](https://github.com/ASAD1960/AEGIS)

---

© 2026 Asad Yar. All rights reserved.