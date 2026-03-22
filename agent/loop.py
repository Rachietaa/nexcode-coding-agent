from langgraph.prebuilt import create_react_agent
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from rich.pretty import Pretty

console = Console()


def show_reasoning(text: str):
    if text and text.strip():
        console.print()
        console.print(
            Panel(
                escape(text),
                title="[bold magenta]Agent Reasoning[/bold magenta]",
                border_style="magenta",
                expand=False,
            )
        )


def show_tool_call(tool_name: str, tool_args):
    console.print()
    console.print(
        Panel(
            Pretty(tool_args),
            title=f"[bold yellow]⚙ Tool Call: {tool_name}[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )


def show_tool_result(tool_name: str, result):
    preview = str(result)
    if len(preview) > 800:
        preview = preview[:800] + "\n... [truncated]"
    console.print()
    console.print(
        Panel(
            escape(preview),
            title=f"[bold green]✓ Tool Result: {tool_name}[/bold green]",
            border_style="green",
            expand=False,
        )
    )


async def run_agent(task: str, llm, tools, auto_execute: bool = False, messages_history: list = None):
    """
    Core agentic loop. Streams LLM responses and displays reasoning and tool calls visibly.
    """
    messages = messages_history or []
    messages.append({"role": "user", "content": task})

    priority_tool_names = [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "create_directory",
        "search_files",
        "directory_tree",
        "tavily-search",
        "tavily-extract",
        "query_documentation",
    ]
    filtered_tools = [t for t in tools if t.name in priority_tool_names]
    if not filtered_tools:
        filtered_tools = tools

    agent = create_react_agent(model=llm, tools=filtered_tools)

    console.print()
    console.rule("[bold cyan]NexCode Agent Running[/bold cyan]")
    console.print(f"[bold white]User Task:[/bold white] {task}")

    full_response = ""
    current_tool = None
    streamed_text_buffer = ""

    try:
        async for msg_chunk, metadata in agent.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            if hasattr(msg_chunk, "tool_call_chunks") and msg_chunk.tool_call_chunks:
                for tc in msg_chunk.tool_call_chunks:
                    tool_name = tc.get("name")
                    tool_args = tc.get("args", "")

                    if tool_name and tool_name != current_tool:
                        current_tool = tool_name
                        show_tool_call(tool_name, tool_args)

                        if not auto_execute:
                            confirm = console.input(
                                "[bold red]Run this tool? (y/n): [/bold red]"
                            ).strip().lower()
                            if confirm != "y":
                                console.print("[red]✗ Tool execution skipped by user.[/red]")
                                return messages

            if hasattr(msg_chunk, "content") and msg_chunk.content:
                if isinstance(msg_chunk.content, str):
                    console.print(msg_chunk.content, end="", highlight=False)
                    full_response += msg_chunk.content
                    streamed_text_buffer += msg_chunk.content

            if hasattr(msg_chunk, "type") and msg_chunk.type == "tool":
                result_preview = msg_chunk.content
                show_tool_result(current_tool or "tool", result_preview)
                current_tool = None

        if streamed_text_buffer.strip():
            show_reasoning(streamed_text_buffer.strip())

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")

    console.print()
    console.rule("[bold cyan]Done[/bold cyan]")

    if full_response:
        messages.append({"role": "assistant", "content": full_response})

    return messages
