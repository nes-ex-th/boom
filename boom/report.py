# Copyright (C) 2017 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
#
# boom/report.py - Text reporting
#
# This file is part of the boom project.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
from boom import _find_minimum_sha_prefix, BOOM_DEBUG_REPORT
import logging
import sys

_log = logging.getLogger(__name__)
_log.set_debug_mask(BOOM_DEBUG_REPORT)

_log_debug = _log.debug
_log_debug_report = _log.debug_masked
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error

_default_columns = 80

#
# def data_fn(data):
#    :returntype: dtype
#

REP_NUM = "num"
REP_STR = "str"
REP_SHA = "sha"

_dtypes = [REP_NUM, REP_STR, REP_SHA]


def _default_sort_fn(v1, v2):
    return v1 > v2

_default_width = 8

ALIGN_LEFT = "left"
ALIGN_RIGHT = "right"

_align_types = [ALIGN_LEFT, ALIGN_RIGHT]

ASCENDING = "ascending"
DESCENDING = "descending"

STANDARD_QUOTE = "'"
STANDARD_PAIR = "="

MIN_SHA_WIDTH = 7

class BoomReportOpts(object):
    """BoomReportOpts()
        Options controlling the formatting and output of a boom report.
    """
    columns = 0
    headings = True
    buffered = True
    separator = None
    field_name_prefix = None
    unquoted = False
    aligned = True
    columns_as_rows = False
    report_file = None

    def __init__(self, columns=_default_columns, headings=True, buffered=True,
                 separator=" ", field_name_prefix="", unquoted=True,
                 aligned=True, report_file=sys.stdout):
        """__init__(self, columns, headings, buffered, report_file)
           -> BoomReportOpts

            Initialise a ``BoomReportOpts`` object to control output
            of a ``BoomReport``.

            :param columns: the number of columns to use for output.
            :param headings: a boolean indicating whether to output
                             column headings for this report.
            :param buffered: a boolean indicating whether to buffer
                             output from this report.
            :param report_file: a file to which output will be sent.
            :returns: a new ``BoomReportOpts`` object.
            :returntype: ``<class BoomReportOpts>``
        """
        self.columns = columns
        self.headings = headings
        self.buffered = buffered
        self.separator = separator
        self.field_name_prefix = field_name_prefix
        self.unquoted = unquoted
        self.aligned = aligned
        self.report_file = report_file


class BoomReportObjType(object):
    """BoomReportObjType()
        Class representing a type of objecct to be reported on.
        Instances of ``BoomReportObjType`` must specify an identifier,
        a description, and a data function that will return the correct
        type of object from a compound object containing data objects
        of different types. For reports that use only a single object
        type the ``data_fn`` member may be simply ``lambda x: x``.
    """

    objtype = -1
    desc = ""
    prefix = ""
    data_fn = None

    def __init__(self, objtype, desc, prefix, data_fn):
        """__init__(self, objtype, desc, prefix, data_fn)
            Initialise a new ``BoomReportObjType`` object with the
            specified ``objtype``, ``desc``, optional ``prefix`` and
            ``data_fn``. The ``objtype`` must be an integer power of two
            that is unique within a given report. The ``data_fn`` should
            accept an object as its only argument and return an object
            of the requested type.
        """
        if not objtype or objtype < 0:
            raise ValueError("BoomReportObjType objtype cannot be <= 0.")

        if not desc:
            raise ValueError("BoomReportObjType desc cannot be empty.")

        if not data_fn:
            raise ValueError("BoomReportObjType requires data_fn.")

        self.objtype = objtype
        self.desc = desc
        self.prefix = prefix
        self.data_fn = data_fn


