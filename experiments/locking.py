from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from experiments.models import Experiment


User = get_user_model()


class ExperimentLockError(Exception):
    """
    Raised when an experiment lock cannot be acquired or used.
    """


class ExperimentLockService:
    """
    Coordinate exclusive engineering access to experiments.
    """

    LOCK_DURATION_MINUTES = 30

    @classmethod
    def _expiry_time(cls):
        return timezone.now() + timedelta(
            minutes=cls.LOCK_DURATION_MINUTES
        )

    @classmethod
    def clear_expired_locks(cls) -> None:
        """
        Release all expired locks.
        """

        now = timezone.now()

        Experiment.objects.filter(
            lock_expires_at__lte=now
        ).update(
            locked_by=None,
            locked_at=None,
            lock_expires_at=None,
        )

    @classmethod
    @transaction.atomic
    def acquire(
        cls,
        *,
        experiment: Experiment,
        user: User,
    ) -> Experiment:
        """
        Acquire the experiment for one engineer.

        One experiment can be locked by only one engineer and one
        engineer can hold only one experiment lock at a time.
        """

        cls.clear_expired_locks()

        locked_experiment = (
            Experiment.objects.select_for_update().get(
                pk=experiment.pk
            )
        )

        if locked_experiment.is_locked_by(user):
            locked_experiment.lock_expires_at = (
                cls._expiry_time()
            )

            locked_experiment.save(
                update_fields=[
                    "lock_expires_at",
                    "updated_at",
                ]
            )

            return locked_experiment

        if locked_experiment.is_locked_by_another_user(user):
            owner = locked_experiment.locked_by

            owner_name = (
                owner.get_full_name()
                or owner.get_username()
            )

            raise ExperimentLockError(
                "Експериментът вече се обработва от "
                f"{owner_name}."
            )

        other_lock = (
            Experiment.objects.select_for_update()
            .filter(
                locked_by=user,
            )
            .exclude(
                pk=locked_experiment.pk
            )
            .first()
        )

        if other_lock is not None:
            raise ExperimentLockError(
                "Вече работите по друг експеримент: "
                f"{other_lock.name}. Освободете го, "
                "преди да заключите нов."
            )

        now = timezone.now()

        locked_experiment.locked_by = user
        locked_experiment.locked_at = now
        locked_experiment.lock_expires_at = (
            cls._expiry_time()
        )

        try:
            locked_experiment.save(
                update_fields=[
                    "locked_by",
                    "locked_at",
                    "lock_expires_at",
                    "updated_at",
                ]
            )
        except IntegrityError as error:
            raise ExperimentLockError(
                "Неуспешно заключване. Проверете дали "
                "не работите по друг експеримент."
            ) from error

        return locked_experiment

    @classmethod
    @transaction.atomic
    def release(
        cls,
        *,
        experiment: Experiment,
        user: User,
        force: bool = False,
    ) -> Experiment:
        """
        Release an experiment lock.
        """

        locked_experiment = (
            Experiment.objects.select_for_update().get(
                pk=experiment.pk
            )
        )

        if locked_experiment.locked_by_id is None:
            return locked_experiment

        can_force = (
            force
            and (
                user.is_staff
                or user.is_superuser
            )
        )

        if (
            locked_experiment.locked_by_id != user.pk
            and not can_force
        ):
            raise ExperimentLockError(
                "Само инженерът, заключил експеримента, "
                "може да го освободи."
            )

        locked_experiment.locked_by = None
        locked_experiment.locked_at = None
        locked_experiment.lock_expires_at = None

        locked_experiment.save(
            update_fields=[
                "locked_by",
                "locked_at",
                "lock_expires_at",
                "updated_at",
            ]
        )

        return locked_experiment

    @classmethod
    def assert_owned(
        cls,
        *,
        experiment: Experiment,
        user: User,
    ) -> None:
        """
        Reject a write operation when the current user owns no lock.
        """

        cls.clear_expired_locks()

        experiment.refresh_from_db(
            fields=[
                "locked_by",
                "locked_at",
                "lock_expires_at",
            ]
        )

        if experiment.is_locked_by(user):
            return

        if experiment.is_locked_by_another_user(user):
            owner = experiment.locked_by

            owner_name = (
                owner.get_full_name()
                or owner.get_username()
            )

            raise ExperimentLockError(
                "Експериментът се обработва от "
                f"{owner_name}. Достъпът ви е само за преглед."
            )

        raise ExperimentLockError(
            "Преди да извършите тази операция, "
            "заключете експеримента за работа."
        )

    @classmethod
    def refresh(
        cls,
        *,
        experiment: Experiment,
        user: User,
    ) -> None:
        """
        Extend the current engineer lock.
        """

        cls.assert_owned(
            experiment=experiment,
            user=user,
        )

        Experiment.objects.filter(
            pk=experiment.pk,
            locked_by=user,
        ).update(
            lock_expires_at=cls._expiry_time()
        )