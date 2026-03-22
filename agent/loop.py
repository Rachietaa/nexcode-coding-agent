from langgraph.prebuilt import create_react_agent
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape

console = Console()


async def run_agent(task: str, llm, tools, auto_execute: bool = False, messages_history: list = None):
    """
    Core agentic loop. Streams LLM responses and displays tool calls visibly.
    """
    messages = messages_history or []
    messages.append({"role": "user", "content": task})

    # Limit to key tools only — Groq struggles with too many tools at once
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
        filtered_tools = tools  # fallback to all if filter fails

    agent = create_react_agent(model=llm, tools=filtered_tools)

    console.print()
    console.rule("[bold cyan]NexCode Agent Running[/bold cyan]")

    full_response = ""
    current_tool = None

    try:
        async for msg_chunk, metadata in agent.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            # Show tool calls clearly
            if hasattr(msg_chunk, "tool_call_chunks") and msg_chunk.tool_call_chunks:
                for tc in msg_chunk.tool_call_chunks:
                    if tc.get("name") and tc["name"] != current_tool:
                        current_tool = tc["name"]
                        console.print()
                        console.print(
                            Panel(
                                f"[bold yellow]⚙  Tool Call:[/bold yellow] [cyan]{tc['name']}[/cyan]",
                                border_style="yellow",
                                expand=False,
                            )
                        )
                        if not auto_execute:
                            confirm = console.input(
                                "[bold red]  Run this tool? (y/n): [/bold red]"
                            ).strip().lower()
                            if confirm != "y":
                                console.print("[red]  ✗ Skipped by user.[/red]")
                                return messages

            # Show tool args
            if hasattr(msg_chunk, "tool_call_chunks") and msg_chunk.tool_call_chunks:
                for tc in msg_chunk.tool_call_chunks:
                    if tc.get("args"):
                        console.print(f"[dim]  {escape(tc['args'])}[/dim]", end="")

            # Stream AI text
            if hasattr(msg_chunk, "content") and msg_chunk.content:
                if isinstance(msg_chunk.content, str):
                    console.print(msg_chunk.content, end="", highlight=False)
                    full_response += msg_chunk.content

            # Show tool result
            if hasattr(msg_chunk, "type") and msg_chunk.type == "tool":
                result_preview = str(msg_chunk.content)[:300]
                console.print()
                console.print(
                    Panel(
                        f"[bold green]✓ Result:[/bold green] [dim]{escape(result_preview)}[/dim]",
                        border_style="green",
                        expand=False,
                    )
                )
                current_tool = None

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")

    console.print()
    console.rule("[bold cyan]Done[/bold cyan]")

    if full_response:
        messages.append({"role": "assistant", "content": full_response})

    return messages
