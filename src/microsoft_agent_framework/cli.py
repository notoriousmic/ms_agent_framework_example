"""Command-line interface for the Microsoft Agent Framework."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from microsoft_agent_framework.application.factories import agent_factory
from microsoft_agent_framework.application.services import (
    AgentService,
    ConversationService,
)
from microsoft_agent_framework.application.services.conversation_manager import (
    ConversationManager,
)
from microsoft_agent_framework.application.services.conversation_session import (
    ConversationSession,
)
from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.models import AgentConfig, AgentType
from microsoft_agent_framework.infrastructure.repositories import (
    FileConversationRepository,
)

# Initialize Typer app
app = typer.Typer(
    name="microsoft_agent_framework",
    help="Microsoft Agent Framework CLI - Multi-agent AI orchestration",
    add_completion=False,
)

# Rich console for pretty output
console = Console()


@app.command()
def info():
    """Display framework information."""
    table = Table(title="Microsoft Agent Framework Info")

    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Environment", settings.app.environment.value)
    table.add_row("Debug Mode", str(settings.app.debug))
    table.add_row("API Host", settings.app.api_host)
    table.add_row("API Port", str(settings.app.api_port))
    table.add_row("Agent Timeout", f"{settings.app.agent_timeout}s")
    table.add_row("Azure Endpoint", settings.azure.endpoint)
    table.add_row("Azure API Version", settings.azure.api_version)
    table.add_row("OTEL Enabled", str(settings.observability.enable_otel))

    console.print(table)


@app.command()
def list_agents():
    """List available agent types."""
    factory = agent_factory.get_factory()
    agent_types = factory.get_supported_types()

    table = Table(title="Available Agent Types")
    table.add_column("Agent Type", style="cyan")
    table.add_column("Description", style="green")

    descriptions = {
        "supervisor": "Coordinates and delegates tasks to other agents",
        "research": "Performs web research using search tools",
        "writer": "Creates professional email content",
    }

    for agent_type in agent_types:
        description = descriptions.get(agent_type, "No description available")
        table.add_row(agent_type, description)

    console.print(table)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send to the agent"),
    agent_type: str = typer.Option("supervisor", help="Type of agent to use"),
    new: bool = typer.Option(False, "--new", "-n", help="Start a new conversation"),
    thread_id: str | None = typer.Option(None, "--thread", "-t", help="Continue specific conversation"),
    title: str | None = typer.Option(None, "--title", help="Title for new conversations"),
    no_save: bool = typer.Option(False, "--no-save", help="Don't save the conversation"),
):
    """Chat with an agent (automatically manages conversation threads)."""

    async def run_chat():
        try:
            # Initialize services
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            session_manager = ConversationSession()
            conversation_manager = ConversationManager(conversation_service, session_manager)

            # Create agent
            config = AgentConfig(
                name=f"{agent_type}_agent",
                agent_type=AgentType(agent_type),
                instructions="",
            )
            agent = agent_factory.create_agent(agent_type, config)
            await agent.initialize()

            # Show session info if continuing
            if not new and not thread_id:
                current_thread_id = session_manager.get_current_thread_id(agent_type)
                if current_thread_id:
                    console.print(f"[dim]Continuing conversation: {current_thread_id}[/dim]")
                else:
                    console.print("[dim]Starting new conversation[/dim]")
            elif thread_id:
                console.print(f"[cyan]Using conversation: {thread_id}[/cyan]")
            elif new:
                console.print(f"[cyan]Starting new conversation{f': {title}' if title else ''}[/cyan]")

            # Execute chat
            console.print(f"[cyan]Sending: {message}[/cyan]")
            response, thread = await conversation_manager.chat(
                agent=agent,
                message=message,
                thread_id=thread_id,
                new_conversation=new,
                conversation_title=title,
                auto_save=not no_save,
            )

            # Display response
            status = response.status if isinstance(response.status, str) else response.status.value
            if status == "completed":
                console.print("[green]Response:[/green]")
                for msg in response.messages:
                    console.print(f"  {msg.content}")
                message_count_info = f" | Messages: {len(thread.messages)}" if len(thread.messages) > 2 else ""
                console.print(
                    f"[dim]Time: {response.execution_time:.2f}s | Thread: {thread.thread_id}{message_count_info}[/dim]"
                )

                if not no_save:
                    console.print("[green]💾 Conversation saved[/green]")
            else:
                console.print(f"[red]Failed:[/red] {response.error}")

            # Cleanup
            await agent.cleanup()
            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_chat())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the FastAPI server."""
    import uvicorn

    console.print(f"[cyan]Starting server on {host}:{port}[/cyan]")
    uvicorn.run(
        "microsoft_agent_framework.infrastructure.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def config(
    show_sensitive: bool = typer.Option(False, help="Show sensitive configuration values"),
):
    """Display current configuration."""
    table = Table(title="Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Value", style="green")

    # App config
    for key, value in settings.app.model_dump().items():
        table.add_row("app", key, str(value))

    # Azure config (hide sensitive values unless requested)
    azure_config = settings.azure.model_dump()
    if not show_sensitive:
        azure_config["api_key"] = "***HIDDEN***"

    for key, value in azure_config.items():
        table.add_row("azure", key, str(value))

    # Observability config
    obs_config = settings.observability.model_dump()
    if not show_sensitive and obs_config.get("applicationinsights_connection_string"):
        obs_config["applicationinsights_connection_string"] = "***HIDDEN***"

    for key, value in obs_config.items():
        table.add_row("observability", key, str(value))

    # Tools config
    tools_config = settings.tools.model_dump()
    if not show_sensitive and tools_config.get("brave_api_key"):
        tools_config["brave_api_key"] = "***HIDDEN***"

    for key, value in tools_config.items():
        table.add_row("tools", key, str(value))

    console.print(table)


