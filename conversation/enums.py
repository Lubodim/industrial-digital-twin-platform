from django.db import models


class ConversationType(models.TextChoices):
    """
    Определя предназначението на разговора.
    """

    GLOBAL = "GLOBAL", "Global AI Assistant"
    EXPERIMENT = "EXPERIMENT", "Experiment Chat"
    RESEARCH = "RESEARCH", "AI Research"


class ConversationStatus(models.TextChoices):
    """
    Определя текущото състояние на разговора.
    """

    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class MessageRole(models.TextChoices):
    """
    Определя автора и предназначението на съобщението.
    """

    ENGINEER = "ENGINEER", "Engineer"
    AI = "AI", "AI Assistant"
    SYSTEM = "SYSTEM", "System"


class ContextCategory(models.TextChoices):
    """
    Категории за структурирания контекст на конкретен разговор.
    """

    GOAL = "GOAL", "Goal"
    CONSTRAINT = "CONSTRAINT", "Constraint"
    MATERIAL = "MATERIAL", "Material"
    MANUFACTURING = "MANUFACTURING", "Manufacturing"
    COST = "COST", "Cost"
    QUALITY = "QUALITY", "Quality"
    GEOMETRY = "GEOMETRY", "Geometry"
    PERFORMANCE = "PERFORMANCE", "Performance"
    SAFETY = "SAFETY", "Safety"
    OTHER = "OTHER", "Other"


class MemoryCategory(models.TextChoices):
    """
    Категории за дългосрочната памет за инженера.
    """

    PREFERENCE = "PREFERENCE", "Preference"
    RESTRICTION = "RESTRICTION", "Restriction"
    DEFAULT_VALUE = "DEFAULT_VALUE", "Default value"
    WORKING_METHOD = "WORKING_METHOD", "Working method"
    ORGANIZATION_RULE = "ORGANIZATION_RULE", "Organization rule"
    OTHER = "OTHER", "Other"


class ContextSource(models.TextChoices):
    """
    Показва откъде е възникнал даден ContextItem или MemoryItem.
    """

    ENGINEER = "ENGINEER", "Engineer"
    AI_EXTRACTED = "AI_EXTRACTED", "AI extracted"
    SYSTEM = "SYSTEM", "System"
    IMPORTED = "IMPORTED", "Imported"


class ContextValueType(models.TextChoices):
    """
    Показва как трябва да бъде интерпретирана стойността.
    Самата стойност ще се съхранява като текст.
    """

    TEXT = "TEXT", "Text"
    INTEGER = "INTEGER", "Integer"
    DECIMAL = "DECIMAL", "Decimal"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    BOOLEAN = "BOOLEAN", "Boolean"
    JSON = "JSON", "JSON"
