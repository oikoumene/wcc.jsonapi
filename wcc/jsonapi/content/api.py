from five import grok
from zope.publisher.interfaces import IRequest
from Products.CMFCore.interfaces import ISiteRoot
import Acquisition
from zope.component.hooks import getSite
from zope.interface import Interface
from wcc.jsonapi.interfaces import ISignatureService, IJsonProvider
from wcc.activity.interfaces import IActivityRelation
from plone.uuid.interfaces import IUUID
from Acquisition import aq_parent

class Context(Acquisition.Implicit):
    pass

class ContentContext(Context):

    def __init__(self, obj):
        self.obj = obj

    def query(self):
        return IJsonProvider(self.obj).to_dict()


class AdapterContext(Context, grok.MultiAdapter):
    grok.baseclass()
    grok.provides(Interface)

    def __init__(self, parent, request):
        self.request = request

class APIRoot(AdapterContext):

    # http://site/api
    grok.adapts(ISiteRoot, IRequest)
    grok.name('api')


class V10(AdapterContext):

    # http://site/api/1.0/

    grok.adapts(APIRoot, IRequest)
    grok.name('1.0')

class ActivityCollection(AdapterContext):

    # http://site/api/1.0/activities

    grok.adapts(V10, IRequest)
    grok.name('activities')

    def query(self):
        brains = self.portal_catalog(portal_type='wcc.activity.activity')
        result = []
        for brain in brains:
            obj = brain.getObject()
            item = IJsonProvider(obj).to_dict()
            result.append(item)
        return result


    def __getattr__(self, uuid):
        site = getSite()
        brains = site.portal_catalog(UID=uuid)
        if not brains:
            raise AttributeError(uuid)
        return Activity(brains[0].getObject())

class Activity(ContentContext):
    pass

class ActivityNewsCollection(AdapterContext):
    grok.adapts(Activity, IRequest)
    grok.name('news')

    def query(self):
        activity_uuid = IUUID(aq_parent(self).obj)
        brains = self.portal_catalog(UID=activity_uuid)
        if not brains:
            return []

        rels = IActivityRelation(brains[0].getObject())

        limit = int(self.request.get('limit', 20))

        return [IJsonProvider(o).to_dict() for o in rels.related_news()[:limit]]

class NewsCollection(AdapterContext):

    # http://site/api/1.0/news

    grok.adapts(V10, IRequest)
    grok.name('news')

    def query(self):
        activity_uuid = self.request.get('activity', '')
        params = {
            'object_provides': IATNewsItem.__identifier__,
            'sort_on': 'Date',
            'sort_order': 'descending',
            'Language': 'all',
        }
        category = self.request.get('category', '')
        if category:
            params['Subject'] = category.strip()
        params['Language'] = self.request.get('language', 'all')
        objs = [
            brain.getObject() for brain in self.portal_catalog(
                **params)
        ]

        result = []

        limit = int(self.request.get('limit', 20))
        for obj in objs[:limit]:
            item = IJsonProvider(obj).to_dict()
            result.append(item)

        return result

