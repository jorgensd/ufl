"Differential operators."

from __future__ import absolute_import

__authors__ = "Martin Sandve Alnes"
__date__ = "2008-03-14 -- 2008-11-07"

from .output import ufl_assert
from .base import Expr, Terminal
from .zero import Zero
from .scalar import ScalarValue
from .indexing import Indexed, MultiIndex, Index, extract_indices
from .variable import Variable
from .tensors import as_tensor
from .tensoralgebra import Identity
from .function import Function, Constant, VectorConstant, TensorConstant

from .common import domain2dim

#--- Basic differentiation objects ---

spatially_constant_types = (ScalarValue, Zero, Identity, Constant, VectorConstant, TensorConstant) # FacetNormal: not for higher order geometry!

class SpatialDerivative(Expr):
    "Partial derivative of an expression w.r.t. spatial directions given by indices."
    __slots__ = ("_expression", "_shape", "_indices", "_free_indices", "_index_dimensions", "_repeated_indices", "_dx_free_indices", "_dx_repeated_indices")
    def __new__(cls, expression, indices):
        if isinstance(expression, Terminal):
            # Return zero if expression is trivially 
            # constant, and there are no free indices.
            # (there are no expression.free_indices() in terminal types)
            ind = [i for i in indices if isinstance(i, Index)]
            si = set(ind)
            if len(ind) == 2*len(si):
                if isinstance(expression, spatially_constant_types):
                    return Zero(expression.shape())
        return Expr.__new__(cls)
    
    def __init__(self, expression, indices):
        self._expression = expression
        
        if not isinstance(indices, MultiIndex):
            # if constructed from repr
            indices = MultiIndex(indices, len(indices)) # TODO: Do we need len(indices) in MultiIndex?
        self._indices = indices
        
        # Find free and repeated indices in the dx((i,i,j)) part
        (self._dx_free_indices, self._dx_repeated_indices, dummy, dummy) = \
            extract_indices(self._indices._indices)
        
        domain = expression.domain()
        ufl_assert(domain is not None, "Need to know the spatial dimension to compute the shape of derivatives.")
        dim = domain2dim[domain]
        self._index_dimensions = {}
        for i in self._dx_free_indices:
            # set free index dimensions to the spatial dimension 
            self._index_dimensions[i] = dim
        
        # Find free and repeated indices among the combined
        # indices of the expression and dx((i,j,k))
        fi = expression.free_indices()
        fid = expression.index_dimensions()
        indices = fi + self._dx_free_indices
        dimensions = tuple(fid[i] for i in fi) + (dim,)*len(self._dx_free_indices)
        (self._free_indices, self._repeated_indices, self._shape, self._index_dimensions) = \
            extract_indices(indices, dimensions)
    
    def operands(self):
        return (self._expression, self._indices)
    
    def free_indices(self):
        return self._free_indices
    
    def repeated_indices(self):
        return self._repeated_indices
    
    def index_dimensions(self):
        # FIXME: Can we remove this now?
        # Repeated indices here always iterate over the default
        # spatial range, so I think this should be correct:
        #d = {}
        #for i in self._repeated_indices:
        #    d[i] = default_dim
        #return d
        return self._index_dimensions

    def shape(self):
        return self._shape

    def __str__(self):
        # TODO: Pretty-print for higher order derivatives.
        return "(d[%s] / dx_%s)" % (self._expression, self._indices)
    
    def __repr__(self):
        return "SpatialDerivative(%r, %r)" % (self._expression, self._indices)

class VariableDerivative(Expr):
    __slots__ = ("_f", "_v", "_index", "_free_indices", "_index_dimensions", "_shape")
    def __new__(cls, f, v):
        # Return zero if expression is trivially independent 
        # of Function, and there are no free indices
        if (not isinstance(f, Variable)) and isinstance(f, Terminal):
            # Remove repeated indices to get the free 
            free_indices = set(f.free_indices()) ^ set(v.free_indices())
            if not free_indices:
                return Zero(f.shape())
        return Expr.__new__(cls)
    
    def __init__(self, f, v):
        ufl_assert(isinstance(f, Expr), "Expecting an Expr in VariableDerivative.")
        if isinstance(v, Indexed):
            ufl_assert(isinstance(v._expression, Variable), \
                "Expecting a Variable in VariableDerivative.")
            ufl_warning("diff(f, v[i]) probably isn't handled properly in all code.") # FIXME
        else:
            ufl_assert(isinstance(v, Variable), \
                "Expecting a Variable in VariableDerivative.")
        self._f = f
        self._v = v
        fi = f.free_indices()
        vi = v.free_indices()
        fid = f.index_dimensions()
        vid = v.index_dimensions()
        ufl_assert(not (set(fi) ^ set(vi)), \
            "Repeated indices not allowed in VariableDerivative.") # TODO: Allow diff(f[i], v[i])?
        self._free_indices = tuple(fi + vi)
        self._index_dimensions = dict(fid)
        self._index_dimensions.update(vid)
        self._shape = f.shape() + v.shape()
    
    def operands(self):
        return (self._f, self._v)
    
    def free_indices(self):
        return self._free_indices

    def index_dimensions(self):
        return self._index_dimensions
    
    def shape(self):
        return self._shape
    
    def __str__(self):
        return "(d[%s] / d[%s])" % (self._f, self._v)

    def __repr__(self):
        return "VariableDerivative(%r, %r)" % (self._f, self._v)

