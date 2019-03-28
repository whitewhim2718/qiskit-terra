# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Schedule.
"""
import logging
import pprint
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import List

from qiskit.pulse.channels import DeviceSpecification
from qiskit.pulse.channels import Channel
from qiskit.pulse.commands import PulseCommand, SamplePulse
from qiskit.pulse.exceptions import ScheduleError

logger = logging.getLogger(__name__)


class TimedPulseBlock(metaclass=ABCMeta):
    """
    Common interface of TimedPulse and PulseSchedule (Component in the Composite Pattern)."""

    @abstractmethod
    def start_time(self) -> int:
        pass

    @abstractmethod
    def end_time(self) -> int:
        pass

    @abstractmethod
    def duration(self) -> int:
        pass

    @abstractmethod
    def children(self) -> List['TimedPulseBlock']:
        pass


class TimedPulse(TimedPulseBlock):
    """TimedPulse = Pulse with start time context."""

    def __init__(self, pulse_command: PulseCommand, to_channel: Channel, start_time: int):
        if isinstance(pulse_command, to_channel.__class__.supported):
            self.command = pulse_command
            self.channel = to_channel
            self.t0 = start_time
        else:
            raise ScheduleError("%s (%s) is not supported on %s (%s)" % (
                                pulse_command.__class__.__name__, pulse_command.name,
                                to_channel.__class__.__name__, to_channel.name))

    def start_time(self) -> int:
        return self.t0

    def end_time(self) -> int:
        return self.t0 + self.command.duration

    def duration(self) -> int:
        return self.command.duration

    def children(self) -> List[TimedPulseBlock]:
        return None

    def __str__(self):
        return "(%s, %s, %d)" % (self.command.name, self.channel.name, self.t0)


class Schedule(TimedPulseBlock):
    """Schedule."""

    def __init__(self,
                 device: DeviceSpecification,
                 name: str = None
                 ):
        """Create empty schedule.

        Args:
            channels:
            name:
        """
        self._name = name
        self._device = device
        self._children = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def device(self) -> DeviceSpecification:
        return self._device

    def append(self, command: PulseCommand, channel: Channel):
        """Append a new pulse command on a channel at the timing
        just after the last command finishes on the channel.

        Args:
            command (PulseCommand):
            channel (Channel):
        """
        try:
            start_time = self.end_time()  # TODO: need to add buffer?
            self._add(TimedPulse(command, channel, start_time))
        except ScheduleError as err:
            logger.warning("Fail to append %s to %s", command, channel)
            raise ScheduleError(err.message)

    def insert(self, start_time: int, command: PulseCommand, channel: Channel):
        """Insert new pulse command with `channel` at `start_time`.

        Args:
            start_time:
            command (PulseCommand):
            channel:
        """
        try:
            self._add(TimedPulse(command, channel, start_time))
        except ScheduleError as err:
            logger.warning("Fail to insert %s to %s at %s", command, channel, start_time)
            raise ScheduleError(err.message)

    def _add(self, block: TimedPulseBlock):
        """Add a new composite pulse `TimedPulseBlock`.

        Args:
            block:
        """
        if isinstance(block, Schedule):
            if self._device is not block._device:
                raise ScheduleError("Additional block must have the same device as self")

        if self._is_occupied_time(block):
            logger.warning("A pulse block is not added due to the occupied timing: %s", str(block))
            raise ScheduleError("Cannot add to occupied time slot.")
        else:
            self._children.append(block)

    def start_time(self) -> int:
        return min([self._start_time(child) for child in self._children], default=0)

    def end_time(self) -> int:
        return max([self._end_time(child) for child in self._children], default=0)

    def end_time_by(self, channel: Channel) -> int:
        """End time of the occupation in this schedule on a `channel`.
        Args:
            channel:

        Returns:

        """
        #  TODO: Handle schedule of schedules
        end_time = 0
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimePulse.")
            if child.channel == channel:
                end_time = max(end_time, child.end_time())
        return end_time

    def duration(self) -> int:
        return self.end_time() - self.start_time()

    def children(self) -> List[TimedPulseBlock]:
        return self._children

    def _start_time(self, block: TimedPulseBlock) -> int:
        if isinstance(block, TimedPulse):
            return block.start_time()
        else:
            return min([self._start_time(child) for child in block.children()])

    def _end_time(self, block: TimedPulseBlock) -> int:
        if isinstance(block, TimedPulse):
            return block.end_time()
        else:
            return max([self._end_time(child) for child in block.children()])

    def _is_occupied_time(self, timed_pulse) -> bool:
        # TODO: Handle schedule of schedules
        if not isinstance(timed_pulse, TimedPulse):
            raise NotImplementedError("This version assumes all children are TimePulse.")
        for pulse in self.flat_pulse_sequence():
            if pulse.channel == timed_pulse.channel:
                # interval check
                if pulse.start_time() < timed_pulse.end_time() \
                        and timed_pulse.start_time() < pulse.end_time():
                    return True
        return False

    def __str__(self):
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimePulse.")
        dic = defaultdict(list)
        for c in self._children:
            dic[c.channel.name].append(str(c))
        return pprint.pformat(dic)

    def get_sample_pulses(self) -> List[PulseCommand]:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimePulse.")
        # TODO: Improve implementation (compute at add and remove would be better)
        lib = []
        for tp in self._children:
            if isinstance(tp.command, SamplePulse) and \
                    tp.command not in lib:
                lib.append(tp.command)
        return lib

    def flat_pulse_sequence(self) -> List[TimedPulse]:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimePulse.")
        return self._children
