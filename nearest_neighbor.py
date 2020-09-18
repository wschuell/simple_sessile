# ====================================================================================== #
# Module for analyzing properties of nearest neighbors in forest plots.
# Author : Eddie Lee, edlee@santafe.edu
# ====================================================================================== #
from .utils import *



def dist(xy):
    """Find distances to nearest neighbors in tree plot.

    Parameters
    ----------
    xy : ndarray
        List of xy positions by row.
    
    Returns
    -------
    ndarray 
    """
    
    assert len(xy) < 1e4, "No. of pairwise distances to compute is too large."

    # calculate distance to nearest neighbor
    dr = pdist(xy)

    dr = squareform(dr)
    dr[np.diag_indices_from(dr)] = np.inf

    return dr.min(0)

def survival(N, boundaries, no_boundary_correction=False):
    """Probability that nearest neighbor distance is greater than dr, or survival
    probability distribution, for randomly distributed points.

    Parameters
    ----------
    N : int
        Number of points.
    boundaries : float or tuple
        Length of one side of square plot or length of each boundary.
    no_boundary_correction : bool, False

    Returns
    -------
    function
    """

    if hasattr(boundaries, '__len__'):
        assert len(boundaries)==2
        A = boundaries[0] * boundaries[1]
        boundaries = sum(boundaries)
    else:
        A = boundaries**2
        boundaries *= 4

    rho = N/A

    if no_boundary_correction:
        def ccdf(r, rho=rho):
            return np.exp(-np.pi * rho * r**2)
        
        return ccdf

    f = boundaries * np.sqrt(1 / rho / np.pi) / 2 / A
    def ccdf(r, rho=rho, f=f):
        return (1-f) * np.exp(-np.pi * rho * r**2) + f * np.exp(-np.pi * rho * r**2 / 2)
    
    return ccdf

def pdf(N, boundaries, no_boundary_correction=False):
    """Return probability distribution of distance to nearest neighbor. See nn_survival().

    Parameters
    ----------
    N : int
        Number of points.
    A : int
        Area of plot.
    boundaries : float or tuple
        Length of one side of square plot or length of each boundary.

    Returns
    -------
    function
    """

    if hasattr(boundaries, '__len__'):
        assert len(boundaries)==2
        A = boundaries[0] * boundaries[1]
        boundaries = sum(boundaries)
    else:
        A = boundaries**2
        boundaries *= 4

    rho = N/A

    if no_boundary_correction:
        def p(r, rho=rho):
            return 2 * np.pi * rho * r * np.exp(-np.pi * rho * r**2)
        return p

    f = boundaries * np.sqrt(1 / rho / np.pi) / 2 / A
    def p(r, rho=rho, f=f):
        return (2 * np.pi * rho * r * (1-f) * np.exp(-np.pi * rho * r**2) +
                np.pi * rho * r * f * np.exp(-np.pi * rho * r**2 / 2))
    return p

def kl(r_sample, N, boundaries, bin_width):
    """Kullback-Leibler divergence estimated between estimate from the given sample and
    the analytic approximation for a box.

    Parameters
    ----------
    r_sample : ndarray
    N : int
    boundaries : float or tuple
    bin_width : float
        Spacing used to generate histogram from given sample. This must be small enough to
        allow for linear approximation of analytic form while being large enough for the
        given sample set.

    Returns
    -------
    float
        Divergence in bits.
    """
    
    bins = np.arange(int(np.ceil(r_sample.max() / bin_width))+1) * bin_width
    binCenters = (bins[1:] + bins[:-1]) / 2

    ix = np.digitize(r_sample, bins) - 1
    epdf = np.bincount(ix)
    epdf = epdf / epdf.sum()
    
    # analytic approx to box
    p = pdf(N, boundaries)
    
    return np.nansum(epdf * (np.log2(epdf) - np.log2(p(binCenters) * bin_width)))

def interp_dkl(bindx, dkl, tol=1e-2,
               first_order=False,
               return_all=False,
               **kwargs):
    """Interpolate DKL using expansion in terms of bin widths.
    
    Parameters
    ----------
    bindx : ndarray
    dkl : ndarray
        KL-estimated at each of these bin widths.
    tol : float, 1e-3
        This is the square of the sums so is quite generous.
    return_all : bool, False
    **kwargs
        For scipy.optimize.minimize.

    Returns
    -------
    """

    from scipy.optimize import minimize
    sortix = np.argsort(bindx)
    bindx = bindx[sortix]
    dkl = dkl[sortix]

    # first fit lower order to get coefficients for higher order fit
    def fit_log(x, y):
        def cost(args):
            a, b, c = args
            yhat = a * np.log(x) * (1 + b/x) + c
            return ((1/yhat - 1/y)**2).sum()
        return minimize(cost, (-.01, 0, y.min()), **kwargs)

    soln = fit_log(bindx, dkl)
    lowOrder_ab = soln['x']
    if first_order:
        if return_all:
            return lowOrder_ab, soln
        return lowOrder_ab

    
    # higher order fit to order dx**-2
    def fit_log(x, y):
        def cost(args):
            a, b, c, d = args
            yhat = a * np.log(x) * (1 + b/x + c/x**2) + d
            # make sure that yhat is ordered...this can inhibit good solution finding
            #if not (np.diff(yhat)<=0).all():
            #    return 1e30
            return ((1/yhat - 1/y)**2).sum()
        return minimize(cost, (lowOrder_ab[0], lowOrder_ab[1], 0, lowOrder_ab[-1]), **kwargs)

    soln = fit_log(bindx, dkl)

    # check solution for monotonicity
    a, b, c, d = soln['x']
    yhat = a * np.log(bindx) * (1 + b/bindx + c/bindx**2) + d
    if not (np.diff(yhat)<=0).all():
        raise Exception

    if return_all:
        return soln['x'], soln, lowOrder_ab
    return soln['x']

def pair_correlation(xy, bins=None, bounding_box=None):
    """Correlation function between all points within bounding box to all neighbors.
    <n(dr)>, average no. of neighbors at distance dr. 

    Parameters
    ----------
    xy : ndarray
    bins : ndarray
    bounding_box : tuple, None
        Specify bottom left hand corner and then width and height.
    
    Returns
    -------
    ndarray
        Correlation function.
    ndarray
        Distance.
    """
    
    dr = pdist(xy)
    dr = squareform(dr)
    
    if not bounding_box is None:
        assert len(bounding_box)==4
        x0, x1 = bounding_box[0], bounding_box[0] + bounding_box[2]
        y0, y1 = bounding_box[1], bounding_box[1] + bounding_box[3]
        
        # only keep elements from center of box
        selectix = (xy[:,0]>x0) & (xy[:,0]<x1) & (xy[:,1]>y0) & (xy[:,1]<y1)
        dr = dr[selectix]
    dr = dr.ravel()
    
    if bins is None:
        p, bins = np.histogram(dr, bins=np.linspace(0, dr.max(), int(np.sqrt(dr.size))))
    else:
        p, bins = np.histogram(dr, bins=bins)
        
    p = p / p[0]
    r = (bins[1:] + bins[:-1]) / 2
    
    return p, r
