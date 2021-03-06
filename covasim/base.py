'''
Base classes for Covasim. These classes handle a lot of the boilerplate of the
People and Sim classes (e.g. loading, saving, key lookups, etc.), so those classes
can be focused on the disease-specific functionality.
'''

import numpy as np
import pandas as pd
import sciris as sc
import datetime as dt
from . import version as cvv
from . import utils as cvu
from . import misc as cvm
from . import defaults as cvd
from . import parameters as cvpar
from .settings import options as cvo

# Specify all externally visible classes this file defines
__all__ = ['ParsObj', 'Result', 'BaseSim', 'BasePeople', 'Person', 'FlexDict', 'Contacts', 'Layer']


#%% Define simulation classes

class FlexPretty(sc.prettyobj):
    '''
    A class that by default changes the display type depending on the current level
    of verbosity.
    '''

    def __repr__(self):
        ''' Set display options based on current level of verbosity '''
        try:
            if cvo['verbose']:
                string = self._disp()
            else:
                string = self._brief()
        except Exception as E:
            string = sc.objectid(self)
            string += f'Warning, something went wrong printing object:\n{str(E)}'
        return string

    def _disp(self):
        ''' Verbose output -- use Sciris' pretty repr by default '''
        return sc.prepr(self)

    def disp(self, output=False):
        ''' Print or output verbose representation of the object '''
        string = self._disp()
        if not output:
            print(string)
        else:
            return string

    def _brief(self):
        ''' Brief output -- use a one-line output, a la Python's default '''
        return sc.objectid(self)

    def brief(self, output=False):
        ''' Print or output a brief representation of the object '''
        string = self._brief()
        if not output:
            print(string)
        else:
            return string


class ParsObj(FlexPretty):
    '''
    A class based around performing operations on a self.pars dict.
    '''

    def __init__(self, pars):
        self.update_pars(pars, create=True)
        return


    def __getitem__(self, key):
        ''' Allow sim['par_name'] instead of sim.pars['par_name'] '''
        try:
            return self.pars[key]
        except:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)


    def __setitem__(self, key, value):
        ''' Ditto '''
        if key in self.pars:
            self.pars[key] = value
        else:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)
        return


    def update_pars(self, pars=None, create=False):
        '''
        Update internal dict with new pars.

        Args:
            pars (dict): the parameters to update (if None, do nothing)
            create (bool): if create is False, then raise a KeyNotFoundError if the key does not already exist
        '''
        if pars is not None:
            if not isinstance(pars, dict):
                raise TypeError(f'The pars object must be a dict; you supplied a {type(pars)}')
            if not hasattr(self, 'pars'):
                self.pars = pars
            if not create:
                available_keys = list(self.pars.keys())
                mismatches = [key for key in pars.keys() if key not in available_keys]
                if len(mismatches):
                    errormsg = f'Key(s) {mismatches} not found; available keys are {available_keys}'
                    raise sc.KeyNotFoundError(errormsg)
            self.pars.update(pars)
        return


class Result(object):
    '''
    Stores a single result -- by default, acts like an array.

    Args:
        name (str): name of this result, e.g. new_infections
        npts (int): if values is None, precreate it to be of this length
        scale (bool): whether or not the value scales by population scale factor
        color (str/arr): default color for plotting (hex or RGB notation)

    **Example**::

        import covasim as cv
        r1 = cv.Result(name='test1', npts=10)
        r1[:5] = 20
        print(r1.values)
    '''

    def __init__(self, name=None, npts=None, scale=True, color=None):
        self.name =  name  # Name of this result
        self.scale = scale # Whether or not to scale the result by the scale factor
        if color is None:
            color = '#000000'
        self.color = color # Default color
        if npts is None:
            npts = 0
        self.values = np.array(np.zeros(int(npts)), dtype=cvd.result_float)
        self.low    = None
        self.high   = None
        return

    def __repr__(self, *args, **kwargs):
        ''' Use pretty repr, like sc.prettyobj, but displaying full values '''
        output  = sc.prepr(self, skip=['values', 'low', 'high'], use_repr=False)
        output += 'values:\n' + repr(self.values)
        if self.low is not None:
            output += '\nlow:\n' + repr(self.low)
        if self.high is not None:
            output += '\nhigh:\n' + repr(self.high)
        return output

    def __getitem__(self, *args, **kwargs):
        ''' To allow e.g. result[5] instead of result.values[5] '''
        return self.values.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        ''' To allow e.g. result[:] = 1 instead of result.values[:] = 1 '''
        return self.values.__setitem__(*args, **kwargs)

    def __len__(self):
        ''' To allow len(result) instead of len(result.values) '''
        return len(self.values)

    @property
    def npts(self):
        return len(self.values)


def set_metadata(obj):
    ''' Set standard metadata for an object '''
    obj.created = sc.now()
    obj.version = cvv.__version__
    obj.git_info = cvm.git_info()
    return


