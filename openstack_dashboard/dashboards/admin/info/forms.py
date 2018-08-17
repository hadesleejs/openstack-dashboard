#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/15 14:57
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


LOG = logging.getLogger(__name__)


class CreateQos(forms.SelfHandlingForm):
    pass