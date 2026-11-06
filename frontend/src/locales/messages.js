export const messages = {
  en: {
    home: 'Home', materials: 'Materials', registration: 'Registration', login: 'Login', upload: 'Upload', admin: 'Admin', logout: 'Log out',
    title: 'Study Materials Exchange', intro: 'Find and share course notes with other students.',
    fullName: 'Full name', email: 'Email', password: 'Password', confirm: 'Confirm password',
    register: 'Create account', signIn: 'Sign in', passwordHint: 'Use 12–128 characters.',
    required: 'Complete all required fields.', mismatch: 'Passwords do not match.',
    passwordLength: 'Password must contain 12–128 characters.', invalidEmail: 'Enter a valid email address.',
    duplicate: 'This email is already registered.', invalidLogin: 'Email or password is incorrect.',
    network: 'Cannot reach the server. Check your connection and try again.', invalid: 'Check the form fields and try again.',
    denied: 'Access denied. An administrator account is required.', loginRequired: 'Please sign in to continue.',
    unavailable: 'The service is unavailable. Check the backend and database.', failed: 'Request failed. Please try again.',
    loading: 'Loading…', saving: 'Submitting…', registered: 'Account created. You can now sign in.',
    search: 'Search', searchLabel: 'Search title, course or category', empty: 'No materials found.',
    materialTitle: 'Title', category: 'Category', course: 'Course', choose: 'Choose…', pdf: 'PDF file',
    fileHint: 'Readable, unencrypted PDF only. Maximum 50 MB (52,428,800 bytes).',
    badFile: 'Choose a nonempty PDF of at most 50 MB.', uploaded: 'Material uploaded.',
    download: 'Download PDF', downloadLogin: 'Sign in to download', studentRequired: 'Only student accounts can upload.',
    totalUsers: 'Registered users', totalMaterials: 'Uploaded materials', retry: 'Try again', previous: 'Previous', next: 'Next',
    footer: 'Study Materials Exchange · University project · Week 11', language: 'Language',
    locale: 'en-GB', skip: 'Skip to content', accountDisabled: 'This account has been blocked. Contact an administrator.',
    duplicateItem: 'This item already exists.', selfChange: 'You cannot change your own account here.',
    delete: 'Delete', 'materials.deleteConfirm': ({ title }) => `Delete "${title}"? This cannot be undone.`,
    'connection.title': 'Backend connection', 'connection.loading': 'Connecting to FastAPI…',
    'connection.connected': ({ service, status }) => `Connected · ${service} · ${status}`,
    'connection.failed': ({ details }) => `Cannot connect to the backend. Check that FastAPI is running and VITE_API_BASE_URL is correct. ${details}`,
    'connection.check': 'Check connection',
    'materials.eyebrow': 'STUDY MATERIALS', 'materials.title': 'Find study materials',
    'materials.intro': 'Browse and search notes, presentations and course resources shared by students.',
    'materials.searchFormLabel': 'Search study materials', 'materials.searchLabel': 'Search', 'materials.searchPlaceholder': 'Title, course or category',
    'materials.allCategories': 'All categories', 'materials.allCourses': 'All courses', 'materials.clear': 'Clear search',
    'materials.filtersFailed': 'Category and course filters are unavailable right now.', 'materials.retryFilters': 'Retry filters',
    'materials.loading': 'Loading materials…', 'materials.pagerLabel': 'Materials pages',
    'materials.uploaded': ({ date }) => `Uploaded ${date}`, 'materials.categoryFallback': ({ id }) => `Category #${id}`, 'materials.courseFallback': ({ id }) => `Course #${id}`,
    'materials.summary': ({ from, to, total }) => `Showing ${from}–${to} of ${total} ${total === 1 ? 'material' : 'materials'}`,
    'materials.empty': 'No materials have been uploaded yet.', 'materials.noMatch': 'No materials match your search.',
    'materials.pastEnd': ({ total }) => `No materials on this page. ${total} ${total === 1 ? 'material' : 'materials'} in total.`,
    'materials.error.unavailable.title': 'Materials aren’t available yet', 'materials.error.unavailable.message': 'This page is ready, but the server does not provide the materials service yet.',
    'materials.error.invalid.title': 'This search could not be applied', 'materials.error.server.title': 'The server could not load materials',
    'materials.error.timeout.title': 'The server took too long to respond', 'materials.error.timeout.message': 'Please try again.',
    'materials.error.connection.title': 'Materials could not be loaded', 'units.b': 'B', 'units.kb': 'KB', 'units.mb': 'MB',
    'admin.courses': 'Materials per course', 'admin.coursesHelp': 'Courses with the fewest materials come first, so you can invite students to contribute.',
    'admin.code': 'Code', 'admin.materialCount': 'Materials', 'admin.noMaterials': 'No materials yet',
    'admin.downloads': 'Most downloaded', 'admin.totalDownloads': 'Total downloads', 'admin.material': 'Material', 'admin.downloadCount': 'Downloads', 'admin.nothing': 'Nothing to show yet.',
    'admin.users': 'Users', 'admin.findUsers': 'Find users', 'admin.find': 'Find', 'admin.name': 'Name', 'admin.role': 'Role', 'admin.status': 'Status',
    'admin.active': 'Active', 'admin.blocked': 'Blocked', 'admin.block': 'Block', 'admin.unblock': 'Unblock', 'admin.roleStudent': 'Student', 'admin.roleAdmin': 'Administrator',
    'admin.taxonomy': 'Categories and courses', 'admin.categoryName': 'Category name', 'admin.addCategory': 'Add category',
    'admin.courseName': 'Course name', 'admin.courseCode': 'Course code', 'admin.addCourse': 'Add course', 'admin.added': 'Added.',
    'admin.storage': 'File storage', 'admin.storageOk': 'Storage is consistent', 'admin.storageBad': 'Needs attention',
    'admin.orphans': 'Files without a record', 'admin.partial': 'Incomplete uploads', 'admin.missing': 'Records without a file',
    'admin.storageHelp': 'Run scripts/reconcile_storage.py on the server to review these.',
  },
  ru: {
    home: 'Главная', materials: 'Материалы', registration: 'Регистрация', login: 'Вход', upload: 'Загрузка', admin: 'Администрирование', logout: 'Выйти',
    title: 'Обмен учебными материалами', intro: 'Находите конспекты и делитесь ими с другими студентами.',
    fullName: 'Полное имя', email: 'Электронная почта', password: 'Пароль', confirm: 'Повторите пароль',
    register: 'Создать аккаунт', signIn: 'Войти', passwordHint: 'Используйте от 12 до 128 символов.',
    required: 'Заполните все обязательные поля.', mismatch: 'Пароли не совпадают.',
    passwordLength: 'Пароль должен содержать от 12 до 128 символов.', invalidEmail: 'Введите корректный адрес почты.',
    duplicate: 'Этот адрес уже зарегистрирован.', invalidLogin: 'Неверная почта или пароль.',
    network: 'Нет связи с сервером. Проверьте подключение и повторите попытку.', invalid: 'Проверьте поля формы.',
    denied: 'Доступ запрещён. Требуется аккаунт администратора.', loginRequired: 'Сначала войдите в аккаунт.',
    unavailable: 'Сервис недоступен. Проверьте сервер и базу данных.', failed: 'Запрос не выполнен. Повторите попытку.',
    loading: 'Загрузка…', saving: 'Отправка…', registered: 'Аккаунт создан. Теперь можно войти.',
    search: 'Найти', searchLabel: 'Поиск по названию, курсу или категории', empty: 'Материалы не найдены.',
    materialTitle: 'Название', category: 'Категория', course: 'Курс', choose: 'Выберите…', pdf: 'PDF-файл',
    fileHint: 'Читаемый PDF без шифрования. Не более 50 МБ (52 428 800 байт).',
    badFile: 'Выберите непустой PDF размером до 50 МБ.', uploaded: 'Материал загружен.',
    download: 'Скачать PDF', downloadLogin: 'Войдите, чтобы скачать', studentRequired: 'Загружать материалы могут только студенты.',
    totalUsers: 'Пользователи', totalMaterials: 'Материалы', retry: 'Повторить', previous: 'Назад', next: 'Далее',
    footer: 'Обмен учебными материалами · Учебный проект · Неделя 11', language: 'Язык',
    locale: 'ru-RU', skip: 'Перейти к содержимому', accountDisabled: 'Этот аккаунт заблокирован. Обратитесь к администратору.',
    duplicateItem: 'Такая запись уже существует.', selfChange: 'Здесь нельзя менять собственный аккаунт.',
    delete: 'Удалить', 'materials.deleteConfirm': ({ title }) => `Удалить «${title}»? Это действие нельзя отменить.`,
    'connection.title': 'Подключение к серверу', 'connection.loading': 'Подключение к FastAPI…',
    'connection.connected': ({ service, status }) => `Подключено · ${service} · ${status}`,
    'connection.failed': ({ details }) => `Не удалось подключиться к серверу. Проверьте, что FastAPI запущен и VITE_API_BASE_URL указан верно. ${details}`,
    'connection.check': 'Проверить подключение',
    'materials.eyebrow': 'УЧЕБНЫЕ МАТЕРИАЛЫ', 'materials.title': 'Найдите учебные материалы',
    'materials.intro': 'Просматривайте и ищите конспекты, презентации и материалы курсов, которыми поделились студенты.',
    'materials.searchFormLabel': 'Поиск учебных материалов', 'materials.searchLabel': 'Поиск', 'materials.searchPlaceholder': 'Название, курс или категория',
    'materials.allCategories': 'Все категории', 'materials.allCourses': 'Все курсы', 'materials.clear': 'Сбросить поиск',
    'materials.filtersFailed': 'Фильтры по категории и курсу сейчас недоступны.', 'materials.retryFilters': 'Загрузить фильтры снова',
    'materials.loading': 'Загрузка материалов…', 'materials.pagerLabel': 'Страницы материалов',
    'materials.uploaded': ({ date }) => `Загружено ${date}`, 'materials.categoryFallback': ({ id }) => `Категория №${id}`, 'materials.courseFallback': ({ id }) => `Курс №${id}`,
    'materials.summary': ({ from, to, total }) => `Показано ${from}–${to} из ${total}`,
    'materials.empty': 'Материалы ещё не загружены.', 'materials.noMatch': 'По вашему запросу ничего не найдено.',
    'materials.pastEnd': ({ total }) => `На этой странице материалов нет. Всего: ${total}.`,
    'materials.error.unavailable.title': 'Материалы пока недоступны', 'materials.error.unavailable.message': 'Страница готова, но сервер пока не предоставляет сервис материалов.',
    'materials.error.invalid.title': 'Не удалось применить этот поиск', 'materials.error.server.title': 'Сервер не смог загрузить материалы',
    'materials.error.timeout.title': 'Сервер слишком долго не отвечает', 'materials.error.timeout.message': 'Попробуйте ещё раз.',
    'materials.error.connection.title': 'Не удалось загрузить материалы', 'units.b': 'Б', 'units.kb': 'КБ', 'units.mb': 'МБ',
    'admin.courses': 'Материалы по курсам', 'admin.coursesHelp': 'Курсы с наименьшим числом материалов идут первыми, чтобы вы могли пригласить студентов их пополнить.',
    'admin.code': 'Код', 'admin.materialCount': 'Материалы', 'admin.noMaterials': 'Материалов пока нет',
    'admin.downloads': 'Самые скачиваемые', 'admin.totalDownloads': 'Всего скачиваний', 'admin.material': 'Материал', 'admin.downloadCount': 'Скачивания', 'admin.nothing': 'Пока нечего показать.',
    'admin.users': 'Пользователи', 'admin.findUsers': 'Найти пользователей', 'admin.find': 'Найти', 'admin.name': 'Имя', 'admin.role': 'Роль', 'admin.status': 'Статус',
    'admin.active': 'Активен', 'admin.blocked': 'Заблокирован', 'admin.block': 'Заблокировать', 'admin.unblock': 'Разблокировать', 'admin.roleStudent': 'Студент', 'admin.roleAdmin': 'Администратор',
    'admin.taxonomy': 'Категории и курсы', 'admin.categoryName': 'Название категории', 'admin.addCategory': 'Добавить категорию',
    'admin.courseName': 'Название курса', 'admin.courseCode': 'Код курса', 'admin.addCourse': 'Добавить курс', 'admin.added': 'Добавлено.',
    'admin.storage': 'Файловое хранилище', 'admin.storageOk': 'Хранилище в порядке', 'admin.storageBad': 'Нужна проверка',
    'admin.orphans': 'Файлы без записи', 'admin.partial': 'Незавершённые загрузки', 'admin.missing': 'Записи без файла',
    'admin.storageHelp': 'Запустите на сервере scripts/reconcile_storage.py, чтобы разобраться с ними.',
  },
};
export const pickLanguage = language => (Object.hasOwn(messages, language ?? '') ? language : 'en');

export function createTranslator(language) {
  const dictionary = messages[pickLanguage(language)];
  return (key, values) => {
    const text = dictionary[key];
    if (text === undefined) return key;
    return typeof text === 'function' ? text(values) : text;
  };
}

export function errorKey(error, context = '') {
  if (error.status === 409) return { taxonomy: 'duplicateItem', user: 'selfChange' }[context] || 'duplicate';
  if (error.status === 401) return context === 'login' ? 'invalidLogin' : 'loginRequired';
  if (error.status === 403) return context === 'login' ? 'accountDisabled' : 'denied';
  if (error.status === 422) return 'invalid';
  if (error.status === 413 || error.status === 415) return 'badFile';
  if (error.status === 503) return 'unavailable';
  return error instanceof TypeError ? 'network' : 'failed';
}
