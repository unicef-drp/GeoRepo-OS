from django.apps import AppConfig


def create_clear_dashboard_session_periodic_task():
    from importlib import import_module
    from django.core.exceptions import ValidationError

    try:
        IntervalSchedule = (
            import_module('django_celery_beat.models').IntervalSchedule
        )

        PeriodicTask = (
            import_module('django_celery_beat.models').PeriodicTask
        )
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=7,
            period=IntervalSchedule.DAYS
        )

        sched_storage_checker, _ = IntervalSchedule.objects.get_or_create(
            every=15,
            period=IntervalSchedule.MINUTES
        )

        sched_log_cleaner, _ = IntervalSchedule.objects.get_or_create(
            every=14,
            period=IntervalSchedule.DAYS
        )
    except Exception as e:
        print(e)
        return

    try:
        PeriodicTask.objects.update_or_create(
            task='clear_dashboard_dataset_session',
            defaults={
                'name': 'Clear dashboard dataset session',
                'interval': schedule
            }
        )
        PeriodicTask.objects.update_or_create(
            task='trigger_storage_checker_api',
            defaults={
                'name': 'Check storage django container',
                'interval': sched_storage_checker
            }
        )
        PeriodicTask.objects.update_or_create(
            task='clean_old_storage_log',
            defaults={
                'name': 'Clean storage log',
                'interval': sched_log_cleaner
            }
        )
    except ValidationError as e:
        print(e)


class DashboardConfig(AppConfig):
    name = 'dashboard'

    def ready(self):
        # Create a task to clear dashboard session browse dataset
        create_clear_dashboard_session_periodic_task()
