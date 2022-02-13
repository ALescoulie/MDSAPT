r"""
:mod:`mdsapt.reader` -- Reads input file and saves configuration
================================================================

MDSAPT uses an yaml file to get user's configurations for SAPT calculations
class`mdsapt.reader.InputReader` is responsible for reading the yaml file and
returning the information from it. If a yaml file is needed it can be generated
using the included *mdsapt_get_runinput* script.

.. autoexception:: InputError

.. autoclass:: InputReader
    :members:
    :inherited-members:
"""

import os
from typing import List, Optional

import yaml

import MDAnalysis as mda

import logging
logger = logging.getLogger('mdsapt.reader')


class InputError(Exception):
    """Raised when error is found in the yaml input"""
    pass


class InputReader(object):
    """Reader for yaml inputs"""

    _input_type: str
    top_path: str
    trj_path: str
    ag_sel: List[int]
    ag_pair: List[List[int]]
    trj_settings: dict
    sys_settings: dict
    opt_settings: dict
    sapt_settings: dict
    sapt_method: str
    sapt_basis: str
    sapt_out: bool
    start: int
    stop: int
    step: int
    pH: float
    ncpus: int
    memory: int
    walltime: str

    def __init__(self, path) -> None:
        """Reads input file, checks it for validity,
         and saves its data as instance variables.

         Errors in run input will result in
         :class`mdsapt.reader.InputError` being
         raised."""
        self.load_input(path)

    def load_input(self, path: str) -> None:
        """Loads input file from path and records settings.
         If an error is found :class:`mdsapt.reader.InputError`
         is raised.

         :Arguments:
            *path*
                Path to yaml input file."""
        try:
            in_cfg = yaml.safe_load(open(path))
            self._check_inputs(in_cfg)
            self._save_params(in_cfg)
        except IOError or InputError:
            logger.fatal(f'error loading file {path}')
            raise InputError

    def _check_type(self, yaml_dict: dict) -> None:
        if 'topology_directory' in yaml_dict.keys():
            self.input_type = 'docking'
        elif 'topology_path' in yaml_dict.keys():
            self._input_type = 'trajectory'
        else:
            logger.fatal('Input file missing information.')
            raise InputError

    @property
    def input_type(self) -> str:
        return self._input_type

    def _save_params(self, yaml_dict: dict) -> None:
        self.top_path = yaml_dict['topology_path']
        self.trj_path = yaml_dict['trajectory_paths']
        self.ag_sel = yaml_dict['selection_resid_num']
        self.ag_pair = yaml_dict['int_pairs']
        self.trj_settings = yaml_dict['trajectory_settings']
        self.sys_settings = yaml_dict['system_settings']
        self.opt_settings = yaml_dict['opt_settings']
        self.sapt_settings = yaml_dict['sapt_settings']
        self.sapt_method = yaml_dict['sapt_settings']['method']
        self.sapt_basis = yaml_dict['sapt_settings']['basis']
        self.sapt_out = yaml_dict['sapt_settings']['save_psi4_output']
        self.start = yaml_dict['trajectory_settings']['start']
        self.stop = yaml_dict['trajectory_settings']['stop']
        self.step = yaml_dict['trajectory_settings']['step']
        self.pH = yaml_dict['opt_settings']['pH']
        self.ncpus = yaml_dict['system_settings']['ncpus']
        self.memory = yaml_dict['system_settings']['memory']
        self.walltime = yaml_dict['system_settings']['time']

    def _check_inputs(self, yaml_dict) -> None:
        if self.input_type == 'trajectory':
            self._check_trj_inputs(yaml_dict)
        elif self.input_type == 'docking':
            self._check_docking_inputs(yaml_dict)
        else:
            logger.fatal('Non valid input type')
            raise InputError
    
    def _check_trj_inputs(self, yaml_dict: dict) -> None:
        # Checking inputs of yaml file
        try:
            top_path = yaml_dict['topology_path']
            trj_path = yaml_dict['trajectory_paths']
            ag_sel = yaml_dict['selection_resid_num']
            ag_pair = yaml_dict['int_pairs']
            trj_settings = yaml_dict['trajectory_settings']
            sys_settings = yaml_dict['system_settings']
            opt_settings = yaml_dict['opt_settings']
            sapt_settings = yaml_dict['sapt_settings']
        except KeyError as err:
            logger.fatal(f'{err}: missing from YAML file')
            raise InputError
        
        unv = self._check_trj_files(top_path, trj_path)
        self._check_selections(unv, ag_sel, ag_pair)
        self._check_sys_settings(sys_settings)
        self._check_trj_settings(unv, trj_settings)
        self._check_opt_sapt_settings(opt_settings, sapt_settings)
    
    def _check_docking_inputs(self, yaml_dict: dict) -> None:
        try:
            top_path = yaml_dict['topology_directory']
            ag_sel = yaml_dict['selection_resid_num']
            ag_pair = yaml_dict['int_pairs']
            sys_settings = yaml_dict['system_settings']
            opt_settings = yaml_dict['opt_settings']
            sapt_settings = yaml_dict['sapt_settings']
        except KeyError as err:
            logger.fatal(f'{err}: missing from YAML file')
            raise InputError
        
        for path in top_path:
            unv = self._check_top_files(path)
            self._check_selections(unv, ag_sel)
        
        self._check_sys_settings(sys_settings)
        self._check_opt_sapt_settings(opt_settings, sapt_settings)

    @staticmethod 
    def _check_trj_files(top_path: str, trj_path: str) -> mda.Universe:
        try:
            if not os.path.exists(os.path.join(os.getcwd(), top_path)):
                raise InputError
            for f in trj_path:
                if not os.path.exists(os.path.join(os.getcwd(), f)):
                    raise InputError
            unv = mda.Universe(os.path.join(os.getcwd(), top_path), [os.path.join(os.getcwd(), x) for x in trj_path])
            return unv
        except mda.exceptions.NoDataError or InputError or ValueError:
            logger.fatal('MD file error')
            raise InputError

    def _check_top_files(top_path) -> mda.Universe:
        try:
            if not os.path.exists(os.path.join(os.getcwd(), top_path)):
                raise InputError
            unv = mda.Universe(os.path.join(os.getcwd(), top_path))
            return unv
        except mda.exceptions.NoDataError or InputError or ValueError:
            logger.fatal('MD file error')
            raise InputError

    @staticmethod
    def _check_selections(universe: mda.Universe, ag_sel: List[int], ag_pair: Optional[List[int, int]]) -> None:
        # Testing names and selections
        for sel in ag_sel:
            try:
                ag = universe.select_atoms(f'resid {sel} and protein')
            except mda.SelectionError:
                raise InputError('Error in selection: {}'.format(sel))
        
        if ag_pair is not None:
            for pair in ag_pair:
                if len(pair) != 2:
                    logger.fatal('Pairs must be a python list of integers with 2 items')
                    raise InputError
                found0 = False
                found1 = False
                for name in ag_sel:
                    if pair[0] == name:
                        found0 = True
                    if pair[1] == name:
                        found1 = True
                if found0 is False:
                    logger.fatal(f'{pair[0]} in {pair} group_pair_selections is not in defined in atom_group_names')
                    raise InputError
                if found1 is False:
                    logger.fatal(f'{pair[1]} in {pair} group_pair_selections is not in defined in atom_group_names')
                    raise InputError

    @staticmethod
    def _check_sys_settings(sys_settings: dict) -> None:
        try:

            cpu = sys_settings['ncpus']
            mem = sys_settings['memory']
            time = sys_settings['time']
        
        except:
            logger.fatal(f'{err}: missing data in input file')
            raise InputError

    @staticmethod
    def _check_trj_settings(universe: mda.Universe, trj_settings: dict) -> None:

        try:
            start = trj_settings['start']
            step = trj_settings['step']
            stop = trj_settings['stop']
        
        except KeyError:
            logger.fatal(f'{err}: missing data in input file')
            raise InputError

        if start >= stop:
            logger.fatal('Start is greater than or equal to stop')
            raise InputError
        if step >= stop:
            logger.fatal('Step is greater than or equal to stop')
            raise InputError
        if step == 0:
            logger.fatal('Step cannot be 0')
            raise InputError

        if len(universe.trajectory) < stop:
            logger.fatal('Stop exceeds length of trajectory.')
            raise InputError

        logger.info('Input Parameters Accepted')

    @staticmethod
    def _check_opt_sapt_settings(opt_settings: dict, sapt_setting: dict) -> None:
        try:
            pH = opt_settings['pH']
            method = sapt_settings['method']
            basis = sapt_settings['basis']
            settings = sapt_settings['settings']
            save_sapt_out = sapt_settings['save_psi4_output']

        except KeyError as err:

            logger.fatal(f'{err}: missing data in input file')
            raise InputError
