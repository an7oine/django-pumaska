class PiirtoMeta(type):
  def __new__(mcs, name, bases, attrs, *, LomakeB):
    if getattr(LomakeB, 'default_renderer', False):
      bases = (LomakeB.default_renderer, *bases)
    return super().__new__(mcs, name, bases, attrs)
  # class PiirtoMeta


class Piirto(metaclass=PiirtoMeta, LomakeB=None):
  ''' Hae kaikki jäsenet alkuperäisen lomakkeen `rendereriltä`. '''

  __slots__ = ['_lomake_a']

  def __init__(self, lomake_a):
    self._lomake_a = lomake_a

  def __getattribute__(self, attr):
    try:
      return super().__getattribute__(attr)
    except:
      return self._lomake_a.renderer.__getattribute__(attr)
    # def __getattribute__

  # class Piirto
