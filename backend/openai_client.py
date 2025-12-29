"""
OpenAI client with function calling for MCP tool orchestration
"""

import os
import json
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from openai import AsyncOpenAI
try:
    from openai import AsyncAzureOpenAI
except ImportError:
    # Fallback if AsyncAzureOpenAI is not available (older versions)
    AsyncAzureOpenAI = None

# Initialize OpenAI client (supports both OpenAI and Azure OpenAI)
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

openai_api_key = os.getenv("OPENAI_API_KEY")

# Use Azure OpenAI if endpoint is configured, otherwise use standard OpenAI
if azure_endpoint and azure_api_key and azure_deployment:
    # Use AsyncAzureOpenAI if available, otherwise fall back to AsyncOpenAI with manual config
    if AsyncAzureOpenAI:
        print(f"Azure OpenAI Configuration (using AsyncAzureOpenAI):")
        print(f"  Endpoint: {azure_endpoint}")
        print(f"  Deployment: {azure_deployment}")
        print(f"  API Version: {azure_api_version}")
        
        openai_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version,
        )
    else:
        # Fallback for older OpenAI library versions
        endpoint_clean = azure_endpoint.rstrip('/')
        if endpoint_clean.endswith("/openai"):
            base_url = endpoint_clean
        else:
            base_url = f"{endpoint_clean}/openai"
        
        print(f"Azure OpenAI Configuration (using AsyncOpenAI fallback):")
        print(f"  Endpoint: {azure_endpoint}")
        print(f"  Base URL: {base_url}")
        print(f"  Deployment: {azure_deployment}")
        print(f"  API Version: {azure_api_version}")
        
        openai_client = AsyncOpenAI(
            api_key=azure_api_key,
            base_url=base_url,
            default_query={"api-version": azure_api_version} if azure_api_version else {},
        )
    
    # Store deployment name for use in API calls as model parameter
    _azure_deployment_name = azure_deployment
    _use_azure = True
elif openai_api_key:
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    _azure_deployment_name = None
    _use_azure = False
else:
    raise ValueError(
        "Either OPENAI_API_KEY or (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT_NAME) must be set"
    )

# Function definitions for OpenAI
FUNCTION_DEFINITIONS = [
    {
        "name": "fetch_github_repo_data",
        "description": "Fetches comprehensive data from a GitHub repository including stats, issues, pull requests, contributors, and languages. Note: Commit history, issues, and pull requests are fetched and displayed in UI tables, but are not included in the response text to prevent context length issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "The GitHub repository owner (username or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "The GitHub repository name",
                },
            },
            "required": ["owner", "repo"],
        },
    },
    {
        "name": "take_repo_screenshot",
        "description": "Takes a screenshot of a GitHub repository page using Playwright",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the GitHub repository page (e.g., https://github.com/owner/repo)",
                },
            },
            "required": ["url"],
        },
    },
]


