# -*- coding: utf-8 -*-
import datetime

from django.test import TestCase

from rest_framework import serializers, routers
from rest_framework import viewsets

from rest_framework_extensions.tests.models import Comment, CommentRating, User
from rest_framework_extensions import filters


class CommentRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentRating
        fields = (
            'id',
            'rating',
            'comment',
            'created',
            'is_moderated',
            'user'
        )


class CommentRatingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommentRatingSerializer
    queryset = CommentRating.objects.all()
    filters_dict = {
        'id': ['exact', 'lte'],
        'rating': ['in', 'range'],
        'created': ['year', 'month', 'day', 'range'],
        'is_moderated': ['exact'],
        'comment': filters.ALL,
        'user': filters.ALL_WITH_RELATIONS
    }
    filter_backends = (filters.DictFilterBackend,)


router = routers.DefaultRouter()
router.register(r'comment-ratings', CommentRatingViewSet, base_name='comment-rating')
urlpatterns = router.urls


class TestDictFilterBackendBase(TestCase):
    urls = 'rest_framework_extensions.tests.test_filters'

    def setUp(self):
        self.created = datetime.datetime(2012, 12, 1)
        self.user = User.objects.create(id=1, name='Gena')
        self.comment = Comment.objects.create(
            id=1,
            email='example@ya.ru',
            content='Hello world',
            created=self.created
        )
        self.comment_rating = CommentRating.objects.create(
            user=self.user,
            comment=self.comment,
            rating='1',
            created=self.created,
            is_moderated=True,
        )

    def filter_should_find(self, filter_args, msg=None):
        return self._filter_should_find(filter_args, is_should_find=True, msg=msg)

    def filter_should_not_find(self, filter_args, msg=None):
        return self._filter_should_find(filter_args, is_should_find=False, msg=msg)

    def _filter_should_find(self, filter_args, is_should_find, msg=None):
        self.assertEqual(self.is_found_by_filter(filter_args), is_should_find, msg=msg)

    def is_found_by_filter(self, filter_args):
        return bool(len(self.client.get('/comment-ratings/?' + filter_args).data))


class TestDictFilterBackend__WhiteListOfLookups(TestDictFilterBackendBase):
    def test__exact(self):
        self.filter_should_find('id=1')
        self.filter_should_not_find('id=2')

    def test__lte(self):
        self.filter_should_find('id__lte=10')
        self.filter_should_not_find('id__lte=0')

    def test_should_not_filter_by_not_listed__gte(self):
        self.filter_should_find('id__gte=10')
        self.filter_should_find('id__gte=0')


class TestDictFilterBackend__ArrayLookups(TestDictFilterBackendBase):
    def test__in(self):
        self.filter_should_find('rating__in=1,2')
        self.filter_should_find('rating__in=2,1')
        self.filter_should_find('rating__in=1')
        self.filter_should_not_find('rating__in=2,3')

    def test__range(self):
        self.filter_should_find('rating__range=0,100')
        self.filter_should_find('rating__in=1,100')
        self.filter_should_not_find('rating__in=2,100')


class TestDictFilterBackend__DateLookups(TestDictFilterBackendBase):
    def test__year(self):
        self.filter_should_find('created__year={0}'.format(self.comment_rating.created.year))
        self.filter_should_not_find('created__year={0}'.format(self.comment_rating.created.year + 1))

    def test__month(self):
        self.filter_should_find('created__month={0}'.format(self.comment_rating.created.month))

        month = self.comment_rating.created.month + 1
        if month > 12:
            month = 1
        self.filter_should_not_find('created__month={0}'.format(month))

    def test__day(self):
        self.filter_should_find('created__day={0}'.format(self.comment_rating.created.day))
        day = self.comment_rating.created.day - 1
        if day <= 0:
            day = 2
        self.filter_should_not_find('created__day={0}'.format(day))

    def test__range(self):
        two_days_after = self.comment_rating.created + datetime.timedelta(days=2)
        two_days_before = self.comment_rating.created - datetime.timedelta(days=2)
        five_days_before = self.comment_rating.created - datetime.timedelta(days=5)

        date_range = '{0},{1}'.format(self.comment_rating.created, two_days_after)
        self.filter_should_find('created__range={0}'.format(date_range))

        date_range = '{0},{1}'.format(two_days_before, five_days_before)
        self.filter_should_not_find('created__range={0}'.format(date_range))


class TestDictFilterBackend__Boolean(TestDictFilterBackendBase):
    def test_bool_in_text(self):
        true_list = [
            'true', 'True'
        ]
        false_list = [
            'false', 'False'
        ]

        for true_item in true_list:
            self.filter_should_find('is_moderated={0}'.format(true_item))
        for false_item in false_list:
            self.filter_should_not_find('is_moderated={0}'.format(false_item))

    def test_bool_none(self):
        none_list = [
            'nil', 'none', 'None'
        ]

        self.comment_rating.is_moderated = None
        self.comment_rating.save()

        for none_item in none_list:
            self.filter_should_find('is_moderated={0}'.format(none_item))

        self.comment_rating.is_moderated = True
        self.comment_rating.save()

        for none_item in none_list:
            self.filter_should_not_find('is_moderated={0}'.format(none_item))


class TestDictFilterBackend__All_Lookup(TestDictFilterBackendBase):
    def test_should_allow_filter_by_all_lookups(self):
        self.filter_should_find('comment__in=1')
        self.filter_should_not_find('comment__in=2,3')

    def test_should_not_allow_filter_by_related_objects(self):
        self.filter_should_find('comment__id=10000')


class TestDictFilterBackend__ALL_WITH_RELATIONS_Lookup(TestDictFilterBackendBase):
    def _test_should_allow_filter_by_all_lookups(self):
        self.filter_should_find('user__in=1')
        self.filter_should_not_find('user__in=2,3')

    def test_should_allow_filter_by_related_objects(self):
        self.filter_should_find('user__name=Gena')
        self.filter_should_find('user__name__startswith=Ge')
        self.filter_should_not_find('user__name=Vova')
        self.filter_should_not_find('user__name__startswith=Vo')


# test filter by field_name or source

# test with django-filter