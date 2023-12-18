from django.db import models


class Edustaja(models.Model):
  nimi = models.CharField(max_length=255)

class Asiakas(models.Model):
  nimi = models.CharField(max_length=255)
  edustaja = models.OneToOneField(
    Edustaja, on_delete=models.SET_NULL, null=True, blank=True
  )

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
