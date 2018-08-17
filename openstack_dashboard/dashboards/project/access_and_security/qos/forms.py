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
from horizon.utils import validators as utils_validators

from openstack_dashboard import api

LOG = logging.getLogger(__name__)


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


class QosBase(forms.SelfHandlingForm):
    """Base class to handle creation and update of qos.

    Children classes must define two attributes:

    .. attribute:: success_message

        A success message containing the placeholder %s,
        which will be replaced by the group name.

    .. attribute:: error_message

        An error message containing the placeholder %s,
        which will be replaced by the error message.
    """
    name = forms.CharField(label=_("Name"),
                           max_length=255,
                           validators=[
                               utils_validators.validate_printable_ascii])
    description = forms.CharField(label=_("Description"),
                                  required=False,
                                  widget=forms.Textarea(attrs={'rows': 4}))

    def _call_network_api(self, request, data):
        """Call the underlying network API: Nova-network or Neutron.

        Used in children classes to create or update a group.
        """
        raise NotImplementedError()

    def handle(self, request, data):
        try:
            sg = self._call_network_api(request, data)
            messages.success(request, self.success_message % sg.name)
            return sg
        except Exception as e:
            redirect = reverse("horizon:project:access_and_security:index")
            error_msg = self.error_message % e
            exceptions.handle(request, error_msg, redirect=redirect)


class UpdateQos(QosBase):
    success_message = _('Successfully updated security group: %s')
    error_message = _('Unable to update security group: %s')

    id = forms.CharField(widget=forms.HiddenInput())

    def _call_network_api(self, request, data):
        return api.network.security_group_update(request,
                                                 data['id'],
                                                 data['name'],
                                                 data['description'])


class AddRule(forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput())
    rule_id = forms.CharField(widget=forms.HiddenInput())
    max_burst_kbps = forms.IntegerField(label=_("max_burst_kbps"),
                                   required=False,
                                   help_text=_("Enter a value for max_burst_kbps "),)
    max_kbps = forms.IntegerField(label=_("max_kbps"),
                                   required=False,
                                   help_text=_("Enter a value for max_kbps "),)

    def handle(self, request, data):
        try:
            max_burst_kbps = data['max_burst_kbps']
            max_kbps = data['max_kbps']
            qos_id = data['id']
            data_send = {
                'max_burst_kbps': max_burst_kbps,
                'max_kbps': max_kbps,
            }
            try:
                if data['rule_id']:
                    rule = data['rule_id']
                    api.neutron.update_qos_bandwidth(rule,qos_id,data_send)
                else:
                    api.neutron.create_qos_bandwidth(qos_id,data_send)
                msg = (_('QoS  %s was updated successful.') %
                       data['id'])
            except Exception:

                msg = (_('QoS  %s was updated failure.') %
                       data['id'])
            LOG.debug(msg)
            messages.success(request, msg)
        except Exception:
            redirect = reverse('horizon:project:access_and_security:index')
            msg = _('Failed to update QoS  %s') % data['id']
            exceptions.handle(request, msg, redirect=redirect)


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
            redirect = reverse('horizon:project:access_and_security:index')
            msg = _('Failed to create QoS policy %s') % data['name']
            exceptions.handle(request, msg, redirect=redirect)
