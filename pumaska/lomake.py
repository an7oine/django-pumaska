# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

from collections.abc import Iterable
import functools
from itertools import chain
import types

from django.db import DatabaseError, transaction
from django import forms
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .nidottu import yhdistetty_lomake
from .piirto import Piirto


@functools.wraps(yhdistetty_lomake)
def yhdista_lomakkeet(
  LomakeA: type,
  LomakeB: type,
  *,
  avain_a: str = None,
  avain_b: str = None,
  tunnus: str = None,
  pakollinen_b: bool = None,
  valita_parametrit: Iterable = (),
):
  '''
  Yhdistää kaksi ModelForm-luokkaa silloin,
  kun A-luokasta on suora viittaus B-luokkaan

  Joko `avain_a` tai `avain_b` on pakollinen.

  Args:
    LomakeA, LomakeB: mallikohtaiset lomakeluokat
    avain_a: viittausavain LomakeA.Meta.model-luokan kohteelta
      LomakeB.Meta.model-luokan kohteelle
    avain_b: viittausavain LomakeB.Meta.model-luokan kohteelta
      LomakeA.Meta.model-luokan kohteelle
      (oletuksena haetaan viittauksen vastaluokan tiedoista)
    tunnus: yksikäsitteinen tunnus LomakeB-lomakkeelle
      (oletuksena ``avain_a`` tai ``avain_b``:n vastaviittaus)
    pakollinen_b: onko lomake B pakollinen, tarkistettava tieto?
      (oletuksena sama kuin A--B-viittauksen pakollisuus, jos annettu)
  '''

  if isinstance(LomakeA, str):
    LomakeA = import_string(LomakeA)
  if isinstance(LomakeB, str):
    LomakeB = import_string(LomakeB)

  # Muodosta avain_a, avain_b, kentta_a ja kentta_b.
  assert avain_a or avain_b
  kentta_a = LomakeA.Meta.model._meta.get_field(avain_a) if avain_a else None

  avain_b = avain_b or kentta_a.remote_field.name
  kentta_b = LomakeB.Meta.model._meta.get_field(avain_b)
  tunnus = tunnus or avain_a or kentta_b.remote_field.name

  if tunnus in LomakeA.base_fields:
    raise RuntimeError(
      f'Sisempää lomaketta ei voida nitoa samalla nimellä'
      f' kuin olemassaoleva lomakekenttä: {tunnus}'
    )

  # Mikäli A-avainta ei ole annettu,
  # B-lomake on oletuksena valinnainen.
  # Muutoin haetaan oletus vastaavan kentän tiedoista.
  if pakollinen_b is None:
    pakollinen_b = avain_a and (
      not LomakeA.Meta.model._meta.get_field(avain_a).null
    )

  def liitos_kwargs(self: LomakeA):
    kohde_b = self.initial.get(tunnus, None)
    if isinstance(kohde_b, LomakeB.Meta.model):
      pass
    elif kohde_b is not None:
      kohde_b = LomakeB.Meta.model.objects.get(pk=kohde_b)
    elif self.instance and avain_a:
      kohde_b = getattr(self.instance, avain_a, None)

    # Mikäli olemassaolevaa B-kohdetta ei löytynyt, luodaan uusi.
    if kohde_b is None:
      kohde_b = LomakeB.Meta.model()
      # Asetetaan linkki B-->A, jos mahdollista
      try:
        setattr(kohde_b, avain_b, self.instance)
      except (AttributeError, TypeError):
        pass
    assert isinstance(kohde_b, LomakeB.Meta.model), (
      f'Kohde B ei voi olla tyyppiä {type(kohde_b)} != {LomakeB.Meta.model}!'
    )
    return {
      **({
        'data': self.data,
        'files': self.files,
      } if self.is_bound else {}),
      'initial': {
        avain.replace(tunnus + '-', '', 1): arvo
        for avain, arvo in self.initial.items()
        if avain.startswith(tunnus + '-') and avain != tunnus + '-'
      },
      'instance': kohde_b,
    }
    # def liitos_kwargs

  YhdistettyLomake = yhdista_lomakkeet.__wrapped__(
    LomakeA, LomakeB,
    tunnus=tunnus,
    liitos_kwargs=liitos_kwargs,
    pakollinen=pakollinen_b,
    valita_parametrit=valita_parametrit,
  )

  @functools.wraps(YhdistettyLomake, updated=())
  class YhdistettyLomake(YhdistettyLomake):
    # pylint: disable=function-redefined

    def __init__(self, *args, **kwargs):
      ''' Piilota ja estä mahdollinen paluuvierasavain B --> A. '''
      super().__init__(*args, **kwargs)
      lomake_b = getattr(self, tunnus)
      if avain_b in lomake_b.fields:
        lomake_b.fields[avain_b].disabled = True
        lomake_b.fields[avain_b].required = False
        lomake_b.fields[avain_b].widget = forms.HiddenInput()
      # def __init__

    # ModelForm:

    @transaction.atomic
    def _save_m2m(self):
      super()._save_m2m()
      # Jos viittaus A-->B voi olla tyhjä, tallennetaan B (vasta) nyt
      if not avain_a or self.Meta.model._meta.get_field(avain_a).null:

        # Haetaan A-kohde ja B-lomake
        kohde_a = self.instance
        lomake_b = getattr(self, tunnus)

        # Otetaan vanha B-kohde talteen
        vanha_kohde_b = getattr(kohde_a, avain_a) \
        if avain_a and hasattr(kohde_a, avain_a) else None

        if vanha_kohde_b == lomake_b.instance and vanha_kohde_b.pk:
          # Päivitetään olemassaoleva B
          try:
            lomake_b.save(commit=True)
          except (ValueError, DatabaseError):
            if pakollinen_b:
              raise
            # Säilytetään olemassaoleva tietue.
            vanha_kohde_b.refresh_from_db()
          # if vanha_kohde_b == lomake_b.instance and vanha_kohde_b.pk
        else:
          # Asetetaan linkki B-->A
          setattr(lomake_b.instance, avain_b, kohde_a)

          # Yritetään tallentaa B ja otetaan virhe kiinni
          try:
            kohde_b = lomake_b.save(commit=True)
          except (ValueError, DatabaseError):
            if pakollinen_b:
              raise
            kohde_b = vanha_kohde_b

          # Asetetaan tarvittaessa linkki A-->B ja tallennetaan A (uudelleen).
          if avain_a:
            setattr(kohde_a, avain_a, kohde_b)
            kohde_a.save()

          # Poistetaan vanha kohde, jos viittaus katkesi
          if vanha_kohde_b and vanha_kohde_b.pk and vanha_kohde_b != kohde_b:
            vanha_kohde_b.delete()
          # if vanha_kohde_b != lomake_b.instance:
        # if ...null

      # def _save_m2m

    @transaction.atomic
    def save(self, commit=True):
      # pylint: disable=access-member-before-definition
      # pylint: disable=attribute-defined-outside-init

      # Jos viittaus A-->B ei voi olla tyhjä, tallennetaan B ensin
      # (muussa tapauksessa B tallennetaan lopuksi `_save_m2m`-metodissa)
      if avain_a and not self.Meta.model._meta.get_field(avain_a).null:
        lomake_b = getattr(self, tunnus)
        kohde_b = lomake_b.save(commit=commit)
        setattr(self.instance, avain_a, kohde_b)

        # Kun `commit=False`, ja B on uusi, tallentamaton tietokantarivi:
        if not commit and kohde_b and not kohde_b.pk:
          # Vaihdetaan A:n tallennusmetodi kertaluontoisesti.
          vanha_save = self.instance.save
          def save(instance):
            # Hae tämänhetkinen B, tallenna se ja aseta uudelleen.
            kohde_b = getattr(instance, avain_a)
            kohde_b.save()
            # Päivitä B-lomakkeen rivi ja kutsu sen `save_m2m`-metodia.
            lomake_b.instance = kohde_b
            lomake_b.save_m2m()
            # Aseta B uudelleen A-kohteelle.
            setattr(instance, avain_a, kohde_b)
            # Palauta oletus-`save`-toteutus paikalleen ja kutsu sitä.
            instance.save = vanha_save
            instance.save()
            # def save
          self.instance.save = types.MethodType(save, self.instance)
          # if not commit and kohde_b and not kohde_b.pk
        return super().save(commit=commit)

      else:
        # Mikäli B on uusi, viittaus A.B on olemassa ja tämä voi olla
        # tyhjä, korvataan A.B arvolla None ennen A:n tallennusta.
        # Palautetaan tallennuksen jälkeen A.B = B.
        # B tallennetaan lopuksi `_save_m2m`-metodissa.
        # Django vaatii tämän A:n tallentamiseksi; ks.
        # django.db.models.base:Model._prepare_related_fields_for_save.
        lomake_b = getattr(self, tunnus)
        if avain_a is None or lomake_b.instance.pk is not None:
          return super().save(commit=commit)
        setattr(self.instance, avain_a, None)
        self.instance = super().save(commit=commit)
        setattr(self.instance, avain_a, lomake_b.instance)
        return self.instance
        # else
      # def save

    # class YhdistettyLomake

  return YhdistettyLomake
  # def yhdista_lomakkeet
