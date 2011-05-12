"""This module defines the Coefficient class and a number
of related classes (functions), including Constant."""

# Copyright (C) 2008-2011 Martin Sandve Alnes
#
# This file is part of UFL.
#
# UFL is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# UFL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with UFL.  If not, see <http://www.gnu.org/licenses/>.
#
# Modified by Anders Logg, 2008-2009.
#
# First added:  2008-03-14
# Last changed: 2009-06-17

from ufl.log import warning
from ufl.assertions import ufl_assert
from ufl.common import Counted, product
from ufl.terminal import FormArgument
from ufl.finiteelement import FiniteElementBase, FiniteElement, VectorElement, TensorElement
from ufl.split_functions import split
from ufl.geometry import as_cell

# --- The Coefficient class represents a coefficient in a form ---

class Coefficient(FormArgument, Counted):
    # Slots are disabled here because they cause trouble in PyDOLFIN multiple inheritance pattern:
    #__slots__ = ("_element", "_repr", "_gradient", "_derivatives")
    _globalcount = 0

    def __init__(self, element, count=None):#, gradient=None, derivatives=None):
        FormArgument.__init__(self)
        Counted.__init__(self, count, Coefficient)
        ufl_assert(isinstance(element, FiniteElementBase),
            "Expecting a FiniteElementBase instance.")
        self._element = element
        self._repr = None
        #self._gradient = gradient
        #self._derivatives = {} if derivatives is None else dict(derivatives)
        #if gradient or derivatives:
        #    # TODO: Use gradient and derivatives in AD
        #    # TODO: Check shapes of gradient and derivatives
        #    warning("Specifying the gradient or derivatives of a Coefficient is not yet implemented anywhere.")

    def reconstruct(self, count=None, element=None):
        # This code is shared with the FooConstant classes
        if element is None or element == self._element:
            element = self._element
        if count is None or count == self._count:
            count = self._count
        if count is self._count and element is self._element:
            return self
        ufl_assert(element.value_shape() == self._element.value_shape(),
                   "Cannot reconstruct a VectorConstant with a different value shape.")
        return self._reconstruct(element, count)

    def _reconstruct(self, element, count):
        # This code is class specific
        return Coefficient(element, count)

    #def gradient(self):
    #    "Hook for experimental feature, do not use!"
    #    return self._gradient

    #def derivative(self, f):
    #    "Hook for experimental feature, do not use!"
    #    return self._derivatives.get(f)

    def element(self):
        return self._element

    def shape(self):
        return self._element.value_shape()

    def cell(self):
        return self._element.cell()

    def __str__(self):
        count = str(self._count)
        if len(count) == 1:
            return "w_%s" % count
        else:
            return "w_{%s}" % count

    def __repr__(self):
        if self._repr is None:
            self._repr = "Coefficient(%r, %r)" % (self._element, self._count)
        return self._repr

    def __eq__(self, other):
        return isinstance(other, Coefficient) and self._element == other._element and self._count == other._count

# --- Subclasses for defining constant functions without specifying element ---

# TODO: Handle actual global constants?

class ConstantBase(Coefficient):
    __slots__ = ()
    def __init__(self, element, count):
        Coefficient.__init__(self, element, count)

class Constant(ConstantBase):
    __slots__ = ()

    def __init__(self, cell, count=None):
        e = FiniteElement("DG", cell, 0)
        ConstantBase.__init__(self, e, count)
        self._repr = "Constant(%r, %r)" % (e.cell(), self._count)

    def _reconstruct(self, element, count):
        return Constant(element.cell(), count)

    def __str__(self):
        count = str(self._count)
        if len(count) == 1:
            return "c_%s" % count
        else:
            return "c_{%s}" % count

class VectorConstant(ConstantBase):
    __slots__ = ()

    def __init__(self, cell, dim=None, count=None):
        e = VectorElement("DG", cell, 0, dim)
        ConstantBase.__init__(self, e, count)
        self._repr = "VectorConstant(%r, %r, %r)" % (e.cell(), e.value_shape()[0], self._count)

    def _reconstruct(self, element, count):
        return VectorConstant(element.cell(), element.value_shape()[0], count)

    def __str__(self):
        count = str(self._count)
        if len(count) == 1:
            return "C_%s" % count
        else:
            return "C_{%s}" % count

class TensorConstant(ConstantBase):
    __slots__ = ()
    def __init__(self, cell, shape=None, symmetry=None, count=None):
        e = TensorElement("DG", cell, 0, shape=shape, symmetry=symmetry)
        ConstantBase.__init__(self, e, count)
        self._repr = "TensorConstant(%r, %r, %r, %r)" % (e.cell(), e.value_shape(), e._symmetry, self._count)

    def _reconstruct(self, element, count):
        e = element
        return TensorConstant(e.cell(), e.value_shape(), e._symmetry, count)

    def __str__(self):
        count = str(self._count)
        if len(count) == 1:
            return "C_%s" % count
        else:
            return "C_{%s}" % count

# --- Helper functions for subfunctions on mixed elements ---

def Coefficients(element):
    return split(Coefficient(element))
