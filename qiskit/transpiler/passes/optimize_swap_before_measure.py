# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.


"""
Transpiler pass to remove swaps in front of measurements by re-targeting the classical bit
 of the measure instruction.
"""

from qiskit.circuit import Measure
from qiskit.extensions.standard import SwapGate
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit


class OptimizeSwapBeforeMeasure(TransformationPass):
    """Remove the swaps followed by measurement (and adapt the measurement)"""

    def run(self, dag):
        """Return a new circuit that has been optimized."""
        swaps = dag.op_nodes(SwapGate)
        for swap in swaps:
            final_successor = []
            for successor in dag.successors(swap):
                final_successor.append(successor.type == 'out' or (successor.type == 'op' and
                                                                   successor.op.name == 'measure'))
            if all(final_successor):
                # the node swap needs to be removed and, if a measure follows, needs to be adapted
                swap_qargs = swap.qargs
                measure_layer = DAGCircuit()
                for qreg in dag.qregs.values():
                    measure_layer.add_qreg(qreg)
                for creg in dag.cregs.values():
                    measure_layer.add_creg(creg)
                for successor in dag.successors(swap):
                    if successor.type == 'op' and successor.op.name == 'measure':
                        # replace measure node with a new one, where qargs is set with the "other"
                        # swap qarg.
                        dag.remove_op_node(successor)
                        old_measure_qarg = successor.qargs[0]
                        new_measure_qarg = swap_qargs[swap_qargs.index(old_measure_qarg) - 1]
                        measure_layer.apply_operation_back(Measure(), [new_measure_qarg],
                                                           [successor.cargs[0]])
                dag.extend_back(measure_layer)
                dag.remove_op_node(swap)
        return dag
