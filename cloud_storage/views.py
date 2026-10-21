import functools
import posixpath
from urllib.parse import urlencode

from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from dropbox import DropboxOAuth2FlowNoRedirect, files
from dropbox.exceptions import ApiError, AuthError

from .client import app_key, env_configured, get_client
from .models import DropboxCredential

CHUNK_SIZE = 8 * 1024 * 1024
# files_upload принимает до 150 МБ, файлы больше грузим сессией по частям
SIMPLE_UPLOAD_LIMIT = 140 * 1024 * 1024

ERROR_TEXTS = [
    ('not_found', 'файл или папка не найдены'),
    ('conflict', 'объект с таким именем уже существует'),
    ('insufficient_space', 'недостаточно места в хранилище'),
    ('malformed_path', 'некорректный путь'),
    ('disallowed_name', 'недопустимое имя'),
    ('cant_move_folder_into_itself', 'нельзя переместить папку саму в себя'),
    ('duplicated_or_nested_paths', 'исходный и целевой путь совпадают'),
    ('too_many_files', 'слишком много файлов'),
    ('email_not_verified', 'подтвердите e-mail в Dropbox, чтобы создавать ссылки'),
    ('shared_link_not_found', 'ссылка не найдена'),
    ('access_denied', 'доступ запрещён'),
]


def describe_error(error):
    text = str(getattr(error, 'error', error))
    for key, message in ERROR_TEXTS:
        if key in text:
            return message
    return getattr(error, 'user_message_text', None) or text


def norm_path(path):
    """Путь в формате Dropbox: корень — '', остальное — '/a/b'."""
    path = (path or '').strip().replace('\\', '/')
    if path in ('', '/'):
        return ''
    return '/' + path.strip('/')


def parent_of(path):
    parent = posixpath.dirname(norm_path(path))
    return '' if parent == '/' else parent


def browse_url(path=''):
    url = reverse('cloud_storage:browse')
    return f'{url}?{urlencode({"path": path})}' if path else url


def metadata_url(path):
    return f'{reverse("cloud_storage:metadata")}?{urlencode({"path": path})}'


