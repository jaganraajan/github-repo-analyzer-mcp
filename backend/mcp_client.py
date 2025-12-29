"""
MCP Client Manager for Python
Manages connections to GitHub and Playwright MCP servers
"""

import os
import json
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClientManager:
    """Manages connections to multiple MCP servers"""
    
    def __init__(self):
        self.github_session: Optional[ClientSession] = None
        self.playwright_session: Optional[ClientSession] = None
        self._github_stdio_ctx = None
        self._playwright_stdio_ctx = None
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP server configuration from environment variables"""
        return {
            "github": {
                "command": os.getenv("GITHUB_MCP_COMMAND", "npx"),
                "args": os.getenv("GITHUB_MCP_ARGS", "@modelcontextprotocol/server-github").split(","),
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
                }
            },
            "playwright": {
                "command": os.getenv("PLAYWRIGHT_MCP_COMMAND", "npx"),
                "args": os.getenv("PLAYWRIGHT_MCP_ARGS", "@playwright/mcp").split(","),
                "env": {}
            }
        }
    
    async def initialize_all(self):
        """Initialize all MCP server connections"""
        await asyncio.gather(
            self._initialize_github(),
            self._initialize_playwright(),
            return_exceptions=True
        )
    
    async def _initialize_github(self):
        """Initialize GitHub MCP server connection"""
        if self.github_session:
            return
        
        try:
            config = self.config["github"]
            # Check if GitHub token is set
            github_token = config["env"].get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            if not github_token:
                print("⚠ Warning: GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN not set. GitHub API calls may fail.")
            
            # Merge environment variables
            env = os.environ.copy()
            env.update(config["env"])
            
            server_params = StdioServerParameters(
                command=config["command"],
                args=[arg.strip() for arg in config["args"]],
                env=env
            )
            
            # stdio_client is an async context manager, need to enter it manually
            stdio_ctx = stdio_client(server_params)
            read_stream, write_stream = await stdio_ctx.__aenter__()
            self.github_session = ClientSession(read_stream, write_stream)
            await self.github_session.__aenter__()
            # Store the context manager so we can exit it later
            self._github_stdio_ctx = stdio_ctx
            print("✓ GitHub MCP client initialized")
        except Exception as e:
            print(f"✗ Failed to initialize GitHub MCP client: {e}")
    
    async def _initialize_playwright(self):
        """Initialize Playwright MCP server connection"""
        if self.playwright_session:
            return
        
        try:
            config = self.config["playwright"]
            env = os.environ.copy()
            env.update(config["env"])
            
            server_params = StdioServerParameters(
                command=config["command"],
                args=[arg.strip() for arg in config["args"]],
                env=env
            )
            
            # stdio_client is an async context manager, need to enter it manually
            stdio_ctx = stdio_client(server_params)
            read_stream, write_stream = await stdio_ctx.__aenter__()
            self.playwright_session = ClientSession(read_stream, write_stream)
            await self.playwright_session.__aenter__()
            # Store the context manager so we can exit it later
            self._playwright_stdio_ctx = stdio_ctx
            print("✓ Playwright MCP client initialized")
        except Exception as e:
            print(f"✗ Failed to initialize Playwright MCP client: {e}")
    
    async def fetch_github_repo_data(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository data from GitHub MCP server"""
        if not self.github_session:
            raise Exception("GitHub MCP client not initialized")
        
        try:
            # Discover available tools dynamically
            tool_names = await self._discover_github_tools()
            
            # Get repository information - try multiple variations (optional, can skip if not available)
            repo_result = None
            repo_tool_name = tool_names.get("repository")
            if repo_tool_name:
                try:
                    repo_result = await self.github_session.call_tool(
                        repo_tool_name,
                        arguments={"owner": owner, "repo": repo}
                    )
                    print(f"[DEBUG] Found repository tool: {repo_tool_name}")
                except Exception as e:
                    print(f"[DEBUG] Repository tool {repo_tool_name} failed: {e}")
            else:
                # Try common variations
                for name in ["list_repository", "get_repository", "github_get_repository", "get_repo", "repository", "repo"]:
                    try:
                        repo_result = await self.github_session.call_tool(
                            name,
                            arguments={"owner": owner, "repo": repo}
                        )
                        print(f"[DEBUG] Found repository tool: {name}")
                        break
                    except Exception as e:
                        print(f"[DEBUG] Tool {name} failed: {e}")
                        continue
                else:
                    print(f"[DEBUG] Repository tool not available, continuing without it")
            
            # Get additional data in parallel
            # Use list_commits as the default fallback since it's the standard GitHub MCP tool name
            # Note: list_contributors and list_languages don't exist in GitHub MCP, so we skip them
            # Reduce per_page to prevent context length issues (30 commits should be enough for most queries)
            results = await asyncio.gather(
                self._call_github_tool(tool_names.get("commits", "list_commits"), {"owner": owner, "repo": repo, "per_page": 30}),
                self._call_github_tool(tool_names.get("issues", "list_issues"), {"owner": owner, "repo": repo, "state": "all", "per_page": 30}),
                self._call_github_tool(tool_names.get("pull_requests", "list_pull_requests"), {"owner": owner, "repo": repo, "state": "all", "per_page": 30}),
                return_exceptions=True
            )
            
            commits, issues, prs = results
            contributors = None  # Not available in GitHub MCP
            languages = None  # Not available in GitHub MCP
            
            return {
                "repository": self._parse_content(repo_result) if repo_result else None,
                "commits": self._parse_content(commits) if not isinstance(commits, Exception) else None,
                "issues": self._parse_content(issues) if not isinstance(issues, Exception) else None,
                "pullRequests": self._parse_content(prs) if not isinstance(prs, Exception) else None,
                "contributors": self._parse_content(contributors) if not isinstance(contributors, Exception) else None,
                "languages": self._parse_content(languages) if not isinstance(languages, Exception) else None,
            }
        except Exception as e:
            raise Exception(f"Error fetching GitHub repo data: {e}")
    
    async def _discover_github_tools(self) -> Dict[str, str]:
        """Discover available GitHub MCP tools and map them to expected names"""
        tool_map = {}
        
        try:
            tools_result = await self.github_session.list_tools()
            if hasattr(tools_result, 'tools'):
                available_tools = [tool.name for tool in tools_result.tools]
                print(f"[DEBUG] Available GitHub tools: {available_tools}")
                
                # Map expected tool names to actual available tool names
                # Common patterns: github_get_repository, get_repo, repository, etc.
                # Prioritize list_* tools as they are the standard GitHub MCP tool names
                expected_mappings = {
                    "repository": ["list_repository", "get_repository", "github_get_repository", "get_repo", "repository", "repo"],  # Prioritize list_repository
                    "commits": ["list_commits", "get_commits", "github_get_commits", "commits"],  # Prioritize list_commits
                    "issues": ["list_issues", "get_issues", "github_get_issues", "issues"],
                    "pull_requests": ["list_pull_requests", "get_pull_requests", "github_get_pull_requests", "get_pulls", "pull_requests", "pulls"],
                    "contributors": ["list_contributors", "get_contributors", "github_get_contributors", "contributors"],
                    "languages": ["list_languages", "get_languages", "github_get_languages", "languages"]
                }
                
                for expected_name, possible_names in expected_mappings.items():
                    for possible_name in possible_names:
                        if possible_name in available_tools:
                            tool_map[expected_name] = possible_name
                            break
                
                print(f"[DEBUG] Mapped GitHub tools: {tool_map}")
        except Exception as e:
            print(f"[DEBUG] Could not list GitHub tools: {e}")
        
        return tool_map
    
    async def _call_github_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Helper to call GitHub MCP tools with error handling and fallback"""
        if not tool_name:
            return None
        
        try:
            return await self.github_session.call_tool(tool_name, arguments=arguments)
        except Exception as e:
            error_str = str(e)
            
            # Check for authentication errors - don't try variations for these
            if "Authentication Failed" in error_str or "Bad credentials" in error_str or "401" in error_str:
                print(f"[ERROR] Authentication failed for {tool_name}. Please check your GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN environment variable.")
                return None
            
            # Check for "Unknown tool" errors - don't try variations for these
            if "Unknown tool" in error_str:
                print(f"[DEBUG] Tool {tool_name} not available: {e}")
                return None
            
            # For pull requests, if validation fails due to null head.repo, try with different states
            # This happens when some PRs are from deleted forks
            if "list_pull_requests" in tool_name or "pull_requests" in tool_name or "pulls" in tool_name:
                if "Invalid input" in error_str or "invalid_type" in error_str or "null" in error_str.lower():
                    print(f"[DEBUG] Pull requests validation error (likely null head.repo): {e}")
                    print(f"[DEBUG] Trying to fetch PRs with 'open' state only to avoid validation issues...")
                    try:
                        # Try with 'open' state only, which is less likely to have deleted fork issues
                        open_prs = await self.github_session.call_tool(tool_name, {**arguments, "state": "open", "per_page": 30})
                        if open_prs:
                            print(f"[DEBUG] Successfully fetched open PRs")
                            return open_prs
                    except Exception as open_e:
                        print(f"[DEBUG] Failed to fetch open PRs: {open_e}")
                    # If that fails, try 'closed' state
                    try:
                        closed_prs = await self.github_session.call_tool(tool_name, {**arguments, "state": "closed", "per_page": 30})
                        if closed_prs:
                            print(f"[DEBUG] Successfully fetched closed PRs")
                            return closed_prs
                        return None
                    except Exception as closed_e:
                        print(f"[DEBUG] Failed to fetch closed PRs: {closed_e}")
                        return None
            
            # Try common variations if the tool name doesn't work (only for other errors)
            print(f"[DEBUG] Tool {tool_name} failed: {e}, trying variations...")
            
            # Common variations for GitHub MCP tools
            variations = [
                f"github_{tool_name}",
                f"get_{tool_name}",
                tool_name.replace("get_", ""),
                tool_name.replace("_", ""),
            ]
            
            for variation in variations:
                if variation == tool_name:
                    continue
                try:
                    print(f"[DEBUG] Trying variation: {variation}")
                    result = await self.github_session.call_tool(variation, arguments=arguments)
                    return result
                except Exception as var_e:
                    # Don't try more variations if it's an auth error
                    if "Authentication Failed" in str(var_e) or "Bad credentials" in str(var_e):
                        print(f"[ERROR] Authentication failed for variation {variation}")
                        return None
                    continue
            
            print(f"[DEBUG] All variations failed for {tool_name}")
            return None
    
    async def take_screenshot(self, url: str) -> str:
        """Take a screenshot using Playwright MCP server"""
        if not self.playwright_session:
            raise Exception("Playwright MCP client not initialized")
        
        try:
            print(f"[DEBUG] Taking screenshot of URL: {url}")
            
            # List available tools to see what's actually available
            try:
                tools_result = await self.playwright_session.list_tools()
                print(f"[DEBUG] Available Playwright tools: {[tool.name for tool in tools_result.tools] if hasattr(tools_result, 'tools') else 'N/A'}")
            except Exception as e:
                print(f"[DEBUG] Could not list tools: {e}")
            
            # Try different possible tool names for Playwright MCP
            # Common names: browser_navigate, browser_snapshot, playwright_navigate, playwright_screenshot, etc.
            navigate_tool_name = None
            screenshot_tool_name = None
            
            # Try to find the correct tool names - prefer exact matches
            try:
                tools_result = await self.playwright_session.list_tools()
                if hasattr(tools_result, 'tools'):
                    for tool in tools_result.tools:
                        tool_name_lower = tool.name.lower()
                        # Prefer exact matches first
                        if tool.name == "browser_navigate":
                            navigate_tool_name = tool.name
                        elif not navigate_tool_name and ('navigate' in tool_name_lower and 'back' not in tool_name_lower):
                            navigate_tool_name = tool.name
                        
                        # Prefer browser_take_screenshot over browser_snapshot
                        if tool.name == "browser_take_screenshot":
                            screenshot_tool_name = tool.name
                        elif not screenshot_tool_name and 'screenshot' in tool_name_lower:
                            screenshot_tool_name = tool.name
                        elif not screenshot_tool_name and ('snapshot' in tool_name_lower or 'capture' in tool_name_lower):
                            screenshot_tool_name = tool.name
            except:
                pass
            
            # Fallback to common names if not found
            if not navigate_tool_name:
                navigate_tool_name = "browser_navigate"
            if not screenshot_tool_name:
                screenshot_tool_name = "browser_take_screenshot"  # Prefer this over snapshot
            
            print(f"[DEBUG] Using navigate tool: {navigate_tool_name}")
            print(f"[DEBUG] Using screenshot tool: {screenshot_tool_name}")
            
            # Navigate to the URL
            print(f"[DEBUG] Calling {navigate_tool_name} tool with url: {url}")
            try:
                navigate_result = await self.playwright_session.call_tool(navigate_tool_name, arguments={"url": url})
                print(f"[DEBUG] Navigate result: {navigate_result}")
            except Exception as e:
                # Try alternative tool names
                print(f"[DEBUG] {navigate_tool_name} failed: {e}, trying alternatives...")
                for alt_name in ["browser_navigate", "playwright_navigate", "navigate", "goto", "visit"]:
                    try:
                        navigate_result = await self.playwright_session.call_tool(alt_name, arguments={"url": url})
                        navigate_tool_name = alt_name
                        print(f"[DEBUG] Success with {alt_name}")
                        break
                    except:
                        continue
                else:
                    raise Exception(f"Could not find navigate tool. Available tools may need to be checked.")
            
            # Take screenshot - use browser_take_screenshot which returns base64 image
            print(f"[DEBUG] Calling {screenshot_tool_name} tool...")
            try:
                # browser_take_screenshot expects different arguments than browser_snapshot
                if screenshot_tool_name == "browser_take_screenshot":
                    result = await self.playwright_session.call_tool(screenshot_tool_name, arguments={"fullPage": False, "type": "png"})
                else:
                    # browser_snapshot doesn't take arguments
                    result = await self.playwright_session.call_tool(screenshot_tool_name, arguments={})
                print(f"[DEBUG] Screenshot result type: {type(result)}")
                print(f"[DEBUG] Screenshot result: {result}")
            except Exception as e:
                # Try alternative tool names
                print(f"[DEBUG] {screenshot_tool_name} failed: {e}, trying alternatives...")
                for alt_name in ["browser_take_screenshot", "playwright_screenshot", "screenshot"]:
                    try:
                        if alt_name == "browser_take_screenshot":
                            result = await self.playwright_session.call_tool(alt_name, arguments={"fullPage": True})
                        else:
                            result = await self.playwright_session.call_tool(alt_name, arguments={})
                        screenshot_tool_name = alt_name
                        print(f"[DEBUG] Success with {alt_name}")
                        break
                    except:
                        continue
                else:
                    raise Exception(f"Could not find screenshot tool. Available tools may need to be checked.")
            
            # Return base64 encoded image
            content = self._parse_content(result)
            print(f"[DEBUG] Parsed content type: {type(content)}")
            print(f"[DEBUG] Parsed content: {str(content)[:200]}...")
            
            # Handle file paths - Playwright MCP may return file paths instead of base64
            if isinstance(content, str):
                # Check if it's a file path (sandbox: protocol or /tmp/ path)
                if content.startswith("sandbox:") or content.startswith("/tmp/") or ".png" in content or ".jpg" in content:
                    print(f"[DEBUG] Detected file path in content, extracting path...")
                    # Extract file path - remove sandbox: prefix if present
                    file_path = content.replace("sandbox:", "").strip()
                    # Try to find the actual path in the text (might be in markdown or plain text)
                    import re
                    # Look for file paths in the content
                    path_match = re.search(r'(sandbox:)?([/\w\-\.]+\.(png|jpg|jpeg))', content)
                    if path_match:
                        file_path = path_match.group(2) if path_match.group(2) else path_match.group(0)
                        if file_path.startswith("sandbox:"):
                            file_path = file_path.replace("sandbox:", "")
                    
                    print(f"[DEBUG] Reading screenshot from file: {file_path}")
                    # Read the file and convert to base64
                    import base64
                    try:
                        with open(file_path, 'rb') as f:
                            image_data = f.read()
                            base64_data = base64.b64encode(image_data).decode('utf-8')
                            print(f"[DEBUG] Successfully read and encoded file, size: {len(base64_data)} chars")
                            return base64_data
                    except FileNotFoundError:
                        # Try alternative paths
                        alt_paths = [
                            file_path,
                            f"/tmp/{file_path.split('/')[-1]}",
                            file_path.replace("/tmp/", "/tmp/playwright-output/"),
                        ]
                        for alt_path in alt_paths:
                            try:
                                print(f"[DEBUG] Trying alternative path: {alt_path}")
                                with open(alt_path, 'rb') as f:
                                    image_data = f.read()
                                    base64_data = base64.b64encode(image_data).decode('utf-8')
                                    print(f"[DEBUG] Successfully read from {alt_path}, size: {len(base64_data)} chars")
                                    return base64_data
                            except:
                                continue
                        raise Exception(f"Could not find screenshot file at any of these paths: {alt_paths}")
                    except Exception as e:
                        raise Exception(f"Error reading screenshot file {file_path}: {e}")
                elif not content:
                    raise Exception("Screenshot returned empty string")
                else:
                    # Assume it's already base64 or return as-is
                    return content
            elif isinstance(content, dict) and "data" in content:
                if not content["data"]:
                    raise Exception("Screenshot data is empty in dict")
                return content["data"]
            else:
                raise Exception(f"Unexpected content format: {type(content)}, content: {content}")
        except Exception as e:
            print(f"[ERROR] Screenshot error details: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error taking screenshot: {e}")
    
    def _parse_content(self, result: Any) -> Any:
        """Parse MCP tool result content"""
        if not result:
            return None
        
        try:
            # Handle MCP tool result structure
            if hasattr(result, "content"):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    # Check all content items, prefer data over text
                    all_text = []
                    for item in content:
                        # Check for data content (base64 images) - prefer this
                        if hasattr(item, "data") and item.data:
                            return item.data
                        elif isinstance(item, dict) and "data" in item and item["data"]:
                            return item["data"]
                        # Collect text content
                        elif hasattr(item, "text") and item.text:
                            all_text.append(item.text)
                        elif isinstance(item, dict) and "text" in item:
                            all_text.append(item["text"])
                    
                    # If we have text, try to parse it
                    if all_text:
                        combined_text = "\n".join(all_text)
                        try:
                            return json.loads(combined_text)
                        except json.JSONDecodeError:
                            return combined_text
                    
                    # Fallback to first content item
                    first_content = content[0]
                    if hasattr(first_content, "text") and first_content.text:
                        return first_content.text
                    elif isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]
            # If result is already a dict
            elif isinstance(result, dict):
                if "content" in result:
                    return self._parse_content(result)
                return result
            return result
        except Exception as e:
            print(f"Error parsing content: {e}")
            return None
    
    async def get_server_status(self) -> Dict[str, bool]:
        """Get status of all MCP servers"""
        return {
            "github": self.github_session is not None,
            "playwright": self.playwright_session is not None
        }
    
    async def cleanup(self):
        """Clean up all MCP server connections"""
        # Use try-except to handle cleanup errors gracefully
        if self.github_session:
            try:
                await self.github_session.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error cleaning up GitHub session: {e}")
            if self._github_stdio_ctx:
                try:
                    await self._github_stdio_ctx.__aexit__(None, None, None)
                except Exception as e:
                    print(f"Error cleaning up GitHub stdio context: {e}")
        
        if self.playwright_session:
            try:
                await self.playwright_session.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error cleaning up Playwright session: {e}")
            if self._playwright_stdio_ctx:
                try:
                    await self._playwright_stdio_ctx.__aexit__(None, None, None)
                except Exception as e:
                    print(f"Error cleaning up Playwright stdio context: {e}")

