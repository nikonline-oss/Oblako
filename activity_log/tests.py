"""Тесты журнала действий. Нужна настоящая MongoDB (docker compose поднимает её сам):
события пишутся в отдельную тестовую БД crm_test_activity, которая удаляется после тестов.
"""
import datetime
import unittest
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from pymongo.errors import PyMongoError

from employees.models import Employee
from products.models import Product
from units.models import Unit

from . import mongo

TEST_DB = 'crm_test_activity'


def mongo_available():
    if not settings.MONGO_URI:
        return False
    try:
        mongo._client(settings.MONGO_URI).admin.command('ping')
        return True
    except PyMongoError:
        return False


@unittest.skipUnless(mongo_available(), 'MongoDB недоступна (MONGO_URI)')
@override_settings(MONGO_DB=TEST_DB)
class ActivityLogTest(TestCase):
    def setUp(self):
        mongo.collection().delete_many({})

    @classmethod
    def tearDownClass(cls):
        mongo._client(settings.MONGO_URI).drop_database(TEST_DB)
        mongo._indexed_databases.discard(TEST_DB)
        super().tearDownClass()

    def events(self, **query):
        return list(mongo.collection().find(query).sort('timestamp', 1))

    def test_create_update_delete(self):
        unit = Unit.objects.create(name='кг')
        unit.name = 'килограмм'
        unit.save()
        unit.save()  # без изменений — в журнал не попадает
        unit_id = unit.pk
        unit.delete()

        create, update, delete = self.events(model='units.Unit', object_id=unit_id)
        self.assertEqual(create['action'], 'create')
        self.assertEqual(create['data'], {'name': 'кг'})
        self.assertEqual(create['model_verbose'], 'Единица измерения')
        self.assertEqual(update['action'], 'update')
        self.assertEqual(update['changes'], {'name': {'old': 'кг', 'new': 'килограмм'}})
        self.assertEqual(delete['action'], 'delete')
        self.assertEqual(delete['object_repr'], 'килограмм')

    def test_foreign_key_decimal_and_date_are_stored(self):
        unit = Unit.objects.create(name='шт')
        product = Product.objects.create(name='Болт', price=Decimal('12.50'), unit=unit)
        doc = self.events(model='products.Product', object_id=product.pk)[0]
        self.assertEqual(doc['data']['unit'], {'id': unit.pk, 'repr': 'шт'})
        self.assertEqual(doc['data']['price'], 12.5)

        employee = Employee.objects.create(
            last_name='Иванов', first_name='Иван', post='Слесарь', passport_series='1234',
            passport_number='567890', passport_issued_by='УФМС', passport_date_of_issue=datetime.date(2020, 5, 1))
        doc = self.events(model='employees.Employee', object_id=employee.pk)[0]
        self.assertEqual(doc['data']['passport_date_of_issue'], '2020-05-01')

    def test_request_user_and_ip_recorded(self):
        self.client.post(reverse('units:create'), {'name': 'литр'}, REMOTE_ADDR='10.1.2.3')
        doc = self.events(model='units.Unit')[0]
        self.assertEqual(doc['ip'], '10.1.2.3')
        self.assertIsNone(doc['user'])
        self.assertEqual(doc['path'], reverse('units:create'))

    def test_journal_page_filters_and_text_search(self):
        Unit.objects.create(name='метр')
        Unit.objects.create(name='тонна')
        Unit.objects.get(name='тонна').delete()

        response = self.client.get(reverse('activity_log:journal'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 3)

        response = self.client.get(reverse('activity_log:journal'), {'action': 'delete'})
        self.assertEqual([e['object_repr'] for e in response.context['events']], ['тонна'])

        # Полнотекстовый поиск с русской морфологией: «тонны» находит «тонна»
        response = self.client.get(reverse('activity_log:journal'), {'q': 'тонны'})
        self.assertEqual({e['object_repr'] for e in response.context['events']}, {'тонна'})

        response = self.client.get(reverse('activity_log:journal'), {'model': 'units.Unit', 'object_id': '999999'})
        self.assertEqual(response.context['total'], 0)

    def test_detail_page_shows_changes(self):
        unit = Unit.objects.create(name='м2')
        unit.name = 'м²'
        unit.save()
        doc = self.events(action='update')[0]
        response = self.client.get(reverse('activity_log:detail', args=[str(doc['_id'])]))
        self.assertContains(response, 'Что изменилось')
        self.assertContains(response, 'м²')
        self.assertEqual(self.client.get(reverse('activity_log:detail', args=['bad-id'])).status_code, 404)

    def test_stats_page_aggregations(self):
        Unit.objects.create(name='а')
        Unit.objects.create(name='б')
        Product.objects.create(name='Гайка', price=Decimal('1'), unit=Unit.objects.first())
        response = self.client.get(reverse('activity_log:stats'))
        self.assertEqual(response.status_code, 200)
        by_model = {row['key']: row['count'] for row in response.context['r']['by_model']}
        self.assertEqual(by_model, {'Единица измерения': 2, 'Товар': 1})
        self.assertEqual(response.context['coll_stats']['count'], 3)


SERIES_TEST_DB = 'crm_test_series'


@unittest.skipUnless(mongo_available(), 'MongoDB недоступна (MONGO_URI)')
@override_settings(MONGO_DB=TEST_DB, MONGO_SERIES_DB=SERIES_TEST_DB)
class SeriesCrudTest(TestCase):
    """CRUD над SeriesDB.series через веб-интерфейс CRM."""

    def setUp(self):
        from .series import series_collection
        self.coll = series_collection()
        self.coll.delete_many({})
        mongo.collection().delete_many({})

    @classmethod
    def tearDownClass(cls):
        client = mongo._client(settings.MONGO_URI)
        client.drop_database(SERIES_TEST_DB)
        client.drop_database(TEST_DB)
        mongo._indexed_databases.discard(TEST_DB)
        super().tearDownClass()

    def create(self, **data):
        form = {'name': 'Friends', 'year': '1994', 'genres': 'Комедия, ситком', 'seasons': '10',
                'rating': '8.9', 'description': '', 'extra': 'страна: США\nсерий: 236\nзавершён: да'}
        form.update(data)
        return self.client.post(reverse('activity_log:series_create'), form)

    def test_create_stores_flexible_document(self):
        response = self.create()
        self.assertRedirects(response, reverse('activity_log:series'))
        doc = self.coll.find_one({'name': 'Friends'})
        self.assertEqual(doc['year'], 1994)
        self.assertEqual(doc['genres'], ['комедия', 'ситком'])        # массив, в нижнем регистре
        self.assertEqual((doc['seasons'], doc['rating']), (10, 8.9))
        self.assertEqual((doc['страна'], doc['серий'], doc['завершён']), ('США', 236, True))
        self.assertNotIn('description', doc)                          # пустые поля не сохраняются
        event = mongo.collection().find_one({'model': 'SeriesDB.series', 'action': 'create'})
        self.assertEqual(event['object_repr'], 'Friends')

    def test_list_filters_search_and_sort(self):
        self.create()
        self.create(name='Suits', year='2011', genres='драма', extra='')
        self.create(name='House of Cards', year='2013', genres='драма, политика', extra='')
        url = reverse('activity_log:series')
        names = lambda r: [row['doc']['name'] for row in r.context['rows']]
        self.assertEqual(names(self.client.get(url)), ['Friends', 'House of Cards', 'Suits'])
        self.assertEqual(names(self.client.get(url, {'q': 'HOUSE'})), ['House of Cards'])
        self.assertEqual(names(self.client.get(url, {'genre': 'драма', 'sort': '-year'})), ['House of Cards', 'Suits'])
        self.assertEqual(names(self.client.get(url, {'year_from': '2000', 'year_to': '2012'})), ['Suits'])
        self.assertEqual(self.client.get(url).context['genres'], ['драма', 'комедия', 'политика', 'ситком'])

    def test_edit_sets_and_unsets_fields(self):
        self.create()
        doc_id = str(self.coll.find_one()['_id'])
        url = reverse('activity_log:series_edit', args=[doc_id])
        page = self.client.get(url)
        self.assertEqual(page.context['form'].initial['genres'], 'комедия, ситком')
        self.assertIn('страна: США', page.context['form'].initial['extra'])

        self.client.post(url, {'name': 'F.R.I.E.N.D.S', 'year': '1994', 'genres': 'комедия', 'seasons': '',
                               'rating': '9', 'description': 'Шестеро друзей', 'extra': 'страна: США'})
        doc = self.coll.find_one()
        self.assertEqual(doc['name'], 'F.R.I.E.N.D.S')
        self.assertEqual(doc['genres'], ['комедия'])
        self.assertNotIn('seasons', doc)                                # $unset
        self.assertNotIn('серий', doc)
        self.assertEqual(doc['description'], 'Шестеро друзей')
        event = mongo.collection().find_one({'action': 'update', 'model': 'SeriesDB.series'})
        self.assertEqual(event['changes']['name'], {'old': 'Friends', 'new': 'F.R.I.E.N.D.S'})
        self.assertEqual(event['changes']['seasons'], {'old': 10, 'new': None})

    def test_delete(self):
        self.create()
        doc_id = str(self.coll.find_one()['_id'])
        self.assertEqual(self.client.get(reverse('activity_log:series_delete', args=[doc_id])).status_code, 405)
        self.client.post(reverse('activity_log:series_delete', args=[doc_id]))
        self.assertEqual(self.coll.count_documents({}), 0)
        self.assertTrue(mongo.collection().find_one({'action': 'delete', 'object_repr': 'Friends'}))

    def test_validation(self):
        response = self.create(name='', year='1800', extra='без двоеточия')
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('name', errors)
        self.assertIn('year', errors)
        self.assertIn('extra', errors)
        self.assertEqual(self.coll.count_documents({}), 0)
        self.assertEqual(self.client.get(reverse('activity_log:series_edit', args=['nope'])).status_code, 404)


class ActivityLogDisabledTest(TestCase):
    @override_settings(MONGO_URI='')
    def test_crm_works_and_page_explains_when_mongo_not_configured(self):
        Unit.objects.create(name='без журнала')  # сохранение не падает
        response = self.client.get(reverse('activity_log:journal'))
        self.assertContains(response, 'MONGO_URI')

    @override_settings(MONGO_URI='mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=300', MONGO_DB='crm_unreachable')
    def test_crm_works_when_mongo_is_down(self):
        Unit.objects.create(name='mongo лежит')  # ошибка MongoDB только пишется в лог
        response = self.client.get(reverse('activity_log:journal'))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'недоступна', status_code=503)
