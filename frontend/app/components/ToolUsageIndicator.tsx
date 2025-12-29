"use client";

import { ToolCall } from "./ChatInterface";
import { Loader2, Github, Camera } from "lucide-react";

interface ToolUsageIndicatorProps {
  toolCalls: ToolCall[];
}

export default function ToolUsageIndicator({ toolCalls }: ToolUsageIndicatorProps) {
  const getToolIcon = (toolName: string) => {
    if (toolName.includes("github") || toolName.includes("repo")) {
      return <Github className="w-4 h-4" />;
    }
    if (toolName.includes("screenshot")) {
      return <Camera className="w-4 h-4" />;
    }
    return <Loader2 className="w-4 h-4" />;
  };

  const getToolLabel = (toolName: string) => {
    if (toolName.includes("github") || toolName.includes("repo")) {
      return "Fetching GitHub data";
    }
    if (toolName.includes("screenshot")) {
      return "Taking screenshot";
    }
    return "Executing tool";
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
        <span className="text-sm font-medium text-black">Executing tools...</span>
      </div>
      <div className="space-y-2">
        {toolCalls.map((toolCall, idx) => (
          <div
            key={idx}
            className="flex items-center gap-2 text-sm text-black bg-white px-3 py-2 rounded"
          >
            {getToolIcon(toolCall.function.name)}
            <span>{getToolLabel(toolCall.function.name)}</span>
            <span className="text-xs text-black ml-auto">
              {toolCall.function.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

