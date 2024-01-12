from collections.abc import Iterable
import functools
from itertools import chain

from django import forms
from django.utils.functional import cached_property
from django import VERSION as django_versio

from pumaska.piirto import Piirto


def yhdistetty_lomake(
  lomake: type,
  liitos: type = None,
  *,
  tunnus: str,
  liitos_kwargs: callable = None,
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

      # Käytetään A-lomakkeen vedostajaa oletuksena myös B-lomakkeella.
      # Huomaa:
      # - Django vaatii, että `renderer` periytyy lomakeluokan
      #   mahdollisesta `default_renderer`-luokasta;
      # - lomake ei ota (Django 4.2) vastaan parametriä `renderer`,
      #   tämä täytyy asettaa jälkeenpäin määreenä.
      if not 'renderer' in ajonaikainen_kwargs:
        class PiirtoB(Piirto, LomakeB=liitos): pass
        # Lomakesarja ei ota `renderer`-parametriä vastaan.
        # Asetetaan tämä alustuksen jälkeen määreenä.
        if issubclass(liitos, forms.BaseFormSet):
          asetettavat_maareet['renderer'] = PiirtoB(self)
        else:
          ajonaikainen_kwargs['renderer'] = PiirtoB(self)
        # if not 'renderer' in ajonaikainen_kwargs

      # Annetaan sisemmän lomakkeen alustuksessa oletuksena:
      # - data ja files, mikäli ulompi lomake on lähetetty,
      # - initial: `<tunnus>-`-alkuiset, epätyhjät avaimet ulomman
      #   lomakkeen initial-datassa
      # - prefix: `<ulompi prefix>-<tunnus>`
      # Huomaa, että `liitos_kwargs()` ja `ajonaikainen_kwargs` (tässä
      # järjestyksessä) ylikirjoittavat nämä oletusarvot.
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
        'prefix': f'{self.prefix}-{tunnus}' if self.prefix else tunnus,
        **(
          liitos_kwargs(self)
          if callable(liitos_kwargs)
          else liitos_kwargs if liitos_kwargs is not None
          else {}
        ),
        **ajonaikainen_kwargs,
      })

      # Asetetaan tarvittavat määreet (renderer).
      for avain, arvo in asetettavat_maareet.items():
        setattr(_liitos, avain, arvo)

      # Asetetaan viittaus ulommasta lomakkeesta sisempään.
      setattr(self, tunnus, _liitos)

      # Jos B-viittaus saa olla tyhjä:
      # - asetetaan kaikki B-lomakkeen kentät valinnaisiksi GET-pyynnöllä;
      # – huomaa, että tämä koskee myös mahdollisten sisäkkäisten
      #   lomakkeiden (C) kenttiä; ks. `__iter__`-toteutus alla;
      # - ohitetaan vimpainten `required`-määreen tulostus;
      # - huomaa, että tämä ei tee mitään sisemmälle lomakesarjalle.
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
      '''
      Iteroidaan lomakesarjaan liittyvät lomakkeet erikseen; lomake erikseen.
      '''
      _liitos = getattr(self, tunnus)
      return chain(
        super().__iter__(),
        chain.from_iterable(_liitos)
        if isinstance(_liitos, forms.BaseFormSet)
        else _liitos.__iter__(),
      )
      # def __iter__

    def __getitem__(self, item):
      '''
      Poimi liitoslomake(sarja), liitoslomakkeen kenttä tai (lomakesarjan
      tapauksessa) liitoslomakesarjan lomake tai tämän kenttä.
      '''
      if item == tunnus:
        return getattr(self, tunnus)
      elif item.startswith(f'{tunnus}-') \
      and (_liitos_kentta := item.partition(f'{tunnus}-')[2]):
        _liitos = getattr(self, tunnus)
        if isinstance(_liitos, forms.BaseFormSet):
          indeksi, _, item = _liitos_kentta.partition('-')
          _liitos_lomake = _liitos.__getitem__(int(indeksi))
          if item:
            return _liitos_lomake.__getitem__(item)
          else:
            return _liitos_lomake
        else:
          return _liitos.__getitem__(_liitos_kentta)
      else:
        return super().__getitem__(item)
      # def __getitem__

    @property
    def errors(self):
      '''
      Lisää liitoslomakkeen tai -sarjan mahdolliset virheet silloin, kun
      liitos on pakollinen tai sitä on muokattu.
      '''
      virheet = list(super().errors.items())
      if (_liitos := getattr(self, tunnus)).has_changed() \
      or pakollinen:
        if isinstance(_liitos, forms.BaseFormSet):
          for indeksi, lomake in enumerate(_liitos.forms):
            if lomake not in _liitos.deleted_forms:
              for avain, arvo in list(lomake.errors.items()):
                virheet.append([
                  '%s-%d-%s' % (tunnus, indeksi, avain), arvo
                ])
          if any(_liitos.non_form_errors()):
            virheet.append([
              # Lisää lomakeriippumattomat virheet hallintolomakkeen kohdalle.
              tunnus + '-TOTAL_FORMS',
              _liitos.non_form_errors()
            ])
        else:
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

    if django_versio < (5, ):
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
      muutokset = super().changed_data
      _liitos = getattr(self, tunnus)
      if isinstance(_liitos, forms.BaseFormSet):
        muutokset += [
          # Muodosta lomakekohtainen kentän etuliite poistamalla
          # liitetyn lomakkeen `prefixin` alusta
          # käsillä olevan (ylä-) lomakkeen oma `prefix` ja välimerkki -.
          f'{lomakekohtainen_tunnus}-{kentta}'
          for lomake, lomakekohtainen_tunnus in (
            (
              lomake,
              (
                lomake.prefix.replace(self.prefix + "-", "", 1)
              ) if self.prefix else lomake.prefix
            )
            for lomake in _liitos
          )
          for kentta in lomake.changed_data
        ]
      else:
        muutokset += [
          f'{tunnus}-{kentta}'
          for kentta in getattr(_liitos, 'changed_data', ())
        ]
      return muutokset
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
