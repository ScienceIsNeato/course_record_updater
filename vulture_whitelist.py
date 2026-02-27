# Vulture whitelist — false positives for imports used only in TYPE_CHECKING
# or string annotations that vulture cannot trace.
#
# See: https://github.com/jendrikseipp/vulture#ignoring-files

from werkzeug.datastructures import (  # noqa: F401 — used in institution_service.py type annotations
    FileStorage,
)

FileStorage  # tell vulture this symbol is used
