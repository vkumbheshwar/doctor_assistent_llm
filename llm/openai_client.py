"""
OpenAI Chat Client with Tool Calling
=======================================

DESIGN CONCEPT: The Conversation Loop
---------------------------------------
This is the core orchestration pattern for LLM-powered agents.

The loop works as follows:

┌─────────────────────────────────────────────────┐
│                  START                           │
│     (User sends a message)                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  1. Send messages + tools to OpenAI API          │
│     (includes system prompt, conversation        │
│      history, and tool definitions)              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  2. OpenAI processes and responds               │
│                                                  │
│  ┌─────────────┐     ┌─────────────────────┐    │
│  │ RESPONSE:   │     │ TOOL CALL:          │    │
│  │ Text reply  │     │ "call tool X with   │    │
│  │ to user     │     │  args {a, b, c}"    │    │
│  └──────┬──────┘     └──────────┬──────────┘    │
│         │                       │                │
└─────────┼───────────────────────┼────────────────┘
          │                       │
          ▼                       ▼
    Print to user          ┌──────────────────────┐
                           │ 3. Execute our       │
                           │    Python handler    │
                           │    function          │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ 4. Send tool result  │
                           │    back to OpenAI    │
                           │    as a "tool"       │
                           │    response message  │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ 5. Go to step 2      │
                           │    (OpenAI uses the  │
                           │    result to decide  │
                           │    next action)      │
                           └──────────────────────┘

This loop continues until:
  a) OpenAI produces a text response (no more tool calls)
  b) We hit a maximum iteration limit (safety guard)

DESIGN CONCEPT: The "Agent" Pattern
--------------------------------------
- The LLM is the "brain" that understands natural language
- The tools are the "hands" that interact with our database
- The loop is the "nervous system" connecting brain to hands

This is a fundamental pattern in modern AI applications called
the "ReAct" (Reasoning + Acting) pattern.
"""

import json
import time
from typing import Optional

from openai import OpenAI

from doctor_assistant.config.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS,
    SYSTEM_PROMPT,
)
from doctor_assistant.tools.tools_definitions import (
    get_tool_definitions,
    create_tool_handlers,
)


class OpenAIChatClient:
    """
    Manages the conversation with OpenAI's API, including tool calling.
    
    This class encapsulates:
      - The OpenAI client initialization
      - The message history management
      - The tool call execution loop
      - Response handling
    
    Attributes:
        client: The OpenAI API client
        model: The model name (e.g., "gpt-4o-mini")
        tools: The tool definitions sent to the API
        handlers: The Python functions that execute tool calls
        messages: The conversation history (list of message dicts)
    """
    
    def __init__(self, db):
        """
        Initialize the chat client.
        
        Args:
            db: Database instance (passed to tool handlers)
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
        self.max_tokens = OPENAI_MAX_TOKENS
        
        # Get tool definitions and handlers
        self.tools = get_tool_definitions()
        self.handlers = create_tool_handlers(db)
        
        # Initialize conversation with the system prompt
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    
    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self.messages.append({"role": "user", "content": content})
    
    def get_response(self) -> str:
        """
        Send messages to OpenAI and handle tool calling loop.
        
        This method:
        1. Sends the current message history to OpenAI
        2. If OpenAI wants to call a tool, executes it and loops
        3. If OpenAI responds with text, returns it
        
        Returns:
            The assistant's text response
        """
        max_iterations = 15  # Safety limit to prevent infinite loops
        iteration_count = 0
        
        while iteration_count < max_iterations:
            iteration_count += 1
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools if self.tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            # Get the response message
            response_message = response.choices[0].message
            
            # Check if the model wants to call tools
            if response_message.tool_calls:
                # Add the assistant's message with tool calls to history
                # (OpenAI expects this to maintain conversation state)
                assistant_msg = {
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in response_message.tool_calls
                    ]
                }
                self.messages.append(assistant_msg)
                
                # Process each tool call
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"\n  [Tool] Calling: {function_name}")
                    print(f"  [Tool] Args: {json.dumps(function_args, indent=2)}")
                    
                    # Look up and execute the handler
                    handler = self.handlers.get(function_name)
                    if handler:
                        try:
                            function_response = handler(**function_args)
                            print(f"  [Tool] Result: {function_response[:200]}{'...' if len(function_response) > 200 else ''}")
                        except Exception as e:
                            function_response = f"Error executing {function_name}: {str(e)}"
                            print(f"  [Tool] Error: {function_response}")
                    else:
                        function_response = f"Unknown tool: {function_name}"
                        print(f"  [Tool] Unknown tool requested: {function_name}")
                    
                    # Send the tool result back to OpenAI
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })
                
                # Continue the loop - let OpenAI process tool results
                continue
            
            # If no tool calls, this is a text response
            if response_message.content:
                # Add assistant response to history
                self.messages.append({
                    "role": "assistant",
                    "content": response_message.content
                })
                return response_message.content
            
            # Fallback (shouldn't happen with well-configured models)
            return "I apologize, but I couldn't process that request."
        
        # Safety limit reached
        return (
            "I apologize, but this conversation has become too complex "
            "for me to handle in one exchange. Please start a new conversation."
        )
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation for debugging/reference.
        Excludes system prompt details for brevity.
        """
        summary = []
        for msg in self.messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "system":
                continue  # Skip system prompt in summary
            
            if role == "assistant":
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        func_name = tc["function"]["name"]
                        summary.append(f"[Assistant called: {func_name}]")
                else:
                    summary.append(f"[Assistant]: {content[:100]}...")
            
            elif role == "tool":
                summary.append(f"[Tool result]: {content[:80]}...")
            
            elif role == "user":
                summary.append(f"[User]: {content[:100]}...")
        
        return "\n".join(summary)
    
    def reset(self):
        """Reset the conversation (keep system prompt, clear history)."""
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]