#--- Compound differentiation objects ---

class Grad(Expr):
    __slots__ = ("_f", "_dim",)

    def __new__(cls, f):
        # Return zero if expression is trivially constant
        if isinstance(f, spatially_constant_types):
            domain = f.domain()
            ufl_assert(domain is not None, "Can't take gradient of expression with undefined domain...")
            dim = domain2dim[domain]
            return Zero((dim,) + f.shape())
        return Expr.__new__(cls)
    
    def __init__(self, f):
        self._f = f
        domain = f.domain()
        ufl_assert(domain is not None, "Can't take gradient of expression with undefined domain. How did this happen?")
        self._dim = domain2dim[domain]
        ufl_assert(not (f.free_indices()), \
            "TODO: Taking gradient of an expression with free indices, should this be a valid expression? Please provide examples!")
    
    def operands(self):
        return (self._f, )
    
    def free_indices(self):
        return self._f.free_indices()
    
    def index_dimensions(self):
        return self._f.index_dimensions()
    
    def shape(self):
        return (self._dim,) + self._f.shape()
    
    def __str__(self):
        return "grad(%s)" % self._f
    
    def __repr__(self):
        return "Grad(%r)" % self._f

class Div(Expr):
    __slots__ = ("_f",)

    def __new__(cls, f):
        # Return zero if expression is trivially constant
        if isinstance(f, spatially_constant_types):
            return Zero(f.shape()[1:])
        return Expr.__new__(cls)

    def __init__(self, f):
        ufl_assert(f.rank() >= 1, "Can't take the divergence of a scalar.")
        ufl_assert(not (f.free_indices()), \
            "TODO: Taking divergence of an expression with free indices, should this be a valid expression? Please provide examples!")
        self._f = f
    
    def operands(self):
        return (self._f, )
    
    def free_indices(self):
        return self._f.free_indices()
    
    def index_dimensions(self):
        return self._f.index_dimensions()
    
    def shape(self):
        return self._f.shape()[1:]
    
    def __str__(self):
        return "div(%s)" % self._f

    def __repr__(self):
        return "Div(%r)" % self._f

class Curl(Expr):
    __slots__ = ("_f", "_dim",)
    
    # TODO: Implement __new__ to discover trivial zeros
    
    def __init__(self, f):
        ufl_assert(f.rank() == 1, "Need a vector.") # TODO: Is curl always 3D?
        ufl_assert(not f.free_indices(), \
            "TODO: Taking curl of an expression with free indices, should this be a valid expression? Please provide examples!")
        self._f = f
        domain = f.domain()
        ufl_assert(domain is not None, "Can't take curl of expression with undefined domain...") # TODO: Is curl always 3D?
        self._dim = domain2dim[domain]
    
    def operands(self):
        return (self._f, )
    
    def free_indices(self):
        return self._f.free_indices()
    
    def index_dimensions(self):
        return self._f.index_dimensions()
    
    def shape(self):
        return (self._dim,)
    
    def __str__(self):
        return "curl(%s)" % self._f
    
    def __repr__(self):
        return "Curl(%r)" % self._f

class Rot(Expr):
    __slots__ = ("_f",)
    
    # TODO: Implement __new__ to discover trivial zeros

    def __init__(self, f):
        ufl_assert(f.rank() == 1, "Need a vector.")
        ufl_assert(not f.free_indices(), \
            "TODO: Taking rot of an expression with free indices, should this be a valid expression? Please provide examples!")
        self._f = f
    
    def operands(self):
        return (self._f, )
    
    def free_indices(self):
        return self._f.free_indices()
    
    def index_dimensions(self):
        return self._f.index_dimensions()
    
    def shape(self):
        return ()
    
    def __str__(self):
        return "rot(%s)" % self._f
    
    def __repr__(self):
        return "Rot(%r)" % self._f
