"""Check supervisor status and restart individual celery workers."""

import subprocess

from django.core.management.base import BaseCommand, CommandError

# Program names defined in deployment/docker/supervisord.conf
WORKER_CHOICES = [
    "celery-worker",
    "celery-tile",
    "celery-exporter",
    "celery-validator",
    "all",
]

DEFAULT_SUPERVISOR_CONFIG = "/supervisord.conf"


class Command(BaseCommand):
    """Django management command wrapping supervisorctl.

    Lets an operator check the status of the celery workers managed by
    supervisord, or restart a single worker program without having to
    restart the whole worker container.
    """

    help = (
        "Get supervisor status or restart a celery worker managed by "
        "supervisord. Usage: "
        "`python manage.py supervisor status` or "
        "`python manage.py supervisor restart <worker>`."
    )

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "action",
            choices=["status", "restart"],
            help="Action to perform: status or restart."
        )
        parser.add_argument(
            "worker",
            nargs="?",
            default=None,
            help=(
                "Worker program name to restart. Required for `restart`. "
                f"Choices: {', '.join(WORKER_CHOICES)}."
            )
        )
        parser.add_argument(
            "--config",
            default=DEFAULT_SUPERVISOR_CONFIG,
            help=(
                "Path to the supervisord config file "
                f"(default: {DEFAULT_SUPERVISOR_CONFIG})."
            )
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        action = options["action"]
        worker = options["worker"]
        config = options["config"]

        if action == "restart":
            if not worker:
                raise CommandError(
                    "Missing worker name. Usage: "
                    "python manage.py supervisor restart <worker>. "
                    f"Choices: {', '.join(WORKER_CHOICES)}."
                )
            if worker not in WORKER_CHOICES:
                raise CommandError(
                    f"Unknown worker '{worker}'. "
                    f"Choices: {', '.join(WORKER_CHOICES)}."
                )

        command = ["supervisorctl", "-c", config, action]
        if worker:
            command.append(worker)

        result = self.run_supervisorctl(command)

        if result.stdout:
            self.stdout.write(result.stdout.strip())
        if result.stderr:
            self.stderr.write(result.stderr.strip())

        if result.returncode != 0:
            raise CommandError(
                f"supervisorctl exited with code {result.returncode}."
            )

    def run_supervisorctl(self, command):
        """Run a supervisorctl command.

        :param command: Full command list to execute.
        :type command: list
        :return: Completed process with captured output.
        :rtype: subprocess.CompletedProcess
        """
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True
            )
        except FileNotFoundError as e:
            raise CommandError(
                f"supervisorctl not found: {e}"
            )
