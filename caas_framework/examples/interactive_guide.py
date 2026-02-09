"""
Interactive Requirement Guide

Provides interactive guidance for users to write better requirements.
"""

from typing import List, Optional

from caas_framework.examples.requirement_examples import (

from caas_framework.utils.logger import get_logger

logger = get_logger(__name__)

    REQUIREMENT_EXAMPLES,
    Complexity,
    Domain,
    RequirementExample,
    get_examples_by_complexity,
    get_examples_by_domain,
    search_examples,
    suggest_examples,
)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class InteractiveGuide:
    """
    Interactive guide for writing better requirements

    Helps users explore examples and get suggestions based on their needs.
    """

    def __init__(self, use_rich: bool = True):
        """
        Initialize interactive guide

        Args:
            use_rich: Use Rich library for formatted output (default: True)
        """
        self.use_rich = use_rich and RICH_AVAILABLE

        if self.use_rich:
            self.console = Console()
        else:
            self.console = None

    def show_welcome(self):
        """Display welcome message"""
        if self.use_rich:
            welcome = Panel(
                "[bold cyan]Requirement Examples & Templates[/bold cyan]\n\n"
                "Get inspired by example requirements across different domains and complexity levels.\n"
                "Learn how to write clear, comprehensive project specifications.",
                title="📝 Welcome to CAAS",
                border_style="cyan",
            )
            self.console.print(welcome)
        else:
            logger.info("\n" + "=" * 70)
            logger.info("📝 Requirement Examples & Templates")
            logger.info("=" * 70)
            logger.info("Get inspired by example requirements across different domains.")
            logger.info("Learn how to write clear, comprehensive project specifications.")
            logger.info("=" * 70 + "\n")
    def browse_by_domain(self) -> Optional[RequirementExample]:
        """
        Browse examples by domain

        Returns:
            Selected example or None
        """
        if self.use_rich:
            self.console.print("\n[bold]Available Domains:[/bold]")

            # Create table
            table = Table(show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Domain", style="green")
            table.add_column("Examples", justify="right")

            domains = list(Domain)
            for i, domain in enumerate(domains, 1):
                examples = get_examples_by_domain(domain)
                table.add_row(
                    str(i), domain.value.replace("_", " ").title(), str(len(examples))
                )

            self.console.print(table)

        else:
            logger.info("\nAvailable Domains:")
            logger.info("-" * 50)
            domains = list(Domain)
            for i, domain in enumerate(domains, 1):
                examples = get_examples_by_domain(domain)
                print(
                    f"{i}. {domain.value.replace('_', ' ').title()} ({len(examples)} examples)"
                )
            logger.info("-" * 50)
        # Get user selection
        choice = input("\nSelect domain (number) or press Enter to skip: ").strip()

        if not choice:
            return None

        try:
            domain_idx = int(choice) - 1
            if 0 <= domain_idx < len(domains):
                selected_domain = domains[domain_idx]
                return self._show_domain_examples(selected_domain)
        except ValueError:
            pass

        return None

    def _show_domain_examples(self, domain: Domain) -> Optional[RequirementExample]:
        """Show examples for a specific domain"""
        examples = get_examples_by_domain(domain)

        if not examples:
            logger.info(f"No examples found for {domain.value}")
            return None

        if self.use_rich:
            self.console.print(
                f"\n[bold]{domain.value.replace('_', ' ').title()} Examples:[/bold]\n"
            )

            table = Table(show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Title", style="green")
            table.add_column("Complexity", style="yellow")
            table.add_column("Features", justify="right")

            for i, ex in enumerate(examples, 1):
                table.add_row(
                    str(i), ex.title, ex.complexity.value, str(len(ex.key_features))
                )

            self.console.print(table)
        else:
            logger.info(f"\n{domain.value.replace('_', ' ').title()} Examples:")
            logger.info("-" * 70)
            for i, ex in enumerate(examples, 1):
                print(
                    f"{i}. {ex.title} [{ex.complexity.value}] - {len(ex.key_features)} features"
                )
            logger.info("-" * 70)
        # Get user selection
        choice = input(
            "\nSelect example (number) to view details or press Enter to skip: "
        ).strip()

        if not choice:
            return None

        try:
            ex_idx = int(choice) - 1
            if 0 <= ex_idx < len(examples):
                return examples[ex_idx]
        except ValueError:
            pass

        return None

    def browse_by_complexity(self) -> Optional[RequirementExample]:
        """
        Browse examples by complexity level

        Returns:
            Selected example or None
        """
        if self.use_rich:
            self.console.print("\n[bold]Complexity Levels:[/bold]")

            table = Table(show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Complexity", style="green")
            table.add_column("Examples", justify="right")
            table.add_column("Description")

            complexities = [
                (Complexity.SIMPLE, "Quick projects, learning, prototypes"),
                (Complexity.MODERATE, "Production apps with moderate features"),
                (Complexity.COMPLEX, "Enterprise systems, critical applications"),
            ]

            for i, (complexity, desc) in enumerate(complexities, 1):
                examples = get_examples_by_complexity(complexity)
                table.add_row(
                    str(i), complexity.value.title(), str(len(examples)), desc
                )

            self.console.print(table)
        else:
            logger.info("\nComplexity Levels:")
            logger.info("-" * 70)
            logger.info("1. Simple - Quick projects, learning, prototypes")
            logger.info("2. Moderate - Production apps with moderate features")
            logger.info("3. Complex - Enterprise systems, critical applications")
            logger.info("-" * 70)
        choice = input("\nSelect complexity (number) or press Enter to skip: ").strip()

        if not choice:
            return None

        complexity_map = {
            "1": Complexity.SIMPLE,
            "2": Complexity.MODERATE,
            "3": Complexity.COMPLEX,
        }

        if choice in complexity_map:
            selected_complexity = complexity_map[choice]
            return self._show_complexity_examples(selected_complexity)

        return None

    def _show_complexity_examples(
        self, complexity: Complexity
    ) -> Optional[RequirementExample]:
        """Show examples for a specific complexity level"""
        examples = get_examples_by_complexity(complexity)

        if not examples:
            logger.info(f"No examples found for {complexity.value}")
            return None

        if self.use_rich:
            self.console.print(f"\n[bold]{complexity.value.title()} Examples:[/bold]\n")

            table = Table(show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Title", style="green")
            table.add_column("Domain", style="yellow")

            for i, ex in enumerate(examples, 1):
                table.add_row(
                    str(i), ex.title, ex.domain.value.replace("_", " ").title()
                )

            self.console.print(table)
        else:
            logger.info(f"\n{complexity.value.title()} Examples:")
            logger.info("-" * 70)
            for i, ex in enumerate(examples, 1):
                logger.info(f"{i}. {ex.title} ({ex.domain.value})")
            logger.info("-" * 70)
        choice = input(
            "\nSelect example (number) to view details or press Enter to skip: "
        ).strip()

        if not choice:
            return None

        try:
            ex_idx = int(choice) - 1
            if 0 <= ex_idx < len(examples):
                return examples[ex_idx]
        except ValueError:
            pass

        return None

    def search_by_keyword(
        self, keyword: Optional[str] = None
    ) -> Optional[RequirementExample]:
        """
        Search examples by keyword

        Args:
            keyword: Search keyword (if None, will prompt user)

        Returns:
            Selected example or None
        """
        if keyword is None:
            keyword = input("\nEnter search keyword: ").strip()

        if not keyword:
            return None

        results = search_examples(keyword)

        if not results:
            logger.info(f"No examples found for '{keyword}'")
            return None

        if self.use_rich:
            self.console.print(
                f"\n[bold]Search results for '{keyword}':[/bold] ({len(results)} found)\n"
            )

            table = Table(show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Title", style="green")
            table.add_column("Domain", style="yellow")
            table.add_column("Complexity")

            for i, ex in enumerate(results, 1):
                table.add_row(
                    str(i),
                    ex.title,
                    ex.domain.value.replace("_", " ").title(),
                    ex.complexity.value,
                )

            self.console.print(table)
        else:
            logger.info(f"\nSearch results for '{keyword}': ({len(results)} found)")
            logger.info("-" * 70)
            for i, ex in enumerate(results, 1):
                logger.info(f"{i}. {ex.title} [{ex.domain.value}] ({ex.complexity.value})")
            logger.info("-" * 70)
        choice = input(
            "\nSelect example (number) to view details or press Enter to skip: "
        ).strip()

        if not choice:
            return None

        try:
            ex_idx = int(choice) - 1
            if 0 <= ex_idx < len(results):
                return results[ex_idx]
        except ValueError:
            pass

        return None

    def show_example(self, example: RequirementExample):
        """Display a detailed example"""
        if self.use_rich:
            # Title panel
            title_panel = Panel(
                f"[bold cyan]{example.title}[/bold cyan]\n\n"
                f"[yellow]Domain:[/yellow] {example.domain.value.replace('_', ' ').title()}\n"
                f"[yellow]Complexity:[/yellow] {example.complexity.value.title()}",
                border_style="cyan",
            )
            self.console.print("\n")
            self.console.print(title_panel)

            # Description
            self.console.print(f"\n[bold]Description:[/bold]\n{example.description}\n")

            # Requirement
            req_panel = Panel(
                example.requirement_text,
                title="Example Requirement",
                border_style="green",
            )
            self.console.print(req_panel)

            # Key Features
            self.console.print("\n[bold]Key Features:[/bold]")
            for feature in example.key_features:
                self.console.print(f"  • {feature}")

            # Tags
            self.console.print(f"\n[bold]Tags:[/bold] {', '.join(example.tags)}")

        else:
            logger.info("\n" + "=" * 70)
            logger.info(f"# {example.title}")
            logger.info("=" * 70)
            logger.info(f"Domain: {example.domain.value.replace('_', ' ').title()}")
            logger.info(f"Complexity: {example.complexity.value.title()}")
            logger.info("\nDescription:")
            logger.info(example.description)
            logger.info("\n" + "-" * 70)
            logger.info("Example Requirement:")
            logger.info("-" * 70)
            logger.info(example.requirement_text)
            logger.info("-" * 70)
            logger.info("\nKey Features:")
            for feature in example.key_features:
                logger.info(f"  - {feature}")
            logger.info(f"\nTags: {', '.join(example.tags)}")
            logger.info("=" * 70)
    def get_suggestions(
        self, user_input: str, limit: int = 3
    ) -> List[RequirementExample]:
        """
        Get example suggestions based on user input

        Args:
            user_input: User's partial requirement
            limit: Maximum number of suggestions

        Returns:
            List of suggested examples
        """
        suggestions = suggest_examples(user_input, limit=limit)

        if suggestions and self.use_rich:
            self.console.print("\n[bold cyan]💡 Suggested Examples:[/bold cyan]\n")

            for i, ex in enumerate(suggestions, 1):
                self.console.print(
                    f"[bold]{i}. {ex.title}[/bold] ({ex.complexity.value})"
                )
                self.console.print(f"   {ex.description[:100]}...")
                self.console.print()

        elif suggestions:
            logger.info("\n💡 Suggested Examples:")
            logger.info("-" * 70)
            for i, ex in enumerate(suggestions, 1):
                logger.info(f"{i}. {ex.title} ({ex.complexity.value})")
                logger.info(f"   {ex.description[:100]}...")
            logger.info("-" * 70)
        return suggestions

    def run_interactive_mode(self):
        """Run interactive guide in terminal"""
        self.show_welcome()

        while True:
            if self.use_rich:
                self.console.print("\n[bold]What would you like to do?[/bold]")
                self.console.print("1. Browse examples by domain")
                self.console.print("2. Browse examples by complexity")
                self.console.print("3. Search by keyword")
                self.console.print("4. View random example")
                self.console.print("5. Exit")
            else:
                logger.info("\nWhat would you like to do?")
                logger.info("1. Browse examples by domain")
                logger.info("2. Browse examples by complexity")
                logger.info("3. Search by keyword")
                logger.info("4. View random example")
                logger.info("5. Exit")
            choice = input("\nYour choice: ").strip()

            if choice == "1":
                example = self.browse_by_domain()
                if example:
                    self.show_example(example)

            elif choice == "2":
                example = self.browse_by_complexity()
                if example:
                    self.show_example(example)

            elif choice == "3":
                example = self.search_by_keyword()
                if example:
                    self.show_example(example)

            elif choice == "4":
                import random

                example = random.choice(REQUIREMENT_EXAMPLES)
                self.show_example(example)

            elif choice == "5" or choice.lower() == "exit":
                if self.use_rich:
                    self.console.print(
                        "\n[bold green]Thanks for using CAAS! 👋[/bold green]\n"
                    )
                else:
                    logger.info("\nThanks for using CAAS! 👋\n")
                break

            else:
                logger.info("Invalid choice. Please try again.")
def show_quick_suggestions(user_input: str):
    """
    Show quick suggestions based on user input (non-interactive)

    Args:
        user_input: User's partial requirement
    """
    guide = InteractiveGuide()
    guide.get_suggestions(user_input, limit=3)
