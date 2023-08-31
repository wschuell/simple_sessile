from pyutils import grow_sim 
from pyutils.grow_sim import Forest2D
from pyutils.grow_sim2 import F2Dbis
from workspace.utils import save_pickle
import numpy as np
from matplotlib import pyplot as plt
import csv
import osmnx as ox

place = 'Josefstadt,Wien'


gdf_shape = ox.geocode_to_gdf(place)
neg_gdf_shape = ox.geometries_from_place(place,tags=dict(building=True,natural='water',highway=True))
ax = gdf_shape.plot()
ax = neg_gdf_shape.plot(ax=ax,color='grey')
plt.show()

def example_sim():
    """Example simulation of a forest.
    """
    # L = 200                     # system length
    g0 = 1000                   # entry rate
    rRange = np.arange(1, 401)  # stem radius range
    coeffs = {'canopy r': 1,
              'canopy h': 5,
              'grow': .3,
              # 'death': .5,
              'death': .00005,
              'light competition': 400,
              'ldecay length': 10,
              'area competition': 0.0}
    nu = 2  # resource fluctuation exponent
    forest = F2Dbis( g0=g0, r_range=rRange, coeffs=coeffs, nu=nu,gdf_shape=gdf_shape,neg_gdf_shape=neg_gdf_shape)
    # forest = Forest2D(L, g0, rRange, coeffs, nu)
    f_sample = forest.sample(3, .1, 10, return_trees=True)
    nk, t, rk, trees = f_sample
    # trees = dict([(i*10,t) for i, t in enumerate(trees)])
    # print(trees)
    # save_pickle(['nk','t','rk','trees','forest'], 'cache/plot_example.p', True)
    print('nk',nk)
    print('t',t)
    print('rk',rk)
    print('tree',trees[0])
    forest.plot(ax=ax)
    plt.show()
    return f_sample

def export(filename,f_sample):
    nk, t, rk, trees = f_sample
    with open(filename,'w') as f:
      wr = csv.writer(f)
      wr.writerow(('id','x','y','r','t'))
      for tt,tr_list in zip(t,trees):
        # id,x,y,r,t
        for tree in tr_list:
          wr.writerow((tree.id,tree.xy[0],tree.xy[1],rk[tree.size_ix],tt))

trees = example_sim()

export('test_trees.csv',trees)