async def execute_tool_call(
    tool_call: Dict[str, Any], mcp_manager, conversation_context: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Execute a tool call using MCP manager"""
    function_name = tool_call["function"]["name"]
    arguments_str = tool_call["function"].get("arguments", "")
    
    # Validate arguments
    if not arguments_str or not arguments_str.strip():
        raise ValueError(f"Tool {function_name} called with empty arguments. Tool call: {tool_call}")
    
    try:
        args = json.loads(arguments_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in tool {function_name} arguments: {arguments_str}. Error: {e}")
    
    # Helper function to extract data from previous tool results
    def extract_from_context(data_key: str, data_type: str = "array"):
        """Extract data from previous tool results in conversation context"""
        if not conversation_context:
            return None
        
        # Look backwards through messages for tool results
        # Tool results are stored with role "tool" and content as JSON string
        for msg in reversed(conversation_context):
            if msg.get("role") == "tool" and "content" in msg:
                try:
                    content = msg["content"]
                    # Content might be a JSON string or already parsed
                    if isinstance(content, str):
                        try:
                            content = json.loads(content)
                        except json.JSONDecodeError:
                            continue
                    
                    # Check if this is the result from fetch_github_repo_data
                    if isinstance(content, dict):
                        # Check for direct data key
                        if data_key in content:
                            data = content[data_key]
                            print(f"[DEBUG] Found {data_key} in tool result, type: {type(data)}")
                            
                            # Handle special case where commits are stored in _data field (when truncated for LLM)
                            if isinstance(data, dict) and "_data" in data:
                                extracted_data = data["_data"]
                                if data_key == "commits" and isinstance(extracted_data, list) and len(extracted_data) > 0:
                                    print(f"[DEBUG] Extracted {data_key} from _data field: {len(extracted_data)} items")
                                    return extracted_data
                                elif data_key != "commits" and isinstance(extracted_data, (list, dict)) and len(extracted_data) > 0:
                                    print(f"[DEBUG] Extracted {data_key} from _data field")
                                    return extracted_data
                            
                            if data_type == "array" and isinstance(data, list) and len(data) > 0:
                                print(f"[DEBUG] Extracted {data_key} from context: {len(data)} items")
                                return data
                            elif data_type == "object" and isinstance(data, dict) and len(data) > 0:
                                print(f"[DEBUG] Extracted {data_key} from context: {len(data)} keys")
                                return data
                        
                        # Also check if the entire content is the data we need (for cases where tool result is just the data)
                        if data_key == "commits" and isinstance(content, list) and len(content) > 0:
                            # Check if this looks like a commits array
                            if all(isinstance(item, dict) and ("commit" in item or "sha" in item) for item in content[:3]):
                                print(f"[DEBUG] Found commits array directly in tool result: {len(content)} items")
                                return content
                except (KeyError, TypeError, AttributeError) as e:
                    print(f"[DEBUG] Error extracting {data_key} from context: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        print(f"[DEBUG] Could not find {data_key} in conversation context")
        return None
    
    try:
        if function_name == "fetch_github_repo_data":
            owner = args["owner"]
            repo = args["repo"]
            result = await mcp_manager.fetch_github_repo_data(owner, repo)
            return result
        
        elif function_name == "take_repo_screenshot":
            print(f"[DEBUG] Executing take_repo_screenshot with URL: {args.get('url')}")
            try:
                screenshot = await mcp_manager.take_screenshot(args["url"])
                print(f"[DEBUG] Screenshot received, length: {len(screenshot) if screenshot else 0}")
                if not screenshot:
                    raise Exception("Screenshot is empty")
                return {"screenshot": screenshot, "url": args["url"]}
            except Exception as e:
                print(f"[ERROR] Screenshot execution failed: {e}")
                raise
        
        else:
            raise ValueError(f"Unknown function: {function_name}")
    
    except Exception as e:
        raise Exception(f"Error executing tool {function_name}: {e}")


def _truncate_tool_result(result: Any, max_base64_length: int = 500) -> Any:
    """Truncate large base64 data in tool results to prevent context bloat"""
    if isinstance(result, dict):
        truncated = {}
        for key, value in result.items():
            # Handle large arrays (like commits, issues, PRs) - limit to first 20 items
            if isinstance(value, list) and len(value) > 20:
                print(f"[DEBUG] Truncating {key} array from {len(value)} to 20 items")
                # For commits, keep only essential fields to reduce size
                if key == "commits" and value and isinstance(value[0], dict):
                    truncated[key] = [
                        {
                            "sha": commit.get("sha", "")[:7] if commit.get("sha") else "",
                            "message": (commit.get("commit", {}).get("message", "") or commit.get("message", ""))[:100],
                            "date": commit.get("commit", {}).get("author", {}).get("date") or commit.get("date", ""),
                            "author": commit.get("commit", {}).get("author", {}).get("name") or commit.get("author", {}).get("login", "") if isinstance(commit.get("author"), dict) else ""
                        }
                        for commit in value[:20]
                    ]
                else:
                    truncated[key] = value[:20]
            # Always truncate screenshot keys if they're large strings (base64 images are huge)
            elif key in ("screenshot", "image") and isinstance(value, str) and len(value) > 1000:
                truncated[key] = f"[{key.capitalize()} data truncated - {len(value)} chars]"
                print(f"[DEBUG] Truncated {key} from {len(value)} to placeholder")
            elif isinstance(value, str) and len(value) > max_base64_length:
                # Check if it looks like base64 (starts with common image base64 prefixes)
                if value.startswith(('iVBORw0KGgo', '/9j/', 'R0lGOD', 'data:image')):
                    truncated[key] = f"[Base64 image data truncated - {len(value)} chars]"
                    print(f"[DEBUG] Truncated {key} from {len(value)} to placeholder")
                else:
                    truncated[key] = value[:max_base64_length] + "... [truncated]"
            elif isinstance(value, dict):
                truncated[key] = _truncate_tool_result(value, max_base64_length)
            elif isinstance(value, list):
                # Recursively truncate list items
                truncated[key] = [_truncate_tool_result(item, max_base64_length) for item in value]
            else:
                truncated[key] = value
        return truncated
    elif isinstance(result, list):
        # Truncate large lists
        if len(result) > 20:
            print(f"[DEBUG] Truncating list from {len(result)} to 20 items")
            return [_truncate_tool_result(item, max_base64_length) for item in result[:20]]
        return [_truncate_tool_result(item, max_base64_length) for item in result]
    elif isinstance(result, str) and len(result) > max_base64_length:
        if result.startswith(('iVBORw0KGgo', '/9j/', 'R0lGOD', 'data:image')):
            return f"[Base64 image data truncated - {len(result)} chars]"
        return result[:max_base64_length] + "... [truncated]"
    return result


def _clean_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean messages to ensure all tool_calls have valid IDs"""
    cleaned = []
    for msg in messages:
        cleaned_msg = msg.copy()
        # If message has tool_calls, validate them
        if "tool_calls" in cleaned_msg and cleaned_msg["tool_calls"]:
            cleaned_msg["tool_calls"] = [
                tc for tc in cleaned_msg["tool_calls"]
                if tc.get("id") and isinstance(tc.get("id"), str) and tc.get("function", {}).get("name")
            ]
            # Remove tool_calls if empty after filtering
            if not cleaned_msg["tool_calls"]:
                cleaned_msg.pop("tool_calls", None)
        cleaned.append(cleaned_msg)
    return cleaned


def _truncate_messages(messages: List[Dict[str, Any]], max_messages: int = 15) -> List[Dict[str, Any]]:
    """Truncate messages to prevent context length errors, preserving tool call groups"""
    if len(messages) <= max_messages:
        return messages
    
    # Group messages: assistant messages with tool_calls must be kept with their tool results
    # Build groups: each assistant message with tool_calls + its tool results form a group
    groups = []
    current_group = []
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # If this is an assistant message with tool_calls, start a new group
        if role == "assistant" and msg.get("tool_calls"):
            # Save previous group if exists
            if current_group:
                groups.append(current_group)
            # Start new group with this assistant message
            current_group = [msg]
        # If this is a tool result, add to current group
        elif role == "tool" and current_group:
            current_group.append(msg)
        # Otherwise, it's a regular message (user, assistant without tool_calls, system)
        else:
            # Save previous group if exists
            if current_group:
                groups.append(current_group)
                current_group = []
            # Regular messages form their own groups
            groups.append([msg])
    
    # Don't forget the last group
    if current_group:
        groups.append(current_group)
    
    # Keep first group (usually system or first user message)
    truncated = []
    if groups:
        # Keep entire first group (might be just one message or a group)
        truncated.extend(groups[0])
    
    # Keep the most recent groups (ensuring we don't break tool call groups)
    # Calculate how many message slots we have left
    remaining_slots = max_messages - len(truncated)
    if remaining_slots > 0 and len(groups) > 1:
        # Take groups from the end, but make sure we don't exceed remaining slots
        recent_groups = []
        total_messages = 0
        for group in reversed(groups[1:]):  # Skip first group
            if total_messages + len(group) <= remaining_slots:
                recent_groups.insert(0, group)
                total_messages += len(group)
            else:
                break
    else:
        recent_groups = []
    
    # Truncate large tool results (like base64 images) to prevent context bloat
    for group in recent_groups:
        for msg in group:
            if msg.get("role") == "tool" and msg.get("content"):
                try:
                    content_str = msg["content"]
                    # If content is a large JSON string with base64 data, truncate it
                    if isinstance(content_str, str) and len(content_str) > 10000:
                        try:
                            content_obj = json.loads(content_str)
                            # If it contains screenshot data, replace with placeholder
                            if isinstance(content_obj, dict):
                                if "screenshot" in content_obj and len(str(content_obj["screenshot"])) > 5000:
                                    content_obj["screenshot"] = "[Screenshot data truncated - too large for context]"
                                msg["content"] = json.dumps(content_obj)
                        except:
                            # If not JSON, just truncate the string
                            if len(content_str) > 10000:
                                msg["content"] = content_str[:1000] + "... [truncated]"
                except:
                    pass
        
        # Add the entire group (preserving assistant + tool results relationship)
        truncated.extend(group)
    
    print(f"[DEBUG] Truncated messages from {len(messages)} to {len(truncated)}")
    return truncated


async def chat_with_tools(
    messages: List[Dict[str, str]],
    mcp_manager,
    on_tool_call: Optional[Callable] = None,
    on_tool_result: Optional[Callable] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Chat with OpenAI using function calling and MCP tools"""
    # Use Azure deployment name if using Azure, otherwise use model name
    model_name = _azure_deployment_name if _use_azure else "gpt-4o-mini"
    # Truncate messages to prevent context length errors
    current_messages = _truncate_messages(messages.copy(), max_messages=10)
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Create chat completion with streaming
        # For Azure OpenAI, use deployment name as model parameter
        # Clean messages first to ensure all tool_calls have valid IDs
        stream = await openai_client.chat.completions.create(
            model=model_name,
            messages=_clean_messages(current_messages),
            tools=[{"type": "function", "function": func} for func in FUNCTION_DEFINITIONS],
            tool_choice="auto",
            stream=True,
        )
        
        assistant_message = ""
        tool_calls = []
        tool_call_buffer = {}
        index_to_id = {}  # Map index to call_id for chunks that only have index
        index_buffer = {}  # Buffer for chunks that arrive before we have the ID
        
        async for chunk in stream:
            if not chunk.choices:
                continue
                
            choice = chunk.choices[0]
            delta = choice.delta if hasattr(choice, 'delta') else None
            
            # Check for complete tool calls in the chunk (some APIs include them)
            if hasattr(choice, 'delta') and choice.delta:
                # Handle content
                if choice.delta.content:
                    assistant_message += choice.delta.content
                    yield {"type": "content", "content": choice.delta.content}
                
                # Handle tool calls from delta
                if choice.delta.tool_calls:
                    for tool_call_delta in choice.delta.tool_calls:
                        call_id = getattr(tool_call_delta, 'id', None)
                        call_index = getattr(tool_call_delta, 'index', None)
                        
                        # If we have an ID, use it; otherwise try to find it from index
                        if not call_id and call_index is not None:
                            call_id = index_to_id.get(call_index)
                            if call_id:
                                print(f"[DEBUG] Matched index {call_index} to call_id {call_id}")
                        
                        # If we have an ID, process it
                        if call_id:
                            # Store index to ID mapping if we have both
                            if call_index is not None:
                                index_to_id[call_index] = call_id
                            
                            if call_id not in tool_call_buffer:
                                tool_call_buffer[call_id] = {
                                    "id": call_id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                }
                                print(f"[DEBUG] Created new tool call buffer for ID: {call_id} (index: {call_index})")
                            
                            if tool_call_delta.function.name:
                                tool_call_buffer[call_id]["function"]["name"] = tool_call_delta.function.name
                                print(f"[DEBUG] Set function name for {call_id}: {tool_call_delta.function.name}")
                            
                            if tool_call_delta.function.arguments:
                                arg_chunk = tool_call_delta.function.arguments
                                tool_call_buffer[call_id]["function"]["arguments"] += arg_chunk
                                print(f"[DEBUG] Added argument chunk for {call_id} (index: {call_index}, length: {len(arg_chunk)}): {arg_chunk[:100]}...")
                            else:
                                print(f"[DEBUG] No arguments in delta for {call_id} (index: {call_index})")
                            
                            # Apply any buffered chunks for this ID
                            if call_index is not None and call_index in index_buffer:
                                buffered = index_buffer.pop(call_index)
                                if buffered.get("arguments"):
                                    tool_call_buffer[call_id]["function"]["arguments"] = buffered["arguments"] + tool_call_buffer[call_id]["function"]["arguments"]
                                    print(f"[DEBUG] Applied buffered arguments for {call_id}")
                                if buffered.get("name") and not tool_call_buffer[call_id]["function"]["name"]:
                                    tool_call_buffer[call_id]["function"]["name"] = buffered["name"]
                        
                        # If no ID but we have an index, buffer it
                        elif call_index is not None:
                            if call_index not in index_buffer:
                                index_buffer[call_index] = {"name": "", "arguments": ""}
                            
                            if tool_call_delta.function.name:
                                index_buffer[call_index]["name"] = tool_call_delta.function.name
                                print(f"[DEBUG] Buffered function name for index {call_index}: {tool_call_delta.function.name}")
                            
                            if tool_call_delta.function.arguments:
                                arg_chunk = tool_call_delta.function.arguments
                                index_buffer[call_index]["arguments"] += arg_chunk
                                print(f"[DEBUG] Buffered argument chunk for index {call_index} (length: {len(arg_chunk)}): {arg_chunk[:100]}...")
                        else:
                            print(f"[DEBUG] Skipping tool call delta with no ID or index")
            
            # Also check for complete tool_calls in the choice (for non-streaming or final chunks)
            if hasattr(choice, 'message') and choice.message and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                print(f"[DEBUG] Found complete tool_calls in message: {len(choice.message.tool_calls)}")
                for tool_call in choice.message.tool_calls:
                    call_id = tool_call.id
                    if call_id and call_id not in tool_call_buffer:
                        tool_call_buffer[call_id] = {
                            "id": call_id,
                            "type": tool_call.type if hasattr(tool_call, 'type') else "function",
                            "function": {
                                "name": tool_call.function.name if hasattr(tool_call.function, 'name') else "",
                                "arguments": tool_call.function.arguments if hasattr(tool_call.function, 'arguments') else ""
                            }
                        }
                        print(f"[DEBUG] Added complete tool call from message: {call_id}, name={tool_call_buffer[call_id]['function']['name']}, args_length={len(tool_call_buffer[call_id]['function']['arguments'])}")
        
        # Process completed tool calls
        if tool_call_buffer:
            print(f"[DEBUG] Processing {len(tool_call_buffer)} tool calls from buffer")
            for call_id, tc in tool_call_buffer.items():
                args = tc.get("function", {}).get("arguments", "")
                print(f"[DEBUG] Tool call {call_id}: name={tc.get('function', {}).get('name')}, args_length={len(args) if args else 0}, args={args[:200] if args else 'EMPTY'}...")
            
            # Filter out any tool calls with None or empty IDs, and ensure arguments are present
            tool_calls = [
                tc for tc in tool_call_buffer.values() 
                if (tc.get("id") and 
                    tc.get("function", {}).get("name") and
                    tc.get("function", {}).get("arguments") is not None and
                    tc.get("function", {}).get("arguments").strip())
            ]
            print(f"[DEBUG] After filtering: {len(tool_calls)} valid tool calls")
            
            # Skip if no valid tool calls
            if not tool_calls:
                # No valid tool calls, add assistant message and we're done
                if assistant_message:
                    current_messages.append({
                        "role": "assistant",
                        "content": assistant_message
                    })
                break
            
            # Notify about tool calls
            for tool_call in tool_calls:
                if on_tool_call:
                    on_tool_call(tool_call)
                yield {"type": "tool_call", "toolCall": tool_call}
            
            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                try:
                    args_str = tool_call.get('function', {}).get('arguments', '')
                    print(f"[DEBUG] Executing tool: {tool_call['function']['name']}")
                    print(f"[DEBUG] Tool arguments (length {len(args_str)}): {args_str[:200]}...")  # Show first 200 chars
                    if not args_str or not args_str.strip():
                        raise ValueError(f"Tool {tool_call['function']['name']} has empty arguments")
                    result = await execute_tool_call(tool_call, mcp_manager, current_messages)
                    print(f"[DEBUG] Tool {tool_call['function']['name']} completed successfully")
                    if on_tool_result:
                        on_tool_result(result)  # Send FULL result to UI
                    
                    # Create a version for LLM context that excludes large data (like commits)
                    result_for_llm = result.copy() if isinstance(result, dict) else result
                    
                    # Replace commits, issues, and pull requests with minimal structures to prevent context bloat
                    # This tells the LLM data was retrieved but prevents it from generating summaries
                    # Full data is sent to UI for table display
                    
                    if isinstance(result_for_llm, dict) and "commits" in result_for_llm:
                        commits_count = len(result_for_llm["commits"]) if isinstance(result_for_llm["commits"], list) else 0
                        if commits_count > 0:
                            result_for_llm["commits"] = {
                                "_count": commits_count,
                                "_instruction": "STOP. DO NOT mention, summarize, list, or discuss commits. Commit history is displayed in the UI table. The user can see it. Only acknowledge availability if directly asked, but provide NO details."
                            }
                            print(f"[DEBUG] Replaced {commits_count} commits with minimal structure in LLM context (full data in UI)")
                    
                    if isinstance(result_for_llm, dict) and "issues" in result_for_llm:
                        issues_count = len(result_for_llm["issues"]) if isinstance(result_for_llm["issues"], list) else 0
                        if issues_count > 0:
                            result_for_llm["issues"] = {
                                "_count": issues_count,
                                "_instruction": "STOP. DO NOT mention, summarize, list, or discuss issues. Issues are displayed in the UI table. The user can see them. Only acknowledge availability if directly asked, but provide NO details."
                            }
                            print(f"[DEBUG] Replaced {issues_count} issues with minimal structure in LLM context (full data in UI)")
                    
                    if isinstance(result_for_llm, dict) and "pullRequests" in result_for_llm:
                        prs_count = len(result_for_llm["pullRequests"]) if isinstance(result_for_llm["pullRequests"], list) else 0
                        if prs_count > 0:
                            result_for_llm["pullRequests"] = {
                                "_count": prs_count,
                                "_instruction": "STOP. DO NOT mention, summarize, list, or discuss pull requests. Pull requests are displayed in the UI table. The user can see them. Only acknowledge availability if directly asked, but provide NO details."
                            }
                            print(f"[DEBUG] Replaced {prs_count} pull requests with minimal structure in LLM context (full data in UI)")
                    
                    # Replace screenshots with minimal structure to prevent LLM from mentioning them
                    if isinstance(result_for_llm, dict) and "screenshot" in result_for_llm:
                        screenshot_data = result_for_llm["screenshot"]
                        if screenshot_data and isinstance(screenshot_data, str) and len(screenshot_data) > 0:
                            result_for_llm["screenshot"] = {
                                "_available": True,
                                "_instruction": "STOP. DO NOT mention, describe, or discuss the screenshot. The screenshot is displayed in the UI gallery. The user can see it. Do NOT include any links, data URLs, or references to the screenshot in your response. Only acknowledge that a screenshot was taken if directly asked, but provide NO details or links."
                            }
                            print(f"[DEBUG] Replaced screenshot with minimal structure in LLM context (full data in UI)")
                    
                    # Truncate other large data for LLM context
                    result_for_llm = _truncate_tool_result(result_for_llm)
                    
                    # Convert to JSON and truncate if still too large (max 50000 chars for tool result content)
                    content_str = json.dumps(result_for_llm)
                    if len(content_str) > 50000:
                        print(f"[DEBUG] Tool result content too large ({len(content_str)} chars), truncating to 50000")
                        content_str = content_str[:50000] + '..."[truncated]"'
                    
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["function"]["name"],
                        "content": content_str  # This goes to LLM context (without commits)
                    })
                    yield {"type": "tool_result", "result": result}  # This goes to UI (with full commits)
                except Exception as e:
                    print(f"[ERROR] Tool {tool_call['function']['name']} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    error_result = {"error": str(e)}
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["function"]["name"],
                        "content": json.dumps(error_result)
                    })
                    yield {"type": "tool_result", "result": error_result}
            
            # Add assistant message and tool results to conversation
            # Ensure all tool_calls have valid IDs before adding
            valid_tool_calls = [
                tc for tc in tool_calls 
                if tc.get("id") and isinstance(tc.get("id"), str) and tc.get("function", {}).get("name")
            ]
            
            current_messages.append({
                "role": "assistant",
                "content": assistant_message or None,
                "tool_calls": valid_tool_calls
            })
            # Add tool results (already truncated)
            current_messages.extend(tool_results)
            
            # Apply additional truncation to prevent context bloat
            current_messages = _truncate_messages(current_messages, max_messages=10)
        else:
            # No tool calls, add assistant message and we're done
            if assistant_message:
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })
            break