@app.command()
def validate():
    """Validate configuration and dependencies."""
    console.print("[cyan]Validating configuration...[/cyan]")

    errors = []
    warnings = []

    # Check Azure OpenAI configuration
    try:
        if not settings.azure.api_key:
            errors.append("Azure OpenAI API key is not set")
        if not settings.azure.endpoint:
            errors.append("Azure OpenAI endpoint is not set")
        if not settings.azure.responses_deployment_name:
            errors.append("Azure OpenAI deployment name is not set")
    except Exception as e:
        errors.append(f"Azure configuration error: {e}")

    # Check optional tools
    if not settings.tools.brave_api_key:
        warnings.append("Brave API key not set - research agent will have limited functionality")

    # Display results
    if errors:
        console.print("[red]Validation Errors:[/red]")
        for error in errors:
            console.print(f"  ❌ {error}")

    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  ⚠️  {warning}")

    if not errors and not warnings:
        console.print("[green]✅ Configuration is valid![/green]")
    elif not errors:
        console.print("[yellow]Configuration is valid with warnings[/yellow]")
    else:
        console.print("[red]Configuration has errors that need to be fixed[/red]")
        raise typer.Exit(1)


@app.command()
def chat_with_thread(
    message: str = typer.Argument(..., help="Message to send to the agent"),
    thread_id: str | None = typer.Option(None, help="Thread ID to continue conversation"),
    agent_type: str = typer.Option("supervisor", help="Type of agent to use"),
    save_thread: bool = typer.Option(True, help="Save conversation thread"),
):
    """Chat with an agent using persisted conversation threads."""

    async def run_thread_chat():
        try:
            # Initialize conversation service
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            # Load or create thread
            thread = None
            if thread_id:
                thread = await conversation_service.load_thread(thread_id)
                if not thread:
                    console.print(f"[red]Thread {thread_id} not found[/red]")
                    return
                console.print(f"[cyan]Continuing conversation in thread: {thread.thread_id}[/cyan]")
            else:
                # Create agent to get its info for thread creation
                config = AgentConfig(
                    name=f"{agent_type}_agent",
                    agent_type=AgentType(agent_type),
                    instructions="",
                )
                agent = agent_factory.create_agent(agent_type, config)
                thread = agent.get_new_thread()
                console.print(f"[cyan]Created new thread: {thread.thread_id}[/cyan]")

            # Initialize agent service
            agent_service = AgentService()
            await agent_service.initialize()

            # Create and register agent
            config = AgentConfig(
                name=f"{agent_type}_agent",
                agent_type=AgentType(agent_type),
                instructions="",
            )
            agent = agent_factory.create_agent(agent_type, config)
            agent_service.register_agent("chat_agent", agent)

            # Execute agent with thread
            console.print(f"[cyan]Sending message: {message}[/cyan]")
            response = await agent.run(message, thread=thread)

            # Display response
            status = response.status if isinstance(response.status, str) else response.status.value
            if status == "completed":
                console.print("[green]Agent Response:[/green]")
                for msg in response.messages:
                    console.print(f"  {msg.content}")
                console.print(f"[dim]Execution time: {response.execution_time:.2f}s[/dim]")
                console.print(f"[dim]Thread: {thread.thread_id}[/dim]")
            else:
                console.print(f"[red]Agent failed:[/red] {response.error}")

            # Save thread if requested
            if save_thread:
                await conversation_service.save_thread(thread)
                console.print(f"[green]Thread saved: {thread.thread_id}[/green]")

            # Cleanup
            await agent_service.cleanup()
            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_thread_chat())


