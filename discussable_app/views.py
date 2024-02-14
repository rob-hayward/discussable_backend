# discussable_app/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Discussion, Comment, Vote

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import DiscussionSerializer, CommentSerializer, VoteSerializer
from django.contrib.contenttypes.models import ContentType

import logging

logger = logging.getLogger(__name__)


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


class DiscussionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, discussion_id, format=None):
        try:
            discussion = Discussion.objects.get(pk=discussion_id)
            comments = discussion.comments.all().order_by('-created_at')
            discussion_serializer = DiscussionSerializer(discussion)
            comments_serializer = CommentSerializer(comments, many=True)
            return Response({
                'discussion': discussion_serializer.data,
                'comments': comments_serializer.data
            })
        except Discussion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class DiscussionsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        sort_by = request.query_params.get('sort', 'created_at')

        # Map URL parameters to model fields for sorting
        sort_options = {
            'popularity': '-wilson_score',
            'newest': '-created_at',
            'oldest': 'created_at',
        }
        sort_field = sort_options.get(sort_by, '-created_at')

        discussions = Discussion.objects.all().order_by(sort_field)
        serializer = DiscussionSerializer(discussions, many=True)
        return Response(serializer.data)



