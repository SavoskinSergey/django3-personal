from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache

from posts.models import Post, Group

User = get_user_model()


class PostUrlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.user2 = User.objects.create_user(username='Petya')
        cls.group = Group.objects.create(title='test1',
                                         slug='test-slug'
                                         )
        cls.post = Post.objects.create(
            text='Заголовок',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostUrlTests.user)

        self.authorized_client2 = Client()
        self.authorized_client2.force_login(PostUrlTests.user2)

    def tearDown(self):
        cache.clear()

    def test_homepage(self):
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_group_url_exists_at_desired_location(self):
        """Страница /group/ доступна любому пользователю."""
        response = self.guest_client.get(f'/group/{PostUrlTests.group.slug}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_url_exists_at_desired_location(self):
        """Страница /profile/ доступна любому пользователю."""
        response = self.guest_client.get('/profile/'
                                         f'{PostUrlTests.user.username}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_url_exists_at_desired_location(self):
        """Страница /post/ доступна любому пользователю."""
        response = self.guest_client.get(f'/posts/{PostUrlTests.post.pk}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_url_redirect_anonymous_on_admin_login(self):
        """Страница /edit/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get(f'/posts/{PostUrlTests.post.pk}/edit')
        self.assertEqual(response.status_code, HTTPStatus.MOVED_PERMANENTLY)

    def test_create_url_redirect_anonymous_on_admin_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_follow_url_redirect_anonymous_on_admin_login(self):
        """Страница /follow/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_follow_url_authorized_user(self):
        """Страница /follow/ откроет форму для
        пользователя авторизованного
        """
        response = self.authorized_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_post_url_authorized_user(self):
        """Страница /create/ откроет форму для
        пользователя авторизованного
        """
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_url_for_author(self):
        """Страница /edit/ вернет форму для автора,
        для стророннего пользователя редирект на пост
        """
        response = self.authorized_client.get(f'/posts/{PostUrlTests.post.pk}'
                                              '/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_client2.get(f'/posts/{PostUrlTests.post.pk}'
                                               '/edit/')
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': PostUrlTests.post.id}))

    def test_error_page(self):
        """Произвольная Страница вернет ошибку 404
        """
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/post_detail.html': '/posts/1/',
            'posts/profile.html': '/profile/StasBasov/',
            'posts/group_list.html': '/group/test-slug/',
            'posts/create_post.html': '/create/',
            'posts/follow.html': '/follow/'
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
