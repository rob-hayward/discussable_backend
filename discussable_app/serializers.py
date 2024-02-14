# discussable_app/serializers.py

from rest_framework import serializers
from .models import Discussion, Comment, Vote


class DiscussionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discussion
        fields = '__all__'
        read_only_fields = ('creator',)  # Make creator read-only

    def create(self, validated_data):
        # Use 'self.context['request'].user' to get the current user
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ('creator', 'discussion')  # Assuming these should not be directly set by the user

    def create(self, validated_data):
        user = self.context['request'].user
        discussion = self.context['discussion']  # Access the discussion directly from context

        # Now correctly add 'creator' and 'discussion' to validated_data
        validated_data['creator'] = user
        validated_data['discussion'] = discussion

        return super().create(validated_data)


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'user', 'content_type', 'object_id', 'vote', 'created_at']
        read_only_fields = ['user', 'content_type', 'object_id']
