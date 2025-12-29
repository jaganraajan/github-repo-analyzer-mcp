import ChatInterface from "./components/ChatInterface";
import MCPStatus from "./components/MCPStatus";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            GitHub Repository Analyzer
          </h1>
          <p className="text-black">
            Analyze GitHub repositories using MCP servers (GitHub, Playwright) with GPT-4o-mini
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat Interface - Takes 2 columns on large screens */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border shadow-sm h-[calc(100vh-12rem)] flex flex-col">
              <div className="border-b p-4">
                <h2 className="text-lg font-semibold text-black">Chat Interface</h2>
                <p className="text-sm text-black mt-1">
                  Ask about any GitHub repository to analyze and visualize
                </p>
              </div>
              <div className="flex-1 overflow-hidden">
                <ChatInterface />
              </div>
            </div>
          </div>

          {/* Sidebar - MCP Status and Examples */}
          <div className="space-y-6">
            <MCPStatus />

            <div className="bg-white rounded-lg border p-4">
              <h3 className="text-sm font-semibold mb-3 text-black">Example Prompts</h3>
              <div className="space-y-2">
                {/* <div className="w-full text-left text-xs p-2 bg-gray-50 rounded border border-gray-200">
                  <p className="font-medium text-black">Analyze Next.js</p>
                  <p className="text-black mt-1">
                    &quot;Analyze the vercel/next.js repository&quot;
                  </p>
                </div> */}
                <div className="w-full text-left text-xs p-2 bg-gray-50 rounded border border-gray-200">
                  <p className="font-medium text-black">Analyze React</p>
                  <p className="text-black mt-1">
                    &quot;Analyze the facebook/react repository&quot;
                  </p>
                </div>
                <div className="w-full text-left text-xs p-2 bg-gray-50 rounded border border-gray-200">
                  <p className="font-medium text-black">Screenshot & Analyze</p>
                  <p className="text-black mt-1">
                    &quot;Take a screenshot of github.com/microsoft/playwright and analyze it&quot;
                  </p>
                </div>
                {/* <div className="w-full text-left text-xs p-2 bg-gray-50 rounded border border-gray-200">
                  <p className="font-medium text-black">Pull Requests for Next.js</p>
                  <p className="text-black mt-1">
                    &quot;Give me pull requests for the vercel/next.js repository&quot;
                  </p>
                </div> */}
              </div>
            </div>

            <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
              <h3 className="text-sm font-semibold mb-2 text-blue-900">How it works</h3>
              <ul className="text-xs text-black space-y-1">
                <li>• GPT-4o-mini analyzes your request</li>
                <li>• Orchestrates MCP tools automatically</li>
                <li>• Fetches GitHub data, takes screenshots</li>
                <li>• Displays results in real-time</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
