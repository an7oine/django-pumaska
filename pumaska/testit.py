# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

import contextlib
from decimal import Decimal
import itertools
from unittest.mock import patch

from django.db import models
from django import forms
from django.test import SimpleTestCase

from pumaska import nido


class Asiakas(models.Model):
  nimi = models.CharField(max_length=255)

class Asiakasosoite(models.Model):
  asiakas = models.ForeignKey(Asiakas, on_delete=models.CASCADE)
  osoite = models.CharField(max_length=255)

class Paamies(models.Model):
  nimi = models.CharField(max_length=255)

class Lasku(models.Model):
  asiakas = models.ForeignKey(Asiakas, on_delete=models.CASCADE)
  paamies = models.ForeignKey(Paamies, on_delete=models.CASCADE)
  numero = models.IntegerField()

class Rivi(models.Model):
  lasku = models.ForeignKey(Lasku, on_delete=models.CASCADE)
  summa = models.DecimalField(max_digits=11, decimal_places=2)


class Testi(SimpleTestCase):

  @contextlib.contextmanager
  def varmista_tietueiden_tallennus(self, tietueet):
    '''
    Varmista, että suoritettava koodi tallentaa tietokantaan
    täsmälleen annettuja sanakirjoja vastaavat tietueet
    annetussa järjestyksessä.
    '''
    tietueet = iter(tietueet)
    def tallenna(self2):
      tietue = {'__class__': type(self2).__name__, **{
        k: v for k, v in self2.__dict__.items()
        if k not in ('id', '_state')
        and not k.endswith('_id')
        and not isinstance(v, models.Model)
      }}
      self.assertEqual(tietue, next(tietueet))
      # def tallenna
    with patch('django.db.transaction.Atomic.__enter__'):
      with patch('django.db.models.base.Model.save', tallenna):
        yield
    self.assertRaises(StopIteration, next, tietueet)
    # def varmista_tietueiden_tallennus

  def testaa_html(self):
    'Toimiiko HTML-sivun muodostus liitoslomakkeen mukaan?'
    # pylint: disable=line-too-long
    html = str(nido(
      forms.modelform_factory(Asiakas, fields=['nimi']),
      forms.modelform_factory(Asiakasosoite, fields=['osoite']),
      nido(
        nido(
          forms.modelform_factory(Lasku, fields=['numero']),
          forms.modelform_factory(Paamies, fields=['nimi']),
          avain_a='paamies'
        ),
        forms.modelform_factory(Rivi, fields=['summa']),
        avain_b='lasku'
      ),
    )())
    for name in map('-'.join, itertools.chain.from_iterable(itertools.starmap(itertools.product, (
      (('asiakasosoite', 'lasku', ), ('TOTAL_FORMS', 'INITIAL_FORMS', 'MIN_NUM_FORMS', 'MAX_NUM_FORMS', )),
      (('asiakasosoite', ), ('__prefix__', ), ('id', 'asiakas', 'osoite', 'DELETE', ), ),
      (('lasku', ), ('__prefix__', ), ('id', 'asiakas', 'numero', 'DELETE', )),
      (('lasku', ), ('__prefix__', ), ('rivi', ), ('TOTAL_FORMS', 'INITIAL_FORMS', 'MIN_NUM_FORMS', 'MAX_NUM_FORMS', )),
      (('lasku', ), ('__prefix__', ), ('rivi', ), ('__prefix__', ), ('id', 'lasku', 'summa', 'DELETE', )),
    )))):
      self.assertIn(f' name="{name}" ', html)
    # def testaa_html

  def testaa_liitospuu(self):
    'Toimiiko monihaaraisen lomakepuun tallennus?'

    lomake = nido(
      forms.modelform_factory(Asiakas, fields=['nimi']),
      forms.modelform_factory(Asiakasosoite, fields=['osoite']),
      nido(
        nido(
          forms.modelform_factory(Lasku, fields=['numero']),
          forms.modelform_factory(Paamies, fields=['nimi']),
        ),
        forms.modelform_factory(Rivi, fields=['summa']),
      ),
    )(data={
      'nimi': 'Testimies Matti',
      'asiakasosoite-TOTAL_FORMS': '2',
      'asiakasosoite-INITIAL_FORMS': '0',
      'asiakasosoite-MIN_NUM_FORMS': '0',
      'asiakasosoite-MAX_NUM_FORMS': '1000',
      'asiakasosoite-0-osoite': 'Testitie 2',
      'asiakasosoite-1-osoite': 'Testitie 3',
      'lasku-TOTAL_FORMS': '1',
      'lasku-INITIAL_FORMS': '0',
      'lasku-MIN_NUM_FORMS': '0',
      'lasku-MAX_NUM_FORMS': '1000',
      'lasku-0-numero': '12345',
      'lasku-0-paamies-nimi': 'Palapallon Turrukkamatkat',
      'lasku-0-rivi-TOTAL_FORMS': '2',
      'lasku-0-rivi-INITIAL_FORMS': '0',
      'lasku-0-rivi-MIN_NUM_FORMS': '0',
      'lasku-0-rivi-MAX_NUM_FORMS': '1000',
      'lasku-0-rivi-0-summa': '123.45',
      'lasku-0-rivi-1-summa': '678.90',
    })
    self.assertTrue(lomake.is_valid())

    with self.varmista_tietueiden_tallennus((
      {'__class__': 'Asiakas', 'nimi': 'Testimies Matti'},
      {'__class__': 'Asiakasosoite', 'osoite': 'Testitie 2'},
      {'__class__': 'Asiakasosoite', 'osoite': 'Testitie 3'},
      {'__class__': 'Paamies', 'nimi': 'Palapallon Turrukkamatkat'},
      {'__class__': 'Lasku', 'numero': 12345},
      {'__class__': 'Rivi', 'summa': Decimal('123.45'),},
      {'__class__': 'Rivi', 'summa': Decimal('678.90'),},
    )):
      lomake.save()
    # def testaa_tallennus

  def testaa_koristeena(self):
    'Toimiiko @nido-koristeen kautta luotu lomake oikein?'

    class Asiakasosoitelomake(forms.ModelForm):
      class Meta:
        model = Asiakasosoite
        fields = ['osoite']
    class Laskulomake(forms.ModelForm):
      class Meta:
        model = Lasku
        fields = ['numero']

    @nido(Asiakasosoitelomake)
    @nido(Laskulomake)
    class Asiakaslomake(forms.ModelForm):
      class Meta:
        model = Asiakas
        fields = ['nimi']

    lomake = Asiakaslomake(data={
      'nimi': 'Testimies Matti',
      'asiakasosoite-TOTAL_FORMS': '1',
      'asiakasosoite-INITIAL_FORMS': '0',
      'asiakasosoite-MIN_NUM_FORMS': '0',
      'asiakasosoite-MAX_NUM_FORMS': '1000',
      'asiakasosoite-0-osoite': 'Testitie 2',
      'lasku-TOTAL_FORMS': '2',
      'lasku-INITIAL_FORMS': '0',
      'lasku-MIN_NUM_FORMS': '0',
      'lasku-MAX_NUM_FORMS': '1000',
      'lasku-0-numero': '12345',
      'lasku-1-numero': '15445',
    })
    self.assertTrue(lomake.is_valid())
    with self.varmista_tietueiden_tallennus((
      {'__class__': 'Asiakas', 'nimi': 'Testimies Matti'},
      {'__class__': 'Lasku', 'numero': 12345},
      {'__class__': 'Lasku', 'numero': 15445},
      {'__class__': 'Asiakasosoite', 'osoite': 'Testitie 2'},
    )):
      lomake.save()
    # def testaa_koristeena

  # class Testi
