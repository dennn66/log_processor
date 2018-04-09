from django.contrib import admin

# Register your models here.
from .models import  City, Collector, Source, Settings, Parser, RadiusAttributeValue, RadiusAttributeType, Dim, Counter, Index, TrafficType, TrafficSummary, UserRequest

admin.site.register(City)
admin.site.register(Collector)
admin.site.register(Source)
admin.site.register(Settings)
admin.site.register(Parser)
admin.site.register(RadiusAttributeType)
admin.site.register(RadiusAttributeValue)
admin.site.register(Dim)
admin.site.register(Counter)
admin.site.register(Index)
admin.site.register(TrafficType)
admin.site.register(TrafficSummary)
admin.site.register(UserRequest)

