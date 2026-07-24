"""Room Type controller.

`code` must be unique PER PROPERTY, not globally (doctype_spec.md §3 naming
note). A Frappe `unique=1` field constraint is global, so the docname uses
`autoname: hash` and per-property uniqueness is enforced here in validate().
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import frappe
from frappe.core.doctype.file.utils import get_file_name
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

    duplicate_url = _avoid_public_name_collision(file_doc)
    if duplicate_url:
        row.image = duplicate_url
        return

    if not _attached_to_is_resolvable(file_doc):
        # Desk's uploader records attach-inside-child-table files against the
        # *parent* doc (attached_to_doctype="Room Type", attached_to_name=the
        # Room Type being edited) rather than the child row, with
        # attached_to_field left as the CHILD's own fieldname ("image") --
        # never a real column on the parent. File.save()'s own is_private
        # handling then either does a doomed `UPDATE <attached_to_doctype>
        # SET image = ...` (1054 "Unknown column 'image' in 'SET'", from a
        # real live crash saving a Room Type with a freshly-uploaded photo),
        # or -- if attached_to_field happens to be unset -- falls back to
        # loading the parent doc by name to guess the field, which throws
        # DoesNotExistError for a not-yet-saved parent (reproduced directly).
        # Clearing all three sidesteps both: harmless, since row.image is set
        # from the resulting file_url right after this returns regardless.
        file_doc.attached_to_doctype = None
        file_doc.attached_to_name = None
        file_doc.attached_to_field = None

    file_doc.is_private = 0
    file_doc.save(ignore_permissions=True)
    row.image = file_doc.file_url


def _avoid_public_name_collision(file_doc) -> str | None:
    """Sidestep `File.save()`'s `FileExistsError` when moving to public
    storage would collide with a same-named file already there (confirmed
    live: re-uploading a photo that had already been made public earlier
    crashed the move with "A file with same name ... already exists").

    Frappe's own upload-time dedup (`frappe.core.doctype.file.utils`) only
    checks for a name collision within the file's CURRENT privacy folder, so
    it can't catch a fresh private upload colliding with an existing public
    file -- that only surfaces later, at the move.

    Same content (compared by `content_hash`, the same signal
    `File.validate_duplicate_entry` already uses elsewhere in Frappe) means
    it's a genuine re-upload of the same photo -- returns the existing
    public file's URL to reuse instead of creating a redundant duplicate.
    Different content that just happens to share an original filename (e.g.
    two unrelated phone photos both named "IMG_0001.jpg") gets renamed to a
    free name first so the later move doesn't collide; safe to do directly
    here since it's a private-folder-only rename, not the private/public
    boundary the buggy path crosses.
    """
    base_name = file_doc.file_url.rsplit("/", 1)[-1]
    existing = frappe.db.get_value(
        "File",
        {"file_url": f"/files/{base_name}", "name": ["!=", file_doc.name]},
        ["name", "content_hash", "file_url"],
        as_dict=True,
    )
    if not existing:
        return None

    if not file_doc.content_hash:
        file_doc.generate_content_hash()

    if existing.content_hash and existing.content_hash == file_doc.content_hash:
        return existing.file_url

    new_name = get_file_name(base_name)
    old_path = Path(frappe.get_site_path("private", "files", base_name))
    new_path = Path(frappe.get_site_path("private", "files", new_name))
    shutil.move(old_path, new_path)
    file_doc.file_name = new_name
    file_doc.file_url = f"/private/files/{new_name}"
    file_doc.db_update()
    return None


def _attached_to_is_resolvable(file_doc) -> bool:
    if not file_doc.attached_to_doctype or not file_doc.attached_to_name:
        return False
    if file_doc.attached_to_field and not frappe.get_meta(file_doc.attached_to_doctype).has_field(
        file_doc.attached_to_field
    ):
        return False
    return bool(frappe.db.exists(file_doc.attached_to_doctype, file_doc.attached_to_name))
