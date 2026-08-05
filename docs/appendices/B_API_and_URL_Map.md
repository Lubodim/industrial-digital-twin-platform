# API and URL Map

# Карта на URL адресите и API

## Въведение

Настоящият документ описва структурата на URL адресите и вътрешните API интерфейси на **Industrial Digital Twin Platform**.

Платформата използва архитектурата **Model – View – Template (MVT)** на Django. В настоящата версия не е реализиран публичен REST API. Всички операции се извършват чрез стандартните Django URL маршрути и вътрешните бизнес услуги.

Архитектурата позволява в бъдещи версии лесно добавяне на REST API без промени в бизнес логиката.

---

# Обща архитектура

```text
Browser
    │
    ▼
URL Dispatcher
    │
    ▼
Views
    │
    ▼
Services
    │
    ▼
Models
    │
    ▼
SQLite Database
```

---

# Основни URL групи

Платформата е разделена на няколко основни функционални области:

| Модул | URL Prefix |
|--------|------------|
| Authentication | `/accounts/` |
| Digital Twins | `/digital-twins/` |
| Materials | `/materials/` |
| Technologies | `/technologies/` |
| Experiments | `/experiments/` |
| Administration | `/admin/` |

---

# Authentication

Основни URL адреси

| URL | Описание |
|-----|----------|
| `/accounts/login/` | Вход |
| `/accounts/logout/` | Изход |
| `/accounts/profile/` | Потребителски профил |

---

# Digital Twins

Основни URL адреси

| URL | Описание |
|-----|----------|
| `/digital-twins/` | Библиотека |
| `/digital-twins/create/` | Нов цифров двойник |
| `/digital-twins/<id>/` | Детайли |
| `/digital-twins/<id>/update/` | Редакция |
| `/digital-twins/<id>/delete/` | Изтриване |
| `/digital-twins/<id>/activate/` | Активиране |
| `/digital-twins/<id>/deactivate/` | Деактивиране |

---

# Materials

| URL | Описание |
|-----|----------|
| `/materials/` | Списък |
| `/materials/create/` | Нов материал |
| `/materials/<id>/update/` | Редакция |
| `/materials/<id>/delete/` | Изтриване |

---

# Manufacturing Technologies

| URL | Описание |
|-----|----------|
| `/technologies/` | Списък |
| `/technologies/create/` | Нова технология |
| `/technologies/<id>/update/` | Редакция |
| `/technologies/<id>/delete/` | Изтриване |

---

# Engineering Experiments

| URL | Описание |
|-----|----------|
| `/experiments/` | Всички експерименти |
| `/experiments/create/` | Нов експеримент |
| `/experiments/<id>/` | Детайли |
| `/experiments/<id>/lock/` | Заключване |
| `/experiments/<id>/unlock/` | Отключване |
| `/experiments/<id>/research/` | Външен AI анализ |
| `/experiments/<id>/local-analysis/` | Локален AI анализ |
| `/experiments/<id>/create-derived/` | Производен цифров двойник |

---

# Engineering Chat

Основните операции се извършват чрез вътрешни заявки към:

- добавяне на съобщение;
- извличане на историята;
- визуализиране на разговора.

Чатът работи само при отключен експеримент.

---

# Engineering Proposals

Основните операции включват:

| Действие | Описание |
|-----------|----------|
| Преглед | Зареждане на предложенията |
| Approve | Одобряване |
| Reject | Отхвърляне |
| Translation | Смяна на езика |

---

# Translation

Използват се вътрешни заявки за:

- показване на английски текст;
- показване на български текст;
- автоматично зареждане на превода.

---

# File Management

Основни операции

| Действие | Описание |
|-----------|----------|
| Upload | Качване |
| Delete | Изтриване |
| Download | Изтегляне |
| Preview | Преглед |

Поддържат се:

- STL;
- STEP;
- PNG;
- PDF;
- DOCX.

---

# 3D Visualization

Визуализацията използва локално зареден STL файл.

Работният процес е:

```text
Browser
     │
     ▼
Three.js
     │
     ▼
STL Loader
     │
     ▼
3D Viewer
```

Не се използват външни API услуги.

---

# Administrative Interface

Стандартният административен панел е достъпен чрез:

```text
/admin/
```

Поддържат се всички административни операции върху:

- потребители;
- цифрови двойници;
- материали;
- технологии;
- експерименти;
- файлове;
- AuditLog.

---

# Вътрешни услуги

Основните бизнес услуги включват:

- DigitalTwinService;
- ExperimentService;
- EngineeringProposalService;
- TranslationService;
- AuditService;
- FileService.

Тези услуги реализират бизнес логиката независимо от потребителския интерфейс.

---

# Работа на заявките

Типичният поток на обработка е:

```text
Browser
    │
    ▼
URL
    │
    ▼
View
    │
    ▼
Service
    │
    ▼
Model
    │
    ▼
Database
```

---

# HTTP методи

Използват се стандартните HTTP методи.

| Метод | Предназначение |
|--------|----------------|
| GET | Зареждане на информация |
| POST | Създаване |
| POST | Редакция |
| POST | Изтриване |

Поради използването на HTML форми повечето операции се реализират чрез POST заявки.

---

# Защита

Всички защитени URL адреси използват:

- Authentication;
- CSRF защита;
- Permission проверки;
- LoginRequiredMixin.

---

# REST API

Настоящата версия не предоставя публичен REST API.

Архитектурата обаче позволява лесно добавяне на:

- Django REST Framework;
- JSON API;
- външни клиенти;
- мобилни приложения.

---

# Бъдещо развитие

Предвидено е реализиране на:

- REST API;
- Swagger/OpenAPI документация;
- API Authentication;
- JWT Authentication;
- WebSocket комуникация;
- интеграция с ERP системи;
- интеграция с PLM/PDM системи.

---

# Заключение

Платформата **Industrial Digital Twin Platform** използва добре структурирана URL архитектура, базирана на Django MVT. Вътрешната бизнес логика е отделена в специализирани услуги, което улеснява бъдещото разширяване на системата и добавянето на REST API без необходимост от съществени промени в съществуващата архитектура.

