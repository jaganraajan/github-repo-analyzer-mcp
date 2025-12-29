"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Loader2, Github, Camera } from "lucide-react";

interface MCPStatus {
  github: boolean;
  playwright: boolean;
}

export default function MCPStatus() {
  const [status, setStatus] = useState<MCPStatus>({
    github: false,
    playwright: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check MCP server status from Python backend
    const checkStatus = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/health`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data.mcp_servers || {
            github: false,
            playwright: false,
          });
        } else {
        setStatus({
          github: false,
          playwright: false,
        });
        }
      } catch (error) {
        console.error("Error checking MCP status:", error);
        setStatus({
          github: false,
          playwright: false,
        });
      } finally {
        setLoading(false);
      }
    };

    checkStatus();
    // Poll status every 10 seconds
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const servers = [
    {
      name: "GitHub MCP",
      status: status.github,
      icon: Github,
      description: "Fetches repository data",
    },
    {
      name: "Playwright MCP",
      status: status.playwright,
      icon: Camera,
      description: "Takes screenshots",
    },
  ];

  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm text-black">Checking MCP server status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold mb-3 text-black">MCP Server Status</h3>
      <div className="space-y-2">
        {servers.map((server) => {
          const Icon = server.icon;
          return (
            <div
              key={server.name}
              className="flex items-center justify-between p-2 rounded border"
            >
              <div className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-gray-600" />
                <div>
                  <p className="text-sm font-medium text-black">{server.name}</p>
                  <p className="text-xs text-black">{server.description}</p>
                </div>
              </div>
              {server.status ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
            </div>
          );
        })}
      </div>
      {/* <p className="text-xs text-black mt-3">
        Note: Configure MCP servers in your environment to enable full functionality
      </p> */}
    </div>
  );
}

