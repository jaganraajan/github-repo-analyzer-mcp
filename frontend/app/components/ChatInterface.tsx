"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import MessageList from "./MessageList";
import ToolUsageIndicator from "./ToolUsageIndicator";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: any[];
  toolResults?: any[];
}

export interface ToolCall {
  id: string;
  function: {
    name: string;
    arguments: string;
  };
}

export interface ToolResult {
  screenshot?: string;
  repository?: any;
  commits?: any[];
  issues?: any[];
  pullRequests?: any[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [currentToolResults, setCurrentToolResults] = useState<ToolResult[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const isNearBottom = () => {
    if (!messagesContainerRef.current) return true;
    const container = messagesContainerRef.current;
    const threshold = 100; // pixels from bottom
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  };

  useEffect(() => {
    // Only auto-scroll if user is near the bottom (hasn't manually scrolled up)
    // Also skip auto-scroll when commits are being displayed (to keep table visible)
    const hasCommits = messages.some(
      (msg) => msg.toolResults?.some((r) => r.commits && Array.isArray(r.commits) && r.commits.length > 0)
    );
    
    if (!hasCommits && isNearBottom()) {
      scrollToBottom();
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setCurrentToolCalls([]);
    setCurrentToolResults([]);

    try {
      // Call Python backend instead of Next.js API route
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";
      let assistantId = Date.now().toString();

      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        toolCalls: [],
        toolResults: [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (reader) {
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            // Decode any remaining buffered data
            if (buffer) {
              const lines = buffer.split("\n");
              for (const line of lines) {
                if (line.trim() === "") continue;
                if (line.startsWith("data: ")) {
                  try {
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;
                    const data = JSON.parse(jsonStr);
                    console.log("Received final event:", data.type, data);
                    // Process the event (same logic as below)
                    if (data.type === "content") {
                      assistantContent += data.content;
                      setMessages((prev) =>
                        prev.map((msg) =>
                          msg.id === assistantId
                            ? { ...msg, content: assistantContent }
                            : msg
                        )
                      );
                    } else if (data.type === "done") {
                      setMessages((prev) =>
                        prev.map((msg) =>
                          msg.id === assistantId
                            ? {
                                ...msg,
                                toolCalls: data.toolCalls || [],
                                toolResults: data.toolResults || [],
                              }
                            : msg
                        )
                      );
                    }
                  } catch (e) {
                    console.error("Error parsing final SSE data:", e);
                  }
                }
              }
            }
            break;
          }

          buffer += decoder.decode(value);
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim() === "") continue; // Skip empty lines
            if (line.startsWith("data: ")) {
              try {
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue; // Skip empty data lines
                const data = JSON.parse(jsonStr);
                console.log("Received event:", data.type, data);

                if (data.type === "content") {
                  assistantContent += data.content;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? { ...msg, content: assistantContent }
                        : msg
                    )
                  );
                } else if (data.type === "tool_call") {
                  setCurrentToolCalls((prev) => [...prev, data.toolCall]);
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? {
                            ...msg,
                            toolCalls: [...(msg.toolCalls || []), data.toolCall],
                          }
                        : msg
                    )
                  );
                } else if (data.type === "tool_result") {
                  setCurrentToolResults((prev) => [...prev, data.result]);
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? {
                            ...msg,
                            toolResults: [...(msg.toolResults || []), data.result],
                          }
                        : msg
                    )
                  );
                } else if (data.type === "done") {
                  // Final update with all tool calls and results
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? {
                            ...msg,
                            toolCalls: data.toolCalls || [],
                            toolResults: data.toolResults || [],
                          }
                        : msg
                    )
                  );
                } else if (data.type === "error") {
                  console.error("Error from server:", data.error);
                  throw new Error(data.error);
                }
              } catch (e) {
                console.error("Error parsing SSE data:", e, "Line:", line);
                // Continue processing other lines even if one fails
              }
            }
          }
        }
      } else {
        console.error("Response body is null or not readable");
      }
    } catch (error: any) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: `Error: ${error.message}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setCurrentToolCalls([]);
      setCurrentToolResults([]);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-2 space-y-4"
      >
        <MessageList messages={messages} />
        {isLoading && currentToolCalls.length > 0 && (
          <ToolUsageIndicator toolCalls={currentToolCalls} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a GitHub repository (e.g., 'Analyze vercel/next.js')..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

