import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .agent import release, resume, run
from .config import Settings
from .models import ResumeRequest, RunRequest


def create_server(settings: Settings | None = None, runner=run):
    current = settings or Settings.load()
    mcp = FastMCP("jev-browser-plugin", log_level="ERROR")

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_run(request: RunRequest) -> dict[str, Any]:
        """Run a bounded ultrafast browser loop in Chrome.

        The caller supplies the complete goal, start URL, allowed domains, explicit stop phrases,
        and any non-sensitive text values. Jev chooses operation, target, and prepared text value
        together; Browser Harness executes through one persistent CDP session. Supply generic
        stages, transition preconditions/results and final evidence for locally verified completion.
        Label/form guards stop recognized sensitive or consequential interactions; they are not
        a universal safety classifier. Use only authorized public, non-sensitive workflows.
        """
        return runner(request, current)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_resume(request: ResumeRequest) -> dict[str, Any]:
        """Resume a paused fast session with additional non-sensitive prepared text.

        Preserves its tab, stages, allowed domains and safety boundaries. Sessions expire after
        30 minutes idle or server restart. Never resumes safety stops or uncertain execution errors.
        """
        return resume(request, current)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_release(session_id: str) -> dict[str, Any]:
        """Release a paused session's memory without closing any Chrome tabs."""
        return release(session_id)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_health() -> dict[str, Any]:
        """Check configuration and fast-browser dependencies without opening Chrome."""
        try:
            import browser_harness  # noqa: F401

            harness_available = True
        except ImportError:
            harness_available = False
        return {
            "configured": bool(current.api_key) and not current.configuration_error,
            "configuration_error": current.configuration_error,
            "model": current.model,
            "browser_harness_available": harness_available,
            "browser_connected": None,
            "browser_check": "not_performed",
            "execution_mode": "ultrafast",
            "advisory_only": False,
        }

    return mcp


def main():
    logging.disable(logging.CRITICAL)
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
