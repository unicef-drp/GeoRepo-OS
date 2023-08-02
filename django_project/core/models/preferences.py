"""Model for Website Preferences."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.singleton import SingletonModel


def default_api_config():
    """
    Default value for Preference's api_config.
    """
    return {'default_page_size': 50, 'max_page_size': 50}


def default_metadata_xml_config():
    """
    Default value for Preference's metadata_xml_config.
    """
    return {
        'ContactName': 'GeoRepo',
        'ContactOrg': 'Unicef',
        'ContactPosition': 'Administrator',
        'License': (
            'Not Specified: The original author '
            'did not specify a license.'
        )
    }


def default_public_groups():
    """
    Default value for Preference's public_group.
    """
    return ['UNICEF']


def default_geometry_checker_params():
    """
    Default value for Preference's geometry_checker_params.
    """
    return {
        'tolerance': 1e-4,
        'overlaps_threshold': 0.01,
        'gaps_threshold': 0.01,
    }


class SitePreferences(SingletonModel):
    """Preference settings specifically for website.

    Preference contains
    - site_title
    - primary_color
    - secondary_color
    - icon
    - favicon
    - search_similarity
    """

    site_title = models.CharField(
        max_length=512,
        default=''
    )

    # -----------------------------------------------
    # THEME
    # -----------------------------------------------
    primary_color = models.CharField(
        max_length=16,
        default='#1CABE2',
        help_text=_(
            'Main color for the website. '
            'Put the hex color with # (e.g. #ffffff) '
            'or put the text of color. (e.g. blue)'
        )
    )
    anti_primary_color = models.CharField(
        max_length=16,
        default='#FFFFFF',
        help_text=_(
            'Anti of primary color that used for text in primary color.'
        )
    )
    secondary_color = models.CharField(
        max_length=16,
        default='#374EA2',
        help_text=_(
            'Secondary color that used for example for button. '
        )
    )
    anti_secondary_color = models.CharField(
        max_length=16,
        default='#FFFFFF',
        help_text=_(
            'Anti of secondary color that used for text in primary color.'
        )
    )
    tertiary_color = models.CharField(
        max_length=16,
        default='#297CC2',
        help_text=_(
            'Tertiary color that used for example for some special place. '
        )
    )
    anti_tertiary_color = models.CharField(
        max_length=16,
        default='#FFFFFF',
        help_text=_(
            'Anti of tertiary color that used for text in primary color.'
        )
    )
    icon = models.FileField(
        upload_to='settings/icons',
        null=True,
        blank=True
    )
    favicon = models.FileField(
        upload_to='settings/icons',
        null=True,
        blank=True
    )
    # -----------------------------------------------
    # Search Similarity Threshold for fuzzy search
    # -----------------------------------------------
    search_similarity = models.FloatField(
        null=True,
        blank=True,
        default=0.3
    )
    # -----------------------------------------------
    # Simplify tolerance for geometry fuzzy search
    # -----------------------------------------------
    search_simplify_tolerance = models.FloatField(
        null=True,
        blank=True,
        default=0.5
    )
    # -----------------------------------------------
    # Threshold for geometry similarity in boundary matching
    # -----------------------------------------------
    geometry_similarity_threshold_new = models.FloatField(
        null=True,
        blank=True,
        default=0.9,
        help_text=(
            'Default threshold of percentage of the new boundary area '
            'covered by the old matching boundary (% new). '
            'Value from 0-1'
        )
    )

    geometry_similarity_threshold_old = models.FloatField(
        null=True,
        blank=True,
        default=0.9,
        help_text=(
            'Default threshold of percentage of the old boundary area '
            'covered by the new matching boundary (% old). '
            'Value from 0-1'
        )
    )
    # -----------------------------------------------
    # JSON template for vector tiling config
    # -----------------------------------------------
    tile_configs_template = models.JSONField(
        default=list,
        blank=True
    )
    # -----------------------------------------------
    # Dataset short code to be excluded from UCode generation
    # -----------------------------------------------
    short_code_exclusion = models.CharField(
        max_length=256,
        default='OAB',
        help_text=_(
            'Dataset short code to be excluded from UCode generation. '
            'Comma separated'
        )
    )
    # -----------------------------------------------
    # JSON template for admin level names
    # -----------------------------------------------
    level_names_template = models.JSONField(
        default=list,
        blank=True
    )
    # -----------------------------------------------
    # API pagination setting
    # -----------------------------------------------
    api_config = models.JSONField(
        default=default_api_config,
        blank=True
    )
    # -----------------------------------------------
    # API current latest version - Usage in background task that generates URL
    # -----------------------------------------------
    api_latest_version = models.CharField(
        max_length=20,
        default='v1',
        help_text=_(
            'API current latest version - '
            'Usage in background task that generates URL'
        )
    )
    # -----------------------------------------------
    # METADATA XML Config
    # -----------------------------------------------
    metadata_xml_config = models.JSONField(
        default=default_metadata_xml_config,
        blank=True
    )
    # -----------------------------------------------
    # Default Group Name (Public)
    # new user will be added to this groups
    # -----------------------------------------------
    default_public_groups = models.JSONField(
        default=default_public_groups,
        blank=True
    )
    # -----------------------------------------------
    # Map Tiler API Keys for browse dataset in FrontEnd
    # -----------------------------------------------
    maptiler_api_key = models.CharField(
        max_length=256,
        default='',
        help_text=_(
            'Used in FrontEnd UI to preview maps'
        )
    )
    # -----------------------------------------------
    # Default Geometry Checker Parameters
    # -----------------------------------------------
    default_geometry_checker_params = models.JSONField(
        default=default_geometry_checker_params,
        blank=True
    )
    # -----------------------------------------------
    # Default Admin Email Addresses
    # send email notification from SignUp and Access Request
    # -----------------------------------------------
    default_admin_emails = models.JSONField(
        default=list,
        blank=True
    )
    # -----------------------------------------------
    # Base URL Help Page in FrontEnd
    # -----------------------------------------------
    base_url_help_page = models.CharField(
        max_length=256,
        default='',
        help_text=_(
            'Used in FrontEnd UI to scraping help text'
        )
    )

    class Meta:  # noqa: D106
        verbose_name_plural = "site preferences"

    @staticmethod
    def preferences() -> "SitePreferences":
        """Load Site Preference."""
        return SitePreferences.load()

    def __str__(self):
        return 'Site Preference'


class SitePreferencesImage(models.Model):
    """Preference images settings specifically for website."""

    preference = models.ForeignKey(
        SitePreferences,
        on_delete=models.CASCADE
    )
    image = models.FileField(
        upload_to='settings/images'
    )
    title = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_('Title of image.')
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text=_('Description of image.')
    )
