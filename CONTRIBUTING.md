# 🤝 Contributing to Fish Classification MLOps

Спасибо за интерес к проекту! Это образовательный проект, и мы приветствуем любой вклад.

## 💡 Как помочь проекту

- 🐛 Сообщить об ошибке
- 📝 Улучшить документацию
- ✨ Предложить новую функцию
- 🎨 Улучшить UI/UX
- 🧪 Добавить тесты
- 📊 Добавить новые дашборды мониторинга

## 📋 Процесс контрибуции

### 1. Fork проекта

```bash
# Форк через GitHub UI
# Затем клонируйте ваш форк
git clone https://github.com/YOUR_USERNAME/fish-classification-mlops.git
cd fish-classification-mlops
```

### 2. Создайте ветку

```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/your-bug-fix
```

Naming convention:
- `feature/` - новый функционал
- `fix/` - исправление ошибок
- `docs/` - изменения в документации
- `refactor/` - рефакторинг кода
- `test/` - добавление тестов

### 3. Внесите изменения

- Следуйте существующему стилю кода
- Добавьте комментарии где необходимо
- Обновите документацию если изменили API
- Добавьте тесты для новой функциональности

### 4. Коммит изменений

```bash
git add .
git commit -m "feat: add new feature description"
```

Используйте [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - новая функция
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `style:` - форматирование, пропущенные точки с запятой и т.д.
- `refactor:` - рефакторинг кода
- `test:` - добавление тестов
- `chore:` - обновление build tasks, package manager configs и т.д.

### 5. Push и создание Pull Request

```bash
git push origin feature/your-feature-name
```

Затем создайте Pull Request через GitHub UI.

## 📝 Guidelines

### Code Style

**Python:**
- Follow [PEP 8](https://pep8.org/)
- Use type hints где возможно
- Максимальная длина строки: 120 символов
- Используйте docstrings для функций и классов

**Terraform:**
- Используйте `terraform fmt` перед коммитом
- Добавляйте описания к переменным и outputs
- Группируйте ресурсы логически

**Kubernetes:**
- Используйте labels и annotations
- Следуйте [best practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- Документируйте resource requests/limits

### Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

Пример:
```
feat(api): add caching for predictions

Implement Redis caching to reduce inference latency
for repeated requests. Cache TTL set to 1 hour.

Closes #123
```

### Documentation

- Обновляйте README.md если изменили основной функционал
- Документируйте новые API endpoints
- Добавляйте примеры использования
- Включайте схемы/диаграммы для сложных изменений

### Testing

```bash
# Запустите тесты перед PR
make test

# Проверьте линтеры
make lint

# Проверьте форматирование
make format-check
```

## 🐛 Reporting Bugs

При сообщении об ошибке включите:

- **Описание:** Что пошло не так?
- **Воспроизведение:** Шаги для воспроизведения
- **Ожидаемое поведение:** Что должно было произойти?
- **Actual behavior:** Что произошло на самом деле?
- **Environment:**
  - OS
  - Python version
  - Terraform version
  - Kubernetes version
- **Logs:** Релевантные логи/error messages
- **Screenshots:** Если применимо

**Template:**

```markdown
## Описание
[Краткое описание проблемы]

## Шаги для воспроизведения
1. 
2. 
3. 

## Ожидаемое поведение
[Что должно происходить]

## Фактическое поведение
[Что происходит сейчас]

## Окружение
- OS: [e.g., macOS 13.0]
- Python: [e.g., 3.11]
- Terraform: [e.g., 1.5.0]

## Логи
```
[Вставьте логи здесь]
```

## Дополнительный контекст
[Любая дополнительная информация]
```

## ✨ Feature Requests

Для предложения новых функций:

1. Проверьте [Issues](https://github.com/denispukinov/fish-classification-mlops/issues) - возможно, уже предложено
2. Создайте новый Issue с label `enhancement`
3. Опишите:
   - Какую проблему решает функция
   - Предлагаемое решение
   - Альтернативы
   - Примеры использования

## 🎯 Priority Areas

Мы особенно приветствуем вклад в:

1. **Тестирование**
   - Unit tests для API
   - Integration tests для пайплайнов
   - E2E tests

2. **Документация**
   - Tutorials для новичков
   - Architecture deep-dives
   - Best practices guides

3. **Мониторинг**
   - Новые Grafana dashboards
   - Alerting rules
   - Performance optimization

4. **ML Features**
   - Новые архитектуры моделей
   - Data augmentation strategies
   - Hyperparameter tuning automation

5. **DevOps**
   - CI/CD improvements
   - Docker optimization
   - Security enhancements

## 📄 License

Внося вклад в проект, вы соглашаетесь что ваш код будет лицензирован под [MIT License](LICENSE).

## 🙏 Acknowledgments

Ваш вклад будет отмечен в:
- README.md (Contributors section)
- Release notes
- Commit history

## ❓ Questions?

Если у вас есть вопросы:
- Откройте [Discussion](https://github.com/denispukinov/fish-classification-mlops/discussions)
- Напишите в Issues с label `question`
- Свяжитесь с maintainer напрямую

---

**Спасибо за ваш вклад в проект! 🎉**

