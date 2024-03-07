# discussable_app/views.py
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, BooleanField
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Discussion, Comment, Vote, UserContentPreference, VisibilityStatus, update_user_content_preference, \
    UserPreference

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import DiscussionSerializer, CommentSerializer, VoteSerializer
from django.contrib.contenttypes.models import ContentType

import logging

logger = logging.getLogger(__name__)


class DiscussionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        sort_by = request.query_params.get('sort', 'created_at')
        sort_options = {
            'popularity': '-wilson_score',
            'newest': '-created_at',
            'oldest': 'created_at',
        }
        sort_field = sort_options.get(sort_by, '-created_at')

        discussions = Discussion.objects.all().order_by(sort_field)
        # Fetch user content preferences for these discussions
        content_type = ContentType.objects.get_for_model(Discussion)
        user_preferences = UserContentPreference.objects.filter(
            user=user,
            content_type=content_type,
            object_id__in=discussions.values_list('id', flat=True)
        ).values_list('object_id', 'preference')
        user_pref_dict = {obj_id: pref for obj_id, pref in user_preferences}

        # Include the user preference in the serialization context
        context = {'request': request, 'user_preferences': user_pref_dict}
        serializer = DiscussionSerializer(discussions, many=True, context=context)
        return Response(serializer.data)


class DiscussionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, discussion_id, format=None):
        try:
            discussion = Discussion.objects.get(pk=discussion_id)
            comments = discussion.comments.all().order_by('created_at')

            # Fetch user content preferences for comments
            user = request.user
            content_type = ContentType.objects.get_for_model(Comment)
            user_preferences = UserContentPreference.objects.filter(
                user=user,
                content_type=content_type,
                object_id__in=comments.values_list('id', flat=True)
            ).values_list('object_id', 'preference')
            user_pref_dict = {obj_id: pref for obj_id, pref in user_preferences}

            # Include the user preference in the serialization context for comments
            context = {'request': request, 'user_preferences': user_pref_dict}
            discussion_serializer = DiscussionSerializer(discussion)
            comments_serializer = CommentSerializer(comments, many=True, context=context)

            return Response({
                'discussion': discussion_serializer.data,
                'comments': comments_serializer.data
            })
        except Discussion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

def hide_all_from_user(request, user_id):
    if request.method == 'POST':
        # Assuming the user is authenticated and you have user_id as the parameter
        target_user_comments = Comment.objects.filter(creator_id=user_id)
        for comment in target_user_comments:
            update_user_content_preference(request.user, comment, UserPreference.HIDE.value)
        return JsonResponse({'message': 'All comments from the user have been hidden.'})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_content_preference(request, votable_type, votable_id, preference):
    # Ensure the preference is valid
    if preference not in [pref.value for pref in UserPreference]:
        return Response({"error": "Invalid preference"}, status=400)

    # Dynamically get the model class based on votable_type
    model_class = ContentType.objects.get(model=votable_type).model_class()

    # Fetch the instance of the model (Discussion or Comment)
    content_object = get_object_or_404(model_class, id=votable_id)

    # Update or create the user's preference for this content object
    update_user_content_preference(request.user, content_object, preference)

    return Response({"message": f"Your preference for {votable_type} {votable_id} has been updated to {preference}."})


class VoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, votable_type, votable_id):
        user = request.user
        data = request.data
        content_type = ContentType.objects.get(model=votable_type)
        votable = get_object_or_404(content_type.model_class(), id=votable_id)

        vote, created = Vote.objects.update_or_create(
            user=user,
            content_type=content_type,
            object_id=votable_id,
            defaults={'vote': data['vote']}
        )

        # Update vote counts on the votable object after vote creation/update
        votable.get_vote_data()  # Recalculate and save updated vote counts

        return Response(VoteSerializer(vote).data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


class CreateCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, discussion_id):
        try:
            discussion = Discussion.objects.get(id=discussion_id)
        except Discussion.DoesNotExist:
            return Response({"error": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)

        # Include the discussion in the serializer's context
        serializer = CommentSerializer(data=request.data, context={'request': request, 'discussion': discussion})
        if serializer.is_valid():
            # No need to pass creator and discussion here since they're handled in the serializer's create method
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateDiscussionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        discussion_serializer = DiscussionSerializer(data=request.data, context={'request': request})

        if discussion_serializer.is_valid():
            discussion = discussion_serializer.save()

            comment_data = request.data.get('comment')
            print("Comment data received:", comment_data)
            if comment_data:
                # Ensure the comment is linked to the discussion and the creator is set correctly
                comment_data['discussion'] = discussion.id
                # Pass the 'discussion' object explicitly in the context for the comment serializer
                comment_serializer = CommentSerializer(data=comment_data, context={'request': request, 'discussion': discussion})
                if comment_serializer.is_valid():
                    comment_serializer.save()
                    return Response({
                        'discussion': discussion_serializer.data,
                        'comment': comment_serializer.data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response(comment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(discussion_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(discussion_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
