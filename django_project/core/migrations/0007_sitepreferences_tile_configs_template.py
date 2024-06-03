# Generated by Django 4.0.7 on 2023-01-26 03:24

from django.db import migrations, models


def init_default_template(apps, schema_editor):
    SitePreferences = apps.get_model('core', 'SitePreferences')
    preferences, _ = SitePreferences.objects.get_or_create(pk=1)
    preferences.tile_configs_template = [
        {
            "zoom_level": 0,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 1,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.005
                },
                {
                    "level": "1",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 2,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.003
                },
                {
                    "level": "1",
                    "tolerance": 0.005
                }
            ]
        },
        {
            "zoom_level": 3,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.001
                },
                {
                    "level": "1",
                    "tolerance": 0.003
                },
                {
                    "level": "2",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 4,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0.001
                },
                {
                    "level": "2",
                    "tolerance": 0.009
                },
                {
                    "level": "3",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 5,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.005
                },
                {
                    "level": "3",
                    "tolerance": 0.009
                },
                {
                    "level": "4",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 6,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.003
                },
                {
                    "level": "3",
                    "tolerance": 0.006
                },
                {
                    "level": "4",
                    "tolerance": 0.009
                },
                {
                    "level": "5",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 7,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.001
                },
                {
                    "level": "3",
                    "tolerance": 0.005
                },
                {
                    "level": "4",
                    "tolerance": 0.009
                },
                {
                    "level": "5",
                    "tolerance": 0.009
                },
                {
                    "level": "6",
                    "tolerance": 0.009
                }
            ]
        },
        {
            "zoom_level": 8,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0
                },
                {
                    "level": "3",
                    "tolerance": 0.001
                },
                {
                    "level": "4",
                    "tolerance": 0.009
                },
                {
                    "level": "5",
                    "tolerance": 0.009
                },
                {
                    "level": "6",
                    "tolerance": 0.009
                }
            ]
        }
    ]
    preferences.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_remove_sitepreferences_geometry_similarity_threshold_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitepreferences',
            name='tile_configs_template',
            field=models.JSONField(blank=True, default=[]),
        ),
        migrations.RunPython(init_default_template),
    ]