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
logger = logging.getLogger('mdsapt.config')


class InputError(Exception):
    """Raised when error is found in the yaml input"""
    pass


class InputReader(object):
    """Reader for yaml inputs"""

    top_path: str
    trj_path: str
    ag_sel: List[int]
    ag_pair: List[List[int]]
    trj_settings: Optional[dict]
    sys_settings: Optional[dict]
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
            logger.warning('error loading file')

    def _save_params(self, yaml_dict: dict) -> None:
        self.top_path = yaml_dict['topology_path']
        self.trj_path = yaml_dict['trajectory_paths']
        self.ag_sel = yaml_dict['selection_resid_num']
        self.ag_pair = yaml_dict['int_pairs']
        self.trj_settings = yaml_dict['trajectory_settings']
        self.sys_settings = yaml_dict['system_settings']
        self.start = yaml_dict['trajectory_settings']['start']
        self.stop = yaml_dict['trajectory_settings']['stop']
        self.step = yaml_dict['trajectory_settings']['step']
        self.pH = yaml_dict['trajectory_settings']['pH']
        self.ncpus = yaml_dict['system_settings']['ncpus']
        self.memory = yaml_dict['system_settings']['memory']
        self.walltime = yaml_dict['system_settings']['time']

    @staticmethod
    def _check_inputs(yaml_dict: dict) -> None:
        # Checking inputs of yaml file
        try:
            top_path = yaml_dict['topology_path']
            trj_path = yaml_dict['trajectory_paths']
            ag_sel = yaml_dict['selection_resid_num']
            ag_pair = yaml_dict['int_pairs']
            trj_settings = yaml_dict['trajectory_settings']
            sys_settings = yaml_dict['system_settings']



        except KeyError:
            logger.fatal('Invalid YAML file')
            assert InputError

        try:
            if not os.path.exists(os.path.join(os.getcwd(), top_path)):
                raise InputError
            for f in trj_path:
                if not os.path.exists(os.path.join(os.getcwd(), f)):
                    raise InputError
            unv = mda.Universe(os.path.join(os.getcwd(), top_path), [os.path.join(os.getcwd(), x) for x in trj_path])
        except mda.exceptions.NoDataError or InputError:
            logger.fatal('MD file error')
            raise InputError

        # Testing names and selections
        for sel in ag_sel:
            try:
                ag = unv.select_atoms(f'resid {sel}')
            except mda.SelectionError:
                raise InputError('Error in selection: {}'.format(sel))

        try:
            start = trj_settings['start']
            step = trj_settings['step']
            stop = trj_settings['stop']
            pH = trj_settings['pH']
            cpu = sys_settings['ncpu']
            mem = sys_settings['memory']
            time = sys_settings['time']

            for pair in ag_pair:
                if len(pair) != 4:
                    raise InputError('Pairs must be a python list of string with 4 items')
                found0 = False
                found1 = False
                for name in ag_sel:
                    if pair[0] == name:
                        found0 = True
                    if pair[1] == name:
                        found1 = True
                if found0 is False:
                    raise InputError(f'{pair[0]} in {pair} group_pair_selections is not in defined in atom_group_names')
                if found1 is False:
                    raise InputError(f'{pair[1]} in {pair} group_pair_selections is not in defined in atom_group_names')

                if start >= stop:
                    raise InputError('Start is greater than or equal to stop')
                if step >= stop:
                    raise InputError('Step is greater than or equal to stop')
                if step == 0:
                    raise InputError('Step cannot be 0')

                if len(unv.trajectory) < stop:
                    raise InputError('Stop exceeds length of trajectory.')

        except KeyError or InputError as err:
            logger.fatal(f'{err} Error in trajectory settings')
            assert InputError

        logger.info('Input Parameters Accepted')
