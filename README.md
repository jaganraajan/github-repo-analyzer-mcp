# GitHub Repository Analyzer & Visualizer

A Next.js application that showcases MCP (Model Context Protocol) capabilities by analyzing GitHub repositories. The app uses GPT-4o-mini to intelligently orchestrate 2 MCP servers (GitHub MCP, Playwright MCP) to fetch repository data and capture screenshots.

## Features

- **Intelligent Tool Orchestration**: GPT-4o-mini analyzes user requests and automatically selects and executes the appropriate MCP tools
- **GitHub Data Analysis**: Fetches comprehensive repository data including commits, issues, PRs, contributors, and languages
- **Visual Screenshots**: Captures repository page screenshots using Playwright
- **Real-time Feedback**: Shows tool execution status and results in real-time
- **Interactive UI**: Chat interface with visual dashboard for repository analysis

## Prerequisites

- Node.js 18+ and npm
- Python 3.8+ (for backend)
- Docker (optional, for Playwright MCP server)
- OpenAI API key
- GitHub Personal Access Token 

## Installation

1. **Install Next.js frontend dependencies:**

```bash
cd frontend
npm install
cd ..
```

**Note:** If you have an existing `node_modules` folder at the root, you may need to remove it and reinstall dependencies in the `frontend/` directory.

2. **Install Python backend dependencies:**

```bash
cd backend
pip install -r requirements.txt
cd ..
```

2. **Set up environment variables:**

Copy `.env.local.example` to `.env.local` and fill in your credentials:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GITHUB_TOKEN`: Your GitHub Personal Access Token (optional but recommended)

3. **Set up MCP Servers:**

### GitHub MCP Server

The GitHub MCP server is typically available as an npm package. Install it globally or use npx:

```bash
npm install -g @modelcontextprotocol/server-github
```

Or configure it to run via npx (default in `.env.local.example`).

### Playwright MCP Server

**Option 1: Using Docker (Recommended)**

```bash
docker pull mcr.microsoft.com/playwright/mcp
```

Then configure in `.env.local`:
```
PLAYWRIGHT_MCP_COMMAND=docker
PLAYWRIGHT_MCP_ARGS=run,-i,--rm,mcr.microsoft.com/playwright/mcp
```

**Option 2: Local Installation**

```bash
npm install -g @playwright/mcp
```


## Running the Application

1. **Start the Python backend:**

```bash
cd backend
python main.py
# Or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start on `http://localhost:8000`

2. **Start the Next.js frontend (in a new terminal):**

```bash
cd frontend && npm run dev
```

3. **Open your browser:**

Navigate to [http://localhost:3000](http://localhost:3000)

4. **Try it out:**

- "Analyze the vercel/next.js repository"
- "Take a screenshot of github.com/microsoft/playwright and show me pull requests information"

## How It Works

1. **User Input**: User provides a GitHub repository URL or name in the chat interface
2. **AI Analysis**: GPT-4o-mini analyzes the request and determines which MCP tools to use
3. **Tool Execution**: The system orchestrates multiple MCP tools:
   - **GitHub MCP**: Fetches repository data (stats, commits, issues, PRs, contributors, languages)
   - **Playwright MCP**: Takes screenshots of the repository page
4. **Data Processing**: GitHub API responses are converted to CSV format for chart generation
5. **Visualization**: Charts and screenshots are displayed in the chat interface and dashboard

## Example Use Cases

### Basic Repository Analysis

```
User: "Analyze the vercel/next.js repository"
```

The system will:
1. Fetch repository data using GitHub MCP
2. Take a screenshot using Playwright MCP
3. Generate multiple tables (commit activity, pull requests, etc.) 
4. Display all results in the dashboard


## Troubleshooting

### MCP Servers Not Connecting

- Ensure MCP servers are installed and accessible in your PATH
- Check that the commands in `.env.local` are correct
- Verify that required dependencies (Python, Docker, etc.) are installed

### GitHub API Rate Limits

- Add a GitHub Personal Access Token to `.env.local` for higher rate limits
- The token needs `public_repo` scope for public repositories

### Screenshots Not Working

- Ensure Playwright MCP server is running
- Check Docker container status if using Docker
- Verify network connectivity

## Development

### Adding New MCP Tools

1. Add tool definition to `frontend/app/lib/openai-client.ts`
2. Implement tool execution in `frontend/app/lib/mcp-client.ts`
3. Add tool to function definitions array
4. Update UI components to display new tool results


## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
