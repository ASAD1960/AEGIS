# AEGIS — Self-Learning AI Agent

<p align="center">
  <strong>An AI agent platform built to understand tasks, use tools, learn from feedback, and evaluate its performance.</strong>
</p>

<p align="center">
  <a href="https://github.com/ASAD1960/AEGIS">GitHub Repository</a> •
  <a href="https://aegis-cyan-phi.vercel.app/">Live Application</a> •
  <a href="https://github.com/ASAD1960">Developer Profile</a>
</p>

## Introduction

**AEGIS is an AI agent platform designed to understand user requests, perform tasks using available tools, remember conversations, and improve its approach through user feedback.**

Instead of simply generating text, AEGIS can select and use tools to perform tasks such as calculations, text processing, and data analysis. It also stores conversation history so users can return to previous conversations.

The project explores an important question:

**Can user feedback help an AI agent perform tasks more successfully and avoid repeating mistakes?**

AEGIS is being developed as a modular research project, with a focus on practical AI capabilities, feedback-based improvement, and measurable performance evaluation.

## Project Links

| Resource | Link |
|---|---|
| GitHub Repository | [ASAD1960/AEGIS](https://github.com/ASAD1960/AEGIS) |
| Live Application | [Open AEGIS](https://aegis-cyan-phi.vercel.app/) |
| Developer Profile | [Asad Yar](https://github.com/ASAD1960) |

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| Frontend | Next.js 16, React 19, TypeScript |
| Styling | Tailwind CSS 4 |
| AI Integration | Cloudflare Workers AI, Ollama |
| Database | SQLite, configurable PostgreSQL |
| Data Processing | Python, CSV workflows |
| Testing | Pytest, TypeScript Compiler |
| Development Tools | Git, GitHub, Visual Studio Code |

## Key Features

### 1. AI Agent and Task Processing
- Processes user requests and identifies the intended task.
- Selects suitable tools based on the task.
- Coordinates tool execution.
- Returns results through the conversational interface.

### 2. Tool Integration

AEGIS currently includes modular tools for:

- **Calculator:** Performs mathematical calculations.
- **Text Processing:** Handles basic text-related operations.
- **Data Analysis:** Supports data analysis workflows.
- **CSV Processing:** Works with uploaded CSV data.

The modular design allows additional tools to be integrated as the project develops.

### 3. Language Model Integration

AEGIS supports multiple language model providers:

- **Cloudflare Workers AI:** Provides access to cloud-hosted AI models.
- **Ollama:** Supports local language model integration.

This approach provides flexibility in choosing between cloud-based and locally running models.

### 4. Conversation Management
- Creates new conversations.
- Stores conversation messages.
- Retrieves previous conversations.
- Displays conversation history.
- Supports opening and deleting conversations.

Conversation persistence allows users to return to previous interactions.

### 5. Feedback and Learning Components

AEGIS includes a feedback-based learning architecture designed to analyze user evaluations and support improvements in future task execution.

Current components include:
- Feedback collection and storage.
- Feedback analysis.
- Performance-based selection components.
- Learning strategy components.
- Integration with the agent workflow.

The effectiveness of these components still requires systematic experimentation and evaluation.

### 6. Benchmarking and Evaluation

AEGIS includes a modular benchmarking framework to support structured performance testing.

Its components include:
- Benchmark dataset generation.
- Scenario families.
- Dataset validation.
- Dataset splitting.
- Dataset processing pipelines.
- Benchmark execution.
- Performance evaluation.
- Analytics and experiment storage.

This framework provides a foundation for comparing agent performance across different test scenarios.

### 7. Web Interface

The frontend provides a conversational interface for interacting with AEGIS.

Current interface features include:
- Chat-based interaction.
- Conversation history.
- Create, open, and delete conversations.
- Backend and system status information.
- Tool information.
- Light, Dark, and System appearance preferences.

## System Architecture

AEGIS follows a modular architecture that separates the user interface, API, agent engine, tools, learning components, and persistent storage.

```text
                 USER
                   |
                   v
          NEXT.JS WEB INTERFACE
                   |
                   v
              FASTAPI
                   |
                   v
              AI AGENT
                   |
          +--------+--------+
          |        |        |
          v        v        v
       TASK     TOOL      LLM
     PROCESSING SELECTION INTEGRATION
                   |
                   v
             TOOL EXECUTION
                   |
          +--------+--------+
          |        |        |
          v        v        v
       CALCULATOR TEXT    DATA
                 TOOLS   ANALYSIS
                   |
                   v
              TASK RESULT
                   |
                   v
             USER FEEDBACK
                   |
                   v
          LEARNING COMPONENTS
                   |
                   v
          PERFORMANCE ANALYSIS

        DATABASE AND PERSISTENCE
        Support conversation,
        feedback, and experiment records.
```

## Project Structure

The project is organized into separate modules to make development, testing, and future expansion easier.

```text
AEGIS/
│
├── app/
│   ├── agent/
│   │   ├── agent.py
│   │   ├── executor.py
│   │   ├── identity.py
│   │   ├── task_parser.py
│   │   └── tool_selector.py
│   │
│   ├── api/
│   │   └── main.py
│   │
│   ├── benchmark/
│   │   ├── analytics.py
│   │   ├── dataset.py
│   │   ├── dataset_generator.py
│   │   ├── dataset_pipeline.py
│   │   ├── dataset_splitter.py
│   │   ├── dataset_validator.py
│   │   ├── evaluator.py
│   │   ├── runner.py
│   │   ├── scenario_families.py
│   │   └── storage.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── learning/
│   │   ├── analyzer.py
│   │   ├── feedback.py
│   │   ├── selector.py
│   │   └── strategy.py
│   │
│   ├── llm/
│   │   ├── cloudflare_client.py
│   │   └── ollama_client.py
│   │
│   ├── memory/
│   │   └── database.py
│   │
│   ├── tools/
│   │   ├── base.py
│   │   ├── calculator_tool.py
│   │   ├── data_analysis_tool.py
│   │   ├── registry.py
│   │   └── text_tool.py
│   │
│   └── main.py
│
├── frontend/
│   └── src/
│       └── app/
│           ├── globals.css
│           ├── layout.tsx
│           └── page.tsx
│
├── tests/
│
├── data/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Database and Persistence

AEGIS uses a database layer to store application information.

Current database functionality includes:
- Conversation records.
- Conversation messages.
- Feedback records.
- Benchmark and experiment records.

SQLite is supported for local development, while PostgreSQL can be configured through the `AEGIS_DATABASE_URL` environment variable.

## Installation and Setup

### Prerequisites

Install the following before running AEGIS:

- Python
- Node.js and npm
- Git
- A code editor such as Visual Studio Code

### 1. Clone the Repository

```powershell
git clone https://github.com/ASAD1960/AEGIS.git
cd AEGIS
```

### 2. Create a Python Virtual Environment

```powershell
python -m venv .venv
```

Activate it in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install Backend Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure AI Provider Credentials

For Cloudflare Workers AI, configure the required environment variables:

```powershell
$env:CLOUDFLARE_ACCOUNT_ID="your_account_id"
$env:CLOUDFLARE_API_TOKEN="your_api_token"
```

Ollama can also be configured for local model integration.

Keep API credentials private. Never commit real tokens, passwords, or secret keys to GitHub.

### 5. Configure the Database (Optional)

SQLite can be used for local development.

For PostgreSQL, configure:

```powershell
$env:AEGIS_DATABASE_URL="your_database_connection_string"
```

### 6. Install Frontend Dependencies

Open another PowerShell terminal:

```powershell
cd frontend
npm.cmd install
```

## Running AEGIS Locally

### Start the Backend

From the project root:

```powershell
python -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

### Start the Frontend

Open another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Frontend:

`http://localhost:3000`

## API Endpoints

The backend exposes API routes for application health, agent interaction, tools, data uploads, and conversation management.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Application status |
| GET | `/api/tools` | Available tools |
| POST | `/api/tasks` | Submit a task |
| POST | `/api/data/upload` | Upload data |
| GET | `/api/conversations` | Retrieve conversations |
| GET | `/api/conversations/{conversation_id}/messages` | Retrieve conversation messages |
| DELETE | `/api/conversations/{conversation_id}` | Delete a conversation |

For the latest API behavior and request formats, refer to the backend documentation at `/docs` when running the application.

## Testing and Quality Assurance

Testing is an important part of AEGIS development.

### Run Backend Tests

Run the complete test suite:

```powershell
python -m pytest
```

For detailed output:

```powershell
python -m pytest -v
```

### Check Frontend TypeScript

From the frontend directory:

```powershell
npx tsc --noEmit
```

### Build the Frontend

```powershell
npm.cmd run build
```

These checks help identify backend test failures, TypeScript errors, and frontend build issues.

## Research Direction

AEGIS is being developed around the following research question:

**Can feedback-driven adaptation improve an AI agent's task success while reducing repeated errors?**

The project aims to investigate how an agent can use feedback and performance history to make better decisions when handling future tasks.

The research direction includes:

1. Establishing baseline agent performance.
2. Collecting feedback from task execution.
3. Analyzing feedback and identifying recurring problems.
4. Exploring feedback-based strategy selection.
5. Evaluating performance across benchmark scenarios.
6. Comparing results to understand whether feedback-based adaptation produces measurable improvements.

The benchmarking framework provides a foundation for conducting these experiments in a structured and reproducible way.

## Current Limitations

AEGIS is an actively developing research project. Some capabilities require further implementation and validation.

Current limitations include:

- Feedback-based improvement has not yet been established as a proven performance gain.
- Advanced long-term semantic memory remains an area for future development.
- Complex multi-step autonomous planning requires further work.
- Tool permission management and stronger execution safeguards need additional development.
- Broader benchmark experiments are needed to establish reliable performance comparisons.
- Production deployment, security, and scalability require further hardening.

These limitations are part of the project's ongoing development and research process.

## Development Roadmap

| Area | Planned Improvements |
|---|---|
| Agent Intelligence | More capable task planning and execution |
| Memory | Improved long-term and contextual memory |
| Learning | More effective feedback-driven adaptation |
| Tool System | Additional tools and integrations |
| Evaluation | Larger benchmark datasets and controlled experiments |
| Safety | Better tool permissions and execution controls |
| Performance | Improved reliability and efficiency |
| Research | Reproducible experiments and documented results |

## Author

**Asad Yar**

Computer Science Graduate
Developer and Researcher

GitHub: [@ASAD1960](https://github.com/ASAD1960)

**AEGIS — Self-Learning AI Agent**

A research-driven project exploring practical AI agents, tool use, feedback-based adaptation, and performance evaluation.
