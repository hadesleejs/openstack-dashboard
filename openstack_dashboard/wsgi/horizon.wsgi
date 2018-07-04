#!/usr/bin/env python
import os
import sys

sys.path.insert(0, '/usr/share/openstack-dashboard')
os.environ['DJANGO_SETTINGS_MODULE'] = 'openstack_dashboard.settings'

import django.core.wsgi
application = django.core.wsgi.get_wsgi_application()
