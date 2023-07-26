from rest_framework import serializers
from georepo.models import (
    DatasetTilingConfig, AdminLevelTilingConfig,
    DatasetViewTilingConfig, ViewAdminLevelTilingConfig
)


class AdminLevelTilingConfigSerializer(serializers.ModelSerializer):

    def validate_level(self, value):
        if value < 0:
            raise serializers.ValidationError(
                f'Invalid admin level {value}'
            )
        # this validation is run twice
        if 'admin_levels' in self.context:
            zoom_level = self.context['zoom_level']
            if value in self.context['admin_levels']:
                raise serializers.ValidationError(
                    f'Duplicate admin level {value} '
                    f'at zoom level {zoom_level}'
                )
        return value

    def validate_simplify_tolerance(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError(
                'Tolerance must be between 0-1'
            )
        return value

    def save(self, tiling_config):
        level = self.validated_data['level']
        simplify_tolerance = self.validated_data['simplify_tolerance']
        # always create new obj
        obj = AdminLevelTilingConfig.objects.create(
            dataset_tiling_config=tiling_config,
            level=level,
            simplify_tolerance=simplify_tolerance
        )
        return obj

    class Meta:
        model = AdminLevelTilingConfig
        fields = [
            'level',
            'simplify_tolerance'
        ]


class TilingConfigSerializer(serializers.ModelSerializer):
    admin_level_tiling_configs = AdminLevelTilingConfigSerializer(
        source='adminleveltilingconfig_set',
        many=True
    )

    def validate_zoom_level(self, value):
        if value < 0 or value > 8:
            raise serializers.ValidationError(
                'Zoom level must be between 0-8'
            )
        if value in self.context['zoom_levels']:
            raise serializers.ValidationError(
                f'Duplicate zoom level {value}'
            )
        return value

    def validate_admin_level_tiling_configs(self, value):
        validated = []
        admin_levels = []
        for data in value:
            serializer = AdminLevelTilingConfigSerializer(
                data=data,
                many=False,
                context={
                    'admin_levels': admin_levels,
                    'zoom_level': self.context['current_zoom']
                }
            )
            serializer.is_valid(raise_exception=True)
            validated.append(serializer)
            admin_levels.append(serializer.validated_data['level'])
        return validated

    def save(self, dataset):
        zoom_level = self.validated_data['zoom_level']
        admin_level_tiling_configs = self.validated_data[
            'adminleveltilingconfig_set']
        config, _ = DatasetTilingConfig.objects.get_or_create(
            dataset=dataset,
            zoom_level=zoom_level
        )
        AdminLevelTilingConfig.objects.filter(
            dataset_tiling_config=config.id
        ).delete()
        for admin_level in admin_level_tiling_configs:
            admin_level.save(tiling_config=config)


    class Meta:
        model = DatasetTilingConfig
        fields = [
            'zoom_level',
            'admin_level_tiling_configs'
        ]


class ViewAdminLevelTilingConfigSerializer(serializers.ModelSerializer):

    def validate_level(self, value):
        if value < 0:
            raise serializers.ValidationError(
                f'Invalid admin level {value}'
            )
        # this validation is run twice
        if 'admin_levels' in self.context:
            zoom_level = self.context['zoom_level']
            if value in self.context['admin_levels']:
                raise serializers.ValidationError(
                    f'Duplicate admin level {value} '
                    f'at zoom level {zoom_level}'
                )
        return value

    def validate_simplify_tolerance(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError(
                'Tolerance must be between 0-1'
            )
        return value

    def save(self, tiling_config):
        level = self.validated_data['level']
        simplify_tolerance = self.validated_data['simplify_tolerance']
        # always create new obj
        obj = ViewAdminLevelTilingConfig.objects.create(
            view_tiling_config=tiling_config,
            level=level,
            simplify_tolerance=simplify_tolerance
        )
        return obj

    class Meta:
        model = ViewAdminLevelTilingConfig
        fields = [
            'level',
            'simplify_tolerance'
        ]


class ViewTilingConfigSerializer(serializers.ModelSerializer):
    admin_level_tiling_configs = ViewAdminLevelTilingConfigSerializer(
        source='viewadminleveltilingconfig_set',
        many=True
    )

    def validate_zoom_level(self, value):
        if value < 0 or value > 8:
            raise serializers.ValidationError(
                'Zoom level must be between 0-8'
            )
        if value in self.context['zoom_levels']:
            raise serializers.ValidationError(
                f'Duplicate zoom level {value}'
            )
        return value

    def validate_admin_level_tiling_configs(self, value):
        validated = []
        admin_levels = []
        for data in value:
            serializer = ViewAdminLevelTilingConfigSerializer(
                data=data,
                many=False,
                context={
                    'admin_levels': admin_levels,
                    'zoom_level': self.context['current_zoom']
                }
            )
            serializer.is_valid(raise_exception=True)
            validated.append(serializer)
            admin_levels.append(serializer.validated_data['level'])
        return validated

    def save(self, dataset_view):
        zoom_level = self.validated_data['zoom_level']
        admin_level_tiling_configs = self.validated_data[
            'viewadminleveltilingconfig_set']
        config, _ = DatasetViewTilingConfig.objects.get_or_create(
            dataset_view=dataset_view,
            zoom_level=zoom_level
        )
        ViewAdminLevelTilingConfig.objects.filter(
            view_tiling_config=config.id
        ).delete()
        for admin_level in admin_level_tiling_configs:
            admin_level.save(tiling_config=config)


    class Meta:
        model = DatasetViewTilingConfig
        fields = [
            'zoom_level',
            'admin_level_tiling_configs'
        ]
