# Python Backend for MCP Demo

FastAPI backend that handles chat requests, MCP server orchestration, and OpenAI integration.

## Setup

1. **Install Python dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

2. **Set up environment variables:**

Create a `.env` file in the `backend` directory (or use the root `.env.local`):

```env
OPENAI_API_KEY=your_openai_api_key_here
GITHUB_TOKEN=your_github_token_here
GITHUB_MCP_COMMAND=npx
GITHUB_MCP_ARGS=@modelcontextprotocol/server-github
PLAYWRIGHT_MCP_COMMAND=docker
PLAYWRIGHT_MCP_ARGS=run,-i,--rm,--pull=always,mcr.microsoft.com/playwright/mcp
PLOTS_MCP_COMMAND=python
PLOTS_MCP_ARGS=-m,mcp_plots
```

3. **Run the backend:**

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check with MCP server status
- `POST /api/chat` - Chat endpoint with streaming support

## Architecture

- `main.py` - FastAPI application and routes
- `mcp_client.py` - MCP server client management
- `openai_client.py` - OpenAI integration with function calling
- `data_processors.py` - Data conversion utilities (GitHub data to CSV)

## MCP Server Integration

The backend manages connections to three MCP servers:
1. **GitHub MCP** - Fetches repository data
2. **Playwright MCP** - Takes screenshots
3. **mcp-plots** - Generates charts

All MCP servers communicate via stdio (standard input/output) transport.

