from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from django.shortcuts import redirect, render, get_object_or_404
from django.conf import settings

from .models import Post, Group, User, Comment, Follow
from .forms import PostForm, CommentForm


def get_page_context(queryset, request):
    paginator = Paginator(queryset, settings.COUNT_POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {'page_obj': page_obj,
            }


@cache_page(20)
def index(request):
    post_list = Post.objects.select_related('author', 'group').all()
    context = get_page_context(post_list, request)
    return render(request, 'posts/index.html', context)


@login_required(redirect_field_name='users:signup')
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user.username)
    else:
        context = {'form': form,
                   }
        return render(request, 'posts/create_post.html', context)


@login_required(redirect_field_name='users:signup')
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author == request.user:
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post
        )
        if form.is_valid():
            post = form.save()
            return redirect('posts:post_detail', post_id=post_id)
        else:
            context = {'form': form,
                       'is_edit': True,
                       }
            return render(request, 'posts/create_post.html', context)
    else:
        return redirect('posts:post_detail', post_id=post_id)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author').all()
    context = {'group': group,
               }
    context.update(get_page_context(post_list, request))

    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = Post.objects.select_related('author').filter(author=author)
    user = request.user
    if user.is_authenticated and user != author:
        following = Follow.objects.filter(
            user=user, author=author
        ).exists()
    else:
        following = False
    context = {'author': author,
               'following': following,
               }
    context.update(get_page_context(post_list, request))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comment_form = CommentForm()
    comments = Comment.objects.filter(post=post)
    context = {
        'post': post,
        'form': comment_form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = request.user
    post_list = Post.objects.filter(author__following__user=user)
    context = get_page_context(post_list, request)
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.get(user=user, author=author)
    follow.delete()
    return redirect('posts:profile', username=username)
