from django.apps import AppConfig

class CalculadorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calculador'
    # IMPORTANTE: Asegúrate de que no haya líneas que digan "import calculador.models" aquí adentro.

