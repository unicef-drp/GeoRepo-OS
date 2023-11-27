from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.decorators import action
from django.contrib.admin.utils import (
    NestedObjects,
    quote,
)
from django.contrib.admin.utils import model_ngettext
from django.core.exceptions import PermissionDenied
from django.db import router
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.text import (
    capfirst,
)
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.csrf import csrf_protect
from georepo.models.entity import GeographicalEntity
from georepo.tasks.dataset_delete import dataset_delete

IS_POPUP_VAR = "_popup"
TO_FIELD_VAR = "_to_field"

HORIZONTAL, VERTICAL = 1, 2
csrf_protect_m = method_decorator(csrf_protect)


def get_deleted_objects(objs, request, admin_site, disable_summary=False):
    """
    This function can be used to override
    django.contrib.admin.utils.get_deleted_objects, to support
    disabling summary of objects that will be deleted.

    Find all objects related to ``objs`` that should also be deleted. ``objs``
    must be a homogeneous iterable of objects (e.g. a QuerySet).

    Return a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.
    """

    try:
        obj = objs[0]
    except IndexError:
        return [], {}, set(), []
    else:
        using = router.db_for_write(obj._meta.model)
    collector = NestedObjects(using=using)
    if not disable_summary:
        collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        model = obj.__class__
        has_admin = model in admin_site._registry
        opts = obj._meta

        no_edit_link = "%s: %s" % (capfirst(opts.verbose_name), obj)

        if has_admin:
            if not admin_site._registry[model]. \
                has_delete_permission(request, obj):
                perms_needed.add(opts.verbose_name)
            try:
                admin_url = reverse(
                    "%s:%s_%s_change"
                    % (admin_site.name, opts.app_label, opts.model_name),
                    None,
                    (quote(obj.pk),),
                )
            except NoReverseMatch:
                # Change url doesn't exist -- don't display link to edit
                return no_edit_link

            # Display a link to the admin page.
            return format_html(
                '{}: <a href="{}">{}</a>',
                capfirst(opts.verbose_name),
                admin_url,
                obj
            )
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return no_edit_link

    to_delete = collector.nested(format_callback)

    protected = [format_callback(obj) for obj in collector.protected]
    if not disable_summary:
        model_count = {
            model._meta.verbose_name_plural: len(objs)
            for model, objs in collector.model_objs.items()
        }
    else:
        to_delete = [
            f'Dataset: {obj.label}' for obj in objs
        ]
        model_count = {
            'dataset': len(objs),
            'Geographical Entities': GeographicalEntity.objects.filter(
                dataset__in=objs
            ).count()
        }

    return to_delete, model_count, perms_needed, protected


@action(
    permissions=["delete"],
    description=gettext_lazy("Delete selected %(verbose_name_plural)s"),
)
def delete_selected(modeladmin, request, queryset):
    """
    This function can be used to override
    django.contrib.admin.actions.delete_selected, to support
    object deletion in background.

    This action first displays a confirmation page which shows all the
    deletable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it deletes all selected objects and redirects back to the
    change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Populate deletable_objects, a data structure of all related objects that
    # will also be deleted.
    (
        deletable_objects,
        model_count,
        perms_needed,
        protected,
    ) = modeladmin.get_deleted_objects(queryset, request)

    # The user has already confirmed the deletion.
    # Do the deletion and return None to display the change list view again.
    if request.POST.get("post") and not protected:
        if perms_needed:
            raise PermissionDenied
        n = queryset.count()
        if n:
            for obj in queryset:
                obj_display = str(obj)
                modeladmin.log_deletion(request, obj, obj_display)
            ids = list(queryset.values_list('id', flat=True))
            dataset_delete.delay(ids)
            modeladmin.message_user(
                request,
                _(
                    "System is currently deleting %(count)d "
                    "%(items)s in the background."
                )
                % {"count": n, "items": model_ngettext(modeladmin.opts, n)},
                messages.SUCCESS,
            )
        # Return None to display the change list page again.
        return None

    objects_name = model_ngettext(queryset)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = {
        **modeladmin.admin_site.each_context(request),
        "title": title,
        "objects_name": str(objects_name),
        "deletable_objects": [deletable_objects],
        "model_count": dict(model_count).items(),
        "queryset": queryset,
        "perms_lacking": perms_needed,
        "protected": protected,
        "opts": opts,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "media": modeladmin.media,
    }

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(
        request,
        modeladmin.delete_selected_confirmation_template or
        [
            "admin/%s/%s/delete_selected_confirmation.html" %
            (app_label, opts.model_name),
            "admin/%s/delete_selected_confirmation.html" % app_label,
            "admin/delete_selected_confirmation.html",
        ],
        context,
    )
