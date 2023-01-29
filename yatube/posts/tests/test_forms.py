import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from posts.models import Post, Group, Comment

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(title='test1',
                                         slug='test-slug'
                                         )
        cls.group2 = Group.objects.create(title='test2',
                                          slug='test-slug2'
                                          )
        cls.post = Post.objects.create(
            text='Заголовок',
            author=cls.user,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post_guest_user(self):
        """Перенаправляем неавторизированного пользователя"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'TestAdd unsign user',
            'group': PostFormTests.group.pk,
        }
        response = self.guest_client.post(
            f'{reverse("posts:post_create")}',
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            f'{reverse("users:login")}'
            f'?users:signup='
            f'{reverse("posts:post_create")}'
        )

    def test_edit_post_guest_user(self):
        """При редактировании поста гостем не изменяется БД"""
        form_data = {
            'text': 'Update text',
            'group': PostFormTests.group.pk,
        }
        url_edit_post = reverse('posts:post_edit',
                                kwargs={'post_id': PostFormTests.post.id})
        response = self.guest_client.post(
            f'{url_edit_post}',
            data=form_data,
            follow=True
        )
        post_id_var = {"post_id": PostFormTests.post.id}
        self.assertRedirects(
            response,
            f'{reverse("users:login")}'
            f'?users:signup='
            f'{reverse("posts:post_edit", kwargs=post_id_var)}'
        )
        post = Post.objects.get(id=PostFormTests.post.id)
        self.assertEqual(post.text, PostFormTests.post.text)
        self.assertEqual(post.group, PostFormTests.post.group)
        self.assertEqual(post.author, PostFormTests.post.author)
        self.assertEqual(post.pub_date, PostFormTests.post.pub_date)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'TestAdd',
            'group': PostFormTests.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            f'{reverse("posts:post_create")}',
            data=form_data,
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        user_var = {"username": PostFormTests.user.username}
        self.assertRedirects(
            response,
            f'{reverse("posts:profile", kwargs=user_var)}'
        )
        post = Post.objects.latest('pub_date')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.pk, form_data['group'])
        self.assertEqual(post.author, PostFormTests.user)
        self.assertEqual(post.image, 'posts/small.gif')

    def test_create_post_wo_group(self):
        """Валидная форма создает запись в Post. Без группы"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'TestAddwoGrroup',
        }
        response = self.authorized_client.post(
            f'{reverse("posts:post_create")}',
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        url_create_var = {'username': PostFormTests.user.username}
        self.assertRedirects(
            response,
            f'{reverse("posts:profile", kwargs=url_create_var)}'
        )
        post = Post.objects.last()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group, None)
        self.assertEqual(post.author, PostFormTests.user)

    def test_edit_post(self):
        """При редактировении поста изменения сохраняются в БД"""
        form_data = {
            'text': 'Update text',
            'group': PostFormTests.group.pk,
        }
        url_post_id_var = {'post_id': PostFormTests.post.id}
        self.authorized_client.post(
            f'{reverse("posts:post_edit", kwargs=url_post_id_var)}',
            data=form_data,
            follow=True
        )
        post = Post.objects.get(id=PostFormTests.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.pk, form_data['group'])
        self.assertEqual(post.author, PostFormTests.user)
        self.assertEqual(post.pub_date, PostFormTests.post.pub_date)

    def test_edit_group_post(self):
        """При редактировение группы поста изменения сохраняются в БД"""
        form_data = {
            'text': 'Test update',
            'group': PostFormTests.group2.pk,
        }
        url_post_id_var = {'post_id': PostFormTests.post.id}
        self.authorized_client.post(
            f'{reverse("posts:post_edit",kwargs=url_post_id_var)}',
            data=form_data,
            follow=True
        )
        post = Post.objects.get(id=PostFormTests.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.pk, form_data['group'])
        self.assertEqual(post.author, PostFormTests.user)
        self.assertEqual(post.pub_date, PostFormTests.post.pub_date)


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='StasBasov')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_comment(self):
        """Валидная форма создает комментарий к посту."""
        form_data = {
            'text': 'текст комментария',
        }
        comments_count = Comment.objects.count()
        url_post_id_var = {'post_id': self.post.id}
        response = self.authorized_client.post(
            f'{reverse("posts:add_comment", kwargs=url_post_id_var)}',
            data=form_data,
        )
        last_comment_in_database = Comment.objects.latest('created')
        self.assertRedirects(
            response,
            f'{reverse("posts:post_detail", kwargs=url_post_id_var)}'
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(last_comment_in_database.text, form_data['text'])
        self.assertEqual(
            last_comment_in_database.author,
            CommentCreateFormTests.author
        )
        self.assertEqual(
            last_comment_in_database.post.id,
            CommentCreateFormTests.post.id
        )

    def test_comment_guest_user(self):
        """При добавление коммента гостем не изменяется БД"""
        form_data = {
            'text': 'Update text',
        }
        comments_count = Comment.objects.count()
        url_post_id_var = {'post_id': self.post.id}
        response = self.guest_client.post(
            f'{reverse("posts:add_comment", kwargs=url_post_id_var)}',
            data=form_data,
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            f'{reverse("users:login")}'
            f'?next='
            f'{reverse("posts:post_detail", kwargs=url_post_id_var)}comment/'
        )
