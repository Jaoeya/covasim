'''
Execute analysis tools in order to broadly cover basic functionality of analysis.py
'''

import numpy as np
import sciris as sc
import covasim as cv


#%% General settings

do_plot = 1 # Whether to plot when run interactively
cv.options.set(interactive=False) # Assume not running interactively

pars = dict(
    pop_size = 1000,
    verbose = 0,
)


#%% Define tests

def test_snapshot():
    sc.heading('Testing snapshot analyzer')
    sim = cv.Sim(pars, analyzers=cv.snapshot('2020-04-04', '2020-04-14'))
    sim.run()
    snapshot = sim.get_analyzer()
    people1 = snapshot.snapshots[0]            # Option 1
    people2 = snapshot.snapshots['2020-04-04'] # Option 2
    people3 = snapshot.get('2020-04-14')       # Option 3
    people4 = snapshot.get(34)                 # Option 4
    people5 = snapshot.get()                   # Option 5

    assert people1 == people2, 'Snapshot options should match but do not'
    assert people3 != people4, 'Snapshot options should not match but do'
    return people5


def test_age_hist():
    sc.heading('Testing age histogram')

    day_list = ["2020-03-20", "2020-04-20"]
    age_analyzer = cv.age_histogram(days=day_list)
    sim = cv.Sim(pars, analyzers=age_analyzer)
    sim.run()

    # Checks to see that compute windows returns correct number of results
    agehist = sim.get_analyzer()
    agehist.compute_windows()
    agehist.get() # Not used, but check get
    agehist.get(day_list[1])
    assert len(age_analyzer.window_hists) == len(day_list), "Number of histograms should equal number of days"

    # Check plot()
    if do_plot:
        plots = agehist.plot(windows=True)
        assert len(plots) == len(day_list), "Number of plots generated should equal number of days"

    return agehist


def test_daily_stats():
    sc.heading('Testing daily stats analyzer')
    ds = cv.daily_stats(days=['2020-04-04', '2020-04-14'], save_inds=True)
    sim = cv.Sim(pars, analyzers=ds)
    sim.run()
    daily = sim.get_analyzer()
    if do_plot:
        daily.plot()
    return daily


def test_fit():
    sc.heading('Testing fitting function')

    # Create a testing intervention to ensure some fit to data
    tp = cv.test_prob(0.1)

    sim = cv.Sim(pars, rand_seed=1, interventions=tp, datafile="example_data.csv")
    sim.run()

    # Checking that Fit can handle custom input
    custom_inputs = {'custom_data':{'data':np.array([1,2,3]), 'sim':np.array([1,2,4]), 'weights':[2.0, 3.0, 4.0]}}
    fit1 = sim.compute_fit(custom=custom_inputs, compute=True)

    # Test that different seed will change compute results
    sim2 = cv.Sim(pars, rand_seed=2, interventions=tp, datafile="example_data.csv")
    sim2.run()
    fit2 = sim2.compute_fit(custom=custom_inputs)

    assert fit1.mismatch != fit2.mismatch, "Differences between fit and data remains unchanged after changing sim seed"

    if do_plot:
        fit1.plot()

    return fit1


def test_transtree():
    sc.heading('Testing transmission tree')

    sim = cv.Sim(pars, pop_size=100)
    sim.run()

    transtree = sim.make_transtree()
    print(len(transtree))
    if do_plot:
        transtree.plot()
        transtree.animate(animate=False)
        transtree.plot_histograms()

    # Try networkx, but don't worry about failures
    try:
        tt = sim.make_transtree(to_networkx=True)
        tt.r0()
    except ImportError as E:
        print(f'Could not test conversion to networkx ({str(E)})')

    return transtree


#%% Run as a script
if __name__ == '__main__':

    # Start timing and optionally enable interactive plotting
    cv.options.set(interactive=do_plot)
    T = sc.tic()

    snapshot  = test_snapshot()
    agehist   = test_age_hist()
    daily     = test_daily_stats()
    fit       = test_fit()
    transtree = test_transtree()

    print('\n'*2)
    sc.toc(T)
    print('Done.')
