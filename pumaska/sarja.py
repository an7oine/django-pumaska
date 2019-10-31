# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

from django.db import transaction
from django.db.models import ProtectedError
from django import forms
from django.template import loader
from django.utils.translation import ugettext_lazy as _


def lisaa_lomakesarja(
  LomakeA, LomakeB, *,
  avain_a=None,
  avain_b=None,
  tunnus=None,
  epasuora=False,
  **kwargs
):
  '''
  Yhdistää ModelForm-luokan ja toisesta ModelForm-luokasta
  muodostetun InlineFormSet-luokan silloin,
  kun B-luokasta on suora (ForeignKey) tai epäsuora (GenericForeignKey)
  viittaus A-luokkaan
  Args:
    LomakeA, LomakeB: mallikohtaiset lomakeluokat
    tunnus: yksikäsitteinen tunnus lomakesarjalle (oletus 'lomakesarja')
    *args, **kwargs: lisäparametrit ``inlineformset_factory``-funktiolle
  '''
  # Pakotetaan ylimääräisten lomakkeiden määräksi nolla.
  kwargs['extra'] = 0

  if epasuora:
    from django.contrib.contenttypes.forms import generic_inlineformset_factory
    lomakesarja = generic_inlineformset_factory(
      LomakeB.Meta.model,
      form=LomakeB,
      **kwargs
    )
  else:
    lomakesarja = forms.models.inlineformset_factory(
      LomakeA.Meta.model,
      LomakeB.Meta.model,
      form=LomakeB,
      **kwargs
    )

  # Käytetään tyhjän lomakkeen oletusarvoina
  # `initial`-datan ensimmäistä alkiota.
  class lomakesarja(lomakesarja):
    # pylint: disable=function-redefined
    def get_form_kwargs(self, index):
      if index is None and self.initial_extra:
        return {
          **super().get_form_kwargs(index), 'initial': self.initial_extra[0]
        }
      else:
        return super().get_form_kwargs(index)
      # def get_form_kwargs
    # class lomakesarja

  # Lisää tarvittaessa oletusarvot HTML-piirtoa varten.
  if not hasattr(lomakesarja, 'label'):
    lomakesarja.label = (
      LomakeB.Meta.model._meta.verbose_name_plural
    ).capitalize()
  if not hasattr(lomakesarja, 'palikka'):
    lomakesarja.palikka = 'pumaska/lomakesarja_lomakekenttana.html'
  if not hasattr(lomakesarja, 'riviluokka'):
    lomakesarja.riviluokka = 'clearfix'
  if not hasattr(lomakesarja, 'lisaa_painike'):
    lomakesarja.lisaa_painike = _('Lisää %(malli)s') % {
      'malli': LomakeB.Meta.model._meta.verbose_name
    }
  if not hasattr(lomakesarja, 'poista_painike'):
    lomakesarja.poista_painike = _('Poista %(malli)s') % {
      'malli': LomakeB.Meta.model._meta.verbose_name
    }

  tunnus = tunnus or avain_a or (
    LomakeB.Meta.model._meta.get_field(avain_b).remote_field.name
  )

  class YhdistettyLomake(LomakeA):
    class Meta(LomakeA.Meta):
      pass

    def __init__(self, *args, prefix=None, **kwargs):
      lomakesarja_kwargs = kwargs.pop(f'{tunnus}_kwargs', {})
      super().__init__(*args, prefix=prefix, **kwargs)
      initial = {
        avain.replace(tunnus + '-', '', 1): arvo
        for avain, arvo in self.initial.items()
        if avain.startswith(tunnus + '-') and avain != tunnus + '-'
      }
      setattr(self, tunnus, lomakesarja(
        data=kwargs.get('data'),
        files=kwargs.get('files'),
        instance=self.instance,
        initial=[initial] if initial else [],
        prefix=prefix + '-' + tunnus if prefix else tunnus,
        **lomakesarja_kwargs,
      ))
      # def __init__

    def _html_output(self, *args, **kwargs):
      # pylint: disable=protected-access
      return super()._html_output(*args, **kwargs) \
      + loader.get_template('pumaska/lomakesarja.html').render({
        'tunnus': tunnus,
        'lomakesarja': getattr(self, tunnus),
      })
      # def _html_output

    def has_changed(self):
      return super().has_changed() \
      or getattr(self, tunnus).has_changed()
      # def has_changed

    def is_valid(self):
      return super().is_valid() \
      and getattr(self, tunnus).is_valid()
      # def is_valid

    @property
    def errors(self):
      virheet = list(super().errors.items())
      lomakesarja = getattr(self, tunnus)
      for indeksi, lomake in enumerate(lomakesarja.forms):
        if lomake not in lomakesarja.deleted_forms:
          for avain, arvo in list(lomake.errors.items()):
            virheet.append([
              '%s-%d-%s' % (lomakesarja.prefix, indeksi, avain), arvo
            ])
      if any(lomakesarja.non_form_errors()):
        virheet.append([
          # Lisää lomakeriippumattomat virheet hallintolomakkeen kohdalle.
          lomakesarja.prefix + '-TOTAL_FORMS',
          lomakesarja.non_form_errors()
        ])
      return forms.utils.ErrorDict(virheet)
      # def errors

    @transaction.atomic
    def save(self, commit=True):
      '''
      Tallennetaan atomaarisena tietokantaoperaationa.
      '''
      return super().save(commit=commit)
      # def save

    def _save_m2m(self):
      '''
      Tallennetaan M2M-kohteet `super`-toteutuksen mukaisesti.
      Tämän jälkeen tallennetaan lomakesarja.
      '''
      super()._save_m2m()
      lomakesarja = getattr(self, tunnus)
      lomakesarja.instance = self.instance
      try:
        with transaction.atomic():
          lomakesarja.save(commit=True)
      except ProtectedError as exc:
        virheteksti = _(
          'Rivin poisto epäonnistui:'
          ' suojattuja, riippuvia %(malli)s-kohteita.'
        ) % {'malli': exc.protected_objects.model._meta.verbose_name}
        # pylint: disable=protected-access
        lomakesarja._non_form_errors.append(forms.ValidationError(
          virheteksti, code='protect'
        ))
        raise forms.ValidationError(exc)
      # def _save_m2m

    # class YhdistettyLomake

  return YhdistettyLomake
  # def lisaa_lomakesarja