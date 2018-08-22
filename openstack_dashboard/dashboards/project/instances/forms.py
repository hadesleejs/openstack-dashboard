# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
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

from django.core.urlresolvers import reverse
from django.template.defaultfilters import filesizeformat  # noqa
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa
import time
from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import validators

from openstack_dashboard import api
from openstack_dashboard.api import cinder
from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
import time
import logging
def _image_choice_title(img):
    gb = filesizeformat(img.size)
    return '%s (%s)' % (img.name or img.id, gb)


class RebuildInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())

    image = forms.ChoiceField(
        label=_("Select Image"),
        widget=forms.SelectWidget(attrs={'class': 'image-selector'},
                                  data_attrs=('size', 'display-name'),
                                  transform=_image_choice_title))
    password = forms.RegexField(
        label=_("Rebuild Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Rebuild Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    disk_config = forms.ChoiceField(label=_("Disk Partition"),
                                    required=False)

    def __init__(self, request, *args, **kwargs):
        super(RebuildInstanceForm, self).__init__(request, *args, **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        self.fields['instance_id'].initial = instance_id

        images = image_utils.get_available_images(request,
                                                  request.user.tenant_id)
        choices = [(image.id, image) for image in images]
        if choices:
            choices.insert(0, ("", _("Select Image")))
        else:
            choices.insert(0, ("", _("No images available")))
        self.fields['image'].choices = choices

        if not api.nova.can_set_server_password():
            del self.fields['password']
            del self.fields['confirm_password']

        try:
            if not api.nova.extension_supported("DiskConfig", request):
                del self.fields['disk_config']
            else:
                # Set our disk_config choices
                config_choices = [("AUTO", _("Automatic")),
                                  ("MANUAL", _("Manual"))]
                self.fields['disk_config'].choices = config_choices
        except Exception:
            exceptions.handle(request, _('Unable to retrieve extensions '
                                         'information.'))

    def clean(self):
        cleaned_data = super(RebuildInstanceForm, self).clean()
        if 'password' in cleaned_data:
            passwd = cleaned_data.get('password')
            confirm = cleaned_data.get('confirm_password')
            if passwd is not None and confirm is not None:
                if passwd != confirm:
                    raise forms.ValidationError(_("Passwords do not match."))
        return cleaned_data

    # We have to protect the entire "data" dict because it contains the
    # password and confirm_password strings.
    @sensitive_variables('data', 'password')
    def handle(self, request, data):
        instance = data.get('instance_id')
        image = data.get('image')
        password = data.get('password') or None
        disk_config = data.get('disk_config', None)
        try:
            api.nova.server_rebuild(request, instance, image, password,
                                    disk_config)
            messages.success(request, _('Rebuilding instance %s.') % instance)
        except Exception:
            redirect = reverse('horizon:project:instances:index')
            exceptions.handle(request, _("Unable to rebuild instance."),
                              redirect=redirect)
        return True


class DecryptPasswordInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    _keypair_name_label = _("Key Pair Name")
    _keypair_name_help = _("The Key Pair name that "
                           "was associated with the instance")
    _attrs = {'readonly': 'readonly', 'rows': 4}
    keypair_name = forms.CharField(widget=forms.widgets.TextInput(_attrs),
                                   label=_keypair_name_label,
                                   help_text=_keypair_name_help,
                                   required=False)
    _encrypted_pwd_help = _("The instance password encrypted "
                            "with your public key.")
    encrypted_password = forms.CharField(widget=forms.widgets.Textarea(_attrs),
                                         label=_("Encrypted Password"),
                                         help_text=_encrypted_pwd_help,
                                         required=False)

    def __init__(self, request, *args, **kwargs):
        super(DecryptPasswordInstanceForm, self).__init__(request,
                                                          *args,
                                                          **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        self.fields['instance_id'].initial = instance_id
        keypair_name = kwargs.get('initial', {}).get('keypair_name')
        self.fields['keypair_name'].initial = keypair_name
        try:
            result = api.nova.get_password(request, instance_id)
            if not result:
                _unavailable = _("Instance Password is not set"
                                 " or is not yet available")
                self.fields['encrypted_password'].initial = _unavailable
            else:
                self.fields['encrypted_password'].initial = result
                self.fields['private_key_file'] = forms.FileField(
                    label=_('Private Key File'),
                    widget=forms.FileInput())
                self.fields['private_key'] = forms.CharField(
                    widget=forms.widgets.Textarea(),
                    label=_("OR Copy/Paste your Private Key"))
                _attrs = {'readonly': 'readonly'}
                self.fields['decrypted_password'] = forms.CharField(
                    widget=forms.widgets.TextInput(_attrs),
                    label=_("Password"),
                    required=False)
        except Exception:
            redirect = reverse('horizon:project:instances:index')
            _error = _("Unable to retrieve instance password.")
            exceptions.handle(request, _error, redirect=redirect)

    def handle(self, request, data):
        return True


class AttachInterface(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    # network = forms.ChoiceField(label=_("Network"))
    network_type = forms.ChoiceField(
        label=_("Network or Port"),
        help_text=_("Choice Network or Port "),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'network_type'
        }))
    network= forms.ChoiceField(
        label=_("Network"),
        required=False,
        help_text='choice a network',
        widget=forms.Select(attrs={
            'class':'switched',
            'data-switch-on':'network_type',
            'data-network_type-network':_('Network'),
        }))
    port = forms.ChoiceField(
        label=_("Port"),
        required=False,
        help_text='choice a port',
        widget=forms.Select(attrs={
            'class':'switched',
            'data-switch-on':'network_type',
            'data-network_type-port':_('Port'),
        }))
    fixed_ip = forms.IPField(
        label=_("Fixed IP"),
        required=False,
        help_text='input fixed ip',
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-network': _('Fixed IP'),
        }))

    def __init__(self, request, *args, **kwargs):
        super(AttachInterface, self).__init__(request, *args, **kwargs)
        networks = instance_utils.network_field_data(request,
                                                     include_empty_option=True)
        self.fields['network'].choices = networks
        choices = [('network', _('Network'))]
        ports = instance_utils.port_field_tenant_data(request)
        if len(ports) > 0:
            self.fields['port'].choices = ports
            choices.append(('port', _("Port")))
        self.fields['network_type'].choices = choices

    def handle(self, request, data):
        instance_id = data['instance_id']
        network = data.get('network')
        port = data.get('port')
        network_type = data.get('network_type')
        fixed_ip = data.get('fixed_ip')
        try:
            if network_type == 'network':
                del data['port']
                if fixed_ip == '':

                    api.nova.interface_attach(request, instance_id, net_id=network)
                    msg = _('Attaching interface for instance %s.') % instance_id
                    messages.success(request, msg)
                else:
                    api.nova.interface_attach(request, instance_id, net_id=network,fixed_ip=fixed_ip)
                    msg = _('Attaching interface for instance %s.') % instance_id
                    messages.success(request, msg)
            else:
                api.nova.interface_attach(request, instance_id,port_id=port)
                msg = _('Attaching interface for instance %s.') % instance_id
                messages.success(request, msg)
        except Exception:
            redirect = reverse('horizon:project:instances:index')
            exceptions.handle(request, _("Unable to attach interface."),
                              redirect=redirect)
        return True

