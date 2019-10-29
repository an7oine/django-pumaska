django-pumaska
==============

Sisäkkäisten lomakkeiden ja -sarjojen käsittely

Nidotun lomakkeen HTML-oletusesitys (`str(lomake)`) sisältää ulomman lomakkeen kenttien lisäksi joko
- sisemmän yksittäisen lomakkeen kentät sellaisenaan tai
- sisemmän lomakesarjan lomakkeet sellaisenaan, sekä sitä vastaavan Django-hallintolomakkeen ja tarvittavan Javascript-lomakesarjankoodin

Nidotun lomakkeen tallennus tallentaa ulomman lomakkeen (A) lisäksi sisemmän lomakkeen tai lomakesarjan (B) joko
- ennen ulompaa lomaketta, mikäli B-kentät ovat pakollisia suhteessa A-tietueeseen
- ulomman lomakkeen jälkeen muuten

Käyttö
------

Nido useita lomakkeita yhteen `nido`-funktion avulla:
```python
from django import forms
from pumaska import nido

from .mallit import Asiakas, Asiakasosoite, Lasku, Paamies, Rivi

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
)

print(lomake(instance=Asiakas.objects.get(pk=123)))
```

Funktiota voidaan käyttää myös python-koristeena:
```python
from django import forms
from pumaska import nido

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

assert Asiakaslomake(data={
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
}).is_valid()
```

Parametrit:
-----------

Funktio ottaa nimeämättöminä parametreina yhteen nidottavat lomakeluokat (`forms.ModelForm`).

Nimettyinä parametreinä voidaan antaa:
- `tunnus`: ulompaan lomakkeeseen asetetun määreen nimi, sisemmän lomakkeen `prefix`-parametri
- `avain_a`: viittaus A-lomakkeen kuvaamalta tietueelta B-lomakkeen kuvaamalle tietueelle
- `avain_b`: viittaus B-lomakkeen kuvaamalta tietueelta A-lomakkeen kuvaamalle tietueelle
- `pakollinen_b`: ovatko B-lomakkeen kentät pakollisia A-lomakkeen tallentamisen kannalta?
- `useita`: luodaanko lomakesarja, joka ottaa vastaan useita B-lomakkeita?

Kaikki em. parametrit poimitaan oletuksena automaattisesti mallien metatietojen perusteella.

Käyttöesimerkkejä:
------------------

Ks. `pumaska/testit.py`.
