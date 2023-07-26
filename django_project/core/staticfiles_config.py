from django.contrib.staticfiles.apps import StaticFilesConfig


class MyStaticFilesConfig(StaticFilesConfig):
    # note: the pattern should match to static directory
    # not root directory like /home/web/media <-- won't work
    ignore_patterns = [
        "CVS",
        ".*",
        "*~",
        "media/",
        "export_data/",
        "error_reports/",
        "layer_files/"
    ]
