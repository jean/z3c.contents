##############################################################################
#
# Copyright (c) 2008 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
$Id:$
"""
__docformat__ = "reStructuredText"

import zope.interface
import zope.component
from zope.index.text.interfaces import ISearchableText
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.app.container.interfaces import IReadContainer
from zope.app.container.interfaces import IObjectFindFilter
from zope.app.container.find import SimpleIdFindFilter

import z3c.table.value
from z3c.contents import interfaces
from z3c.contents import browser


def _search_helper(id, object, container, id_filters, object_filters, result):
    # check id filters if we get a match then return immediately
    for id_filter in id_filters:
        if id_filter.matches(id):
            result.append(object)
            return

    # now check all object filters
    for object_filter in object_filters:
        if object_filter.matches(object):
            result.append(object)
            return

    # do we need to check sub containers?
    if not IReadContainer.providedBy(object):
        return

    container = object
    for id, object in container.items():
        _search_helper(id, object, container, id_filters, object_filters, result)


class SearchableTextFindFilter(object):
    """Filter objects on the ISearchableText adapters to the object."""

    zope.interface.implements(IObjectFindFilter)
    
    def __init__(self, terms):
        self.terms = terms
    
    def matches(self, object):
        """Check if one of the search terms is found in the searchable text
        interface.
        """
        adapter = ISearchableText(object, None)
        if adapter is None:
            return False
        searchable = adapter.getSearchableText().lower()
        for term in [t.lower() for t in self.terms]:
            if term in searchable:
                return True
        return False


class SearchableValues(z3c.table.value.ValuesMixin):
    """Values based on given search."""

    zope.component.adapts(IReadContainer, IBrowserRequest,
        interfaces.IContentsPage)

    @property
    def values(self):
        # search form is not enabled
        if not self.table.allowSearch:
            return self.context.values()

        # first setup and update search form
        searchForm = browser.ContentsSearchForm(self.context,
            self.request)
        searchForm.table = self.table
        searchForm.update()

        # expose the search form in the table for rendering
        self.table.searchForm = searchForm

        # not searching
        if not searchForm.searchterm:
            return self.context.values()

        # setup search filters
        criterias = searchForm.searchterm.strip().split(' ')
        if not criterias:
            # only empty strings given
            return self.context.values()

        result = []
        id_filters = [SimpleIdFindFilter(criterias)]
        object_filters = [SearchableTextFindFilter(criterias)]

        # query items
        for key, value in self.context.items():
            _search_helper(key, value, self.context, id_filters, object_filters,
                result)
        return result
