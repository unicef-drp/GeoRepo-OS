import factory

from dashboard.models import (
    LayerFile,
    LayerUploadSession,
    EntityUploadStatus,
    LayerConfig,
    Notification,
    EntitiesUserConfig,
    EntityUploadChildLv1
)
from dashboard.models.boundary_comparison import BoundaryComparison
from georepo.tests.model_factories import UserF, DatasetF, GeographicalEntityF


class LayerUploadSessionF(factory.django.DjangoModelFactory):
    class Meta:
        model = LayerUploadSession

    dataset = factory.SubFactory(DatasetF)
    uploader = factory.SubFactory(UserF)
    tolerance = 1e-8
    overlaps_threshold = 0.01
    gaps_threshold = 0.01


class LayerFileF(factory.django.DjangoModelFactory):
    class Meta:
        model = LayerFile

    meta_id = factory.Sequence(
        lambda n: u'meta_id_%s' % n
    )

    layer_file = factory.django.FileField(filename='admin.geojson')

    name = factory.Sequence(
        lambda n: u'name %s' % n
    )

    level = factory.Sequence(
        lambda n: u'level %s' % n
    )

    entity_type = factory.Sequence(
        lambda n: u'entity type %s' % n
    )

    layer_upload_session = factory.SubFactory(
        LayerUploadSessionF
    )

    uploader = factory.SubFactory(UserF)


class EntityUploadF(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityUploadStatus

    upload_session = factory.SubFactory(
        LayerUploadSessionF
    )
    original_geographical_entity = factory.SubFactory(
        GeographicalEntityF
    )
    status = 'Started'


class LayerConfigF(factory.django.DjangoModelFactory):
    class Meta:
        model = LayerConfig

    dataset = factory.SubFactory(
        DatasetF
    )

    created_by = factory.SubFactory(UserF)


class BoundaryComparisonF(factory.django.DjangoModelFactory):
    class Meta:
        model = BoundaryComparison

    main_boundary = factory.SubFactory(
        GeographicalEntityF
    )


class NotificationF(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserF)


class EntitiesUserConfigF(factory.django.DjangoModelFactory):
    class Meta:
        model = EntitiesUserConfig

    dataset = factory.SubFactory(
        DatasetF
    )

    user = factory.SubFactory(UserF)


class EntityUploadChildLv1F(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityUploadChildLv1

    entity_upload = factory.SubFactory(EntityUploadF)