class AttachInterface_bak(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())

    network_type = forms.ChoiceField(
        label=_("Network or Port"),
        help_text=_("Choice Network or Port "),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'network_type'
        }))
    port = forms.CharField(
        max_length=255,
        label=_("Port"),
        help_text=_("Port Id"),
        # initial='default',
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-port': _('Port'),
        }))
    fixed_ip = forms.IPField(
        label=_("Fixed IP"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-network': _('Fixed IP'),
        }))

    network= forms.ChoiceField(
        label='Network',
        widget=forms.Select(attrs={
            'class':'switched',
            'data-switch-on':'network_type',
            'data-network_type-network':_('Network'),
        }))
    def __init__(self, request, *args, **kwargs):
        super(AttachInterface, self).__init__(request, *args, **kwargs)
        networks = instance_utils.network_field_data(request,
                                                     include_empty_option=True)
        self.fields['network'].choices = networks
        self.fields['network_type'].choices = [('network', _('Network')),('port', _('Port'))]
    def handle(self, request, data):
        instance_id = data['instance_id']
        network = data['network']
        fixed_ip = data['fixed_ip']
        port_id = data['port']
        try:
            # if fixed_ip != '':
            #     print('ooooooooooooooooooooooooooooooooo--------------------------oooooooooooooooooo')
            #     api.nova.interface_attach(request, instance_id, net_id=network,fixed_ip=fixed_ip)
            # elif port_id != '':
            #     api.nova.interface_attach(request, instance_id, port_id=port_id)
            # else:
            api.nova.interface_attach(request, instance_id,net_id=network)
            msg = _('Attaching interface for instance %s.') % instance_id
            messages.success(request, msg)
        except Exception:
            redirect = reverse('horizon:project:instances:index')
            exceptions.handle(request, _("Unable to attach interface."),
                              redirect=redirect)
        return True

