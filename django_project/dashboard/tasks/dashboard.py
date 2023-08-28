from celery import shared_task
import logging


logger = logging.getLogger(__name__)


@shared_task(name="clear_dashboard_dataset_session")
def clear_dashboard_dataset_session():
    from datetime import datetime, timedelta
    from django.db import connection
    # clear entities user config session that is older than 7 days
    # exclude last config for each user+dataset
    sql = (
        'DELETE FROM dashboard_entitiesuserconfig '
        'WHERE id NOT IN('
        '    select max(de.id) '
        '    from dashboard_entitiesuserconfig de '
        '    group by de.user_id, de.dataset_id '
        '    ) AND '
        'updated_at < %s'
    )
    datetime_filter = datetime.now() - timedelta(days=7)
    with connection.cursor() as cursor:
        cursor.execute(sql, [datetime_filter])
