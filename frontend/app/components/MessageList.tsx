"use client";

import { Message } from "./ChatInterface";
import { User, Bot } from "lucide-react";
import ScreenshotGallery from "./ScreenshotGallery";
import ReactMarkdown from "react-markdown";

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="text-center text-black mt-8">
        <p>Start by asking about a GitHub repository!</p>
        <p className="text-sm mt-2">Try: &quot;Analyze the vercel/next.js repository&quot;</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${
            message.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          {message.role === "assistant" && (
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
          )}

          <div
            className={`max-w-[80%] rounded-lg p-2 ${
              message.role === "user"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-black"
            }`}
          >
            {message.role === "user" ? (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4" />
                <p>{message.content}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {message.content && (
                    <div className="prose prose-sm max-w-none text-black">
                      <ReactMarkdown
                        components={{
                          // Style links
                          a: ({ node, ...props }) => (
                            <a {...props} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" />
                          ),
                          // Style lists
                          ul: ({ node, ...props }) => (
                            <ul {...props} className="list-disc list-inside space-y-1 my-2" />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol {...props} className="list-decimal list-inside space-y-1 my-2" />
                          ),
                          li: ({ node, ...props }) => (
                            <li {...props} className="ml-4" />
                          ),
                          // Style paragraphs
                          p: ({ node, ...props }) => (
                            <p {...props} />
                          ),
                          // Style headings
                          h1: ({ node, ...props }) => (
                            <h1 {...props} className="text-xl font-bold my-3" />
                          ),
                          h2: ({ node, ...props }) => (
                            <h2 {...props} className="text-lg font-bold my-2" />
                          ),
                          h3: ({ node, ...props }) => (
                            <h3 {...props} className="text-base font-semibold my-2" />
                          ),
                          // Style code
                          code: (props: any) => {
                            // In react-markdown v10, inline code doesn't have className, code blocks do
                            const isInline = !props.className || !props.className.includes('language');
                            return isInline ? (
                              <code {...props} className="bg-gray-200 px-1 py-0.5 rounded text-sm font-mono" />
                            ) : (
                              <code {...props} className="block bg-gray-100 p-2 rounded text-sm font-mono overflow-x-auto" />
                            );
                          },
                          // Style blockquotes
                          blockquote: ({ node, ...props }) => (
                            <blockquote {...props} className="border-l-4 border-gray-300 pl-4 italic my-2" />
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                )}

                {/* Display tool results */}
                {message.toolResults && message.toolResults.length > 0 && (
                  <div className="space-y-4 mt-4">
                    {/* Screenshots */}
                    {message.toolResults.some((r) => r.screenshot) && (
                      <ScreenshotGallery
                        screenshots={message.toolResults
                          .filter((r) => r.screenshot)
                          .map((r) => ({
                            data: r.screenshot!,
                            url: r.url || "",
                          }))}
                      />
                    )}

                    {/* Commits, Issues, and PRs data - only show if user asked for them or general analysis */}
                    {(() => {
                      const hasCommits = message.toolResults.some((r) => r.commits && Array.isArray(r.commits) && r.commits.length > 0);
                      const hasPullRequests = message.toolResults.some((r) => r.pullRequests && Array.isArray(r.pullRequests) && r.pullRequests.length > 0);
                      const hasIssues = message.toolResults.some((r) => r.issues && Array.isArray(r.issues) && r.issues.length > 0);
                      
                      // Detect what user asked for from their message
                      // Find the MOST RECENT user message before this assistant message
                      const userMessage = messages
                        .filter((m) => m.role === "user" && m.id <= message.id)
                        .sort((a, b) => Number(b.id) - Number(a.id))[0];
                      const userContent = userMessage?.content?.toLowerCase() || "";
                      
                      const askedForCommits = userContent.includes("commit") || 
                                             userContent.includes("commit history") ||
                                             userContent.includes("commit frequency");
                      
                      const askedForPullRequests = userContent.includes("pull request") || 
                                                  userContent.includes("pr") ||
                                                  userContent.includes("pull requests");
                      
                      const askedForIssues = userContent.includes("issue") && 
                                           !userContent.includes("pull request");
                      
                      const isGeneralAnalysis = userContent.includes("analyze") || 
                                              userContent.includes("show me") ||
                                              userContent.includes("repository info") ||
                                              userContent.includes("repository data");
                      
                      // Show commits if:
                      // - User asked for commits, OR
                      // - General analysis AND user didn't specifically ask for only PRs or only issues
                      const shouldShowCommits = hasCommits && (
                        askedForCommits || 
                        (isGeneralAnalysis && !askedForPullRequests && !askedForIssues)
                      );
                      
                      // Show issues if:
                      // - User asked for issues, OR
                      // - General analysis AND user didn't specifically ask for only PRs
                      const shouldShowIssues = hasIssues && (
                        askedForIssues ||
                        (isGeneralAnalysis && !askedForPullRequests)
                      );
                      
                      // Show PRs if:
                      // - User asked for PRs, OR
                      // - General analysis AND user didn't specifically ask for only issues
                      const shouldShowPullRequests = hasPullRequests && (
                        askedForPullRequests ||
                        (isGeneralAnalysis && !askedForIssues)
                      );
                      
                      return shouldShowCommits ? (
                        <div className="bg-white p-4 rounded border">
                          <h3 className="font-semibold mb-2">
                            Commit History ({message.toolResults.find((r) => r.commits)?.commits?.length || 0} commits)
                          </h3>
                        <div className="max-h-96 overflow-auto">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-100 sticky top-0">
                              <tr>
                                <th className="p-2 text-left">SHA</th>
                                <th className="p-2 text-left">Message</th>
                                <th className="p-2 text-left">Date</th>
                                <th className="p-2 text-left">Author</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(() => {
                                const commitsData = message.toolResults.find((r) => r.commits)?.commits;
                                if (!commitsData || !Array.isArray(commitsData)) return null;
                                return commitsData
                                  .slice(0, 50)  // Show first 50 commits
                                  .map((commit: any, idx: number) => {
                                    // Handle different commit data structures
                                    const sha = commit.sha || commit.commit?.sha || "";
                                    const message = commit.commit?.message || commit.message || "";
                                    const date = commit.commit?.author?.date || commit.commit?.committer?.date || commit.date || "";
                                    const author = commit.commit?.author?.name || commit.author?.login || commit.author?.name || commit.author || "";
                                    
                                    return (
                                      <tr key={idx} className="border-b hover:bg-gray-50">
                                        <td className="p-2 font-mono text-xs">
                                          {sha.substring(0, 7)}
                                        </td>
                                        <td className="p-2">
                                          {message.substring(0, 80)}
                                          {message.length > 80 ? "..." : ""}
                                        </td>
                                        <td className="p-2">
                                          {date ? new Date(date).toLocaleDateString() : ""}
                                        </td>
                                        <td className="p-2">
                                          {author}
                                        </td>
                                      </tr>
                                    );
                                  });
                              })()}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      ) : null;
                    })()}

                    {/* Issues data - only show if user asked for issues or general analysis */}
                    {(() => {
                      const hasIssues = message.toolResults.some((r) => r.issues && Array.isArray(r.issues) && r.issues.length > 0);
                      if (!hasIssues) return null;
                      
                      // Find the MOST RECENT user message before this assistant message
                      const userMessage = messages
                        .filter((m) => m.role === "user" && m.id <= message.id)
                        .sort((a, b) => Number(b.id) - Number(a.id))[0];
                      const userContent = userMessage?.content?.toLowerCase() || "";
                      
                      const askedForPullRequests = userContent.includes("pull request") || 
                                                  userContent.includes("pr") ||
                                                  userContent.includes("pull requests");
                      
                      const askedForIssues = userContent.includes("issue") && 
                                           !userContent.includes("pull request");
                      
                      const isGeneralAnalysis = userContent.includes("analyze") || 
                                              userContent.includes("show me") ||
                                              userContent.includes("repository info") ||
                                              userContent.includes("repository data");
                      
                      // Show issues if:
                      // - User asked for issues, OR
                      // - General analysis AND user didn't specifically ask for only PRs
                      const shouldShowIssues = askedForIssues ||
                                              (isGeneralAnalysis && !askedForPullRequests);
                      
                      return shouldShowIssues ? (
                      <div className="bg-white p-4 rounded border">
                        <h3 className="font-semibold mb-2">
                          Issues ({message.toolResults.find((r) => r.issues)?.issues?.length || 0} issues)
                        </h3>
                        <div className="max-h-96 overflow-auto">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-100 sticky top-0">
                              <tr>
                                <th className="p-2 text-left">#</th>
                                <th className="p-2 text-left">Title</th>
                                <th className="p-2 text-left">State</th>
                                <th className="p-2 text-left">Author</th>
                                <th className="p-2 text-left">Created</th>
                                <th className="p-2 text-left">Comments</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(() => {
                                const issuesData = message.toolResults.find((r) => r.issues)?.issues;
                                if (!issuesData || !Array.isArray(issuesData)) return null;
                                return issuesData
                                  .slice(0, 50)  // Show first 50 issues
                                  .map((issue: any, idx: number) => {
                                    const number = issue.number || issue.issue_number || "";
                                    const title = issue.title || "";
                                    const state = issue.state || "";
                                    const author = issue.user?.login || issue.author?.login || issue.user?.name || "";
                                    const created = issue.created_at || "";
                                    const comments = issue.comments || 0;
                                    const url = issue.html_url || issue.url || "";
                                    
                                    return (
                                      <tr key={idx} className="border-b hover:bg-gray-50">
                                        <td className="p-2 font-mono text-xs">
                                          {url ? (
                                            <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                              #{number}
                                            </a>
                                          ) : (
                                            `#${number}`
                                          )}
                                        </td>
                                        <td className="p-2">
                                          {url ? (
                                            <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                              {title.substring(0, 60)}
                                              {title.length > 60 ? "..." : ""}
                                            </a>
                                          ) : (
                                            <>
                                              {title.substring(0, 60)}
                                              {title.length > 60 ? "..." : ""}
                                            </>
                                          )}
                                        </td>
                                        <td className="p-2">
                                          <span className={`px-2 py-1 rounded text-xs ${
                                            state === "open" ? "bg-green-100 text-green-800" :
                                            state === "closed" ? "bg-red-100 text-red-800" :
                                            "bg-gray-100 text-gray-800"
                                          }`}>
                                            {state}
                                          </span>
                                        </td>
                                        <td className="p-2">
                                          {author}
                                        </td>
                                        <td className="p-2">
                                          {created ? new Date(created).toLocaleDateString() : ""}
                                        </td>
                                        <td className="p-2">
                                          {comments}
                                        </td>
                                      </tr>
                                    );
                                  });
                              })()}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      ) : null;
                    })()}

                    {/* Pull Requests data - only show if user asked for PRs or general analysis */}
                    {(() => {
                      const hasPullRequests = message.toolResults.some((r) => r.pullRequests && Array.isArray(r.pullRequests) && r.pullRequests.length > 0);
                      if (!hasPullRequests) return null;
                      
                      // Find the MOST RECENT user message before this assistant message
                      const userMessage = messages
                        .filter((m) => m.role === "user" && m.id <= message.id)
                        .sort((a, b) => Number(b.id) - Number(a.id))[0];
                      const userContent = userMessage?.content?.toLowerCase() || "";
                      
                      const askedForPullRequests = userContent.includes("pull request") || 
                                                  userContent.includes("pr") ||
                                                  userContent.includes("pull requests");
                      
                      const askedForIssues = userContent.includes("issue") && 
                                           !userContent.includes("pull request");
                      
                      const isGeneralAnalysis = userContent.includes("analyze") || 
                                              userContent.includes("show me") ||
                                              userContent.includes("repository info") ||
                                              userContent.includes("repository data");
                      
                      // Show PRs if:
                      // - User asked for PRs, OR
                      // - General analysis AND user didn't specifically ask for only issues
                      const shouldShowPullRequests = askedForPullRequests ||
                                                    (isGeneralAnalysis && !askedForIssues);
                      
                      return shouldShowPullRequests ? (
                      <div className="bg-white p-4 rounded border">
                        <h3 className="font-semibold mb-2">
                          Pull Requests ({message.toolResults.find((r) => r.pullRequests)?.pullRequests?.length || 0} PRs)
                        </h3>
                        <div className="max-h-96 overflow-auto">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-100 sticky top-0">
                              <tr>
                                <th className="p-2 text-left">#</th>
                                <th className="p-2 text-left">Title</th>
                                <th className="p-2 text-left">State</th>
                                <th className="p-2 text-left">Author</th>
                                <th className="p-2 text-left">Created</th>
                                <th className="p-2 text-left">Comments</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(() => {
                                const prsData = message.toolResults.find((r) => r.pullRequests)?.pullRequests;
                                if (!prsData || !Array.isArray(prsData)) return null;
                                return prsData
                                  .slice(0, 50)  // Show first 50 PRs
                                  .map((pr: any, idx: number) => {
                                    const number = pr.number || pr.pr_number || "";
                                    const title = pr.title || "";
                                    const state = pr.merged_at ? "merged" : (pr.state || "");
                                    const author = pr.user?.login || pr.author?.login || pr.user?.name || "";
                                    const created = pr.created_at || "";
                                    const comments = pr.comments || 0;
                                    const url = pr.html_url || pr.url || "";
                                    
                                    return (
                                      <tr key={idx} className="border-b hover:bg-gray-50">
                                        <td className="p-2 font-mono text-xs">
                                          {url ? (
                                            <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                              #{number}
                                            </a>
                                          ) : (
                                            `#${number}`
                                          )}
                                        </td>
                                        <td className="p-2">
                                          {url ? (
                                            <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                              {title.substring(0, 60)}
                                              {title.length > 60 ? "..." : ""}
                                            </a>
                                          ) : (
                                            <>
                                              {title.substring(0, 60)}
                                              {title.length > 60 ? "..." : ""}
                                            </>
                                          )}
                                        </td>
                                        <td className="p-2">
                                          <span className={`px-2 py-1 rounded text-xs ${
                                            state === "open" ? "bg-green-100 text-green-800" :
                                            state === "merged" ? "bg-purple-100 text-purple-800" :
                                            state === "closed" ? "bg-red-100 text-red-800" :
                                            "bg-gray-100 text-gray-800"
                                          }`}>
                                            {state}
                                          </span>
                                        </td>
                                        <td className="p-2">
                                          {author}
                                        </td>
                                        <td className="p-2">
                                          {created ? new Date(created).toLocaleDateString() : ""}
                                        </td>
                                        <td className="p-2">
                                          {comments}
                                        </td>
                                      </tr>
                                    );
                                  });
                              })()}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      ) : null;
                    })()}

                    {/* Repository data */}
                    {message.toolResults.some((r) => r.repository) && (
                      <div className="bg-white p-4 rounded border">
                        <h3 className="font-semibold mb-2">Repository Data</h3>
                        <pre className="text-xs overflow-auto">
                          {JSON.stringify(
                            message.toolResults.find((r) => r.repository)?.repository,
                            null,
                            2
                          )}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {/* Display tool calls */}
                {message.toolCalls && message.toolCalls.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer text-black">
                      {message.toolCalls.length} tool call(s)
                    </summary>
                    <div className="mt-2 space-y-1">
                      {message.toolCalls.map((toolCall, idx) => (
                        <div
                          key={idx}
                          className="text-xs bg-gray-200 p-2 rounded"
                        >
                          <span className="font-mono">{toolCall.function.name}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>

          {message.role === "user" && (
            <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-gray-700" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

