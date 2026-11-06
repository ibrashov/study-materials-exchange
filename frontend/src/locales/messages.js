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
    footer: 'Study Materials Exchange · University project · Week 10', language: 'Language',
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
    footer: 'Обмен учебными материалами · Учебный проект · Неделя 10', language: 'Язык',
  },
};
export function errorKey(error, context = '') {
  if (error.status === 409) return 'duplicate';
  if (error.status === 401) return context === 'login' ? 'invalidLogin' : 'loginRequired';
  if (error.status === 403) return 'denied';
  if (error.status === 422) return 'invalid';
  if (error.status === 413 || error.status === 415) return 'badFile';
  if (error.status === 503) return 'unavailable';
  return error instanceof TypeError ? 'network' : 'failed';
}
