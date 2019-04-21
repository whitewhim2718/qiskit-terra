# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
ScheduleComponent, a common interface for components of schedule (Instruction and Schedule).
"""
from abc import ABCMeta, abstractmethod
from typing import Tuple

from .timeslots import TimeslotCollection


class ScheduleComponent(metaclass=ABCMeta):
    """Common interface for components of schedule. """

    @property
    @abstractmethod
    def duration(self) -> int:
        """Duration of this schedule component. """
        pass

    @property
    @abstractmethod
    def occupancy(self) -> TimeslotCollection:
        """Occupied time slots by this schedule component. """
        pass

    @abstractmethod
    def shifted(self, shift: int) -> 'ScheduleComponent':
        """Return a new shifted schedule component by `shift`.

        Args:
            shift: time to be shifted

        Returns:
            ScheduleComponent: shifted schedule component
        """
        pass

    @property
    @abstractmethod
    def children(self) -> Tuple['ScheduleComponent', ...]:
        """Child nodes of this schedule component. """
        pass
