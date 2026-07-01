from asyncio import run

from typer import Context, Option, Typer

from taskjournal.cli.context import get_debug, get_manager, get_today, parse_date
from taskjournal.config import MANAGER_NAME
from taskjournal.services.logger import console, logger

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