class DetachInterface(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    port = forms.ChoiceField(label=_("Port"))

    def __init__(self, request, *args, **kwargs):
        super(DetachInterface, self).__init__(request, *args, **kwargs)
        instance_id = self.initial.get("instance_id", None)
        logging.basicConfig(filename='/home/yangsong.log', filemode="w", level=logging.DEBUG)
        logging.debug('This message should go to the log file')
        ports = []
        try:
            ports = api.neutron.port_list(request, device_id=instance_id)
        except Exception:
            exceptions.handle(request, _('Unable to retrieve ports '
                                         'information.'))
        choices = []
        for port in ports:
            ips = []
            for ip in port.fixed_ips:
                ips.append(ip['ip_address'])
            choices.append((port.id, ','.join(ips) or port.id))
        if choices:
            choices.insert(0, ("", _("Select Port")))
        else:
            choices.insert(0, ("", _("No Ports available")))
        self.fields['port'].choices = choices
    def handle(self, request, data):
        instance_id = data['instance_id']
        port = data.get('port')
        ports = api.neutron.port_list(request, device_id=instance_id)

        try:
            api.nova.interface_detach(request, instance_id, port)
            count=1
            while True:
                count+=1
                if count>30:
                    msg = _("Detached interface overtime")
                    messages.error(request, msg)
                    break
                else:
                    ports = api.neutron.port_list(request, device_id=instance_id)
                    for p in ports:
                        if p.id==port:
                            time.sleep(1)
                    else:
                        msg = _('Detached interface %(port)s for instance '
                                '%(instance)s.') % {'port': port, 'instance': instance_id}
                        messages.success(request, msg)
                        break
        except Exception:
            redirect = reverse('horizon:project:instances:index')
            exceptions.handle(request, _("Unable to detach interface."),
                              redirect=redirect)
        return True

def getfileteredvolume(instanceid,volumes):
    #Patch by longxing
    vols=[];
    for vol in volumes:
        #print vol.attachments[0].get("server_id","server_id not existing")
        if vol.attachments[0].get("server_id","server_id not existing") == instanceid:
            vols.append(vol)
    return  vols

def getVolumeList(volumes):
    #Patch by longxing
    choice=[("None","None")]
    for vol in volumes:
        if vol.attachments[0].get("device","error") == "/dev/vda":
            choice.append(tuple([vol.id,"system disk"+" "+vol.name]))
        else:
            choice.append(tuple([vol.id,vol.attachments[0].get("device","error")+" "+vol.name]))
    choice=tuple(choice)
    return choice

class CreateSnapshotAdvanced(forms.SelfHandlingForm):
    #Patch by longxing: Create snapshot based on instance and volume
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)
    name = forms.CharField(max_length=255, label=_("Snapshot Name"))
    description = forms.CharField(max_length=255, label=_("Snapshot Description"))


    def __init__(self, request, *args, **kwargs):
        super(CreateSnapshotAdvanced, self).__init__(request, *args, **kwargs)

        instance_id=kwargs.get('initial', {}).get('instance_id', [])
        search_opts={'status':'in-use'}
        volumes = cinder.volume_list(self.request,search_opts)
        volumes=getfileteredvolume(instance_id,volumes)

        VOL_CHOICES=getVolumeList(volumes)
        #self.fields['volume_radio'] = forms.ChoiceField(widget=forms.RadioSelect(),
        #                                           choices=VOL_CHOICES,label="cloud disk")
        self.fields['volume_select'] = forms.ChoiceField(widget=forms.Select(),
                                                   choices=VOL_CHOICES,label=_("cloud disk"))

    def handle(self, request, data):
        try:
            if data['volume_select'] == "None":
                redirect = reverse("horizon:project:instances:index")
                msg = _('There is no volume selected.')
                exceptions.handle(request,msg,redirect=redirect)
                return "not selected"
            volume = cinder.volume_get(request,
                                       data['volume_select'])
            forceflag = False
            message = _('Creating volume snapshot "%s".') % data['name']
            if volume.status == 'in-use':
                forceflag = True
                message = _('Forcing to create snapshot "%s" '
                            'from attached volume.') % data['name']
            snapshot = cinder.volume_snapshot_create(request,
                                                     data['volume_select'],
                                                     data['name'],
                                                     data['description'],
                                                     force=forceflag)
            messages.info(request, message)
            return snapshot
        except Exception as e:
            redirect = reverse("horizon:project:instances:index")
            msg = _('Unable to create volume snapshot.')
            if data['volume_select'] != "None":
                if e.code == 413:
                    msg = _('Requested snapshot would exceed the allowed quota.')
            else:
                msg = _('There is no volume selected.')
            exceptions.handle(request,
                              msg,
                              redirect=redirect)




class RollbackSnapshotAdvancedAct(forms.SelfHandlingForm):
    #patch by longxing:Rollback snapshot based on instance and volume
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)

    def __init__(self, request, *args, **kwargs):
        super(RollbackSnapshotAdvancedAct, self).__init__(request, *args, **kwargs)

        volume_id=kwargs.get('initial', {}).get('volume_id', [])
        snapshot_id=kwargs.get('initial', {}).get('snapshot_id', [])
        self.fields['volume_id'] = forms.CharField(widget=forms.HiddenInput(),
                                                   initial=volume_id)
        self.fields['snapshot_id'] = forms.CharField(widget=forms.HiddenInput(),
                                                   initial=snapshot_id)


        self.fields['Confirm to rollback?'] = forms.ChoiceField(widget=forms.RadioSelect(),
                                                   choices=(("yes",_("yes")),),label=_("confirm"))

    def handle(self, request, data):
        try:
            instance=api.nova.server_get(request,data['instance_id'])
            if data['Confirm to rollback?'] == "yes":
                

                rollback = api.nova.server_rollback(request,
                                                instance,
                                                data['volume_id'],
                                                data['snapshot_id'],
                                                True)
                time.sleep(1)
                msg = _('Rolling back the current instance...')
                request.session['rollback']=data['instance_id']
                messages.success(request, msg)
                return instance
            return "not do it"
        except Exception,e:
            exceptions.handle(request,
                              _('Unable to rollback snapshot '+e.message))