class BaseSim(ParsObj):
    '''
    The BaseSim class stores various methods useful for the Sim that are not directly
    related to simulating the epidemic. It is not used outside of the Sim object,
    so the separation of methods into the BaseSim and Sim classes is purely to keep
    each one of manageable size.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # Initialize and set the parameters as attributes
        return


    def _disp(self):
        '''
        Print a verbose display of the sim object. Used by repr(). See sim.disp()
        for the user version. Equivalent to sc.prettyobj().
        '''
        return sc.prepr(self)


    def _brief(self):
        '''
        Return a one-line description of a sim -- used internally and by repr();
        see sim.brief() for the user version.
        '''
        # Try to get a detailed description of the sim...
        try:
            if self.results_ready:
                infections = self.summary['cum_infections']
                deaths = self.summary['cum_deaths']
                results = f'{infections:n}⚙, {deaths:n}☠'
            else:
                results = 'not run'

            # Set label string
            labelstr = f'"{self.label}"' if self.label else '<no label>'

            start = sc.date(self['start_day'], as_date=False)
            if self['end_day']:
                end = sc.date(self['end_day'], as_date=False)
            else:
                end = sc.date(self['n_days'], start_date=start)

            pop_size = self['pop_size']
            pop_type = self['pop_type']
            string   = f'Sim({labelstr}; {start} to {end}; pop: {pop_size:n} {pop_type}; epi: {results})'

        # ...but if anything goes wrong, return the default with a warning
        except Exception as E:
            string = sc.objectid(self)
            string += f'Warning, sim appears to be malformed:\n{str(E)}'

        return string


    def update_pars(self, pars=None, create=False, **kwargs):
        ''' Ensure that metaparameters get used properly before being updated '''
        pars = sc.mergedicts(pars, kwargs)
        if pars:
            if pars.get('pop_type'):
                cvpar.reset_layer_pars(pars, force=False)
            if pars.get('prog_by_age'):
                pars['prognoses'] = cvpar.get_prognoses(by_age=pars['prog_by_age'], version=self._default_ver) # Reset prognoses
            super().update_pars(pars=pars, create=create) # Call update_pars() for ParsObj
        return


    def set_metadata(self, simfile):
        ''' Set the metadata for the simulation -- creation time and filename '''
        set_metadata(self)
        if simfile is None:
            datestr = sc.getdate(obj=self.created, dateformat='%Y-%b-%d_%H.%M.%S')
            self.simfile = f'covasim_{datestr}.sim'
        return


    def set_seed(self, seed=-1):
        '''
        Set the seed for the random number stream from the stored or supplied value

        Args:
            seed (None or int): if no argument, use current seed; if None, randomize; otherwise, use and store supplied seed
        '''
        # Unless no seed is supplied, reset it
        if seed != -1:
            self['rand_seed'] = seed
        cvu.set_seed(self['rand_seed'])
        return

    @property
    def n(self):
        ''' Count the number of people -- if it fails, assume none '''
        try: # By default, the length of the people dict
            return len(self.people)
        except: # If it's None or missing
            return 0

    @property
    def scaled_pop_size(self):
        ''' Get the total population size, i.e. the number of agents times the scale factor -- if it fails, assume none '''
        try:
            return self['pop_size']*self['pop_scale']
        except: # If it's None or missing
            return 0

    @property
    def npts(self):
        ''' Count the number of time points '''
        try:
            return int(self['n_days'] + 1)
        except:
            return 0

    @property
    def tvec(self):
        ''' Create a time vector '''
        try:
            return np.arange(self.npts)
        except:
            return np.array([])

    @property
    def datevec(self):
        '''
        Create a vector of dates

        Returns:
            Array of `datetime` instances containing the date associated with each
            simulation time step

        '''
        try:
            return self['start_day'] + self.tvec * dt.timedelta(days=1)
        except:
            return np.array([])


    def day(self, day, *args):
        '''
        Convert a string, date/datetime object, or int to a day (int).

        Args:
            day (str, date, int, or list): convert any of these objects to a day relative to the simulation's start day

        Returns:
            days (int or str): the day(s) in simulation time

        **Example**::

            sim.day('2020-04-05') # Returns 35
        '''
        return sc.day(day, *args, start_day=self['start_day'])


    def date(self, ind, *args, dateformat=None, as_date=False):
        '''
        Convert one or more integer days of simulation time to a date/list of dates --
        by default returns a string, or returns a datetime Date object if as_date is True.
        See also cv.date(), which provides a partly overlapping set of date conversion
        features.

        Args:
            ind (int, list, or array): the index day(s) in simulation time (NB: strings and date objects are accepted, and will be passed unchanged)
            args (list): additional day(s)
            dateformat (str): the format to return the date in
            as_date (bool): whether to return as a datetime date instead of a string

        Returns:
            dates (str, Date, or list): the date(s) corresponding to the simulation day(s)

        **Examples**::

            sim = cv.Sim()
            sim.date(34) # Returns '2020-04-04'
            sim.date([34, 54]) # Returns ['2020-04-04', '2020-04-24']
            sim.date([34, '2020-04-24']) # Returns ['2020-04-04', '2020-04-24']
            sim.date(34, 54, as_date=True) # Returns [datetime.date(2020, 4, 4), datetime.date(2020, 4, 24)]
        '''

        # Handle inputs
        if not isinstance(ind, list): # If it's a number, string, or dateobj, convert it to a list
            ind = sc.promotetolist(ind)
        ind.extend(args)
        if dateformat is None:
            dateformat = '%Y-%m-%d'

        # Do the conversion
        dates = []
        for raw in ind:
            if sc.isnumber(raw):
                date_obj = sc.date(self['start_day'], as_date=True) + dt.timedelta(days=int(raw))
            else:
                date_obj = sc.date(raw, as_date=True)
            if as_date:
                dates.append(date_obj)
            else:
                dates.append(date_obj.strftime(dateformat))

        # Return a string rather than a list if only one provided
        if len(ind)==1:
            dates = dates[0]

        return dates


    def result_keys(self):
        ''' Get the actual results objects, not other things stored in sim.results '''
        keys = [key for key in self.results.keys() if isinstance(self.results[key], Result)]
        return keys


    def copy(self):
        ''' Returns a deep copy of the sim '''
        return sc.dcp(self)


    def export_results(self, for_json=True, filename=None, indent=2, *args, **kwargs):
        '''
        Convert results to dict -- see also to_json().

        The results written to Excel must have a regular table shape, whereas
        for the JSON output, arbitrary data shapes are supported.

        Args:
            for_json (bool): if False, only data associated with Result objects will be included in the converted output
            filename (str): filename to save to; if None, do not save
            indent (int): indent (int): if writing to file, how many indents to use per nested level
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            resdict (dict): dictionary representation of the results

        '''

        if not self.results_ready:
            errormsg = 'Please run the sim before exporting the results'
            raise RuntimeError(errormsg)

        resdict = {}
        resdict['t'] = self.results['t'] # Assume that there is a key for time

        if for_json:
            resdict['timeseries_keys'] = self.result_keys()
        for key,res in self.results.items():
            if isinstance(res, Result):
                resdict[key] = res.values
            elif for_json:
                if key == 'date':
                    resdict[key] = [str(d) for d in res] # Convert dates to strings
                else:
                    resdict[key] = res
        if filename is not None:
            sc.savejson(filename=filename, obj=resdict, indent=indent, *args, **kwargs)
        return resdict


    def export_pars(self, filename=None, indent=2, *args, **kwargs):
        '''
        Return parameters for JSON export -- see also to_json().

        This method is required so that interventions can specify
        their JSON-friendly representation.

        Args:
            filename (str): filename to save to; if None, do not save
            indent (int): indent (int): if writing to file, how many indents to use per nested level
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            pardict (dict): a dictionary containing all the parameter values
        '''
        pardict = {}
        for key in self.pars.keys():
            if key == 'interventions':
                pardict[key] = [intervention.to_json() for intervention in self.pars[key]]
            elif key == 'start_day':
                pardict[key] = str(self.pars[key])
            else:
                pardict[key] = self.pars[key]
        if filename is not None:
            sc.savejson(filename=filename, obj=pardict, indent=indent, *args, **kwargs)
        return pardict


    def to_json(self, filename=None, keys=None, tostring=False, indent=2, verbose=False, *args, **kwargs):
        '''
        Export results as JSON.

        Args:
            filename (str): if None, return string; else, write to file
            keys (str or list): attributes to write to json (default: results, parameters, and summary)
            tostring (bool): if not writing to file, whether to write to string (alternative is sanitized dictionary)
            indent (int): if writing to file, how many indents to use per nested level
            verbose (bool): detail to print
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            A unicode string containing a JSON representation of the results,
            or writes the JSON file to disk

        **Examples**::

            json = sim.to_json()
            sim.to_json('results.json')
            sim.to_json('summary.json', keys='summary')
        '''

        # Handle keys
        if keys is None:
            keys = ['results', 'pars', 'summary']
        keys = sc.promotetolist(keys)

        # Convert to JSON-compatible format
        d = {}
        for key in keys:
            if key == 'results':
                resdict = self.export_results(for_json=True)
                d['results'] = resdict
            elif key in ['pars', 'parameters']:
                pardict = self.export_pars()
                d['parameters'] = pardict
            elif key == 'summary':
                d['summary'] = dict(sc.dcp(self.summary))
            else:
                try:
                    d[key] = sc.sanitizejson(getattr(self, key))
                except Exception as E:
                    errormsg = f'Could not convert "{key}" to JSON: {str(E)}; continuing...'
                    print(errormsg)

        if filename is None:
            output = sc.jsonify(d, tostring=tostring, indent=indent, verbose=verbose, *args, **kwargs)
        else:
            output = sc.savejson(filename=filename, obj=d, indent=indent, *args, **kwargs)

        return output


    def to_excel(self, filename=None):
        '''
        Export results as XLSX

        Args:
            filename (str): if None, return string; else, write to file

        Returns:
            An sc.Spreadsheet with an Excel file, or writes the file to disk

        '''
        resdict = self.export_results(for_json=False)
        result_df = pd.DataFrame.from_dict(resdict)
        result_df.index = self.datevec
        result_df.index.name = 'date'

        par_df = pd.DataFrame.from_dict(sc.flattendict(self.pars, sep='_'), orient='index', columns=['Value'])
        par_df.index.name = 'Parameter'

        spreadsheet = sc.Spreadsheet()
        spreadsheet.freshbytes()
        with pd.ExcelWriter(spreadsheet.bytes, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, sheet_name='Results')
            par_df.to_excel(writer, sheet_name='Parameters')
        spreadsheet.load()

        if filename is None:
            output = spreadsheet
        else:
            output = spreadsheet.save(filename)

        return output


    def shrink(self, skip_attrs=None, in_place=True):
        '''
        "Shrinks" the simulation by removing the people, and returns
        a copy of the "shrunken" simulation. Used to reduce the memory required
        for saved files.

        Args:
            skip_attrs (list): a list of attributes to skip in order to perform the shrinking; default "people"

        Returns:
            shrunken_sim (Sim): a Sim object with the listed attributes removed
        '''

        # By default, skip people (~90% of memory), the popdict (which is usually empty anyway), and _orig_pars (which is just a backup)
        if skip_attrs is None:
            skip_attrs = ['popdict', 'people', '_orig_pars']

        # Create the new object, and copy original dict, skipping the skipped attributes
        if in_place:
            for attr in skip_attrs:
                setattr(self, attr, None)
            return
        else:
            shrunken_sim = object.__new__(self.__class__)
            shrunken_sim.__dict__ = {k:(v if k not in skip_attrs else None) for k,v in self.__dict__.items()}
            return shrunken_sim


    def save(self, filename=None, keep_people=None, skip_attrs=None, **kwargs):
        '''
        Save to disk as a gzipped pickle.

        Args:
            filename (str or None): the name or path of the file to save to; if None, uses stored
            kwargs: passed to sc.makefilepath()

        Returns:
            filename (str): the validated absolute path to the saved file

        **Example**::

            sim.save() # Saves to a .sim file with the date and time of creation by default
        '''

        # Set keep_people based on whether or not we're in the middle of a run
        if keep_people is None:
            if self.initialized and not self.results_ready:
                keep_people = True
            else:
                keep_people = False

        # Handle the filename
        if filename is None:
            filename = self.simfile
        filename = sc.makefilepath(filename=filename, **kwargs)
        self.filename = filename # Store the actual saved filename

        # Handle the shrinkage and save
        if skip_attrs or not keep_people:
            obj = self.shrink(skip_attrs=skip_attrs, in_place=False)
        else:
            obj = self
        cvm.save(filename=filename, obj=obj)

        return filename


    @staticmethod
    def load(filename, *args, **kwargs):
        '''
        Load from disk from a gzipped pickle.

        Args:
            filename (str): the name or path of the file to load from
            kwargs: passed to cv.load()

        Returns:
            sim (Sim): the loaded simulation object

        **Example**::

            sim = cv.Sim.load('my-simulation.sim')
        '''
        sim = cvm.load(filename, *args, **kwargs)
        if not isinstance(sim, BaseSim):
            errormsg = f'Cannot load object of {type(sim)} as a Sim object'
            raise TypeError(errormsg)
        return sim


    def _get_ia(self, which, label=None, partial=False, as_list=False, as_inds=False, die=True, first=False):
        ''' Helper method for get_interventions() and get_analyzers(); see get_interventions() docstring '''

        # Handle inputs
        if which not in ['interventions', 'analyzers']:
            errormsg = f'This method is only defined for interventions and analyzers, not "{which}"'
            raise ValueError(errormsg)

        ia_list = self.pars[which] # List of interventions or analyzers
        n_ia = len(ia_list) # Number of interventions/analyzers

        if label == 'summary': # Print a summary of the interventions
            df = pd.DataFrame(columns=['ind', 'label', 'type'])
            for ind,ia_obj in enumerate(ia_list):
                df = df.append(dict(ind=ind, label=str(ia_obj.label), type=type(ia_obj)), ignore_index=True)
            print(f'Summary of {which}:')
            print(df)
            return

        else: # Standard usage case
            position = 0 if first else -1 # Choose either the first or last element
            if label is None:
                label = position # Get the last element
            labels = sc.promotetolist(label)

            # Calculate the matches
            matches = []
            match_inds = []
            for label in labels:
                if sc.isnumber(label):
                    matches.append(ia_list[label]) # This will raise an exception if an invalid index is given
                    label = n_ia + label if label<0 else label # Convert to a positive number
                    match_inds.append(label)
                elif sc.isstring(label) or isinstance(label, type):
                    for ind,ia_obj in enumerate(ia_list):
                        if sc.isstring(label) and ia_obj.label == label or (partial and (label in str(ia_obj.label))):
                            matches.append(ia_obj)
                            match_inds.append(ind)
                        elif isinstance(label, type) and isinstance(ia_obj, label):
                            matches.append(ia_obj)
                            match_inds.append(ind)
                else:
                    errormsg = f'Could not interpret label type "{type(label)}": should be str, int, or {which} class'
                    raise TypeError(errormsg)

            # Parse the output options
            if as_inds:
                output = match_inds
            elif as_list:
                output = matches
            else: # Normal case, return actual interventions
                if len(matches) == 0:
                    if die:
                        errormsg = f'No {which} matching "{label}" were found'
                        raise ValueError(errormsg)
                    else:
                        output = None
                else:
                    output = matches[position] # Return either the first or last match

            return output


    def get_interventions(self, label=None, partial=False, as_inds=False):
        '''
        Find the matching intervention(s) by label, index, or type. If None, return
        all interventions. If the label provided is "summary", then print a summary
        of the interventions (index, label, type).

        Args:
            label (str, int, Intervention, list): the label, index, or type of intervention to get; if a list, iterate over one of those types
            partial (bool): if true, return partial matches (e.g. 'beta' will match all beta interventions)
            as_inds (bool): if true, return matching indices instead of the actual interventions

        **Examples**::

            tp = cv.test_prob(symp_prob=0.1)
            cb1 = cv.change_beta(days=5, changes=0.3, label='NPI')
            cb2 = cv.change_beta(days=10, changes=0.3, label='Masks')
            sim = cv.Sim(interventions=[tp, cb1, cb2])
            cb1, cb2 = sim.get_interventions(cv.change_beta)
            tp, cb2 = sim.get_interventions([0,2])
            ind = sim.get_interventions(cv.change_beta, as_inds=True) # Returns [1,2]
            sim.get_interventions('summary') # Prints a summary
        '''
        return self._get_ia('interventions', label=label, partial=partial, as_inds=as_inds, as_list=True)


    def get_intervention(self, label=None, partial=False, first=False, die=True):
        '''
        Like get_interventions(), find the matching intervention(s) by label,
        index, or type. If more than one intervention matches, return the last
        by default. If no label is provided, return the last intervention in the list.

        Args:
            label (str, int, Intervention, list): the label, index, or type of intervention to get; if a list, iterate over one of those types
            partial (bool): if true, return partial matches (e.g. 'beta' will match all beta interventions)
            first (bool): if true, return first matching intervention (otherwise, return last)
            die (bool): whether to raise an exception if no intervention is found

        **Examples**::

            tp = cv.test_prob(symp_prob=0.1)
            cb = cv.change_beta(days=5, changes=0.3, label='NPI')
            sim = cv.Sim(interventions=[tp, cb])
            cb = sim.get_intervention('NPI')
            cb = sim.get_intervention('NP', partial=True)
            cb = sim.get_intervention(cv.change_beta)
            cb = sim.get_intervention(1)
            cb = sim.get_intervention()
            tp = sim.get_intervention(first=True)
        '''
        return self._get_ia('interventions', label=label, partial=partial, first=first, die=die, as_inds=False, as_list=False)


    def get_analyzers(self, label=None, partial=False, as_inds=False):
        '''
        Same as get_interventions(), but for analyzers.
        '''
        return self._get_ia('analyzers', label=label, partial=partial, as_list=True, as_inds=as_inds)


    def get_analyzer(self, label=None, partial=False, first=False, die=True):
        '''
        Same as get_intervention(), but for analyzers.
        '''
        return self._get_ia('analyzers', label=label, partial=partial, first=first, die=die, as_inds=False, as_list=False)


#%% Define people classes

class BasePeople(FlexPretty):
    '''
    A class to handle all the boilerplate for people -- note that as with the
    BaseSim vs Sim classes, everything interesting happens in the People class,
    whereas this class exists to handle the less interesting implementation details.
    '''

    def __getitem__(self, key):
        ''' Allow people['attr'] instead of getattr(people, 'attr')
            If the key is an integer, alias `people.person()` to return a `Person` instance
        '''

        if isinstance(key, int):
            return self.person(key)

        try:
            return self.__dict__[key]
        except:
            errormsg = f'Key "{key}" is not a valid attribute of people'
            raise AttributeError(errormsg)


    def __setitem__(self, key, value):
        ''' Ditto '''
        if self._lock and key not in self.__dict__:
            errormsg = f'Key "{key}" is not a valid attribute of people'
            raise AttributeError(errormsg)
        self.__dict__[key] = value
        return


    def __len__(self):
        ''' This is just a scalar, but validate() and _resize_arrays() make sure it's right '''
        return self.pop_size


    def __iter__(self):
        ''' Iterate over people '''
        for i in range(len(self)):
            yield self[i]


    def __add__(self, people2):
        ''' Combine two people arrays '''
        newpeople = sc.dcp(self)
        for key in self.keys():
            newpeople.set(key, np.concatenate([newpeople[key], people2[key]]), die=False) # Allow size mismatch

        # Validate
        newpeople.pop_size += people2.pop_size
        newpeople.validate()

        # Reassign UIDs so they're unique
        newpeople.set('uid', np.arange(len(newpeople)))

        return newpeople


    def _brief(self):
        '''
        Return a one-line description of the people -- used internally and by repr();
        see people.brief() for the user version.
        '''
        try:
            layerstr = ', '.join([str(k) for k in self.layer_keys()])
            string   = f'People(n={len(self):0n}; layers: {layerstr})'
        except Exception as E:
            string = sc.objectid(self)
            string += f'Warning, multisim appears to be malformed:\n{str(E)}'
        return string


    def summarize(self, output=False):
        ''' Print a summary of the people -- same as brief '''
        return self.brief(output=output)


    def set(self, key, value, die=True):
        ''' Ensure sizes and dtypes match '''
        current = self[key]
        value = np.array(value, dtype=self._dtypes[key]) # Ensure it's the right type
        if die and len(value) != len(current):
            errormsg = f'Length of new array does not match current ({len(value)} vs. {len(current)})'
            raise IndexError(errormsg)
        self[key] = value
        return


    def get(self, key):
        ''' Convenience method -- key can be string or list of strings '''
        if isinstance(key, str):
            return self[key]
        elif isinstance(key, list):
            arr = np.zeros((len(self), len(key)))
            for k,ky in enumerate(key):
                arr[:,k] = self[ky]
            return arr


    def true(self, key):
        ''' Return indices matching the condition '''
        return self[key].nonzero()[0]


    def false(self, key):
        ''' Return indices not matching the condition '''
        return (~self[key]).nonzero()[0]


    def defined(self, key):
        ''' Return indices of people who are not-nan '''
        return (~np.isnan(self[key])).nonzero()[0]


    def undefined(self, key):
        ''' Return indices of people who are nan '''
        return np.isnan(self[key]).nonzero()[0]


    def count(self, key):
        ''' Count the number of people for a given key '''
        return (self[key]>0).sum()


    def count_not(self, key):
        ''' Count the number of people who do not have a property for a given key '''
        return (self[key]==0).sum()


    def set_pars(self, pars):
        '''
        Very simple method to re-link the parameters stored in the people object
        to the sim containing it: included simply for the sake of being explicit.
        '''
        self.pars = pars
        return


    def keys(self):
        ''' Returns keys for all properties of the people object '''
        return self.meta.all_states[:]


    def person_keys(self):
        ''' Returns keys specific to a person (e.g., their age) '''
        return self.meta.person[:]


    def state_keys(self):
        ''' Returns keys for different states of a person (e.g., symptomatic) '''
        return self.meta.states[:]


    def date_keys(self):
        ''' Returns keys for different event dates (e.g., date a person became symptomatic) '''
        return self.meta.dates[:]


    def dur_keys(self):
        ''' Returns keys for different durations (e.g., the duration from exposed to infectious) '''
        return self.meta.durs[:]


    def layer_keys(self):
        ''' Get the available contact keys -- try contacts first, then beta_layer '''
        try:
            keys = list(self.contacts.keys())
        except: # If not fully initialized
            try:
                keys = list(self.pars['beta_layer'].keys())
            except: # If not even partially initialized
                keys = []
        return keys


    def indices(self):
        ''' The indices of each people array '''
        return np.arange(len(self))


    def validate(self, die=True, verbose=False):

        # Check that the keys match
        contact_layer_keys = set(self.contacts.keys())
        layer_keys    = set(self.layer_keys())
        if contact_layer_keys != layer_keys:
            errormsg = f'Parameters layers {layer_keys} are not consistent with contact layers {contact_layer_keys}'
            raise ValueError(errormsg)

        # Check that the length of each array is consistent
        expected_len = len(self)
        for key in self.keys():
            actual_len = len(self[key])
            if actual_len != expected_len:
                if die:
                    errormsg = f'Length of key "{key}" did not match population size ({actual_len} vs. {expected_len})'
                    raise IndexError(errormsg)
                else:
                    if verbose:
                        print(f'Resizing "{key}" from {actual_len} to {expected_len}')
                    self._resize_arrays(keys=key)

        # Check that the layers are valid
        for layer in self.contacts.values():
            layer.validate()

        return


    def _resize_arrays(self, pop_size=None, keys=None):
        ''' Resize arrays if any mismatches are found '''
        if pop_size is None:
            pop_size = len(self)
        self.pop_size = pop_size
        if keys is None:
            keys = self.keys()
        keys = sc.promotetolist(keys)
        for key in keys:
            self[key].resize(pop_size, refcheck=False)
        return


    def to_df(self):
        ''' Convert to a Pandas dataframe '''
        df = pd.DataFrame.from_dict({key:self[key] for key in self.keys()})
        return df


    def to_arr(self):
        ''' Return as numpy array '''
        arr = np.empty((len(self), len(self.keys())), dtype=cvd.default_float)
        for k,key in enumerate(self.keys()):
            if key == 'uid':
                arr[:,k] = np.arange(len(self))
            else:
                arr[:,k] = self[key]
        return arr


    def person(self, ind):
        ''' Method to create person from the people '''
        p = Person()
        for key in self.meta.all_states:
            setattr(p, key, self[key][ind])

        contacts = {}
        for lkey, layer in self.contacts.items():
            contacts[lkey] = layer.find_contacts(ind)
        p.contacts = contacts

        return p


    def to_people(self):
        ''' Return all people as a list '''
        return list(self)


    def from_people(self, people, resize=True):
        ''' Convert a list of people back into a People object '''

        # Handle population size
        pop_size = len(people)
        if resize:
            self._resize_arrays(pop_size=pop_size)

        # Iterate over people -- slow!
        for p,person in enumerate(people):
            for key in self.keys():
                self[key][p] = getattr(person, key)

        return


    def init_contacts(self, reset=False):
        ''' Initialize the contacts dataframe with the correct columns and data types '''

        # Create the contacts dictionary
        contacts = Contacts(layer_keys=self.layer_keys())

        if self.contacts is None or reset: # Reset all
            self.contacts = contacts
        else: # Only replace specified keys
            for key,layer in contacts.items():
                self.contacts[key] = layer
        return


    def add_contacts(self, contacts, lkey=None, beta=None):
        '''
        Add new contacts to the array. See also contacts.add_layer().
        '''

        # If no layer key is supplied and it can't be worked out from defaults, use the first layer
        if lkey is None:
            lkey = self.layer_keys()[0]

        # Validate the supplied contacts
        if isinstance(contacts, Contacts):
            new_contacts = contacts
        elif isinstance(contacts, Layer):
            new_contacts = {}
            new_contacts[lkey] = contacts
        elif sc.checktype(contacts, 'array'):
            new_contacts = {}
            new_contacts[lkey] = pd.DataFrame(data=contacts)
        elif isinstance(contacts, dict):
            new_contacts = {}
            new_contacts[lkey] = pd.DataFrame.from_dict(contacts)
        elif isinstance(contacts, list): # Assume it's a list of contacts by person, not an edgelist
            new_contacts = self.make_edgelist(contacts) # Assume contains key info
        else:
            errormsg = f'Cannot understand contacts of type {type(contacts)}; expecting dataframe, array, or dict'
            raise TypeError(errormsg)

        # Ensure the columns are right and add values if supplied
        for lkey, new_layer in new_contacts.items():
            n = len(new_layer['p1'])
            if 'beta' not in new_layer.keys() or len(new_layer['beta']) != n:
                if beta is None:
                    beta = 1.0
                beta = cvd.default_float(beta)
                new_layer['beta'] = np.ones(n, dtype=cvd.default_float)*beta

            # Create the layer if it doesn't yet exist
            if lkey not in self.contacts:
                self.contacts[lkey] = Layer()

            # Actually include them, and update properties if supplied
            for col in self.contacts[lkey].keys(): # Loop over the supplied columns
                self.contacts[lkey][col] = np.concatenate([self.contacts[lkey][col], new_layer[col]])
            self.contacts[lkey].validate()

        return


    def make_edgelist(self, contacts):
        '''
        Parse a list of people with a list of contacts per person and turn it
        into an edge list.
        '''

        # Handle layer keys
        lkeys = self.layer_keys()
        if len(contacts):
            contact_keys = contacts[0].keys() # Pull out the keys of this contact list
            lkeys += [key for key in contact_keys if key not in lkeys] # Extend the layer keys

        # Initialize the new contacts
        new_contacts = Contacts(layer_keys=lkeys)
        for lkey in lkeys:
            new_contacts[lkey]['p1']    = [] # Person 1 of the contact pair
            new_contacts[lkey]['p2']    = [] # Person 2 of the contact pair

        # Populate the new contacts
        for p,cdict in enumerate(contacts):
            for lkey,p_contacts in cdict.items():
                n = len(p_contacts) # Number of contacts
                new_contacts[lkey]['p1'].extend([p]*n) # e.g. [4, 4, 4, 4]
                new_contacts[lkey]['p2'].extend(p_contacts) # e.g. [243, 4538, 7,19]

        # Turn into a dataframe
        for lkey in lkeys:
            new_layer = Layer()
            for ckey,value in new_contacts[lkey].items():
                new_layer[ckey] = np.array(value, dtype=new_layer.meta[ckey])
            new_contacts[lkey] = new_layer

        return new_contacts


    @staticmethod
    def remove_duplicates(df):
        ''' Sort the dataframe and remove duplicates -- note, not extensively tested '''
        p1 = df[['p1', 'p2']].values.min(1) # Reassign p1 to be the lower-valued of the two contacts
        p2 = df[['p1', 'p2']].values.max(1) # Reassign p2 to be the higher-valued of the two contacts
        df['p1'] = p1
        df['p2'] = p2
        df.sort_values(['p1', 'p2'], inplace=True) # Sort by p1, then by p2
        df.drop_duplicates(['p1', 'p2'], inplace=True) # Remove duplicates
        df = df[df['p1'] != df['p2']] # Remove self connections
        df.reset_index(inplace=True, drop=True)
        return df


