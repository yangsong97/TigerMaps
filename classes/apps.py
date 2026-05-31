from django.apps import AppConfig


class ClassesConfig(AppConfig):
    name = 'classes'
    # Set here (rather than only in settings.py) so the auto field type is
    # consistent across every settings module, including the local/offline
    # configurations. This silences the models.W042 system-check warning.
    # AutoField (not BigAutoField) matches the pinned type in 0001_initial and
    # the existing integer primary keys, so no schema migration is generated.
    default_auto_field = 'django.db.models.AutoField'
