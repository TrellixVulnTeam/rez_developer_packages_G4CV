"""The main module which implements :ref:`rez_bisect run`'s work.

Attributes:
    _BisectSummary:
        The found, serialized result of the bisect. It includes information
        such as the last "good" index, the first, found "bad" index, and the
        diff between the two Rez :ref:`contexts`.

"""

from __future__ import division

import collections

from . import bisecter

_BisectSummary = collections.namedtuple("_BisectSummary", "last_good, first_bad, diff")


def _reduce_to_two_contexts(has_issue, contexts):
    """Convert ``contexts``, which may contain many, many:ref:`contexts`, into just 2.

    Args:
        has_issue (callable[rez.resolved_context.Context] -> bool):
            A function that returns True if the executable ``path`` fails.
            Otherwise, it returns False, indicating success. It takes a Rez
            :ref:`context` as input.
        contexts (list[rez.resolved_context.Context]):
            The :ref:`contexts` which could be 2-or-more to reduce down to into just 2.

    Returns:
        tuple[int, int]:
            The last index where ``has_issue`` returns False and the first
            index where ``has_issue`` returns True.

    """
    upper_bound = bisecter.bisect_right(has_issue, contexts)

    return upper_bound - 1, upper_bound


def bisect(has_issue, contexts):
    """Find the indices where ``has_issue`` returns True / False.

    Args:
        has_issue (callable[rez.resolved_context.Context] -> bool):
            A function that returns True if the executable ``path`` fails.
            Otherwise, it returns False, indicating success. It takes a Rez
            :ref:`context` as input.
        contexts (list[rez.resolved_context.Context]):
            The :ref:`contexts` which could be 2-or-more to reduce down to into just 2.

    Returns:
        _BisectSummary:
            The found, serialized result of the bisect.

    """
    count = len(contexts)

    if count > 2:
        last_good, first_bad = _reduce_to_two_contexts(has_issue, contexts)
    elif count == 2:
        last_good = 0
        first_bad = 1
    elif count == 1:
        raise NotImplementedError()  # TODO : Write here
    elif not count:
        raise NotImplementedError()  # TODO : Write here

    diff = contexts[last_good].get_resolve_diff(contexts[first_bad])

    return _BisectSummary(last_good=last_good, first_bad=first_bad, diff=diff)