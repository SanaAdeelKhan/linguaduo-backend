from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Message, Group, Membership
from .translation import get_or_create_translation

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversations(request):
    user = request.user

    sent = Message.objects.filter(sender=user, group=None).values_list('recipient_id', flat=True)
    received = Message.objects.filter(recipient=user, group=None).values_list('sender_id', flat=True)
    dm_user_ids = set(list(sent) + list(received)) - {user.id}

    dm_list = []
    for uid in dm_user_ids:
        other = User.objects.filter(id=uid).first()
        if not other:
            continue
        last_msg = Message.objects.filter(
            group=None,
            sender__in=[user, other],
            recipient__in=[user, other]
        ).order_by('-created_at').first()

        dm_list.append({
            'type': 'dm',
            'user': {
                'id': other.id,
                'username': other.username,
                'is_online': other.is_online,
                'preferred_language': other.preferred_language,
            },
            'last_message': last_msg.original_text if last_msg else '',
            'last_message_at': last_msg.created_at.isoformat() if last_msg else None,
            'room_name': f'dm_{other.id}',
        })

    memberships = Membership.objects.filter(user=user).select_related('group')
    group_list = []
    for m in memberships:
        last_msg = Message.objects.filter(group=m.group).order_by('-created_at').first()
        group_list.append({
            'type': 'group',
            'group': {
                'id': m.group.id,
                'name': m.group.name,
                'description': m.group.description,
                'is_study_group': m.group.is_study_group,
            },
            'role': m.role,
            'last_message': last_msg.original_text if last_msg else '',
            'last_message_at': last_msg.created_at.isoformat() if last_msg else None,
            'room_name': f'group_{m.group.id}',
        })

    return Response({'dms': dm_list, 'groups': group_list})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.exclude(id=request.user.id)
    if query:
        users = users.filter(username__icontains=query)
    users = users[:20]
    return Response([
        {
            'id': u.id,
            'username': u.username,
            'preferred_language': u.preferred_language,
            'is_online': u.is_online,
        }
        for u in users
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_history(request, room_name):
    user = request.user
    page = int(request.GET.get('page', 1))
    page_size = 50
    offset = (page - 1) * page_size

    qs = Message.objects.filter(is_deleted=False).select_related('sender')

    if room_name.startswith('group_'):
        group_id = int(room_name.split('_')[1])
        qs = qs.filter(group_id=group_id)
    elif room_name.startswith('dm_'):
        other_id = int(room_name.split('_')[1])
        other = User.objects.filter(id=other_id).first()
        if not other:
            return Response({'error': 'User not found'}, status=404)
        qs = qs.filter(
            sender__in=[user, other],
            recipient__in=[user, other],
            group=None
        )

    total = qs.count()
    messages = qs.order_by('-created_at')[offset:offset + page_size]

    target_lang = user.preferred_language
    result = []
    for m in reversed(list(messages)):
        text = m.original_text
        if m.original_language != target_lang:
            try:
                text = get_or_create_translation(m, target_lang)
            except Exception:
                pass
        result.append({
            'id': m.id,
            'message': text,
            'original_message': m.original_text,
            'sender_id': m.sender_id,
            'sender_username': m.sender.username if m.sender else 'deleted',
            'message_type': m.message_type,
            'created_at': m.created_at.isoformat(),
        })

    return Response({
        'messages': result,
        'total': total,
        'page': page,
        'has_more': total > page * page_size,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group(request):
    name = request.data.get('name', '').strip()
    description = request.data.get('description', '')
    is_study_group = request.data.get('is_study_group', False)
    member_ids = request.data.get('member_ids', [])  # list of user IDs to invite

    if not name:
        return Response({'error': 'Group name is required.'}, status=400)

    group = Group.objects.create(
        name=name,
        description=description,
        is_study_group=is_study_group,
        created_by=request.user
    )
    # Creator is admin
    Membership.objects.create(user=request.user, group=group, role='admin')

    # Add invited members
    for uid in member_ids:
        if uid == request.user.id:
            continue
        member = User.objects.filter(id=uid).first()
        if member:
            Membership.objects.get_or_create(user=member, group=group, defaults={'role': 'member'})

    members = Membership.objects.filter(group=group).select_related('user')
    return Response({
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'is_study_group': group.is_study_group,
        'room_name': f'group_{group.id}',
        'members': [
            {'id': m.user.id, 'username': m.user.username, 'role': m.role}
            for m in members
        ],
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, group_id):
    group = Group.objects.filter(id=group_id).first()
    if not group:
        return Response({'error': 'Group not found.'}, status=404)

    membership, created = Membership.objects.get_or_create(
        user=request.user,
        group=group,
        defaults={'role': 'member'}
    )
    if not created:
        return Response({'message': 'Already a member.'})

    return Response({'message': f'Joined {group.name} successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_member(request, group_id):
    """Admin only — add a member to a group."""
    group = Group.objects.filter(id=group_id).first()
    if not group:
        return Response({'error': 'Group not found.'}, status=404)

    is_admin = Membership.objects.filter(user=request.user, group=group, role='admin').exists()
    if not is_admin:
        return Response({'error': 'Only admins can add members.'}, status=403)

    user_id = request.data.get('user_id')
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({'error': 'User not found.'}, status=404)

    membership, created = Membership.objects.get_or_create(
        user=user, group=group, defaults={'role': 'member'}
    )
    if not created:
        return Response({'message': 'User is already a member.'})

    return Response({'message': f'{user.username} added to {group.name}.'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_member(request, group_id, user_id):
    """Admin only — remove a member from a group."""
    group = Group.objects.filter(id=group_id).first()
    if not group:
        return Response({'error': 'Group not found.'}, status=404)

    is_admin = Membership.objects.filter(user=request.user, group=group, role='admin').exists()
    if not is_admin:
        return Response({'error': 'Only admins can remove members.'}, status=403)

    if user_id == request.user.id:
        return Response({'error': 'Admin cannot remove themselves.'}, status=400)

    deleted, _ = Membership.objects.filter(user_id=user_id, group=group).delete()
    if deleted:
        return Response({'message': 'Member removed.'})
    return Response({'error': 'Member not found.'}, status=404)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def rename_group(request, group_id):
    """Admin only — rename a group."""
    group = Group.objects.filter(id=group_id).first()
    if not group:
        return Response({'error': 'Group not found.'}, status=404)

    is_admin = Membership.objects.filter(user=request.user, group=group, role='admin').exists()
    if not is_admin:
        return Response({'error': 'Only admins can rename the group.'}, status=403)

    new_name = request.data.get('name', '').strip()
    if not new_name:
        return Response({'error': 'Name cannot be empty.'}, status=400)

    group.name = new_name
    group.save()
    return Response({'message': 'Group renamed.', 'name': group.name})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members(request, group_id):
    """List all members of a group."""
    group = Group.objects.filter(id=group_id).first()
    if not group:
        return Response({'error': 'Group not found.'}, status=404)

    members = Membership.objects.filter(group=group).select_related('user')
    return Response([
        {
            'id': m.user.id,
            'username': m.user.username,
            'preferred_language': m.user.preferred_language,
            'is_online': m.user.is_online,
            'role': m.role,
        }
        for m in members
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_list(request):
    groups = Group.objects.all().order_by('-created_at')[:20]
    return Response([
        {
            'id': g.id,
            'name': g.name,
            'description': g.description,
            'is_study_group': g.is_study_group,
            'member_count': g.memberships.count(),
            'room_name': f'group_{g.id}',
        }
        for g in groups
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_audio(request):
    """Upload voice message to Cloudinary and return URL."""
    import cloudinary
    import cloudinary.uploader
    from django.conf import settings

    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({'error': 'No audio file provided.'}, status=400)

    if audio_file.size > 10 * 1024 * 1024:
        return Response({'error': 'File too large. Max 10MB.'}, status=400)

    try:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        result = cloudinary.uploader.upload(
            audio_file,
            resource_type='video',
            folder='linguaduo/voice_messages',
        )
        return Response({
            'url': result['secure_url'],
            'duration': result.get('duration', 0),
            'public_id': result['public_id'],
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
