from django.apps import AppConfig


def create_store_api_logs_periodic_task():
    from importlib import import_module
    from django.core.exceptions import ValidationError

    try:
        IntervalSchedule = (
            import_module('django_celery_beat.models').IntervalSchedule
        )

        PeriodicTask = (
            import_module('django_celery_beat.models').PeriodicTask
        )
        # Run every 15 minutes
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=15,
            period=IntervalSchedule.MINUTES
        )
    except Exception as e:
        print(e)
        return

    try:
        PeriodicTask.objects.update_or_create(
            task='store_api_logs',
            defaults={
                'name': 'store_api_logs',
                'interval': schedule
            }
        )
    except ValidationError as e:
        print(e)


class CoreAppConfig(AppConfig):
    name = 'core'

    def ready(self):
        create_store_api_logs_periodic_task()
