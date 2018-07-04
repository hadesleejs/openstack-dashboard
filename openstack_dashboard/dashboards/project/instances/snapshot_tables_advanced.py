# Copyright 2013 Metacloud, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

#**************************************************
# This file is Added by Longxing
# For snapshot show based on each instance
# Date 2016/10/16
#**************************************************

from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from horizon.utils import filters

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import html
from django.utils.http import urlencode
from django.utils import safestring

from django.utils.translation import ungettext_lazy

from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.api import cinder
from openstack_dashboard import policy

from horizon import exceptions


def get_size(volume):
    return _("%sGiB") % volume.size


class VolumesTableBase(tables.DataTable):
    STATUS_CHOICES = (
        ("in-use", True),
        ("available", True),
        ("creating", None),
        ("error", False),
        ("error_extending", False),
        ("maintenance", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("available", pgettext_lazy("Current status of a Volume",
                                    u"Available")),
        ("in-use", pgettext_lazy("Current status of a Volume", u"In-use")),
        ("error", pgettext_lazy("Current status of a Volume", u"Error")),
        ("creating", pgettext_lazy("Current status of a Volume",
                                   u"Creating")),
        ("error_extending", pgettext_lazy("Current status of a Volume",
                                          u"Error Extending")),
        ("extending", pgettext_lazy("Current status of a Volume",
                                    u"Extending")),
        ("attaching", pgettext_lazy("Current status of a Volume",
                                    u"Attaching")),
        ("detaching", pgettext_lazy("Current status of a Volume",
                                    u"Detaching")),
        ("deleting", pgettext_lazy("Current status of a Volume",
                                   u"Deleting")),
        ("error_deleting", pgettext_lazy("Current status of a Volume",
                                         u"Error deleting")),
        ("backing-up", pgettext_lazy("Current status of a Volume",
                                     u"Backing Up")),
        ("restoring-backup", pgettext_lazy("Current status of a Volume",
                                           u"Restoring Backup")),
        ("error_restoring", pgettext_lazy("Current status of a Volume",
                                          u"Error Restoring")),
        ("maintenance", pgettext_lazy("Current status of a Volume",
                                      u"Maintenance")),
    )
    name = tables.Column("name",
                         verbose_name=_("Name"),
                         link="horizon:project:volumes:volumes:detail")
    description = tables.Column("description",
                                verbose_name=_("Description"),
                                truncate=40)
    size = tables.Column(get_size,
                         verbose_name=_("Size"),
                         attrs={'data-type': 'size'})
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    def get_object_display(self, obj):
        return obj.name


class SnapshotVolumeNameColumn(tables.Column):
    #column to show the volume name
    def get_raw_data(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_name = volume.name
            volume_name = html.escape(volume_name)
        else:
            volume_name = _("Unknown")
        return safestring.mark_safe(volume_name)

    def get_link_url(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_id = volume.id
            return reverse(self.link, args=(volume_id,))

class SnapshotInstanceNameColumn(tables.Column):
    #column to show the instance name of a snapshot
    def get_raw_data(self, snapshot):
        instance = snapshot._instance
        if instance:
            instance_name = instance.name
            instance_name = html.escape(instance_name)
        else:
            instance_name = _("Unknown")
        return safestring.mark_safe(instance_name)

    def get_link_url(self, snapshot):
        instance = snapshot._instance
        if instance:
            instance_id = instance.id
            return reverse(self.link, args=(instance_id,))

class SnapshotCreateDateColumn(tables.Column):
    #column to show the created date info of a snapshot
    def get_raw_data(self, snapshot):
        dates = snapshot.created_at
        dates=dates.replace("T"," ").split(".")[0]
        if dates:
            dates = html.escape(dates)
        else:
            dates = _("Unknown")
        return safestring.mark_safe(dates)


class SnapshotAttachDiskColumn(tables.Column):
    #column to show the attached disk for a volume
    def get_raw_data(self, snapshot):
        volume = snapshot._volume
        attached=volume.attachments[0].get("device","error")
        if attached:
            attached = html.escape(attached)
        else:
            attached = _("Unknown")
        return safestring.mark_safe(attached)



class VolumeSnapshotsFilterAction(tables.FilterAction):
    #Table action for filtering volumes

    def filter(self, table, snapshots, filter_string):
        """Naive case-insensitive search."""
        query = filter_string.lower()
        return [snapshot for snapshot in snapshots
                if query in snapshot.name.lower()]


#class DeleteVolumeSnapshot(policy.PolicyTargetMixin, tables.DeleteAction):
class DeleteVolumeSnapshot(tables.DeleteAction):
    classes = ("btn-danger",)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Instance Snapshot",
            u"Delete Instance Snapshots",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Instance Snapshot",
            u"Scheduled deletion of Instance Snapshots",
            count
        )

    #policy_rules = (("compute", "compute:delete"),)
    #policy_target_attrs = (("project_id",
       #                     'os-extended-snapshot-attributes:project_id'),)

    def delete(self, request, obj_id):
        try:

            cinder.volume_snapshot_delete(request, obj_id)
        except Exception:
            exceptions.handle(request, _('Unable to delete snapshot '
                                         'information.'))



class EditVolumeSnapshot(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Snapshot")
    url = "horizon:project:volumes:snapshots:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("volume", "volume:update_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def allowed(self, request, snapshot=None):
        return snapshot.status == "available"

    def get_link_url(self, datum):
        base_url = super(EditVolumeSnapshot, self).get_link_url(datum)
        params = urlencode({"instance_id": datum._volume.attachments[0]["server_id"],"type":"instance"})
        return "?".join([base_url,params])

class CreateVolumeFromSnapshot(tables.LinkAction):
    #create volume from snapshot, just use the same one from volume/snapshots
    name = "create_from_snapshot"
    verbose_name = _("Create Volume")
    url = "horizon:project:volumes:volumes:create"
    classes = ("ajax-modal",)
    icon = "camera"
    policy_rules = (("volume", "volume:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({"snapshot_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])

    def allowed(self, request, volume=None):
        if volume and cinder.is_volume_service_enabled(request):
            return volume.status == "available"
        return False



class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, snapshot_id):
        snapshot = cinder.volume_snapshot_get(request, snapshot_id)
        snapshot._volume = cinder.volume_get(request, snapshot.volume_id)
        return snapshot


class RollbackSnapshotAdvancedAction(tables.LinkAction):
    #function to rollback the snapshots
    name = "rollbacksnapshotadvancedact"
    verbose_name = _("Rollback Snapshot Advanced")
    url = "horizon:project:instances:rollback_snapshot_advanced_act"
    classes = ("ajax-modal",)
    icon = "camera"

    def get_link_url(self, datum):
        #print "datum"
        pid = datum.__getattribute__('os-extended-snapshot-attributes:project_id')
        if  hasattr(datum, "_instance") :
            instance_id=datum._instance.id
        else:
            instance_id=datum._volume.attachments[0]["server_id"]
        volume_id=datum.volume_id
        snapshot_id=datum.id
        base_url = reverse(self.url,args=(instance_id,volume_id,snapshot_id,))
        return base_url


class VolumeSnapshotsTable(VolumesTableBase):

    name = tables.Column("name",
                         verbose_name=_("Name"),
#                         link="horizon:project:volumes:snapshots:detail")
                         )
    volume_name = SnapshotVolumeNameColumn(
        "volume_name",
        verbose_name=_("Volume Name"),
        link="horizon:project:volumes:volumes:detail")

    attacheddisk= SnapshotAttachDiskColumn(
        "attached disk",
        verbose_name=_("Attached Disk"),
#        link="horizon:project:volumes:volumes:detail")
        )

#    instance_name = SnapshotInstanceNameColumn(
#        "instance_name",
#        verbose_name=_("Instance Name"),
##        link="horizon:project:volumes:volumes:detail")
#        )

    dates= SnapshotCreateDateColumn(
        "create date",
        verbose_name=_("Create Date"),
#        link="horizon:project:volumes:volumes:detail")
        )


    class Meta(object):
        name = "volume_snapshots"
        verbose_name = _("Volume Snapshots")
        pagination_param = 'snapshot_marker'
        prev_pagination_param = 'prev_snapshot_marker'
        table_actions = (VolumeSnapshotsFilterAction, DeleteVolumeSnapshot,)
        row_actions=(RollbackSnapshotAdvancedAction,CreateVolumeFromSnapshot,EditVolumeSnapshot,DeleteVolumeSnapshot)
        status_columns = ("status",)
        row_class = UpdateRow
        permissions = [(
            ('openstack.services.compute', 'openstack.services.computev2'),
        )]






