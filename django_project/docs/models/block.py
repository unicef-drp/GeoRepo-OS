from django.db import models


class Block(models.Model):
    """Block of an page of documentation."""

    url = models.CharField(
        verbose_name='Relative Documentation Url',
        max_length=128,
        help_text=(
            'Relative url of documentation base url that will be used to '
            'autofetch the content and also will be used as '
            '"Visit our documentation" button.'
        )
    )

    anchor = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text=(
            'Anchor of block on the page on the documentation. '
            'This will be used as a start or the content.'
            'If the anchor is not provided, it will use whole content.'
        )
    )

    thumbnail = models.ImageField(
        upload_to='docs/icons',
        null=True,
        blank=True,
        help_text=(
            'If no thumbnail is provided, it will use the first image '
            'in the help page under '
            'the anchor specified above will be used. '
            'We recommend to normally leave this blank'
        )
    )

    title = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text=(
            'If no title is provided, it will use the title of the anchor '
            'on documentation page.'
        )
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text=(
            'If no description is provided, '
            'it will use the first paragraph from the help center under '
            'the anchor specified above will be used. '
            'We recommend to normally leave this blank'
        )
    )

    class Meta:  # noqa: D106
        ordering = ('anchor',)

    def __str__(self):
        """String of object."""
        return f'{self.title} - {self.url}{self.anchor}'

    @property
    def link(self):
        """String of object."""
        from docs.models.preferences import Preferences
        return Preferences.preferences().documentation_base_url + self.url


class BlockChild(models.Model):
    """Block children"""

    parent = models.ForeignKey(
        Block,
        on_delete=models.CASCADE
    )
    child = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name='block_children'
    )
    order = models.IntegerField(default=0)