class Person(sc.prettyobj):
    '''
    Class for a single person. Note: this is largely deprecated since sim.people
    is now based on arrays rather than being a list of people.
    '''
    def __init__(self, pars=None, uid=None, age=-1, sex=-1, contacts=None):
        self.uid         = uid # This person's unique identifier
        self.age         = cvd.default_float(age) # Age of the person (in years)
        self.sex         = cvd.default_int(sex) # Female (0) or male (1)
        self.contacts    = contacts # Contacts
        # self.infected = [] #: Record the UIDs of all people this person infected
        # self.infected_by = None #: Store the UID of the person who caused the infection. If None but person is infected, then it was an externally seeded infection
        return


class FlexDict(dict):
    '''
    A dict that allows more flexible element access: in addition to obj['a'],
    also allow obj[0]. Lightweight implementation of the Sciris odict class.
    '''

    def __getitem__(self, key):
        ''' Lightweight odict -- allow indexing by number, with low performance '''
        try:
            return super().__getitem__(key)
        except KeyError as KE:
            try: # Assume it's an integer
                dictkey = self.keys()[key]
                return self[dictkey]
            except:
                raise sc.KeyNotFoundError(KE) # Raise the original error

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())

    def items(self):
        return list(super().items())


class Contacts(FlexDict):
    '''
    A simple (for now) class for storing different contact layers.
    '''
    def __init__(self, layer_keys=None):
        if layer_keys is not None:
            for key in layer_keys:
                self[key] = Layer()
        return

    def __repr__(self):
        ''' Use slightly customized repr'''
        keys_str = ', '.join([str(k) for k in self.keys()])
        output = f'Contacts({keys_str})\n'
        for key in self.keys():
            output += f'\n"{key}": '
            output += self[key].__repr__() + '\n'
        return output


    def __len__(self):
        ''' The length of the contacts is the length of all the layers '''
        output = 0
        for key in self.keys():
            try:
                output += len(self[key])
            except:
                pass
        return output


    def add_layer(self, **kwargs):
        '''
        Small method to add one or more layers to the contacts. Layers should
        be provided as keyword arguments.

        **Example**::

            hospitals_layer = cv.Layer()
            sim.people.contacts.add_layer(hospitals=hospitals_layer)
        '''
        for lkey,layer in kwargs.items():
            layer.validate()
            self[lkey] = layer
        return


    def pop_layer(self, *args):
        '''
        Remove the layer(s) from the contacts.

        **Example**::

            sim.people.contacts.pop_layer('hospitals')

        Note: while included here for convenience, this operation is equivalent
        to simply popping the key from the contacts dictionary.
        '''
        for lkey in args:
            self.pop(lkey)
        return


