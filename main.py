import argparse
import os
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

from src.leetcode_client import LeetCodeClient
from src.codechef_client import CodeChefClient
from src.codeforces_client import CodeforcesClient
from src.dashboard import DashboardRenderer


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch and display Multi-Platform DSA Dashboards.")
    parser.add_argument(
        "-p",
        "--platform",
        choices=["leetcode", "codechef", "codeforces"],
        default="leetcode",
        help="Target platform (leetcode, codechef, codeforces)",
    )
    parser.add_argument("-u", "--username", help="User handle to query", default=None)
    parser.add_argument("-s", "--save", help="Save dashboard data to JSON file", action="store_true")
    parser.add_argument("-o", "--output", help="Output path for JSON file", default=None)
    parser.add_argument("--raw-json", help="Print raw JSON instead of UI", action="store_true")
    parser.add_argument("--web", help="Launch the interactive Web Dashboard", action="store_true")

    args = parser.parse_args()
    console = Console(legacy_windows=False)

    if args.web:
        console.print("\n[bold cyan]🚀 Starting Multi-Platform Web Dashboard...[/bold cyan]")
        console.print("[dim]Open in your browser:[/dim] [bold underline green]http://127.0.0.1:5000[/bold underline green]\n")
        from app import app
        app.run(host="127.0.0.1", port=5000, debug=False)
        return

    platform = args.platform.lower()

    # Determine default username by platform
    env_keys = {
        "leetcode": "LEETCODE_USERNAME",
        "codechef": "CODECHEF_USERNAME",
        "codeforces": "CODEFORCES_USERNAME",
    }
    env_var = env_keys.get(platform, "LEETCODE_USERNAME")
    username = args.username or os.getenv(env_var)

    if not username or username.strip() == "":
        username = Prompt.ask(f"[bold cyan]Enter your {platform.capitalize()} username[/bold cyan]")

    username = username.strip()
    if not username:
        console.print("[bold red]Error:[/bold red] No username provided. Exiting.")
        sys.exit(1)

    renderer = DashboardRenderer(console=console)

    with console.status(f"[bold green]Fetching {platform.capitalize()} dashboard for '{username}'...[/bold green]"):
        try:
            if platform == "codechef":
                client = CodeChefClient()
                data = client.get_user_profile(username)
            elif platform == "codeforces":
                client = CodeforcesClient()
                data = client.get_user_profile(username)
            else:
                client = LeetCodeClient()
                data = client.get_full_dashboard(username)
                data["platform"] = "leetcode"
        except Exception as e:
            console.print(f"\n[bold red]Failed to retrieve data from {platform.capitalize()} for '{username}':[/bold red] {e}")
            sys.exit(1)

    if args.raw_json:
        import json
        console.print_json(data=data)
    else:
        renderer.render(data)

    if args.save:
        out_file = args.output or f"data/{platform}_{username}_dashboard.json"
        out_path = renderer.export_to_json(data, out_file)
        console.print(f"\n[bold green]✓[/bold green] Dashboard details saved to: [underline]{out_path}[/underline]")


if __name__ == "__main__":
    main()
