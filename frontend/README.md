# 🐟 Fish Classification - Web Frontend

Веб-интерфейс для классификации рыб с помощью нейросети.

## 🎨 Особенности

- **Красивый UI** с градиентами и анимациями
- **Drag & Drop** загрузка изображений
- **Real-time классификация** через API
- **Отображение уверенности** модели с цветовой индикацией
- **Информация о видах** рыб
- **Responsive design** для мобильных устройств
- **Proxy к API** через Nginx
- **Кэширование результатов** для ускорения

## 📦 Технологии

- **HTML5/CSS3** с Bootstrap 5
- **Vanilla JavaScript** (без фреймворков)
- **Nginx** как веб-сервер и reverse proxy
- **Docker** для контейнеризации
- **Kubernetes** для оркестрации

## 🚀 Быстрый старт

### Локальная разработка

```bash
# 1. Запустите API (должен быть доступен на http://localhost:8000)
cd ../api
python main.py

# 2. Откройте index.html в браузере или используйте простой HTTP сервер
python -m http.server 8080
```

Откройте http://localhost:8080

### Docker

```bash
# Сборка образа
docker build -t fish-classification-frontend .

# Запуск контейнера
docker run -d -p 80:80 fish-classification-frontend
```

Откройте http://localhost

### Kubernetes

```bash
# Автоматическое развёртывание
../scripts/deploy_frontend.sh

# Или вручную:
kubectl apply -f ../k8s/frontend/deployment.yaml

# Получить внешний IP
kubectl get svc frontend -n ml-inference
```

## 🏗️ Архитектура

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ HTTP
       ↓
┌──────────────┐
│   Nginx      │ (Port 80)
│              │
│  - Static    │ → index.html, app.js
│  - Proxy     │ → /api/* → inference-api:8000
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Inference    │ (Port 8000)
│     API      │
└──────────────┘
```

## 📝 API Endpoints

Frontend взаимодействует с Inference API через следующие endpoints:

### `POST /api/predict`
Классификация одного изображения

**Request:**
- `file`: изображение (multipart/form-data)

**Response:**
```json
{
  "species_id": 0,
  "species_name": "Perca Fluviatilis",
  "confidence": 0.95,
  "processing_time_ms": 234,
  "cached": false
}
```

### `GET /api/health`
Проверка здоровья API

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## 🎨 Кастомизация

### Изменение API URL

В production API URL настраивается автоматически через Nginx proxy.

Для локальной разработки можно переопределить:

```html
<script>
  window.API_BASE_URL = 'http://localhost:8000';
</script>
<script src="app.js"></script>
```

### Стилизация

Основные CSS переменные в `index.html`:

```css
:root {
    --primary-color: #0d6efd;
    --ocean-blue: #006994;
    --ocean-light: #4da6c7;
}
```

### Добавление новых видов рыб

Обновите объект `speciesInfo` в `app.js`:

```javascript
const speciesInfo = {
    "New Species": "Описание нового вида...",
    // ...
};
```

## 🔒 Безопасность

- **CORS** настроен через Nginx
- **Security headers** (X-Frame-Options, X-Content-Type-Options)
- **Rate limiting** можно добавить в Nginx
- **File size limit** 10MB в JavaScript
- **Content-Type validation** только изображения

## 📊 Мониторинг

### Логи Nginx

```bash
# В Docker
docker logs <container_id>

# В Kubernetes
kubectl logs -f -n ml-inference -l app=frontend
```

### Метрики

Метрики доступны через Prometheus (если настроен):
- HTTP requests
- Response time
- Error rate

## 🐛 Отладка

### Проверка здоровья API

```bash
curl http://frontend-service/api/health
```

### Проверка Nginx конфигурации

```bash
# В контейнере
docker exec <container_id> nginx -t

# В Kubernetes pod
kubectl exec -it <pod_name> -n ml-inference -- nginx -t
```

### Proxy не работает

1. Проверьте, что inference-api доступен:
```bash
kubectl get svc inference-api -n ml-inference
```

2. Проверьте логи Nginx на ошибки proxy

## 🚀 Production Checklist

- [ ] Настроен HTTPS/TLS
- [ ] Добавлен rate limiting
- [ ] Настроен monitoring (Prometheus)
- [ ] Добавлены health checks
- [ ] Настроен auto-scaling (HPA)
- [ ] Проверена безопасность (CSP headers)
- [ ] Оптимизированы изображения
- [ ] Добавлен CDN для статики (опционально)

## 📚 Документация

- [API Documentation](../api/README.md)
- [Deployment Guide](../README.md)
- [Architecture](../ARCHITECTURE.md)

## 🤝 Вклад

Для добавления новых функций:

1. Обновите `index.html` (UI)
2. Обновите `app.js` (логика)
3. Обновите `nginx.conf` (если нужен новый proxy)
4. Обновите `deployment.yaml` (если нужны новые env variables)
5. Пересоберите Docker образ

---

**Powered by** Kubernetes · Nginx · Bootstrap · Font Awesome

