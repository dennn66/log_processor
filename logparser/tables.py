import django_tables2 as tables
import django_tables2.utils as tu
from django_tables2.utils import A  # alias for Accessor

from django.utils.safestring import mark_safe
from .models import UserRequest
import itertools
counter = itertools.count()

class CheckBoxColumnWithValueInName(tables.CheckBoxColumn):
    def render(self, value, bound_column):  # pylint: disable=W0221
        default = {
            'type': 'checkbox',
            'name': bound_column.name + str(value),
            'value': value
        }
        general = self.attrs.get('input')
        specific = self.attrs.get('td__input')
        attrs = tu.AttributeDict(default, **(specific or general or {}))
        return mark_safe('<input %s/>' % attrs.as_html())

class UserRequestTable(tables.Table):
    #check_column = CheckBoxColumnWithValueInName(accessor='pk', orderable=False)
    edit = tables.LinkColumn('request_edit', text='Edit', args=[A('pk')], orderable=False, empty_values=())
    delete = tables.LinkColumn('request_delete', text='Delete', args=[A('pk')], orderable=False, empty_values=())
    test = tables.LinkColumn('test', text='Test', args=[A('pk')], orderable=False, empty_values=())
    # еще нужные поля

    class Meta:
        empty_text = u'Объекты, удовлетворяющие критериям поиска, не найдены...'
        model = UserRequest
        sequence = ('created', 	'city', 	'username', 	'from_date', 	'to_date', 	'parser', 	'author', 'filename') # тут столбцы, выводимые в таблицу
        #exclude = tuple( set(model._meta.get_fields()) - set(sequence))
        exclude = 'id'
        #order_by = ('-id',)
        # add class="paleblue" to <table> tag
        #attrs = {"class": "paleblue", "id": lambda: "table_%d" % next(counter)}