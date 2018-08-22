#!/usr/bin/env python
# coding=utf-8
# author=hades
# @Time    : 2018/8/17 9:24

import re
import logging

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api

LOG = logging.getLogger(__name__)

"""create qos form"""


class QoSPolicyForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255,
                           label=_("Name"),
                           required=True)
    description = forms.CharField(max_length=255,
                                  label=_("Description"),
                                  required=False)
    shared = forms.BooleanField(label=_("Shared"),
                                initial=False, required=False)

    def _get_params(self, request, data):
        params = {'name': data['name'],
                  'description': data['description'],
                  'shared':data['shared']
                  }
        return params


"""create qos"""


class CreateQoSPolicy(QoSPolicyForm):
    tenant_id = forms.ChoiceField(label=_("Project"),
                                  required=False)

    @classmethod
    def _instantiate(cls, request, *args, **kwargs):
        return cls(request, *args, **kwargs)

    def __init__(self, request, *args, **kwargs):
        super(CreateQoSPolicy, self).__init__(request, *args, **kwargs)

        tenant_choices = [('', _("Select a project"))]
        tenants, has_more = api.keystone.tenant_list(request)
        for tenant in tenants:
            if tenant.enabled:
                tenant_choices.append((tenant.id, tenant.name))
        self.fields['tenant_id'].choices = tenant_choices

    def handle(self, request, data):
        try:
            params = self._get_params(request, data)
            params['tenant_id'] = data['tenant_id']
            qos = api.neutron.policy_create(request, **params)
            msg = (_('QoS policy %s was successfully created.') %
                   data['description'])
            LOG.debug(msg)
            messages.success(request, msg)
            return qos
        except Exception:
            redirect = reverse('horizon:admin:info:index')
            msg = _('Failed to create QoS policy %s') % data['name']
            exceptions.handle(request, msg, redirect=redirect)


"""add rule form"""


class AddRule(forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput())
    rule = forms.CharField(widget=forms.HiddenInput())
    max_burst_kbps = forms.IntegerField(label=_("max_burst_kbps"),
                                   required=True,
                                   help_text=_("Enter a value for max_burst_kbps "),)
    max_kbps = forms.IntegerField(label=_("max_kbps"),
                                   required=True,
                                   help_text=_("Enter a value for max_kbps "),)

    def __init__(self, *args, **kwargs):
        sg_list = kwargs.pop('sg_list', [])
        super(AddRule, self).__init__(*args, **kwargs)

    def handle(self, request, data):
        redirect = reverse("horizon:admin:info:"
                           "qos:detail", args={data['id']:data['id']})
        try:
            params = {
                'max_burst_kbps': data['max_burst_kbps'],
                'max_kbps': data['max_kbps'],
            }
            if data['rule'] == 'no':
                rule = api.neutron.create_qos_bandwidth(request,data['id'],**params)
            else:
                api.neutron.delete_qos_bandwidth(request, data['id'], data['rule'])
                rule = api.neutron.create_qos_bandwidth(request, data['id'], **params)
            messages.success(request,
                             _('Successfully added rule: %s')
                             % data['id'])
            return rule
        except exceptions.Conflict as error:
            exceptions.handle(request, error, redirect=redirect)
        except Exception:
            exceptions.handle(request,
                              _('Unable to add rule to qos:%s')%(data['id']),
                              redirect=redirect)


"""update rule form"""
"""the feature is completed. 2018/8/21"""


class UpdateGroup(forms.SelfHandlingForm):
    pass