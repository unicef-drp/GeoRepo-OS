from django.apps import AppConfig


def create_celery_sync_periodic_task():
    from importlib import import_module
    from django.core.exceptions import ValidationError

    try:
        IntervalSchedule = (
            import_module('django_celery_beat.models').IntervalSchedule
        )

        PeriodicTask = (
            import_module('django_celery_beat.models').PeriodicTask
        )
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES
        )
    except Exception as e:
        print(e)
        return

    try:
        PeriodicTask.objects.update_or_create(
            task='check_celery_background_tasks',
            defaults={
                'name': 'check_celery_background_tasks',
                'interval': schedule
            }
        )
    except ValidationError as e:
        print(e)


def create_clear_task_request_periodic_task():
    from importlib import import_module
    from django.core.exceptions import ValidationError

    try:
        IntervalSchedule = (
            import_module('django_celery_beat.models').IntervalSchedule
        )

        PeriodicTask = (
            import_module('django_celery_beat.models').PeriodicTask
        )
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS
        )
    except Exception as e:
        print(e)
        return

    try:
        PeriodicTask.objects.update_or_create(
            task='remove_old_task_requests',
            defaults={
                'name': 'remove_old_task_requests',
                'interval': schedule
            }
        )
    except ValidationError as e:
        print(e)


class GeorepoConfig(AppConfig):
    name = 'georepo'

    def ready(self):
        create_celery_sync_periodic_task()
        create_clear_task_request_periodic_task()