class BoomFieldType(object):
    """BoomFieldType()
        The ``BoomFieldType`` class describes the properties of a field
        available in a ``BoomReport`` instance.
    """
    objtype = -1
    name = None
    head = None
    desc = None
    width = _default_width
    align = None
    dtype = None
    report_fn = None
    sort_fn = None

    def __init__(self, objtype, name, head, desc, width, dtype, report_fn,
                 align=None, sort_fn=None):
        if not objtype:
            raise ValueError("'objtype' must be non-zero")
        if not name:
            raise ValueError("'name' is required")
        self.objtype = objtype
        self.name = name
        self.head = head
        self.desc = desc

        if dtype not in _dtypes:
            raise ValueError("Invalid field dtype: %s " % dtype)

        if align and align not in _align_types:
            raise ValueError("Invalid field alignment: %s" % align)

        self.dtype = dtype
        self.report_fn = report_fn

        if not align:
            if dtype == REP_STR or dtype == REP_SHA:
                self.align = ALIGN_LEFT
            if dtype == REP_NUM:
                self.align = ALIGN_RIGHT
        else:
            self.align = align

        if width < 0:
            raise ValueError("Field width cannot be < 0")
        self.width = width if width else _default_width

        self.sort_fn = sort_fn


class BoomFieldProperties(object):
    field_num = None
    # sort_posn
    initial_width = 0
    width = 0
    objtype = None
    dtype = None
    align = None
    #
    # Field flags
    #
    hidden = False
    implicit = False
    sort_key = False
    sort_dir = None
    compact_one = False # used for implicit fields
    compacted = False
    sort_posn = None


class BoomField(object):
    """BoomField()
        A ``BoomField`` represents an instance of a ``BoomFieldType``
        including its associated data values.
    """
    #: reference to the containing BoomReport
    _report = None
    #: reference to the BoomFieldProperties describing this field
    _props = None
    #: The formatted string to be reported for this field.
    report_string = None
    #: The raw value of this field. Used for sorting.
    sort_value = None

    def __init__(self, report, props):
        self._report = report
        self._props = props

    def report_str(self, value):
        self.set_value(value, sort_value=value)

    def report_sha(self, value):
        self.set_value(value, sort_value=value)

    def report_num(self, value):
        self.set_value(str(value), sort_value=value)

    def set_value(self, report_string, sort_value=None):
        if report_string is None:
            raise ValueError("No value assigned to field.")
        self.report_string = report_string
        self.sort_value = sort_value if sort_value else report_string


class BoomRow(object):
    """BoomRow()
        A class representing a single data row making up a report.
    """
    #: the report that this BoomRow belongs to
    _report = None
    #: the list of report fields in display order
    _fields = None
    #: fields in sort order
    _sort_fields = None
    def __init__(self, report):
        self._report = report
        self._fields = []

    def add_field(self, field):
        self._fields.append(field)

def __none_returning_fn(obj):
    return None

# Implicit report fields and types

BR_SPECIAL = 0x80000000
_implicit_special_report_types = [
    BoomReportObjType(
        BR_SPECIAL, "Special", "special_", __none_returning_fn
    )
]

def __no_report_fn(f, d):
    return

_special_field_help_name = "help"

_implicit_special_report_fields = [
    BoomFieldType(
        BR_SPECIAL, _special_field_help_name, "Help", "Show help", 8,
        REP_STR, __no_report_fn)
]


# BoomReport class

