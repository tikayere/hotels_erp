"""Room Type controller.

`code` must be unique PER PROPERTY, not globally (doctype_spec.md §3 naming
note). A Frappe `unique=1` field constraint is global, so the docname uses
`autoname: hash` and per-property uniqueness is enforced here in validate().
"""
from __future__ import annotations

import json

import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class RoomType(Document):
    def validate(self):
        self._validate_unique_code_per_property()
        self._sync_photos_from_gallery()
        self._sync_amenities_from_list()

    def _validate_unique_code_per_property(self):
        existing = frappe.db.get_value(
            "Room Type",
            {"property": self.property, "code": self.code, "name": ["!=", self.name]},
            "name",
        )
        if existing:
            frappe.throw(
                f"Room Type code '{self.code}' already exists for property '{self.property}'",
                frappe.DuplicateEntryError,
            )

    def _sync_photos_from_gallery(self):
        """`photos` (the JSON array of URLs the §4.4 API contract serializes
        -- see hotel_erp.api.serializers.serialize_room_type) is derived from
        the `photo_gallery` child table, not edited directly. Attach Image
        gives staff real drag-and-drop upload instead of hand-typed URLs; row
        order (idx) sets display order, so row 0 becomes the cover photo.

        Uploaded files must be public: the Aggregator/Portal/Web render these
        URLs cross-origin with no Frappe session, so a private (login-gated)
        file would silently 403 for every viewer but the uploader.
        """
        urls = []
        for row in self.photo_gallery:
            if not row.image:
                continue
            _make_file_public(row)
            urls.append(row.image if row.image.startswith(("http://", "https://")) else get_url(row.image))
        self.photos = json.dumps(urls)
        self.cover_image = self.photo_gallery[0].image if self.photo_gallery else None

    def _sync_amenities_from_list(self):
        """`amenities` (the JSON array of strings the §4.4 API contract
        serializes) is derived from the `amenity_list` child table, not
        edited directly -- same hand-typed-JSON usability problem `photos`
        had, same fix: one row per amenity instead of array syntax."""
        self.amenities = json.dumps([row.amenity for row in self.amenity_list if row.amenity])


def _make_file_public(row) -> None:
    """Flip a File from private to public, if needed.

    `is_private` isn't just a DB flag -- Frappe physically stores private and
    public files in different folders, and only `File.save()` moves the file
    and rewrites its own `file_url` to match (a raw `frappe.db.set_value`
    would desync the flag from where the file actually lives on disk, so it
    has to go through the real controller). `row.image` is reassigned to the
    File's resulting `file_url` since the move changes it (private files live
    under `/private/files/...`, public ones under `/files/...`).
    """
    file_name = frappe.db.get_value("File", {"file_url": row.image}, "name")
    if not file_name:
        return
    file_doc = frappe.get_doc("File", file_name)
    if not file_doc.is_private:
        return

    # Desk's uploader records attach-inside-child-table files against the
    # *parent* doc (attached_to_doctype="Room Type", attached_to_name=the
    # Room Type being edited), not the child row -- but attached_to_field is
    # still the CHILD's fieldname ("image"), which isn't a real column on the
    # parent. File.save()'s own is_private handling does an unconditional
    # `UPDATE <attached_to_doctype> SET <attached_to_field> = ...` write-back
    # and 1054s on that mismatch (confirmed live: "Unknown column 'image' in
    # 'SET'" saving a Room Type with a freshly-uploaded, not-yet-saved
    # photo). Harmless to clear here since we set row.image ourselves right
    # after -- Frappe's write-back would just be redoing that.
    if file_doc.attached_to_field and file_doc.attached_to_doctype:
        if not frappe.get_meta(file_doc.attached_to_doctype).has_field(file_doc.attached_to_field):
            file_doc.attached_to_field = None

    file_doc.is_private = 0
    file_doc.save(ignore_permissions=True)
    row.image = file_doc.file_url
