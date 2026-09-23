from pathlib import Path
from zipfile import BadZipFile

from typer import Typer, Context, Option, Argument, Exit, confirm

from taskjournal.cli.context import get_manager, get_debug
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Backup commands.",
        no_args_is_help=True,
    )

    @app.command(
        "run",
        help="Create a backup all files Examples:\n wk backup run\n",
    )
    def backup_run(ctx: Context) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).create_backup()

    @app.command("verify", help="Check the integrity and safety of a backup ZIP.")
    def backup_verify(
        ctx: Context, archive: Path = Argument(..., help="Backup ZIP to inspect.")
    ) -> None:
        try:
            entries = get_manager(ctx).inspect_backup(archive)
        except (OSError, BadZipFile, ValueError) as exc:
            console.print(f"[red]Backup verification failed:[/red] {exc}")
            raise Exit(code=1) from exc
        console.print(f"[green]✓[/green] Backup verified: {len(entries)} files")

    @app.command("restore", help="Preview and restore missing files from a backup ZIP.")
    def backup_restore(
        ctx: Context,
        archive: Path = Argument(..., help="Backup ZIP to restore."),
        yes: bool = Option(False, "--yes", help="Confirm restore without prompting."),
    ) -> None:
        manager = get_manager(ctx)
        try:
            entries = manager.inspect_backup(archive)
            for path, exists in entries:
                console.print(f"{'Skip (exists)' if exists else 'Restore'}: {path}")
            pending = sum(not exists for _, exists in entries)
            console.print(
                f"{pending} files to restore; {len(entries) - pending} existing files will be kept."
            )
            if not pending:
                return
            if not yes and not confirm("Restore missing files?", default=False):
                console.print("Restore cancelled.")
                return
            restored = manager.restore_backup(archive)
        except (OSError, BadZipFile, ValueError) as exc:
            console.print(f"[red]Backup restore failed:[/red] {exc}")
            raise Exit(code=1) from exc
        console.print(
            f"[green]✓[/green] Restored {len(restored)} files; existing files were not overwritten."
        )

    @app.command(
        "schedule",
        help=(
            "Schedule automatic daily backups.\n\n"
            "Examples:\n"
            " wk backup schedule --time 18:00\n"
            " wk backup schedule --disable\n"
        ),
    )
    def backup_schedule(
        ctx: Context,
        time: str | None = Option(
            None, "--time", help="Time in HH:MM format (e.g. 18:00)."
        ),
        disable: bool = Option(False, "--disable", help="Remove the backup schedule."),
    ) -> None:
        manager = get_manager(ctx)
        if disable:
            try:
                manager.disable_backup_schedule()
            except RuntimeError as e:
                logger.error(str(e))
            return
        if not time:
            console.print(
                "[red]Error:[/red] --time is required. Example: wk backup schedule --time 18:00"
            )
            return
        try:
            parts = time.split(":")
            if len(parts) != 2:
                raise ValueError
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            logger.error(f"Invalid time format: {time!r}. Use HH:MM (e.g. 18:00).")
            return
        try:
            manager.schedule_backup(hour=hour, minute=minute)
        except RuntimeError as e:
            logger.error(str(e))

    return app
