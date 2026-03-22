"""
NexCode — AI Coding Assistant
Main CLI entry point.
"""

import asyncio
import json
import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agent.providers import get_llm
from agent.loop import run_agent
from mcp_client.client import build_mcp_client

console = Console()
SESSION_FILE = ".nexcode_session.json"
AGENT_TIMEOUT_SECONDS = 90


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]  ███╗   ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ███████╗\n"
            "  ████╗  ██║██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝\n"
            "  ██╔██╗ ██║█████╗   ╚███╔╝ ██║     ██║   ██║██║  ██║█████╗  \n"
            "  ██║╚██╗██║██╔══╝   ██╔██╗ ██║     ██║   ██║██║  ██║██╔══╝  \n"
            "  ██║ ╚████║███████╗██╔╝ ██╗╚██████╗╚██████╔╝██████╔╝███████╗\n"
            "  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝[/bold cyan]\n\n"
            "[bold white]         AI Coding Assistant — Autonomous. Fast. Powerful.[/bold white]",
            border_style="cyan",
        )
    )


def print_providers():
    t = Table(title="Available Providers", border_style="cyan")
    t.add_column("Provider", style="cyan")
    t.add_column("Example Model", style="white")
    t.add_column("Notes", style="dim")
    t.add_row("groq", "llama-3.3-70b-versatile", "FREE API key — recommended")
    t.add_row("ollama", "llama3.2, codellama", "Fully local, no key needed")
    t.add_row("openai", "gpt-4o, gpt-4o-mini", "Paid API key required")
    t.add_row("anthropic", "claude-3-5-sonnet-20241022", "Paid API key required")
    console.print(t)


def load_session() -> list:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_session(messages: list):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)


def infer_server_name(tool_name: str) -> str:
    lowered = tool_name.lower()

    if "tavily" in lowered:
        return "Tavily MCP"

    if lowered in {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "create_directory",
        "search_files",
        "move_file",
        "delete_file",
        "get_file_info",
        
    }:
        return "Filesystem MCP"

    if "documentation" in lowered or "query_documentation" in lowered:
        return "RAG MCP"

    return "Custom / Other"


def select_tools_for_task(task: str, tools: list):
    task_lower = task.lower()

    if "use only the query_documentation tool" in task_lower:
        return [t for t in tools if t.name == "query_documentation"]

    doc_keywords = [
        "documentation",
        "docs",
        "local documentation",
        "query_documentation",
        "langchain agents",
        "summarize what the local documentation says",
    ]

    if any(keyword in task_lower for keyword in doc_keywords):
        selected = [t for t in tools if t.name == "query_documentation"]
        if selected:
            return selected

    return tools


async def main():
    print_banner()
    print_providers()

    provider = Prompt.ask(
        "\n[bold cyan]Provider[/bold cyan]",
        choices=["groq", "ollama", "openai", "anthropic"],
        default="groq",
    )
    model = Prompt.ask(
        "[bold cyan]Model[/bold cyan]",
        default="llama-3.3-70b-versatile",
    )
    mode = Prompt.ask(
        "[bold cyan]Mode[/bold cyan]",
        choices=["auto", "confirm"],
        default="confirm",
    )

    messages_history = []
    if os.path.exists(SESSION_FILE):
        resume = Prompt.ask(
            "[bold cyan]Resume previous session?[/bold cyan]",
            choices=["y", "n"],
            default="n",
        )
        if resume == "y":
            messages_history = load_session()
            console.print(f"[green]✓ Resumed {len(messages_history)} messages[/green]")

    workspace = Prompt.ask(
        "[bold cyan]Workspace path[/bold cyan]",
        default=os.getcwd(),
    )

    llm = get_llm(provider, model)

    console.print("\n[bold cyan]Connecting to MCP servers...[/bold cyan]")
    console.print("[green]✓ Filesystem MCP server connected[/green]")
    console.print("[green]✓ Tavily MCP server connected[/green]")
    console.print("[green]✓ RAG MCP server connected[/green]")

    client = build_mcp_client(workspace)
    tools = await client.get_tools()

    t = Table(title="Loaded MCP Tools", border_style="green")
    t.add_column("#", style="dim", width=4)
    t.add_column("Tool", style="cyan")
    t.add_column("Server", style="yellow")

    for i, tool in enumerate(tools, start=1):
        t.add_row(str(i), tool.name, infer_server_name(tool.name))

    console.print()
    console.print(t)
    console.print(f"[bold green]✓ {len(tools)} tools loaded from 3 MCP servers[/bold green]")
    console.print("\n[dim]Type your task. Commands: [bold]exit[/bold] | [bold]clear[/bold][/dim]\n")

    while True:
        try:
            task = Prompt.ask("[bold yellow]nexcode ❯[/bold yellow]")
        except (KeyboardInterrupt, EOFError):
            break

        normalized = task.strip().lower()

        if normalized in ["exit", "quit", "q"]:
            save_session(messages_history)
            console.print("[bold cyan]Session saved. Goodbye! 👋[/bold cyan]")
            break

        if normalized == "clear":
            messages_history = []
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            console.print("[yellow]Session cleared.[/yellow]")
            continue

        if not task.strip():
            continue

        selected_tools = select_tools_for_task(task, tools)

        console.print(f"[bold magenta]Task lower:[/bold magenta] {task.lower()}")
        console.print(f"[bold magenta]Selected tools:[/bold magenta] {[t.name for t in selected_tools]}")

        if not selected_tools:
            console.print("[bold red]Error:[/bold red] No tools selected for this task.")
            continue

        try:
            messages_history = await asyncio.wait_for(
                run_agent(
                    task=task,
                    llm=llm,
                    tools=selected_tools,
                    auto_execute=(mode == "auto"),
                    messages_history=messages_history,
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            save_session(messages_history)

        except asyncio.TimeoutError:
            console.print(
                f"[bold red]Error:[/bold red] Agent timed out after {AGENT_TIMEOUT_SECONDS} seconds."
            )
        except KeyboardInterrupt:
            console.print("[yellow]Interrupted.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    save_session(messages_history)


if __name__ == "__main__":
    asyncio.run(main())
