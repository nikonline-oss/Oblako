import re

from django import forms

from .series import BASE_FIELDS, extra_fields

EXTRA_KEY = re.compile(r'^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_ ]{0,49}$')


def _parse_value(text):
    """«12» → 12, «8.5» → 8.5, «да/нет» → True/False, иначе строка."""
    low = text.lower()
    if low in ('да', 'true'):
        return True
    if low in ('нет', 'false'):
        return False
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def _show_value(value):
    if isinstance(value, bool):
        return 'да' if value else 'нет'
    return value


class SeriesForm(forms.Form):
    name = forms.CharField(label='Название', max_length=200)
    year = forms.IntegerField(label='Год выхода', min_value=1900, max_value=2100)
    genres = forms.CharField(label='Жанры (через запятую)', required=False, max_length=300,
                             help_text='Сохраняются массивом: ["драма", "комедия"]')
    seasons = forms.IntegerField(label='Сезонов', required=False, min_value=1, max_value=100)
    rating = forms.FloatField(label='Рейтинг (0–10)', required=False, min_value=0, max_value=10)
    description = forms.CharField(label='Описание', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    extra = forms.CharField(
        label='Дополнительные поля', required=False, widget=forms.Textarea(attrs={'rows': 4}),
        help_text='По одному на строку, «поле: значение» — например «страна: США» или «серий: 236». '
                  'У каждого документа свой набор полей — схема MongoDB это позволяет.')

    @classmethod
    def from_document(cls, doc):
        initial = {k: doc.get(k) for k in BASE_FIELDS}
        initial['genres'] = ', '.join(doc.get('genres') or [])
        initial['extra'] = '\n'.join(f'{k}: {_show_value(v)}' for k, v in extra_fields(doc).items())
        return cls(initial=initial)

    def clean_extra(self):
        result = {}
        for number, line in enumerate(self.cleaned_data['extra'].splitlines(), 1):
            if not line.strip():
                continue
            if ':' not in line:
                raise forms.ValidationError(f'Строка {number}: нужен формат «поле: значение»')
            key, value = (part.strip() for part in line.split(':', 1))
            if not EXTRA_KEY.match(key):
                raise forms.ValidationError(f'Строка {number}: имя поля — буквы, цифры, пробел, «_», до 50 символов')
            if key in BASE_FIELDS:
                raise forms.ValidationError(f'Строка {number}: «{key}» уже есть в форме')
            result[key] = _parse_value(value)
        return result

    def to_document(self):
        """Документ MongoDB: пустые необязательные поля просто не сохраняются."""
        data = self.cleaned_data
        doc = {'name': data['name'].strip(), 'year': data['year']}
        genres = [g.strip().lower() for g in data['genres'].split(',') if g.strip()]
        if genres:
            doc['genres'] = list(dict.fromkeys(genres))
        for key in ('seasons', 'rating'):
            if data[key] is not None:
                doc[key] = data[key]
        if data['description'].strip():
            doc['description'] = data['description'].strip()
        doc.update(data['extra'])
        return doc
