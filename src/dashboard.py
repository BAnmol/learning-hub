import datetime
import json
import os
import sys
from typing import Any, Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns


class DashboardRenderer:
    """Renders LeetCode, CodeChef, and Codeforces statistics to rich terminal interfaces and files."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console(legacy_windows=False)

    def render(self, data: Dict[str, Any]) -> None:
        """Dispatch rendering based on platform."""
        platform = data.get("platform", "leetcode")
        if platform == "codechef":
            self.render_codechef(data)
        elif platform == "codeforces":
            self.render_codeforces(data)
        else:
            self.render_leetcode(data)

    def render_leetcode(self, data: Dict[str, Any]) -> None:
        """Render the complete LeetCode dashboard."""
        username = data.get("username", "Unknown")
        profile = data.get("profile", {})
        contest = data.get("contest", {})
        contest_info = contest.get("contest_info", {})
        recent_submissions = data.get("recent_submissions", [])
        ac_stats = data.get("ac_submissions", {})
        total_stats = data.get("total_submissions", {})
        all_q = data.get("all_questions_count", {})

        # --- Header Panel ---
        real_name = profile.get("realName") or username
        ranking = profile.get("ranking")
        ranking_str = f"#{ranking:,}" if ranking else "Unranked"
        company = profile.get("company") or "N/A"
        country = profile.get("countryName") or "Global"
        streak = data.get("streak", 0)
        active_days = data.get("total_active_days", 0)

        header_text = Text()
        header_text.append(f"👤 {real_name} (@{username})\n", style="bold cyan")
        header_text.append(f"🏆 Global Rank: ", style="bold")
        header_text.append(f"{ranking_str}   ", style="bold green")
        header_text.append(f"🔥 Active Streak: ", style="bold")
        header_text.append(f"{streak} days   ", style="bold red")
        header_text.append(f"📅 Total Active: ", style="bold")
        header_text.append(f"{active_days} days\n", style="bold yellow")
        header_text.append(f"🏢 Company: {company} | 📍 Location: {country}\n", style="dim")

        if profile.get("aboutMe"):
            header_text.append(f"📝 {profile.get('aboutMe').strip()[:100]}\n", style="italic")

        header_panel = Panel(
            header_text,
            title="[bold yellow]LeetCode User Profile[/bold yellow]",
            border_style="cyan",
            expand=True,
        )
        self.console.print(header_panel)

        # --- Problems Solved Table ---
        table = Table(
            title="📊 Problems Solved Progress",
            header_style="bold magenta",
            border_style="blue",
            expand=True,
        )
        table.add_column("Difficulty", style="bold", justify="left")
        table.add_column("Solved", justify="right")
        table.add_column("Total Available", justify="right")
        table.add_column("Completion %", justify="right")
        table.add_column("Total Submissions", justify="right")
        table.add_column("Acceptance Rate", justify="right")

        diff_colors = {
            "Easy": "green",
            "Medium": "yellow",
            "Hard": "red",
            "All": "bold cyan",
        }

        for diff in ["Easy", "Medium", "Hard", "All"]:
            solved = ac_stats.get(diff, {}).get("count", 0)
            total = all_q.get(diff, 0)
            pct = (solved / total * 100) if total > 0 else 0.0

            sub_ac = ac_stats.get(diff, {}).get("submissions", 0)
            sub_tot = total_stats.get(diff, {}).get("submissions", 0)
            acc_rate = (sub_ac / sub_tot * 100) if sub_tot > 0 else 0.0

            color = diff_colors.get(diff, "white")
            table.add_row(
                f"[{color}]{diff}[/{color}]",
                f"[{color}]{solved}[/{color}]",
                str(total),
                f"{pct:.1f}%",
                str(sub_tot),
                f"{acc_rate:.1f}%",
            )

        self.console.print(table)

        # --- Contest Information ---
        if contest_info and contest_info.get("attendedContestsCount", 0) > 0:
            c_rating = round(contest_info.get("rating", 0))
            c_rank = contest_info.get("globalRanking", 0)
            c_attended = contest_info.get("attendedContestsCount", 0)
            c_top_pct = contest_info.get("topPercentage", 0)
            c_badge = contest_info.get("badge", {}).get("name") if contest_info.get("badge") else "None"

            c_text = Text()
            c_text.append(f"🎯 Rating: ", style="bold")
            c_text.append(f"{c_rating}   ", style="bold yellow")
            c_text.append(f"🏅 Global Contest Rank: ", style="bold")
            c_text.append(f"#{c_rank:,}   ", style="bold green")
            c_text.append(f"📊 Top: ", style="bold")
            c_text.append(f"{c_top_pct:.2f}%   ", style="bold cyan")
            c_text.append(f"⚔️ Contests: ", style="bold")
            c_text.append(f"{c_attended}   ", style="bold magenta")
            if c_badge != "None":
                c_text.append(f"🎖️ Badge: {c_badge}", style="bold gold1")

            self.console.print(
                Panel(
                    c_text,
                    title="[bold yellow]Contest Performance[/bold yellow]",
                    border_style="magenta",
                    expand=True,
                )
            )

    def render_codechef(self, data: Dict[str, Any]) -> None:
        """Render CodeChef profile dashboard."""
        username = data.get("username", "Unknown")
        name = data.get("name", username)
        rating = data.get("rating", 0)
        highest = data.get("highest_rating", 0)
        stars = data.get("stars", "1★")
        division = data.get("division", "Div 4")
        global_rank = data.get("global_rank", "N/A")
        country_rank = data.get("country_rank", "N/A")
        country = data.get("country", "Global")
        contests_count = data.get("contests_count", 0)
        fully_solved = data.get("fully_solved", 0)
        partially_solved = data.get("partially_solved", 0)
        total_solved = data.get("total_solved", 0)

        header_text = Text()
        header_text.append(f"👤 {name} (@{username})   ", style="bold yellow")
        header_text.append(f"⭐ {stars}   ", style="bold gold1")
        header_text.append(f"🛡️ {division}\n", style="bold cyan")
        header_text.append(f"🎯 Rating: {rating} (Peak: {highest})   ", style="bold green")
        header_text.append(f"🌍 Global Rank: #{global_rank}   ", style="bold")
        header_text.append(f"📍 Country Rank ({country}): #{country_rank}\n", style="dim")

        header_panel = Panel(
            header_text,
            title="[bold orange3]CodeChef User Dashboard[/bold orange3]",
            border_style="yellow",
            expand=True,
        )
        self.console.print(header_panel)

        # Problems & Contests Table
        table = Table(title="📈 Solved & Participation", border_style="yellow", expand=True)
        table.add_column("Category", style="bold")
        table.add_column("Count", justify="right", style="bold cyan")
        table.add_row("Fully Solved Problems", str(fully_solved))
        table.add_row("Partially Solved Problems", str(partially_solved))
        table.add_row("Total Problems Solved", f"[bold green]{total_solved}[/bold green]")
        table.add_row("Rated Contests Attended", f"[bold magenta]{contests_count}[/bold magenta]")
        self.console.print(table)

    def render_codeforces(self, data: Dict[str, Any]) -> None:
        """Render Codeforces profile dashboard."""
        username = data.get("username", "Unknown")
        name = data.get("name", username)
        rating = data.get("rating", 0)
        max_rating = data.get("max_rating", 0)
        rank = data.get("rank", "Unrated")
        max_rank = data.get("max_rank", "Unrated")
        country = data.get("country", "Global")
        city = data.get("city", "N/A")
        contests_count = data.get("contests_count", 0)
        total_solved = data.get("total_solved", 0)
        contribution = data.get("contribution", 0)

        header_text = Text()
        header_text.append(f"👤 {name} (@{username})   ", style="bold cyan")
        header_text.append(f"🎖️ {rank}\n", style="bold red")
        header_text.append(f"🎯 Current Rating: {rating}   ", style="bold green")
        header_text.append(f"🔥 Max Rating: {max_rating} ({max_rank})\n", style="bold yellow")
        header_text.append(f"📍 Location: {city}, {country} | 🤝 Contribution: {contribution}\n", style="dim")

        header_panel = Panel(
            header_text,
            title="[bold cyan]Codeforces User Dashboard[/bold cyan]",
            border_style="cyan",
            expand=True,
        )
        self.console.print(header_panel)

        # Stats Table
        table = Table(title="📊 Codeforces Performance", border_style="cyan", expand=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right", style="bold green")
        table.add_row("Unique Solved Problems", str(total_solved))
        table.add_row("Rated Contests Attended", str(contests_count))
        self.console.print(table)

    @staticmethod
    def export_to_json(data: Dict[str, Any], filepath: str = "data/dashboard_snapshot.json") -> str:
        """Export raw dashboard data to a JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath
