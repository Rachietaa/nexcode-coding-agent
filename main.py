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


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]  ███╗   ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ███████╗\n"
        "  ████╗  ██║██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝\n"
        "  ██╔██╗ ██║█████╗   ╚███╔╝ ██║     ██║   ██║██║  ██║█████╗  \n"
        "  ██║╚██╗██║██╔══╝   ██╔██╗ ██║     ██║   ██║██║  ██║██╔══╝  \n"
        "  ██║ ╚████║███████╗██╔╝ ██╗╚██████╗╚██████╔╝██████╔╝███████╗\n"
        "  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝[/bold cyan]\n\n"
        "[bold white]         AI Coding Assistant — Autonomous. Fast. Powerful.[/bold white]",
        border_style="cyan",
    ))


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
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return []


def save_session(messages: list):
    with open(SESSION_FILE, "w") as f:
        json.dump(messages, f, indent=2)


async def main():
    print_banner()
    print_providers()

    # Provider and model selection
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

    # Session persistence
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

    console.print("\n[cyan]Connecting to MCP servers...[/cyan]")

    # Updated API: no async with, just call get_tools() directly
    client = build_mcp_client(workspace)
    tools = await client.get_tools()

    # Show all loaded tools in a table
    t = Table(title="Loaded MCP Tools", border_style="green")
    t.add_column("Tool", style="cyan")
    t.add_column("Server", style="yellow")
    for tool in tools:
        parts = tool.name.split("_")
        server = parts[0] if len(parts) > 1 else "rag"
        t.add_row(tool.name, server)
    console.print(t)
    console.print(f"[bold green]✓ {len(tools)} tools loaded from 3 MCP servers[/bold green]")
    console.print("\n[dim]Type your task. Commands: [bold]exit[/bold] | [bold]clear[/bold][/dim]\n")

    # Main REPL loop
    while True:
        try:
            task = Prompt.ask("[bold yellow]nexcode ❯[/bold yellow]")
        except (KeyboardInterrupt, EOFError):
            break

        if task.strip().lower() in ["exit", "quit", "q"]:
            save_session(messages_history)
            console.print("[bold cyan]Session saved. Goodbye! 👋[/bold cyan]")
            break

        if task.strip().lower() == "clear":
            messages_history = []
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            console.print("[yellow]Session cleared.[/yellow]")
            continue

        if not task.strip():
            continue

        messages_history = await run_agent(
            task=task,
            llm=llm,
            tools=tools,
            auto_execute=(mode == "auto"),
            messages_history=messages_history,
        )
        save_session(messages_history)


if __name__ == "__main__":
    asyncio.run(main())
