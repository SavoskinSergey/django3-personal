import shutil
import tempfile

from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django import forms

from posts.forms import PostForm
from posts.models import Post, Group, Follow, Comment

User = get_user_model()
COUNT_POSTS_FOR_PAGGINATOR = 27
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PagginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(title='test1',
                                         slug='test-slug'
                                         )
        for i in range(COUNT_POSTS_FOR_PAGGINATOR):
            cls.post = Post.objects.create(
                text='Заголовок',
                author=cls.user,
                group=cls.group,
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PagginatorTests.user)

    def tearDown(self):
        cache.clear()

    def test_first_page_containts_right_count_posts(self):
        """Проверка Пагинатора. Считаем количество постов на первой странице"""
        slug_var = PagginatorTests.group.slug
        user_var = PagginatorTests.user.username
        urls_names = (
            f"{reverse('posts:index')}",
            f"{reverse('posts:group_list', kwargs={'slug':slug_var })}",
            f"{reverse('posts:profile', kwargs={'username': user_var})}",
        )
        for test_url in urls_names:
            response = self.authorized_client.get(test_url)
            self.assertEqual(len(response.context['page_obj']),
                             settings.COUNT_POSTS_ON_PAGE)

    def test_last_page_containts_count_posts(self):
        """Проверка Пагинатора. Количество постов на последней странице"""
        slug_var = PagginatorTests.group.slug
        user_var = PagginatorTests.user.username
        urls_names = (
            f"{reverse('posts:index')}",
            f"{reverse('posts:group_list', kwargs={'slug': slug_var})}",
            f"{reverse('posts:profile', kwargs={'username':user_var})}",
        )
        for test_url in urls_names:
            page_number = (COUNT_POSTS_FOR_PAGGINATOR
                           // settings.COUNT_POSTS_ON_PAGE)
            count_post = (COUNT_POSTS_FOR_PAGGINATOR
                          - (settings.COUNT_POSTS_ON_PAGE * page_number))
            response = self.authorized_client.get(test_url
                                                  + '?page='
                                                  + str(page_number + 1))
            self.assertEqual(len(response.context['page_obj']), count_post)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='StasBasov')
        cls.user_follower = User.objects.create_user(username='StasIvanov')
        cls.group = Group.objects.create(title='test1',
                                         slug='test-slug'
                                         )
        cls.post = Post.objects.create(
            text='Заголовок',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewsTests.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(PostViewsTests.user_follower)

    def tearDown(self):
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон.Views"""
        post_var = PostViewsTests.post.id
        user_var = PostViewsTests.user.username
        slug_var = PostViewsTests.group.slug
        templates_url_names = {
            'posts/index.html': f"{reverse('posts:index')}",
            'posts/post_detail.html':
            f"{reverse('posts:post_detail', kwargs={'post_id': post_var})}",
            'posts/profile.html':
            f"{reverse('posts:profile', kwargs={'username': user_var})}",
            'posts/group_list.html':
            f"{reverse('posts:group_list', kwargs={'slug': slug_var })}",
            'posts/create_post.html': f"{reverse('posts:post_create')}",
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_pages_show_correct_context(self):
        """Проверяем контекст index, profile, group_list"""
        user_var = PostViewsTests.user.username
        group_var = PostViewsTests.group.slug
        Follow.objects.create(user=PostViewsTests.user_follower,
                              author=PostViewsTests.user)
        context_pages = (
            f"{reverse('posts:index')}",
            f"{reverse('posts:follow_index')}",
            f"{reverse('posts:profile', kwargs={'username': user_var})}",
            f"{reverse('posts:group_list', kwargs={'slug': group_var})}",
        )
        for page in context_pages:
            response = self.authorized_client2.get(page)
            first_object = response.context['page_obj'][0]
            post_group_0 = first_object.group.title
            post_text_0 = first_object.text
            post_pub_date_0 = first_object.pub_date
            post_author0 = first_object.author.username
            post_image = first_object.image
            self.assertEqual(post_group_0, PostViewsTests.post.group.title)
            self.assertEqual(post_text_0, PostViewsTests.post.text)
            self.assertEqual(post_pub_date_0, PostViewsTests.post.pub_date)
            self.assertEqual(post_author0, PostViewsTests.post.author.username)
            self.assertEqual(post_image, PostViewsTests.post.image)

    def test_author_page_show_correct_context(self):
        """Проверяем контекст автора для страницы автора"""
        user_var = PostViewsTests.user.username
        response = self.authorized_client.get(
            f"{reverse('posts:profile', kwargs={'username':user_var})}"
        )
        author = response.context['author']
        self.assertEqual(author, PostViewsTests.post.author)

    def test_group_page_show_correct_context(self):
        """Проверяем контекст group для страницы Группы"""
        slug_var = PostViewsTests.group.slug
        response = self.authorized_client.get(
            f"{reverse('posts:group_list', kwargs={'slug': slug_var })}"
        )
        group = response.context['group']
        self.assertEqual(group, PostViewsTests.post.group)

    def test_edit_page_show_correct_context(self):
        """Проверяем контекст edit для страницы редактирования"""
        # нет сил править f-строки дальше, что-то надо делать по другому...
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': Post.objects.first().id})
        )
        is_edit = response.context['is_edit']
        form = response.context['form']
        self.assertTrue(is_edit)
        self.assertIsInstance(form, PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_cache_index(self):
        """Главная страница кэшируется"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        deleted_post = Post.objects.get(id=self.post.id)
        deleted_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_post_detail_contain_comment_form(self):
        """Шаблон post_detail содержит форму создания комментария"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': PostViewsTests.post.id}))
        form = response.context.get('form')
        comment_fields = {
            'text': forms.fields.CharField,
        }
        for value, expected in comment_fields.items():
            with self.subTest(field=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_content_comments(self):
        """Шаблон post_detail содержит комментарии к посту"""
        self.comment = Comment.objects.create(
            post=PostViewsTests.post,
            author=PostViewsTests.user,
            text='Текст комментария',
        )
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': PostViewsTests.post.id}))
        comment = response.context.get('comments')[0]

        comment_post_0 = comment.post
        comment_text_0 = comment.text
        comment_pub_date_0 = comment.created
        comment_author0 = comment.author.username
        self.assertEqual(comment_post_0, self.comment.post)
        self.assertEqual(comment_text_0, self.comment.text)
        self.assertEqual(comment_pub_date_0, self.comment.created)
        self.assertEqual(comment_author0, PostViewsTests.post.author.username)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Follower')
        cls.user_author = User.objects.create_user(username='Author')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_profile_follow(self):
        """Авторизованный пользователь может подписаться на автора."""
        self.authorized_client.get(reverse(
            'posts:follow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertTrue(after_follower)

    def test_profile_unfollow(self):
        """Авторизованный пользователь может отписаться от автора."""
        Follow.objects.create(user=self.user, author=self.user_author)
        self.authorized_client.get(reverse(
            'posts:unfollow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertFalse(after_follower)

    def test_follow_index(self):
        """При создании автором новой записи, она появляется у подписчика."""
        Follow.objects.create(user=self.user, author=self.user_author)
        self.new_post = Post.objects.create(
            text='Тестовый пост',
            author=self.user_author
        )
        self.user_non_follower = User.objects.create_user(
            username='non_follower'
        )
        self.authorized_non_follower = Client()
        self.authorized_non_follower.force_login(self.user_non_follower)
        response_follower = self.authorized_client.get(reverse(
            'posts:follow_index'))
        self.assertTrue(self.new_post in response_follower.context['page_obj'])
        response_non_follower = self.authorized_non_follower.get(reverse(
            'posts:follow_index'
        ))
        self.assertFalse(self.new_post in response_non_follower.context[
            'page_obj']
        )