class Layer(FlexDict):
    ''' A small class holding a single layer of contacts '''

    def __init__(self, **kwargs):
        self.meta = {
            'p1':    cvd.default_int,   # Person 1
            'p2':    cvd.default_int,   # Person 2
            'beta':  cvd.default_float, # Default transmissibility for this contact type
        }
        self.basekey = 'p1' # Assign a base key for calculating lengths and performing other operations

        # Initialize the keys of the layers
        for key,dtype in self.meta.items():
            self[key] = np.empty((0,), dtype=dtype)

        # Set data, if provided
        for key,value in kwargs.items():
            self[key] = np.array(value, dtype=self.meta[key])

        return


    def __len__(self):
        try:
            return len(self[self.basekey])
        except:
            return 0


    def __repr__(self):
        ''' Convert to a dataframe for printing '''
        keys_str = ', '.join(self.keys())
        output = f'Layer({keys_str})\n'
        output += self.to_df().__repr__()
        return output


    def __contains__(self, item):
        """
        Check if a person is present in a layer

        Args:
            item: Person index

        Returns: True if person index appears in any interactions

        """
        return (item in self['p1']) or (item in self['p2'])

    @property
    def members(self):
        """
        Return sorted array of all members
        """
        return np.unique([self['p1'], self['p2']])


    def meta_keys(self):
        ''' Return the keys for the layer's meta information -- i.e., p1, p2, beta '''
        return self.meta.keys()


    def validate(self):
        ''' Check the integrity of the layer: right types, right lengths '''
        n = len(self[self.basekey])
        for key,dtype in self.meta.items():
            if dtype:
                actual = self[key].dtype
                expected = dtype
                if actual != expected:
                    errormsg = f'Expecting dtype "{expected}" for layer key "{key}"; got "{actual}"'
                    raise TypeError(errormsg)
            actual_n = len(self[key])
            if n != actual_n:
                errormsg = f'Expecting length {n} for layer key "{key}"; got {actual_n}'
                raise TypeError(errormsg)
        return


    def pop_inds(self, inds):
        '''
        "Pop" the specified indices from the edgelist and return them as a dict.
        Returns in the right format to be used with layer.append().

        Args:
            inds (int, array, slice): the indices to be removed
        '''
        output = {}
        for key in self.meta_keys():
            output[key] = self[key][inds] # Copy to the output object
            self[key] = np.delete(self[key], inds) # Remove from the original
        return output


    def append(self, contacts):
        '''
        Append contacts to the current layer.

        Args:
            contacts (dict): a dictionary of arrays with keys p1,p2,beta, as returned from layer.pop_inds()
        '''
        for key in self.keys():
            new_arr = contacts[key]
            n_curr = len(self[key]) # Current number of contacts
            n_new = len(new_arr) # New contacts to add
            n_total = n_curr + n_new # New size
            self[key] = np.resize(self[key], n_total) # Resize to make room, preserving dtype
            self[key][n_curr:] = new_arr # Copy contacts into the layer
        return


    def to_df(self):
        ''' Convert to dataframe '''
        df = pd.DataFrame.from_dict(self)
        return df


    def from_df(self, df):
        ''' Convert from a dataframe '''
        for key in self.meta_keys():
            self[key] = df[key].to_numpy()
        return self


    def find_contacts(self, inds, as_array=True):
        """
        Find all contacts of the specified people

        For some purposes (e.g. contact tracing) it's necessary to find all of the contacts
        associated with a subset of the people in this layer. Since contacts are bidirectional
        it's necessary to check both P1 and P2 for the target indices. The return type is a Set
        so that there is no duplication of indices (otherwise if the Layer has explicit
        symmetric interactions, they could appear multiple times). This is also for performance so
        that the calling code doesn't need to perform its own unique() operation. Note that
        this cannot be used for cases where multiple connections count differently than a single
        infection, e.g. exposure risk.

        Args:
            inds (array): indices of people whose contacts to return
            as_array (bool): if true, return as sorted array (otherwise, return as unsorted set)

        Returns:
            contact_inds (array): a set of indices for pairing partners

        Example: If there were a layer with
        - P1 = [1,2,3,4]
        - P2 = [2,3,1,4]
        Then find_contacts([1,3]) would return {1,2,3}
        """

        # Check types
        if not isinstance(inds, np.ndarray):
            inds = sc.promotetoarray(inds)
        if inds.dtype != np.int64: # This is int64 since indices often come from cv.true(), which returns int64
            inds = np.array(inds, dtype=np.int64)

        # Find the contacts
        contact_inds = cvu.find_contacts(self['p1'], self['p2'], inds)
        if as_array:
            contact_inds = np.fromiter(contact_inds, dtype=cvd.default_int)
            contact_inds.sort()  # Sorting ensures that the results are reproducible for a given seed as well as being identical to previous versions of Covasim

        return contact_inds
