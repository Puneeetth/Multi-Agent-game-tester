# Multi-Agent Game Tester POC

A multi-agent system for automated testing of web-based puzzle/math games using LangChain, Playwright, and local vision models.

## Features

- 🎯 **Intelligent Test Generation**: Generates 20+ test cases using LangChain
- 📊 **Smart Ranking**: Ranks and selects top 10 most valuable tests
- 🤖 **Multi-Agent Execution**: Coordinated test execution with multiple agents
- 📸 **Artifact Capture**: Screenshots, DOM snapshots, console/network logs
- ✅ **Validation**: Repeat and cross-agent validation for reliability
- 📈 **Progressive Learning**: RAG-based learning improves over time

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **AI Framework**: LangChain
- **Vision Model**: Ollama + LLaVA
- **Browser Automation**: Playwright
- **Vector Store**: ChromaDB
- **Frontend**: Vanilla HTML/CSS/JS

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start Ollama (in separate terminal)
ollama run llava

# Run the backend
uvicorn backend.main:app --reload --port 8000

# Open browser
# Navigate to http://localhost:8000
```

## Project Structure

```
multi_agent_game_tester/
├── backend/
│   ├── agents/          # AI agents (planner, ranker, executor, etc.)
│   ├── browser/         # Playwright automation
│   ├── rag/             # Knowledge base for learning
│   ├── models/          # Data models
│   └── main.py          # FastAPI application
├── frontend/            # Minimal web UI
├── artifacts/           # Test artifacts (screenshots, logs)
├── reports/             # Generated test reports
└── tests/               # Unit and integration tests
```

## Usage

1. Enter game URL (e.g., https://play.ezygamers.com/)
2. Click "Analyze Game" to understand game mechanics
3. Click "Generate Tests" to create 20+ test cases
4. Click "Rank & Select" to choose top 10
5. Click "Execute" to run tests with artifact capture
6. View comprehensive report with verdicts and evidence

## License

MIT
