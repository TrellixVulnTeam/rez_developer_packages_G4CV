#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A Python class that is meant to parse and replace Python import statements."""

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseAdapter(object):
    """A Python class that is meant to parse and replace Python import statements."""

    def __init__(self, node, partial=False, namespaces=frozenset(), aliases=False):
        """Keep reference to a parso node (which defines some import).

        Args:
            node (object):
                The subclass of this class defines what type of parso
                node is expected.
            partial (bool, optional):
                If True, allow namespace replacement even if the user
                doesn't provide 100% of the namespace. If False, they must
                describe the entire import namespace before it can be
                renamed. Default is False.
            namespaces (set[str], optional):
                If `partial` is False, these dot-separated Python import
                namespaces are used to figure out if it's okay to replace an
                import or if any part of an import statement is missing. If
                no namespaces are given then `partial` must be set to True.
                Default: set().
            aliases (bool, optional):
                If True and replacing a namespace would cause Python
                statements to fail, auto-add an import alias to ensure
                backwards compatibility If False, don't add aliases. Default
                is False.

        Raises:
            ValueError: If `namespaces` is empty and `partial` is not True.

        """
        if not namespaces and not partial:
            raise ValueError(
                "Either set partial to True or define some Python namespaces."
            )

        super(BaseAdapter, self).__init__()

        self._aliases = aliases
        self._node = node
        self._partial = partial
        self._namespaces = namespaces

    @staticmethod
    @abc.abstractmethod
    def is_valid(node):
        """Check if `node` is compatible with this class.

        Args:
            node (:class:`parso.python.tree.PythonNode`):
                Some node that may or may not work with this class.

        Returns:
            bool: If `node` is valid.

        """
        return False  # pragma: no cover

    @staticmethod
    @abc.abstractmethod
    def _replace(
        node, old_parts, new_parts, namespaces=frozenset(), attributes=tuple()
    ):
        """Change `node` from `old_parts` to `new_parts`.

        Warning:
            This method directly modifies `node`.

        Args:
            node (:class:`parso.python.tree.ImportFrom`):
                A parso object that represents a Python import.
            old_parts (list[str]):
                The namespace that is expected to be all or part of the
                namespace that `node` defines.
            new_parts (list[str]):
                The namespace to replace `node` with. e.g. ["foo", "bar"].
            namespaces (iter[str]):
                Full attribute namespaces. e.g. `["module.attribute"]`
                These namespaces indicate what is "in-use" in the
                current graph. If an import statements imports multiple
                statements but at least one of its imports also is
                present in `namespaces` then the import is split into
                a separate import statement, to retain the original
                behavior.

        """
        raise NotImplementedError("Implement in subclasses.")  # pragma: no cover

    @staticmethod
    @abc.abstractmethod
    def _get_namespaces(node):
        """Find every dot-separated namespace that this instance encapsulates.

        Args:
            node (:class:`parso.python.tree.PythonNode`):
                Some node that represents an import.

        Returns:
            set[str]: Dot-separated namespaces such as {"foo.bar.bazz"}.

        """
        return set()  # pragma: no cover

    @staticmethod
    @abc.abstractmethod
    def get_import_type():
        """str: An identifier used to categorize instances of this class."""
        return ""

    @staticmethod
    @abc.abstractmethod
    def get_node_namespace_mappings():
        """Get each "real" namespace and its "aliased" counterpart.

        If the namespace has no alias then the key / value pair will
        both point to the "real" namespace.

        Returns:
            dict[str, str]: The unique, found for this import namespaces.

        """
        return dict()

    def get_node_namespaces(self):
        """Get all defined namespaces from the given adapter node.

        Args:
            adapter (:class:`BaseAdapter`):
                An object that defines at least one namespace of a Python import.

        Returns:
            set[str]: Dot-separated namespaces such as {"foo.bar.bazz"}.

        """
        return self._get_namespaces(self._node)

    def replace(self, old, new, namespaces=frozenset(), attributes=tuple()):
        """Change `node` from `old` to `new`.

        Warning:
            This method directly modifies `node`.

        Args:
            node (:class:`parso.python.tree.ImportFrom`):
                A parso object that represents a Python import.
            old (str):
                The namespace that is expected to be all or part of the
                namespace that `node` defines.
            new (str):
                The namespace to replace `node` with. e.g. "foo.bar".
            namespaces (iter[str]):
                Full attribute namespaces. e.g. `["module.attribute"]`
                These namespaces indicate what is "in-use" in the
                current graph. If an import statements imports multiple
                statements but at least one of its imports also is
                present in `namespaces` then the import is split into
                a separate import statement, to retain the original
                behavior.

        """
        self._replace(
            self._node,
            old.split("."),
            new.split("."),
            namespaces=namespaces,
            attributes=attributes,
        )

    def __contains__(self, namespace):
        """Check if this instance defines a given Python dot-separated namespace.

        A single instance may define 1-or-more namspaces. For example
        "import foo" only defines one namespace. But "import foo, bar"
        and "from foo import bar, thing, another" imports 2 and separate
        3 namspaces, respectively.

        Args:
            namespace (str): A Python dot-separated import string. Such as "foo.bar".

        Returns:
            bool: If this instance contains `namespace`.

        """
        namespaces = self._get_namespaces(self._node)

        if namespace in namespaces:
            # Check for a perfect match
            return True

        # Check for a partial match
        return any(
            namespace_
            for namespace_ in namespaces
            if namespace_.startswith(namespace + ".")
        )

    def __repr__(self):
        """str: Show how to reproduce this instance."""
        return (
            "{self.__class__.__name__}("
            "{self._node!r}, "
            "partial={self._partial!r}, "
            "namespaces={self._namespaces!r}, "
            "aliases={self._aliases!r}"
            ")".format(self=self)
        )