@app.command()
def list_threads(
    agent_name: str | None = typer.Option(None, help="Filter by agent name"),
    agent_type: str | None = typer.Option(None, help="Filter by agent type"),
    limit: int = typer.Option(10, help="Maximum number of threads to show"),
):
    """List conversation threads."""

    async def run_list():
        try:
            # Initialize conversation service
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            # Get threads
            summaries = await conversation_service.list_threads(
                agent_name=agent_name, agent_type=agent_type, limit=limit
            )

            if not summaries:
                console.print("[yellow]No threads found[/yellow]")
                return

            # Display threads
            console.print(f"[green]Found {len(summaries)} threads:[/green]")
            for summary in summaries:
                console.print(f"\n[bold]Thread: {summary.thread_id}[/bold]")
                console.print(f"  Agent: {summary.agent_name} ({summary.agent_type})")
                console.print(f"  Messages: {summary.message_count}")
                console.print(f"  Created: {summary.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"  Updated: {summary.updated_at.strftime('%Y-%m-%d %H:%M')}")
                if summary.title:
                    console.print(f"  Title: {summary.title}")
                if summary.last_message_preview:
                    console.print(f"  Last: {summary.last_message_preview}...")

            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_list())


@app.command()
def show_thread(
    thread_id: str = typer.Argument(..., help="Thread ID to display"),
    full: bool = typer.Option(False, help="Show full conversation"),
):
    """Show details of a conversation thread."""

    async def run_show():
        try:
            # Initialize conversation service
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            # Load thread
            thread = await conversation_service.load_thread(thread_id)
            if not thread:
                console.print(f"[red]Thread {thread_id} not found[/red]")
                return

            # Display thread info
            console.print(f"[bold]Thread: {thread.thread_id}[/bold]")
            console.print(f"Agent: {thread.agent_name} ({thread.agent_type})")
            console.print(f"Messages: {len(thread.messages)}")
            console.print(f"Created: {thread.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"Updated: {thread.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if thread.title:
                console.print(f"Title: {thread.title}")
            if thread.tags:
                console.print(f"Tags: {', '.join(thread.tags)}")

            if full and thread.messages:
                console.print("\n[bold]Conversation:[/bold]")
                for i, msg in enumerate(thread.messages, 1):
                    role_color = "blue" if msg.role == "user" else "green"
                    role_name = "User" if msg.role == "user" else "Assistant"
                    console.print(f"\n[{role_color}]{i}. {role_name}:[/{role_color}]")
                    console.print(f"   {msg.content}")
                    console.print(f"   [dim]{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")

            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_show())


@app.command()
def delete_thread(
    thread_id: str = typer.Argument(..., help="Thread ID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a conversation thread."""

    async def run_delete():
        try:
            # Initialize conversation service
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            # Check if thread exists
            thread = await conversation_service.load_thread(thread_id)
            if not thread:
                console.print(f"[red]Thread {thread_id} not found[/red]")
                return

            if not confirm:
                console.print(f"Thread: {thread.thread_id}")
                console.print(f"Agent: {thread.agent_name}")
                console.print(f"Messages: {len(thread.messages)}")
                user_confirmed = typer.confirm("Are you sure you want to delete this thread?")
                if not user_confirmed:
                    console.print("[yellow]Cancelled[/yellow]")
                    return

            # Delete thread
            success = await conversation_service.delete_thread(thread_id)
            if success:
                console.print(f"[green]Thread {thread_id} deleted successfully[/green]")

                # Clear from session if it was current
                session_manager = ConversationSession()
                session_info = session_manager.get_session_info()
                for agent_type, current_id in session_info.get("threads", {}).items():
                    if current_id == thread_id:
                        session_manager.clear_current_thread(agent_type)
                        console.print(f"[dim]Cleared from {agent_type} session[/dim]")
            else:
                console.print(f"[red]Failed to delete thread {thread_id}[/red]")

            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_delete())


@app.command()
def session():
    """Show current conversation sessions."""
    try:
        session_manager = ConversationSession()
        session_info = session_manager.get_session_info()

        if not session_info.get("threads"):
            console.print("[yellow]No active conversation sessions[/yellow]")
            return

        console.print("[bold]Current Sessions:[/bold]")
        for agent_type, thread_id in session_info["threads"].items():
            console.print(f"  {agent_type}: [cyan]{thread_id}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@app.command()
def clear_session(
    agent_type: str | None = typer.Option(None, "--agent", "-a", help="Clear specific agent session"),
    all: bool = typer.Option(False, "--all", help="Clear all sessions"),
):
    """Clear conversation sessions."""
    try:
        session_manager = ConversationSession()

        if all:
            session_manager.clear_all_sessions()
            console.print("[green]All sessions cleared[/green]")
        elif agent_type:
            session_manager.clear_current_thread(agent_type)
            console.print(f"[green]Session cleared for {agent_type}[/green]")
        else:
            console.print("[yellow]Specify --agent TYPE or --all[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@app.command()
def recent(
    agent_type: str | None = typer.Option(None, "--agent", "-a", help="Filter by agent type"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of conversations to show"),
):
    """Show recent conversations."""

    async def run_recent():
        try:
            repository = FileConversationRepository()
            conversation_service = ConversationService(repository)
            await conversation_service.initialize()

            summaries = await conversation_service.list_threads(agent_type=agent_type, limit=limit)

            if not summaries:
                console.print("[yellow]No recent conversations found[/yellow]")
                return

            console.print("[bold]Recent Conversations:[/bold]")
            for i, summary in enumerate(summaries, 1):
                title_display = f" - {summary.title}" if summary.title else ""
                time_display = summary.updated_at.strftime("%m-%d %H:%M")
                console.print(f"  {i}. [cyan]{summary.thread_id[:8]}...[/cyan]{title_display}")
                console.print(f"     {summary.agent_type} | {summary.message_count} msgs | {time_display}")
                if summary.last_message_preview:
                    console.print(f"     [dim]{summary.last_message_preview[:60]}...[/dim]")
                console.print()

            await conversation_service.cleanup()

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

    asyncio.run(run_recent())


if __name__ == "__main__":
    app()
