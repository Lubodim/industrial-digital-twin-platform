# Database Entities

# Основни обекти в базата данни

## Въведение

Настоящият документ описва основните обекти (Entities), използвани в базата данни на **Industrial Digital Twin Platform**.

Базата данни е реализирана чрез Django ORM и използва релационен модел. Всеки бизнес обект е представен чрез отделен Django Model, който съответства на таблица в SQLite базата данни.

Обектите са организирани така, че да поддържат целия жизнен цикъл на цифровия двойник – от неговото създаване, през инженерния анализ, до създаването на производни цифрови двойници.

---

# Обща схема

```text
User
 │
 ├──────────────┐
 ▼              ▼
AuditLog    Engineering Experiment
                   │
                   ▼
             Digital Twin
             /     |      \
            /      |       \
     Material  Technology  Files
                    │
                    ▼
          Engineering Proposal
                    │
                    ▼
          Derived Digital Twin
```

---

# User

Представлява регистриран потребител на платформата.

Основни атрибути:

- Username
- Password
- First Name
- Last Name
- Email
- Is Active
- Is Staff
- Date Joined

Основни връзки:

- Engineering Experiments
- AuditLog
- Locks

---

# DigitalTwin

Основният бизнес обект в платформата.

Представлява виртуален модел на производствен детайл.

Основни атрибути:

- Name
- Part Number
- Description
- Material
- Technology
- Weight
- Cost
- Status
- Created At
- Updated At

Основни връзки:

- Material
- Technology
- Files
- Engineering Experiments
- Derived Twins

---

# Material

Представлява производствен материал.

Основни атрибути:

- Name
- Standard
- Density
- Description
- Is Active

Връзки:

- Digital Twins

---

# ManufacturingTechnology

Представлява технология за производство.

Основни атрибути:

- Name
- Description
- Is Active

Връзки:

- Digital Twins

---

# DigitalTwinFile

Представлява файл, свързан с цифров двойник.

Поддържани типове:

- STEP
- STL
- PNG
- PDF
- DOCX
- Други файлове

Основни атрибути:

- File
- File Type
- Description
- Uploaded At

Връзки:

- Digital Twin

---

# EngineeringExperiment

Представлява инженерен експеримент.

Всеки експеримент принадлежи на един цифров двойник.

Основни атрибути:

- Title
- Description
- Status
- Locked By
- Locked At
- Lock Expires At
- Created At

Връзки:

- Digital Twin
- User
- Engineering Chat
- AI Results
- Engineering Proposals

---

# ExperimentMessage

Представлява съобщение в инженерния разговор.

Основни атрибути:

- Role
- Message
- Created At

Връзки:

- Engineering Experiment

---

# ExternalAIResult

Представлява резултат от външен AI модел.

Основни атрибути:

- Provider
- Response
- Response BG
- Created At

Връзки:

- Engineering Experiment

Поддържани доставчици:

- OpenAI
- Claude
- Gemini
- Grok

---

# LocalAIAnalysis

Представлява локален AI анализ.

Основни атрибути:

- Prompt
- Response
- Response BG
- Created At

Връзки:

- Engineering Experiment

---

# EngineeringProposal

Представлява инженерно предложение.

Основни атрибути:

- Title
- Title BG
- Description
- Description BG
- Reasoning
- Expected Impact
- Status

Връзки:

- Engineering Experiment

Статуси:

- Pending
- Approved
- Rejected

---

# DerivedDigitalTwin

Представлява цифров двойник, създаден след инженерен експеримент.

Основни атрибути:

- Source Twin
- Result Twin
- Applied Changes
- Manual Changes
- Created At

Връзки:

- Engineering Experiment
- Original Digital Twin
- New Digital Twin

---

# AuditLog

Представлява одитен запис.

Основни атрибути:

- User
- Action
- Entity Type
- Entity ID
- Details
- IP Address
- Computer Name
- User Agent
- Created At

Връзки:

- User

---

# Translation

Представлява преведен AI резултат.

Основни атрибути:

- English Text
- Bulgarian Text
- Created At

Използва се от:

- External AI
- Local AI
- Engineering Proposals

---

# Entity Relationships

Основните зависимости между обектите са:

```text
User
 │
 ├────────────── AuditLog
 │
 └────────────── Engineering Experiment
                       │
                       ▼
                 Digital Twin
                  │       │
                  │       ├──────── Material
                  │       ├──────── Technology
                  │       └──────── Files
                  │
                  ▼
          External AI Results
                  │
                  ▼
          Local AI Analysis
                  │
                  ▼
         Engineering Proposals
                  │
                  ▼
        Derived Digital Twin
```

---

# Кардиналности

| Връзка | Тип |
|---------|-----|
| User → Experiments | One-to-Many |
| User → AuditLog | One-to-Many |
| Material → Digital Twin | One-to-Many |
| Technology → Digital Twin | One-to-Many |
| Digital Twin → Files | One-to-Many |
| Digital Twin → Experiments | One-to-Many |
| Experiment → Messages | One-to-Many |
| Experiment → AI Results | One-to-Many |
| Experiment → Proposals | One-to-Many |
| Experiment → Derived Digital Twin | One-to-One |

---

# Индекси

Основните индекси са изградени върху:

- Primary Keys
- Foreign Keys
- Created At
- Status
- User
- Entity Type
- Entity ID

Това осигурява бързо филтриране и търсене.

---

# Ограничения

Основните ограничения включват:

- всеки инженерен експеримент принадлежи на един цифров двойник;
- един експеримент може да бъде заключен само от един инженер;
- производният цифров двойник винаги произлиза от един оригинален цифров двойник;
- всички инженерни предложения принадлежат на един експеримент.

---

# Бъдещо развитие

Предвижда се добавяне на нови обекти:

- CAD Model;
- Simulation;
- Knowledge Base;
- IoT Device;
- Sensor Data;
- Production Line;
- Maintenance History;
- Machine Learning Dataset.

---

# Заключение

Моделът на базата данни е организиран около цифровия двойник като централен бизнес обект. Всички останали същности – инженерни експерименти, AI анализи, инженерни предложения, файлове и одитни записи – са логически свързани с него. Използването на Django ORM осигурява ясно структурирани зависимости, добра производителност и възможност за лесно разширяване на платформата в бъдещи версии.
