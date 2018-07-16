# Copyright 2012 NEC Corporation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.networks.ports \
    import forms as project_forms


LOG = logging.getLogger(__name__)
VNIC_TYPES = [('normal', _('Normal')), ('direct', _('Direct')),
              ('macvtap', _('MacVTap'))]


class CreatePort(forms.SelfHandlingForm):
    network_name = forms.CharField(label=_("Network Name"),
                                   widget=forms.TextInput(
                                       attrs={'readonly': 'readonly'}),
                                   required=False)
    network_id = forms.CharField(label=_("Network ID"),
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    name = forms.CharField(max_length=255,
                           label=_("Name"),
                           required=False)
    admin_state = forms.ChoiceField(choices=[(True, _('UP')),
                                             (False, _('DOWN'))],
                                    label=_("Admin State"))
    device_id = forms.CharField(max_length=100, label=_("Device ID"),
                                help_text=_("Device ID attached to the port"),
                                required=False)
    device_owner = forms.CharField(max_length=100, label=_("Device Owner"),
                                   help_text=_("Device owner attached to the "
                                               "port"),
                                   required=False)
    mac_address = forms.MACAddressField(
        label=_("MAC Address"),
        required=False,
        help_text=_("Specify the MAC address for the new port")
    )
    # specify_ip = forms.ThemableChoiceField(
    #     label=_("Specify IP address or subnet"),
    #     help_text=_("To specify a subnet or a fixed IP, select any options."),
    #     required=True,
    #     choices=[('', _("Unspecified")),
    #              ('subnet_id', _("Subnet")),
    #              ('fixed_ip', _("Fixed IP Address"))],
    #     widget=forms.Select(attrs={
    #         'class': 'switchable',
    #         'data-slug': 'specify_ip',
    #     }))
    # subnet_id = forms.ThemableChoiceField(
    #     label=_("Subnet"),
    #     required=False,
    #     widget=forms.Select(attrs={
    #         'class': 'switched',
    #         'data-switch-on': 'specify_ip',
    #         'data-specify_ip-subnet_id': _('Subnet'),
    #     }))
    fixed_ip = forms.IPField(
        label=_("Fixed IP Address"),
        required=False,
        help_text=_("Specify the subnet IP address for the new port"),
        version=forms.IPv4 | forms.IPv6,
        # widget=forms.TextInput(attrs={
        #     'class': 'switched',
        #     'data-switch-on': 'specify_ip',
        #     'data-specify_ip-fixed_ip': _('Fixed IP Address'),
        # })
        )
    binding__host_id = forms.CharField(
        label=_("Binding: Host"),
        help_text=_("The ID of the host where the port is allocated. In some "
                    "cases, different implementations can run on different "
                    "hosts."),
        required=False)

    failure_url = 'horizon:admin:networks:detail'

    def __init__(self, request, *args, **kwargs):
        super(CreatePort, self).__init__(request, *args, **kwargs)
        if api.neutron.is_extension_supported(request, 'binding'):
            neutron_settings = getattr(settings,
                                       'OPENSTACK_NEUTRON_NETWORK', {})
            supported_vnic_types = neutron_settings.get(
                'supported_vnic_types', ['*'])
            if supported_vnic_types:
                if supported_vnic_types == ['*']:
                    vnic_type_choices = VNIC_TYPES
                else:
                    vnic_type_choices = [
                        vnic_type for vnic_type in VNIC_TYPES
                        if vnic_type[0] in supported_vnic_types
                    ]

                self.fields['binding__vnic_type'] = forms.ChoiceField(
                    choices=vnic_type_choices,
                    label=_("Binding: VNIC Type"),
                    help_text=_(
                        "The VNIC type that is bound to the neutron port"),
                    required=False)
        if api.neutron.is_extension_supported(request, 'mac-learning'):
            self.fields['mac_state'] = forms.BooleanField(
                label=_("MAC Learning State"), initial=False, required=False)

    def handle(self, request, data):
        try:
            # We must specify tenant_id of the network which a subnet is
            # created for if admin user does not belong to the tenant.
            network = api.neutron.network_get(request, data['network_id'])
            data['tenant_id'] = network.tenant_id
            data['admin_state_up'] = (data['admin_state'] == 'True')
            del data['network_name']
            del data['admin_state']
            # print(data)
            # print(data['specify_ip'])
            # if data['specify_ip'] == 'subnet_id':
            #     if data['subnet_id']:
            #         data['fixed_ips'] = [{"subnet_id": data['subnet_id']}]
            # elif data['specify_ip'] == 'fixed_ip':
            #     if data['fixed_ip']:
            #         data['fixed_ips'] = [{"ip_address": data['fixed_ip']}]
            #         del data['subnet_id']
            #         del data['specify_ip']
            #         del data['fixed_ip']
            #         print(data)
            if data['fixed_ip']:
                data['fixed_ips'] = [{'ip_address':data['fixed_ip']}]
                del data['fixed_ip']
            else:
                del data['fixed_ip']
            if data['mac_address']:
                pass
            else:
                del data['mac_address']
            if 'mac_state' in data:
                data['mac_learning_enabled'] = data['mac_state']
                del data['mac_state']

            port = api.neutron.port_create(request, **data)
            msg = _('Port %s was successfully created.') % port['id']
            LOG.debug(msg)
            messages.success(request, msg)
            return port
        except Exception:
            msg = _('Failed to create a port for network %s') \
                % data['network_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url,
                               args=(data['network_id'],))
            exceptions.handle(request, msg, redirect=redirect)


class UpdatePort(project_forms.UpdatePort):
    # tenant_id = forms.CharField(widget=forms.HiddenInput())
    device_id = forms.CharField(max_length=100, label=_("Device ID"),
                                help_text=_("Device ID attached to the port"),
                                required=False)
    device_owner = forms.CharField(max_length=100, label=_("Device Owner"),
                                   help_text=_("Device owner attached to the "
                                               "port"),
                                   required=False)
    binding__host_id = forms.CharField(
        label=_("Binding: Host"),
        help_text=_("The ID of the host where the port is allocated. In some "
                    "cases, different implementations can run on different "
                    "hosts."),
        required=False)
    allowed_address_pair =  forms.CharField(label=_("Allowed-Address-Pair"),
                                            required=False,
                                            help_text=_("Plase send {'ip_address':'ip','mac_address':'mac_address'}"),
                                            widget=forms.Textarea())
    failure_url = 'horizon:admin:networks:detail'

    def handle(self, request, data):
        try:
            port = api.neutron.port_get(request,data['port_id'])
            print(port)
            LOG.debug('params = %s' % data)
            extension_kwargs = {}
            data['admin_state'] = (data['admin_state'] == 'True')
            if 'binding__vnic_type' in data:
                extension_kwargs['binding__vnic_type'] = \
                    data['binding__vnic_type']

            if 'mac_state' in data:
                extension_kwargs['mac_learning_enabled'] = data['mac_state']
            if 'allowed_address_pair' in data:
                print(data['allowed_address_pair'])
                port.allowed_address_pairs.append(eval(data['allowed_address_pair'].encode('ascii')))
                print(port.allowed_address_pairs)
                port = api.neutron.port_update(request,
                                               data['port_id'],
                                               name=data['name'],
                                               admin_state_up=data['admin_state'],
                                               device_id=data['device_id'],
                                               device_owner=data['device_owner'],
                                               allowed_address_pairs=port.allowed_address_pairs,
                                               binding__host_id=data
                                               ['binding__host_id'],
                                               **extension_kwargs)
            else:
                port = api.neutron.port_update(request,
                                               data['port_id'],
                                               name=data['name'],
                                               admin_state_up=data['admin_state'],
                                               device_id=data['device_id'],
                                               device_owner=data['device_owner'],
                                               binding__host_id=data
                                               ['binding__host_id'],
                                               **extension_kwargs)
            msg = _('Port %s was successfully updated.') % data['port_id']
            LOG.debug(msg)
            messages.success(request, msg)
            return port
        except Exception:
            msg = _('Failed to update port %s') % data['port_id']
            LOG.info(msg)
            redirect = reverse(self.failure_url,
                               args=[data['network_id']])
            exceptions.handle(request, msg, redirect=redirect)
