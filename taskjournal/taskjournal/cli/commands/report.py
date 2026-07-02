from asyncio import run

from rich.table import Table
from typer import Context, Option, Typer

from taskjournal.cli.context import get_debug, get_manager, get_today, parse_date
from taskjournal.config import MANAGER_NAME
from taskjournal.services.logger import console, logger
from taskjournal.services.time import TimeService

_DATETIME_FMT = "%Y-%m-%d %H:%M"


def build_app() -> Typer:
    app = Typer(
        help="Generate period reports (month, half-year, retro, 1on1).",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command(
        "month",
        help=(
            "Create a monthly report for the month containing the given date.\n\n"
            "Examples:\n"
            "  wk report month\n"
            "  wk report month --date 2025-08-31\n"
        ),
    )
    def report_month(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target month: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date)

        run(m.create_month_review(custom_date))

    @app.command(
        "half-year",
        help=(
            "Create a half-year report.\n\n"
            "Examples:\n"
            "  wk report half-year\n"
        ),
    )
    def report_half_year(
        ctx: Context,
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        run(get_manager(ctx).create_half_year_review(get_today(ctx)))

    @app.command(
        "retro",
        help=(
            "Create or open a retrospective file for the current sprint.\n\n"
            "Examples:\n"
            "  wk report retro\n"
            "  wk report retro --date 2025-09-02\n"
        ),
    )
    def report_retro(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target week: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date, _DATETIME_FMT)

        m.create_retro(custom_date)

    @app.command(
        "quarter",
        help=(
            "Create a quarterly report for the quarter containing the given date.\n\n"
            "Examples:\n"
            "  wk report quarter\n"
            "  wk report quarter --date 2025-08-31\n"
        ),
    )
    def report_quarter(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target quarter: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")
        if date:
            custom_date = parse_date(date)
        run(m.create_quarter_review(custom_date))

    @app.command(
        "year",
        help=(
            "Create a yearly report for the given year.\n\n"
            "Examples:\n"
            "  wk report year\n"
            "  wk report year --date 2025-06-01\n"
        ),
    )
    def report_year(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target year: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")
        if date:
            custom_date = parse_date(date)
        run(m.create_year_review(custom_date))

    # compare sub-group
    compare_app = Typer(
        help="Compare stats across months or quarters.",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )
    app.add_typer(compare_app, name="compare")

    @compare_app.command(
        "months",
        help=(
            "Compare monthly stats across a full year.\n\n"
            "Examples:\n"
            "  wk report compare months\n"
            "  wk report compare months --year 2025\n"
        ),
    )
    def compare_months(
        ctx: Context,
        year: int = Option(0, "--year", help="Year to compare (default: current year)."),
    ) -> None:
        today = get_today(ctx)
        target_year = year if year else today.year
        results = get_manager(ctx).compare_periods("month", target_year)

        table = Table(title=f"Monthly comparison — {target_year}", show_header=True, header_style="bold")
        table.add_column("Month", width=10)
        table.add_column("Worked", justify="right", width=8)
        table.add_column("Vacation", justify="right", width=9)
        table.add_column("Office", justify="right", width=7)
        table.add_column("Home", justify="right", width=6)
        table.add_column("Total time", justify="right", width=11)

        ts = TimeService()
        for row in results:
            h, m = ts.seconds_to_hours_minutes(int(row["total_time_seconds"]))
            table.add_row(
                str(row["label"]),
                str(row["total_worked_days"]),
                str(row["vacation_days"]),
                str(row["days_at_office"]),
                str(row["days_at_home"]),
                f"{h}h {m}m",
            )
        console.print(table)

    @compare_app.command(
        "quarters",
        help=(
            "Compare quarterly stats across a full year.\n\n"
            "Examples:\n"
            "  wk report compare quarters\n"
            "  wk report compare quarters --year 2025\n"
        ),
    )
    def compare_quarters(
        ctx: Context,
        year: int = Option(0, "--year", help="Year to compare (default: current year)."),
    ) -> None:
        today = get_today(ctx)
        target_year = year if year else today.year
        results = get_manager(ctx).compare_periods("quarter", target_year)

        table = Table(title=f"Quarterly comparison — {target_year}", show_header=True, header_style="bold")
        table.add_column("Quarter", width=10)
        table.add_column("Worked", justify="right", width=8)
        table.add_column("Vacation", justify="right", width=9)
        table.add_column("Office", justify="right", width=7)
        table.add_column("Home", justify="right", width=6)
        table.add_column("Total time", justify="right", width=11)

        ts = TimeService()
        for row in results:
            h, m = ts.seconds_to_hours_minutes(int(row["total_time_seconds"]))
            table.add_row(
                str(row["label"]),
                str(row["total_worked_days"]),
                str(row["vacation_days"]),
                str(row["days_at_office"]),
                str(row["days_at_home"]),
                f"{h}h {m}m",
            )
        console.print(table)

    # 1on1 is a sub-group: wk report 1on1 create / add-topic
    one_on_one_app = Typer(
        help="1on1 meeting notes (create note, add agenda topics).",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )
    app.add_typer(one_on_one_app, name="1on1")

    @one_on_one_app.command(
        "create",
        help="Create a 1on1 note.\n\nExamples:\n  wk report 1on1 create\n  wk report 1on1 create --person 'Alice'\n",
    )
    def report_one_on_one(
        ctx: Context,
        person: str = Option(MANAGER_NAME, "--person", "-p", help="Name of the person you are meeting with."),
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).create_one_on_one(get_today(ctx), person_name=person)

    @one_on_one_app.command(
        "add-topic",
        help=(
            "Add a topic to the next 1on1 session without opening the file.\n\n"
            "Examples:\n"
            "  wk report 1on1 add-topic -t 'Discuss Q3 career plan'\n"
        ),
    )
    def report_add_topic(
        ctx: Context,
        topic: str = Option(..., "--topic", "-t", help="Topic to add."),
    ) -> None:
        today = get_today(ctx)
        try:
            get_manager(ctx).add_topic_to_one_on_one(today, topic)
            console.print(f"[green]✓[/green] Added topic: {topic}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))

    return app
