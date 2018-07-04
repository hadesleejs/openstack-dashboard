# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
import time

from openstack_dashboard.api import cinder


class UpdateForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Snapshot Name"))
    description = forms.CharField(max_length=255,
                                  widget=forms.Textarea(attrs={'rows': 4}),
                                  label=_("Description"),
                                  required=False)

    def handle(self, request, data):
        snapshot_id = self.initial['snapshot_id']
        try:
            cinder.volume_snapshot_update(request,
                                          snapshot_id,
                                          data['name'],
                                          data['description'])

            message = _('Updating volume snapshot "%s"') % data['name']
            messages.info(request, message)
            return True
        except Exception:
            redirect = reverse("horizon:project:volumes:index")
            exceptions.handle(request,
                              _('Unable to update volume snapshot.'),
                              redirect=redirect)


class RollbackSnapshot(forms.SelfHandlingForm):
    #patch by longxing:Rollback snapshot based on volume

    def __init__(self, request, *args, **kwargs):
        super(RollbackSnapshot, self).__init__(request, *args, **kwargs)

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
            volume=cinder.volume_get(request,data['volume_id'])

            if data['Confirm to rollback?'] == "yes":


                rollback = cinder.volume_snapshot_rollback(request,
                                                volume,
                                                data['snapshot_id'],
                                                force=True)
                msg = _('Rolling back the current volume...')
                messages.success(request, msg)
                return volume
            return "not do it"
        except Exception:
            exceptions.handle(request,
                              _('Unable to rollback snapshot.'))