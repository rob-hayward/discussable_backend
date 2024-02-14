# discussable_app/urls.py
from django.urls import path
from .views import CreateDiscussionView, DiscussionDetailView, DiscussionsListView, CreateCommentView, VoteView

urlpatterns = [
    path('discussions/create/', CreateDiscussionView.as_view(), name='create-discussion'),
    path('discussions/<int:discussion_id>/comments/create/', CreateCommentView.as_view(), name='create-comment'),
    path('discussions/<int:discussion_id>/', DiscussionDetailView.as_view(), name='discussion-detail'),
    path('discussions/', DiscussionsListView.as_view(), name='discussions-list'),
    path('vote/<str:votable_type>/<int:votable_id>/', VoteView.as_view(), name='vote'),
]
