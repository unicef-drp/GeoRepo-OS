from rest_framework import serializers

from docs.models.block import Block, BlockChild
from docs.models.page import Page


class BlockSerializer(serializers.ModelSerializer):
    """Block serializer."""

    blocks = serializers.SerializerMethodField()

    def get_blocks(self, obj: Block):
        """Return blocks."""
        blocks = []
        for block_child in BlockChild.objects.filter(
                parent=obj).order_by('order'):
            blocks.append(block_child.child)
        return BlockSerializer(blocks, many=True).data

    class Meta:  # noqa: D106
        model = Block
        fields = (
            'title', 'description', 'thumbnail', 'anchor', 'link', 'blocks'
        )


class PageSerializer(serializers.ModelSerializer):
    """Page serializer."""

    blocks = serializers.SerializerMethodField()

    def get_blocks(self, obj: Page):
        """Return blocks."""
        blocks = []
        for page_block in obj.pageblock_set.all().order_by('order'):
            blocks.append(page_block.block)
        return BlockSerializer(blocks, many=True).data

    class Meta:  # noqa: D106
        model = Page
        fields = ('title', 'intro', 'link', 'blocks')
