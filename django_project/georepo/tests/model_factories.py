import factory
from datetime import datetime
from typing import Generic, TypeVar
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from georepo.models import (
    Dataset,
    GeographicalEntity,
    EntityType, Module, Language, EntityName,
    EntityId, DatasetView, DatasetViewResource, IdType,
    DatasetAdminLevelName, BoundaryType
)

T = TypeVar('T')


class BaseMetaFactory(Generic[T], factory.base.FactoryMetaClass):
    def __call__(cls, *args, **kwargs) -> T:
        return super().__call__(*args, **kwargs)


class BaseFactory(Generic[T], factory.django.DjangoModelFactory):
    @classmethod
    def create(cls, **kwargs) -> T:
        return super().create(**kwargs)


class UserF(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(
        lambda n: u'username %s' % n
    )


class GroupF(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(
        lambda n: u'group %s' % n
    )


class ModuleF(factory.django.DjangoModelFactory):
    class Meta:
        model = Module

    name = factory.Sequence(
        lambda n: u'module %s' % n
    )


class DatasetF(factory.django.DjangoModelFactory):
    class Meta:
        model = Dataset

    label = factory.Sequence(
        lambda n: u'dataset %s' % n
    )

    module = factory.SubFactory(ModuleF)

    created_by = factory.SubFactory(UserF)


class DatasetViewF(BaseFactory[DatasetView],
                   metaclass=BaseMetaFactory[DatasetView]):
    class Meta:
        model = DatasetView

    name = factory.Sequence(
        lambda n: u'view %s' % n
    )
    description = factory.Sequence(
        lambda n: u'description %s' % n
    )
    dataset = factory.SubFactory(DatasetF)

    created_by = factory.SubFactory(UserF)


class DatasetViewResourceF(
    BaseFactory[DatasetViewResource],
    metaclass=BaseMetaFactory[DatasetViewResource]
):
    class Meta:
        model = DatasetViewResource

    dataset_view = factory.SubFactory(DatasetViewF)


class EntityTypeF(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityType

    label = factory.Sequence(
        lambda n: u'entity type %s' % n
    )


class GeographicalEntityF(BaseFactory[GeographicalEntity],
                          metaclass=BaseMetaFactory[GeographicalEntity]):
    class Meta:
        model = GeographicalEntity

    dataset = factory.SubFactory(DatasetF)
    start_date = datetime.now()

    label = factory.Sequence(
        lambda n: u'entity %s' % n
    )

    type = factory.SubFactory(EntityTypeF)


class LanguageF(factory.django.DjangoModelFactory):
    class Meta:
        model = Language

    name = factory.Sequence(
        lambda n: u'lang %s' % n
    )

    code = factory.Sequence(
        lambda n: u'code %s' % n
    )


class EntityNameF(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityName

    language = factory.SubFactory(
        LanguageF
    )

    name = factory.Sequence(
        lambda n: u'entity name %s' % n
    )

    default = True

    geographical_entity = factory.SubFactory(
        GeographicalEntityF
    )

    label = factory.Sequence(
        lambda n: u'Name %s' % n
    )


class EntityIdF(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityId

    default = False

    geographical_entity = factory.SubFactory(
        GeographicalEntityF
    )


class IdTypeF(factory.django.DjangoModelFactory):
    class Meta:
        model = IdType

    name = factory.Sequence(
        lambda n: u'idtype%s' % n
    )


class DatasetAdminLevelNameF(factory.django.DjangoModelFactory):
    class Meta:
        model = DatasetAdminLevelName

    dataset = factory.SubFactory(DatasetF)
    level = factory.Sequence(
        lambda n: n
    )
    label = factory.LazyAttribute(lambda o: 'Level-%s' % o.level)


class BoundaryTypeF(factory.django.DjangoModelFactory):
    class Meta:
        model = BoundaryType

    dataset = factory.SubFactory(DatasetF)
    type = factory.SubFactory(EntityTypeF)