class BoomReport(object):
    """BoomReport()
        A class representing a configurable text report with multiple
        caller-defined fields. An optional title may be provided and he
        ``fields`` argument must contain a list of ``BoomField`` objects
        describing the required report.

    """
    report_types = 0

    _fields = None
    _types = None
    _data = None
    _rows = None
    _keys_count = 0
    _field_properties = None
    _header_written = False
    _field_calc_needed = True
    _sort_required = False
    _already_reported = False

    # Implicit field support
    _implicit_types = _implicit_special_report_types
    _implicit_fields = _implicit_special_report_fields

    private = None
    opts = None

    def __help_requested(self):
        for fp in self._field_properties:
            if fp.implicit:
                name = self._implicit_fields[fp.field_num].name
                if name == _special_field_help_name:
                    return True
        return False

    def __get_longest_field_name_len(self, fields):
        max_len = 0
        for f in fields:
            cur_len = len(f.name)
            max_len = cur_len if cur_len > max_len else max_len
        for t in self._types:
            cur_len = len(t.prefix) + 3
            max_len = cur_len if cur_len > max_len else max_len
        return max_len

    def __do_display_fields(self, fields, display_field_types):
        name_len = self.__get_longest_field_name_len(fields)
        last_desc = ""
        banner = "-" * 79
        for f in fields:
            t = self.__find_type(f.objtype)
            if t:
                desc = t.desc
            else:
                desc = ""
            if desc != last_desc:
                if len(last_desc):
                    print(" ")
                desc_len = len(desc) + 7
                print("%s Fields" % desc)
                print("%*.*s" % (desc_len, desc_len, banner))
            print("  %-*s - %s%s%s%s" %
                  (name_len, f.name, f.desc,
                   " [" if display_field_types else "",
                   f.dtype if display_field_types else "",
                   "]" if display_field_types else ""))
            last_desc = desc

    def __display_fields(self, display_field_types):
        """__display_fields(self) -> None

            Output a list of fields for this ``BoomReport`` object.
        """
        self.__do_display_fields(self._fields, display_field_types)

    def __find_type(self, report_type):
        # FIXME implicit field handling

        for t in self._implicit_types:
            if t.objtype == report_type:
                return t
        for t in self._types:
            if t.objtype == report_type:
                return t

        raise ValueError("Unknown report object type: %d" % report_type)

    def __copy_field(self, field_num, implicit):
        fp = BoomFieldProperties()
        fp.field_num = field_num
        fp.width = fp.initial_width = self._fields[field_num].width
        fp.implicit = implicit
        fp.objtype = self.__find_type(self._fields[field_num].objtype)
        fp.dtype = self._fields[field_num].dtype
        fp.align = self._fields[field_num].align
        return fp

    def __add_field(self, field_num, implicit):
        fp = self.__copy_field(field_num, implicit)
        if fp.hidden:
            self._field_properties.insert(0, fp)
        else:
            self._field_properties.append(fp)

    def __get_field(self, field_name):
        """__get_field(field_name)
        """
        # FIXME implicit fields
        for field in self._implicit_fields:
            if field.name == field_name:
                return (self._implicit_fields.index(field), True)
        for field in self._fields:
            if field.name == field_name:
                return (self._fields.index(field), False)
        raise ValueError("No matching field name: %s" % field_name)

    def __field_match(self, field_name, type_only):
        try:
            (f, implicit) = self.__get_field(field_name)
            if (type_only):
                if implicit:
                    self.report_types |= self._implicit_fields[f].objtype
                else:
                    self.report_types |= self._fields[f].objtype
                return
            return self.__add_field(f, implicit)
        except ValueError as e:
            # FIXME handle '$PREFIX_all'
            # re-raise 'e' if it fails.
            raise e

    def __parse_fields(self, field_format, type_only):
        for word in field_format.split(','):
            # Allow consecutive commas
            if not word:
                continue
            try:
                self.__field_match(word, type_only)
            except ValueError as e:
                self.__display_fields(True)
                print("Unrecognised field: %s" % word)
                raise e

    def __add_sort_key(self, field_num, sort, implicit, type_only):
        fields = self._implicity_fields if implicit else self._fields
        found = None

        for fp in self._field_properties:
            if fp.implicit == implicit and fp.field_num == field_num:
                found = fp

        if not found:
            if type_only:
                self.report_types |= fields[field_num].objtype
                return
            else:
                found = self.__add_field(field_num, implicit)

        if found.sort_key:
            _log_info("Ignoring duplicate sort field: %s" %
                      fields[field_num].name)
        found.sort_key = True
        found.sort_dir = sort
        found.sort_posn = self._keys_count
        self._keys_count += 1

    def __key_match(self, key_name, type_only):
        sort_dir = None

        if not key_name:
            raise ValueError("Sort key name cannot be empty")

        if key_name.startswith('+'):
            sort_dir =  ASCENDING
            key_name = key_name[1:]
        elif key_name.startswith('-'):
            sort_dir = DESCENDING
            key_name = key_name[1:]
        else:
            sort_dir = ASCENDING

        for field in self._implicit_fields:
            fields = self._implicit_fields
            if field.name == key_name:
                return self.__add_sort_key(fields.index(field), sort_dir,
                                           True, type_only)
        for field in self._fields:
            fields = self._fields
            if field.name == key_name:
                return self.__add_sort_key(fields.index(field), sort_dir,
                                           False, type_only)

        raise ValueError("Unknown sort key name: %s" % key_name)

    def __parse_keys(self, keys, type_only):
        if not keys:
            return
        for word in keys.split(','):
            # Allow consecutive commas
            if not word:
                continue
            try:
                self.__key_match(word, type_only)
            except ValueError as e:
                self.__display_fields(True)
                print("Unrecognised field: %s" % word)
                raise e

    def __init__(self, types, fields, output_fields, opts,
                 sort_keys, private):
        """__init__(self, types, fields, output_fields, opts,
           sort_keys, private)
           -> ``BoomReport``

            Initialise a new ``BoomReport`` object with the specified fields
            and output control options.

            :param types: List of BoomReportObjType used in this report.
            :param fields: A list of ``BoomField`` field descriptions.
            :param output_fields: An optional list of output fields to
                                  be rendered by this report.
            :param opts: An instance of ``BoomReportOpts`` or None.
            :returns: A new report object.
            :returntype: ``BoomReport``.
        """

        self._fields = fields
        self._types = types
        self._private = private

        if opts.buffered:
            self._sort_required = True

        self.opts = opts if opts else BoomReportOpts()

        self._rows = []
        self._field_properties = []

        # set field_prefix from type

        # canonicalize_field_ids()

        if not output_fields:
            output_fields = ",".join([field.name for field in fields])

        # First pass: set up types
        self.__parse_fields(output_fields, 1)
        self.__parse_keys(sort_keys, 1)

        # Second pass: initialise fields
        self.__parse_fields(output_fields, 0)
        self.__parse_keys(sort_keys, 0)

        if self.__help_requested():
            self._already_reported = True
            self.__display_fields(display_field_types=True)
            print("")

    def __recalculate_sha_width(self):
        shas = {}
        props_map = {}
        for row in self._rows:
            for field in row._fields:
                if self._fields[field._props.field_num].dtype == REP_SHA:
                    # Use field_num as index to apply check across rows
                    num = field._props.field_num
                    if num not in shas:
                        shas[num] = set()
                        props_map[num] = field._props
                    shas[num].add(field.report_string)
        for num in shas.keys():
            min_prefix = max(MIN_SHA_WIDTH, props_map[num].width)
            props_map[num].width = _find_minimum_sha_prefix(shas[num], min_prefix)

    def __recalculate_fields(self):
        for row in self._rows:
            for field in row._fields:
                if self._sort_required and field._props.sort_key:
                    row._sort_fields[field._props.sort_posn] = field
                if self._fields[field._props.field_num].dtype == REP_SHA:
                    continue
                field_len = len(field.report_string)
                if field_len > field._props.width:
                    field._props.width = field_len

    def __report_headings(self):
        self._header_written = True
        if not self.opts.headings:
            return

        line = ""
        props = self._field_properties
        for fp in props:
            if fp.hidden:
                continue
            fields = self._fields
            heading = fields[fp.field_num].head
            headertuple = (fp.width, fp.width, heading)
            if self.opts.aligned:
                heading = "%-*.*s" % headertuple
            line += heading
            if props.index(fp) != (len(props) - 1):
                line += self.opts.separator
        self.opts.report_file.write(line + "\n")

    def __row_key_fn(self):
        def _row_cmp(row_a, row_b):
            for cnt in range(0, row_a._report._keys_count):
                sfa = row_a._sort_fields[cnt]
                sfb = row_b._sort_fields[cnt]
                if sfa._props.dtype == REP_NUM:
                    num_a = sfa.sort_value
                    num_b = sfb.sort_value
                    if num_a == num_b:
                        continue
                    if sfa._props.sort_dir == ASCENDING:
                        return 1 if num_a > num_b else -1
                    else:
                        return 1 if num_a < num_b else -1
                else:
                    stra = sfa.sort_value
                    strb = sfb.sort_value
                    if stra == strb:
                        continue
                    if sfa._props.sort_dir == ASCENDING:
                        return 1 if stra > strb else -1
                    else:
                        return 1 if stra < strb else -1
            return 0

        class __RowKey(object):
           def __init__(self, obj, *args):
               self.obj = obj
           def __lt__(self, other):
               return _row_cmp(self.obj, other.obj) < 0
           def __gt__(self, other):
               return _row_cmp(self.obj, other.obj) > 0
           def __eq__(self, other):
               return _row_cmp(self.obj, other.obj) == 0
           def __le__(self, other):
               return _row_cmp(self.obj, other.obj) <= 0
           def __ge__(self, other):
               return _row_cmp(self.obj, other.obj) >= 0
           def __ne__(self, other):
               return _row_cmp(self.obj, other.obj) != 0
        return __RowKey

    def _sort_rows(self):
        self._rows.sort(key=self.__row_key_fn())

    def report_object(self, obj):
        """report_object(self, data) -> None
            Add a row of data to this ``BoomReport``. The ``data``
            argument should be an object of the type understood by this
            report's fields. It will be passed in turn to each field to
            obtain data for the current row.

            :param data: the object to report on for this row.
        """
        if obj is None:
            raise ValueError("Cannot report NoneType object.")

        if self._already_reported:
            return

        row = BoomRow(self)
        fields = self._fields
        if self._sort_required:
            row._sort_fields = [-1] * self._keys_count
        for fp in self._field_properties:
            field = BoomField(self, fp)
            data = fp.objtype.data_fn(obj)

            if data is None:
                raise ValueError("No data assigned to field %s" %
                                 fields[fp.field_num].name)

            try:
                fields[fp.field_num].report_fn(field, data)
            except ValueError:
                raise ValueError("No value assigned to field %s" %
                                 fields[fp.field_num].name)
            row.add_field(field)
        self._rows.append(row)

        if not self.opts.buffered:
            return self.report_output()

    def _output_field(self, field):
        fields = self._fields
        prefix = self.opts.field_name_prefix
        quote = "" if self.opts.unquoted else STANDARD_QUOTE

        if prefix:
            field_name = fields[field._props.field_num].name
            prefix += "%s%s%s" % (field_name.upper(), STANDARD_PAIR,
                                  STANDARD_QUOTE)

        repstr = field.report_string
        width = field._props.width
        if self.opts.aligned:
            align = field._props.align
            if not align:
                if field._props.dtype == REP_NUM:
                    align = ALIGN_RIGHT
                else:
                    align = ALIGN_LEFT
            reptuple = (width, width, repstr)
            if align == ALIGN_LEFT:
                repstr = "%-*.*s" % reptuple
            else:
                repstr = "%*.*s" % reptuple

        suffix = quote
        return prefix + repstr + suffix

    def _output_as_rows(self):
        pass

    def _output_as_columns(self):
        if not self._header_written:
            self.__report_headings()
        for row in self._rows:
            do_field_delim = False
            line = ""
            for field in row._fields:
                if field._props.hidden:
                    continue
                if do_field_delim:
                    line += self.opts.separator
                else:
                    do_field_delim = True
                line += self._output_field(field)
            self.opts.report_file.write(line + "\n")

    def report_output(self):
        """output(self) -> int
            Output this report's data to the configured report file,
            using the configured output controls and fields.

            On success the number of rows output is returned. On
            error an exception is raised.

            :returns: the number of rows of output written.
            :returntype: ``int``
        """
        if self._already_reported:
            return
        if self._field_calc_needed:
            self.__recalculate_sha_width()
            self.__recalculate_fields()
        if self._sort_required:
            self._sort_rows()
        if self.opts.columns_as_rows:
            return self._output_as_rows()
        else:
            return self._output_as_columns()

__all__ = [
    # Module constants

    'REP_NUM', 'REP_STR', 'REP_SHA',
    'ALIGN_LEFT', 'ALIGN_RIGHT',
    'ASCENDING', 'DESCENDING',

    # Report objects
    'BoomReportOpts', 'BoomReportObjType', 'BoomField', 'BoomFieldType',
    'BoomFieldProperties', 'BoomReport'
]

# vim: set et ts=4 sw=4 :
