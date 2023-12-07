from collections.abc import Iterable
import functools
from itertools import chain

from django import forms
from django.utils.functional import cached_property

from pumaska.piirto import Piirto


def yhdistetty_lomake(
  lomake: type,
  liitos: type = None,
  *,
  tunnus: str,
  liitos_kwargs: callable,
  pakollinen: bool = False,
  valita_parametrit: Iterable = (),
):
  assert valita_parametrit is not None
  if liitos is None:
    return functools.partial(
      yhdistetty_lomake,
      liitos=lomake,
      tunnus=tunnus,
      liitos_kwargs=liitos_kwargs,
      pakollinen=pakollinen,
      valita_parametrit=valita_parametrit
    )
    # if liitos is None

  class YhdistettyLomake(lomake):

    def __init__(self, *args, prefix=None, **kwargs):
      ajonaikainen_kwargs = kwargs.pop(f'{tunnus}_kwargs', {})
      asetettavat_maareet = {}
      for param in valita_parametrit:
        try:
          ajonaikainen_kwargs[param] = kwargs[param]
        except KeyError:
          pass

      super().__init__(*args, prefix=prefix, **kwargs)

      # Käytetään A-lomakkeen vedostajaa oletuksena
      # myös B-lomakkeella.
      # Huomaa, että Django vaatii, että `renderer` periytyy
      # lomakeluokan mahdollisesta `default_renderer`-luokasta.
      if not 'renderer' in ajonaikainen_kwargs:
        class PiirtoB(Piirto, LomakeB=liitos): pass
        # Lomakesarja ei ota `renderer`-parametriä vastaan.
        # Asetetaan tämä alustuksen jälkeen määreenä.
        if issubclass(liitos, forms.BaseFormSet):
          asetettavat_maareet['renderer'] = PiirtoB(self)
        else:
          ajonaikainen_kwargs['renderer'] = PiirtoB(self)
        # if not 'renderer' in ajonaikainen_kwargs

      # Asetetaan liitoksen oletus-`prefix`.
      ajonaikainen_kwargs.setdefault(
        'prefix', f'{self.prefix}-{tunnus}' if self.prefix else tunnus
      )

      _liitos = liitos(**{
        **({
          'data': self.data,
          'files': self.files,
        } if self.is_bound else {}),
        'initial': {
          avain.replace(tunnus + '-', '', 1): arvo
          for avain, arvo in self.initial.items()
          if avain.startswith(tunnus + '-') and avain != tunnus + '-'
        },
        **liitos_kwargs(self),
        **ajonaikainen_kwargs,
      })
      for avain, arvo in asetettavat_maareet.items():
        setattr(_liitos, avain, arvo)
      setattr(self, tunnus, _liitos)
      # Jos B-viittaus saa olla tyhjä, asetetaan kaikki B-lomakkeen
      # kentät valinnaisiksi GET-pyynnöllä.
      # – Huomaa, että tämä koskee myös mahdollisten sisäkkäisten
      # lomakkeiden (C) kenttiä.
      # Lisäksi ohitetaan vimpainten `required`-määreen tulostus.
      if not pakollinen:
        for kentta in _liitos:
          if hasattr(kentta, 'field'):
            if not self.data:
              kentta.field.required = False
            kentta.field.widget.use_required_attribute = lambda initial: False
      # def __init__

    # def order_fields(self, field_order)
    # def __str__(self)
    # def __repr__(self)

    def __iter__(self):
      return chain(
        super().__iter__(),
        getattr(self, tunnus).__iter__(),
      )
      # def __iter__

    def __getitem__(self, item):
      if item == tunnus:
        return getattr(self, tunnus)
      elif item.startswith(f'{tunnus}-'):
        return getattr(self, tunnus).__getitem__(
          item.partition(f'{tunnus}-')[2]
        )
      else:
        return super().__getitem__(item)
      # def __getitem__

    @property
    def errors(self):
      '''
      Lisää B-lomakkeen mahdolliset virheet silloin, kun
      B-viittaus ei saa olla tyhjä, tai B-lomaketta on muokattu.
      '''
      virheet = list(super().errors.items())
      if (_liitos := getattr(self, tunnus)).has_changed() \
      or pakollinen:
        for avain, arvo in list(_liitos.errors.items()):
          virheet.append([
            '%s-%s' % (tunnus, avain), arvo
          ])
      return forms.utils.ErrorDict(virheet)
      # def errors

    def is_valid(self):
      '''
      Jos B-viittaus saa olla tyhjä eikä sitä ole muokattu,
      ei välitetä B-lomakkeen mahdollisesta epäkelpoisuudesta.
      '''
      return super().is_valid() and (
        (_liitos := getattr(self, tunnus)).is_valid()
        or (not pakollinen and not _liitos.has_changed())
      )
      # def is_valid

    # def add_prefix(self, field_name)
    # def add_initial_prefix(self, field_name)

    def _html_output(self, *args, **kwargs):
      # pylint: disable=protected-access
      return super()._html_output(*args, **kwargs) \
      + getattr(self, tunnus)._html_output(*args, **kwargs)
      # def _html_output

    # def as_table(self)
    # def as_ul(self)
    # def as_p(self)
    # def non_field_errors(self)
    # def add_error(self, field, error)
    # def has_error(self, field, code=None)
    # def full_clean(self)
    # def _clean_fields(self)
    # def _clean_form(self)
    # def _post_clean(self)
    # def clean(self)

    def has_changed(self):
      return super().has_changed() \
      or getattr(self, tunnus).has_changed()
      # def has_changed

    @cached_property
    def changed_data(self):
      '''
      Palauta ylälomakkeen omien muutosten lisäksi
      liitoslomakkeen mahdolliset muutokset
      `tunnus`-etuliitteellä varustettuina.
      '''
      lomake = getattr(self, tunnus)
      return super().changed_data + [
        f'{tunnus}-{kentta}'
        for kentta in getattr(lomake, 'changed_data', ())
      ]
      # def changed_data

    @property
    def media(self):
      return super().media + getattr(self, tunnus).media

    #def is_multipart(self)

    def hidden_fields(self):
      return [
        f for f in super().hidden_fields()
        if f.form is self
      ]
      # def hidden_fields

    #def visible_fields(self)
    #def get_initial_for_field(self, field, field_name)

    # `in`

    def __contains__(self, key):
      if key == tunnus:
        return True
      elif key.startswith(f'{tunnus}-'):
        key = key.partition(f'{tunnus}-')[2]
        if hasattr(getattr(self, tunnus), '__contains__') \
        and getattr(self, tunnus).__contains__(key):
          return True
        return key in getattr(self, tunnus).fields
        # if key.startswith
      elif hasattr(super(), '__contains__') \
      and super().__contains__(key):
        return True
      else:
        return key in self.fields
      # def __contains__

    # class YhdistettyLomake

  YhdistettyLomake.__name__ += f'_{tunnus}'
  YhdistettyLomake.__qualname__ += f'_{tunnus}'
  return YhdistettyLomake
  # def yhdista_lomakkeet