def go_back(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(fallback)


def dropbox_view(view):
    """Передаёт во view клиент Dropbox и превращает ошибки API в сообщения."""
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        dbx = get_client()
        if dbx is None:
            return redirect('cloud_storage:connect')
        try:
            return view(request, dbx, *args, **kwargs)
        except AuthError as e:
            if e.error.is_missing_scope():
                scope = e.error.get_missing_scope().required_scope
                messages.error(request, f'У приложения Dropbox нет разрешения «{scope}». '
                                        'Включите его на вкладке Permissions и подключите аккаунт заново.')
            else:
                messages.error(request, 'Токен Dropbox недействителен — подключите аккаунт заново.')
            return redirect('cloud_storage:connect')
        except ApiError as e:
            if request.method == 'POST':
                messages.error(request, f'Ошибка Dropbox: {describe_error(e)}')
                return go_back(request, browse_url(parent_of(request.POST.get('path'))))
            return render(request, 'cloud_storage/error.html', {
                'error': describe_error(e),
                'page_title': 'Dropbox',
            })
    return wrapper


def entry_info(md):
    return {
        'name': md.name,
        'path': md.path_display,
        'parent': parent_of(md.path_display),
        'is_folder': isinstance(md, files.FolderMetadata),
        'size': getattr(md, 'size', None),
        'modified': getattr(md, 'server_modified', None),
    }


def breadcrumbs(path):
    crumbs = [{'name': 'Dropbox', 'path': ''}]
    current = ''
    for part in [p for p in path.split('/') if p]:
        current += '/' + part
        crumbs.append({'name': part, 'path': current})
    return crumbs


def space_usage(dbx):
    usage = dbx.users_get_space_usage()
    allocation = usage.allocation
    if allocation.is_individual():
        allocated = allocation.get_individual().allocated
    elif allocation.is_team():
        allocated = allocation.get_team().allocated
    else:
        allocated = 0
    return {
        'used': usage.used,
        'allocated': allocated,
        'free': max(allocated - usage.used, 0),
        'percent': round(usage.used * 100 / allocated, 1) if allocated else 0,
    }


def list_folders(dbx):
    """Все папки аккаунта — для выбора, куда перемещать/копировать."""
    result = dbx.files_list_folder('', recursive=True)
    entries = list(result.entries)
    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        entries += result.entries
    return [''] + sorted(e.path_display for e in entries if isinstance(e, files.FolderMetadata))


# ---------- Просмотр ----------

@dropbox_view
def browse(request, dbx):
    path = norm_path(request.GET.get('path'))
    result = dbx.files_list_folder(path)
    entries = list(result.entries)
    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        entries += result.entries
    entries = sorted((entry_info(e) for e in entries), key=lambda e: (not e['is_folder'], e['name'].lower()))

    account = dbx.users_get_current_account()
    return render(request, 'cloud_storage/browse.html', {
        'page_title': 'Dropbox',
        'path': path,
        'crumbs': breadcrumbs(path),
        'entries': entries,
        'account': account,
        'space': space_usage(dbx),
    })


@dropbox_view
def account(request, dbx):
    acc = dbx.users_get_current_account()
    return render(request, 'cloud_storage/account.html', {
        'page_title': 'Dropbox',
        'acc': acc,
        'account_type': acc.account_type._tag,
        'space': space_usage(dbx),
        'credential': DropboxCredential.objects.first(),
    })


@dropbox_view
def metadata(request, dbx):
    path = norm_path(request.GET.get('path'))
    if not path:
        return redirect('cloud_storage:account')
    md = dbx.files_get_metadata(path)
    info = entry_info(md)

    details = [('ID', md.id), ('Имя', md.name), ('Путь', md.path_display)]
    if info['is_folder']:
        result = dbx.files_list_folder(path)
        count = len(result.entries)
        details.append(('Элементов внутри (1-й уровень)', f'{count}+' if result.has_more else count))
    else:
        details += [
            ('Размер, байт', md.size),
            ('Изменён на клиенте', md.client_modified),
            ('Изменён на сервере', md.server_modified),
            ('Ревизия', md.rev),
            ('Content hash', md.content_hash),
            ('Можно скачать', 'да' if md.is_downloadable else 'нет'),
        ]
    if md.sharing_info:
        details.append(('Общая папка/файл', 'да'))

    links = dbx.sharing_list_shared_links(path=path, direct_only=True).links
    return render(request, 'cloud_storage/metadata.html', {
        'page_title': 'Dropbox',
        'item': info,
        'details': details,
        'links': links,
        'crumbs': breadcrumbs(path),
        'folders': list_folders(dbx),
    })


@dropbox_view
def download(request, dbx):
    path = norm_path(request.GET.get('path'))
    md = dbx.files_get_metadata(path)
    if isinstance(md, files.FolderMetadata):
        _, response = dbx.files_download_zip(path)
        filename = f'{md.name}.zip'
        content_type = 'application/zip'
    else:
        _, response = dbx.files_download(path)
        filename = md.name
        content_type = 'application/octet-stream'

    http_response = StreamingHttpResponse(response.iter_content(CHUNK_SIZE), content_type=content_type)
    http_response['Content-Disposition'] = content_disposition_header(True, filename)
    if not isinstance(md, files.FolderMetadata):
        http_response['Content-Length'] = md.size
    return http_response


# ---------- Изменения ----------

@require_POST
@dropbox_view
def create_folder(request, dbx):
    parent = norm_path(request.POST.get('path'))
    name = request.POST.get('name', '').strip().strip('/')
    if not name:
        messages.error(request, 'Введите имя папки')
        return redirect(browse_url(parent))
    dbx.files_create_folder_v2(f'{parent}/{name}')
    messages.success(request, f'Папка «{name}» создана')
    return redirect(browse_url(parent))


@require_POST
@dropbox_view
def upload(request, dbx):
    parent = norm_path(request.POST.get('path'))
    uploaded = request.FILES.getlist('file')
    if not uploaded:
        messages.error(request, 'Выберите файл')
        return redirect(browse_url(parent))

    replace = request.POST.get('replace') == 'on'
    mode = files.WriteMode.overwrite if replace else files.WriteMode.add
    for f in uploaded:
        target = f'{parent}/{f.name}'
        try:
            upload_file(dbx, f, target, mode)
        except ApiError as e:
            if 'conflict' in str(e.error) and not replace:
                messages.error(request, f'«{f.name}» уже существует — отметьте «Заменить существующие» '
                                        'и загрузите снова')
                continue
            raise
        messages.success(request, f'«{f.name}» {"заменён" if replace else "загружен"}')
    return redirect(browse_url(parent))


def upload_file(dbx, f, target, mode):
    if f.size <= SIMPLE_UPLOAD_LIMIT:
        dbx.files_upload(f.read(), target, mode=mode, autorename=False)
        return
    chunks = f.chunks(CHUNK_SIZE)
    first = next(chunks)
    session = dbx.files_upload_session_start(first)
    cursor = files.UploadSessionCursor(session_id=session.session_id, offset=len(first))
    for chunk in chunks:
        dbx.files_upload_session_append_v2(chunk, cursor)
        cursor.offset += len(chunk)
    dbx.files_upload_session_finish(b'', cursor, files.CommitInfo(path=target, mode=mode, autorename=False))


def _transfer(request, dbx, action):
    source = norm_path(request.POST.get('path'))
    folder = norm_path(request.POST.get('to_folder'))
    name = request.POST.get('new_name', '').strip().strip('/') or posixpath.basename(source)
    target = f'{folder}/{name}'
    if action == 'move':
        result = dbx.files_move_v2(source, target, autorename=False)
        messages.success(request, f'Перемещено в {result.metadata.path_display}')
    else:
        result = dbx.files_copy_v2(source, target, autorename=False)
        messages.success(request, f'Скопировано в {result.metadata.path_display}')
    return redirect(metadata_url(result.metadata.path_display))


@require_POST
@dropbox_view
def move(request, dbx):
    return _transfer(request, dbx, 'move')


@require_POST
@dropbox_view
def copy(request, dbx):
    return _transfer(request, dbx, 'copy')


@require_POST
@dropbox_view
def delete(request, dbx):
    path = norm_path(request.POST.get('path'))
    if not path:
        messages.error(request, 'Корень хранилища удалить нельзя')
        return redirect(browse_url())
    md = dbx.files_delete_v2(path).metadata
    messages.success(request, f'«{md.name}» удалён(а)')
    return redirect(browse_url(parent_of(path)))


# ---------- Общий доступ ----------

@require_POST
@dropbox_view
def share(request, dbx):
    path = norm_path(request.POST.get('path'))
    try:
        link = dbx.sharing_create_shared_link_with_settings(path)
        messages.success(request, f'Ссылка создана: {link.url}')
    except ApiError as e:
        if not e.error.is_shared_link_already_exists():
            raise
        link = dbx.sharing_list_shared_links(path=path, direct_only=True).links[0]
        messages.info(request, f'Ссылка уже была: {link.url}')
    return go_back(request, metadata_url(path))


@dropbox_view
def shared(request, dbx):
    result = dbx.sharing_list_shared_links()
    links = list(result.links)
    while result.has_more:
        result = dbx.sharing_list_shared_links(cursor=result.cursor)
        links += result.links
    rows = [{
        'name': link.name,
        'path': link.path_lower,
        'url': link.url,
        'is_folder': link.__class__.__name__ == 'FolderLinkMetadata',
        'visibility': link.link_permissions.resolved_visibility._tag if link.link_permissions.resolved_visibility else '',
        'expires': link.expires,
    } for link in links]
    return render(request, 'cloud_storage/shared.html', {'page_title': 'Dropbox', 'links': rows})


@require_POST
@dropbox_view
def revoke(request, dbx):
    dbx.sharing_revoke_shared_link(request.POST['url'])
    messages.success(request, 'Доступ по ссылке отключён')
    return go_back(request, reverse('cloud_storage:shared'))


# ---------- Поиск ----------

@dropbox_view
def search(request, dbx):
    query = request.GET.get('q', '').strip()
    path = norm_path(request.GET.get('path'))
    by_content = request.GET.get('content') == 'on'
    results = []
    if query:
        options = files.SearchOptions(path=path or None, max_results=100, filename_only=not by_content)
        result = dbx.files_search_v2(query, options=options)
        for match in result.matches:
            if match.metadata.is_metadata():
                results.append(entry_info(match.metadata.get_metadata()))
    return render(request, 'cloud_storage/search.html', {
        'page_title': 'Dropbox',
        'query': query,
        'path': path,
        'by_content': by_content,
        'results': results,
    })


# ---------- Подключение аккаунта ----------

def _oauth_flow():
    return DropboxOAuth2FlowNoRedirect(app_key(), use_pkce=True, token_access_type='offline')


def connect(request):
    context = {
        'page_title': 'Dropbox',
        'app_key': app_key(),
        'env_configured': env_configured(),
        'credential': DropboxCredential.objects.first(),
    }
    if request.method == 'POST':
        flow = _oauth_flow()
        flow.code_verifier = request.session.get('dropbox_code_verifier', '')
        try:
            result = flow.finish(request.POST.get('code', '').strip())
        except Exception as e:  # SDK бросает разные исключения на неверный/просроченный код
            messages.error(request, f'Не удалось подключить аккаунт: {e}')
            return redirect('cloud_storage:connect')
        DropboxCredential.objects.all().delete()
        credential = DropboxCredential.objects.create(refresh_token=result.refresh_token)
        name = get_client().users_get_current_account().name.display_name
        credential.account_name = name
        credential.save()
        messages.success(request, f'Аккаунт Dropbox «{name}» подключён')
        return redirect('cloud_storage:browse')

    if context['app_key']:
        flow = _oauth_flow()
        context['authorize_url'] = flow.start()
        request.session['dropbox_code_verifier'] = flow.code_verifier
    return render(request, 'cloud_storage/connect.html', context)


@require_POST
def disconnect(request):
    DropboxCredential.objects.all().delete()
    messages.success(request, 'Аккаунт Dropbox отключён')
    return redirect('cloud_storage:connect')
