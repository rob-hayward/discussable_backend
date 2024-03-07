from django.urls import path
from .views import (
    CreateDiscussionView,
    DiscussionDetailView,
    DiscussionsListView,
    CreateCommentView,
    VoteView,
    update_content_preference,
    hide_all_from_user,
    show_all_from_user,
)

urlpatterns = [
    path('discussions/create/', CreateDiscussionView.as_view(), name='create-discussion'),
    path('discussions/<int:discussion_id>/comments/create/', CreateCommentView.as_view(), name='create-comment'),
    path('discussions/<int:discussion_id>/', DiscussionDetailView.as_view(), name='discussion-detail'),
    path('discussions/', DiscussionsListView.as_view(), name='discussions-list'),
    path('vote/<str:votable_type>/<int:votable_id>/', VoteView.as_view(), name='vote'),
    path('preferences/<str:votable_type>/<int:votable_id>/<str:preference>/', update_content_preference, name='update-content-preference'),
    path('hide-all-from-user/<int:user_id>/', hide_all_from_user, name='hide-all-from-user'),
    path('show-all-from-user/<int:user_id>/', show_all_from_user, name='show_all_from_user'),
]
