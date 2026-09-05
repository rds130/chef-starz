import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.posts.models import PostModel
from django.db.models import Count, ExpressionWrapper, FloatField, F
from django.db.models.functions import ExtractDay, Now

qs = PostModel.objects.annotate(
    engagement=Count('likes', distinct=True) + Count('comments', distinct=True),
    age_in_days=ExtractDay(Now() - F('created_at'))
).annotate(
    ranking_score=ExpressionWrapper(
        F('engagement') / (F('age_in_days') + 1.0),
        output_field=FloatField()
    )
).order_by('-ranking_score', '-created_at')

print("SQL:", str(qs.query))
print("First post:", qs.first())
