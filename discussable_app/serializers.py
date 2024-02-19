# discussable_app/serializers.py

from rest_framework import serializers
from .models import Discussion, Comment, Vote, UserContentPreference, UserPreference


class DiscussionSerializer(serializers.ModelSerializer):
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_preference = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = '__all__'  # Adjust as needed

    def get_user_preference(self, obj):
        user_pref_dict = self.context.get('user_preferences', {})
        return user_pref_dict.get(obj.id, UserPreference.NONE.value)

    def create(self, validated_data):
        # Use 'self.context['request'].user' to get the current user
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user_preference = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ('creator', 'discussion')  # Assuming these should not be directly set by the user

    def get_user_preference(self, obj):
        user_pref_dict = self.context.get('user_preferences', {})
        return user_pref_dict.get(obj.id, UserPreference.NONE.value)

    def create(self, validated_data):
        user = self.context['request'].user
        discussion = self.context['discussion']

        validated_data['creator'] = user
        validated_data['discussion'] = discussion

        return super().create(validated_data)


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'user', 'content_type', 'object_id', 'vote', 'created_at']
        read_only_fields = ['user', 'content_type', 'object_id']
