#
#    This file is part of awebox.
#
#    awebox -- A modeling and optimization framework for multi-kite AWE systems.
#    Copyright (C) 2017-2019 Jochem De Schutter, Rachel Leuthold, Moritz Diehl,
#                            ALU Freiburg.
#    Copyright (C) 2018-2019 Thilo Bronnenmeyer, Kiteswarms Ltd.
#    Copyright (C) 2016      Elena Malz, Sebastien Gros, Chalmers UT.
#
#    awebox is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 3 of the License, or (at your option) any later version.
#
#    awebox is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with awebox; if not, write to the Free Software Foundation,
#    Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
#
'''
Class NLP generates an NLP from the model of the tree-structure multi-kite system
_python-3.5 / casadi-3.4.5
- authors: rachel leuthold, jochem de schutter, thilo bronnenmeyer alu-fr 2017-2018
'''
import awebox.tools.print_operations as print_op

from . import discretization

from . import objective

import logging

from . import var_bounds

import time

class NLP(object):

    def __init__(self):
        self.__status = 'NLP not yet built.'
        self.__Outputs = None
        self.__timings = {}

    def build(self, nlp_options, model, formulation):

        logging.info('Building NLP...')

        if self.__status == 'I am an NLP.':

            logging.info('NLP already built.')
            return None

        elif model.status == 'I am a model.' and formulation.status == 'I am a formulation.':

            timer = time.time()
            self.__generate_discretization(nlp_options, model,formulation)
            self.__generate_variable_bounds(nlp_options, model)
            self.__generate_objective(nlp_options, model)

            self.__status = 'I am an NLP.'

            logging.info('NLP built.')
            self.__timings['overall'] = time.time()-timer
            logging.info('NLP construction time: %s', print_op.print_single_timing(self.__timings['overall']))
            logging.info('')
        else:

            raise ValueError('Cannot build NLP without first building model and formulation.')

    def __generate_discretization(self, nlp_options, model, formulation):

        logging.info('discretize problem... ')

        timer = time.time()
        [V,
        P,
        Xdot,
        Xdot_fun,
        g,
        g_fun,
        g_jacobian_fun,
        g_bounds,
        Outputs,
        Outputs_fun,
        Integral_outputs,
        Integral_outputs_fun,
        time_grids,
        Collocation,
        Multiple_shooting] =  discretization.discretize(nlp_options,model,formulation)
        self.__timings['discretization'] = time.time()-timer

        self.__V = V
        self.__P = P
        self.__Xdot = Xdot
        self.__Xdot_fun = Xdot_fun
        self.__g = g
        self.__g_fun = g_fun
        self.__g_jacobian_fun = g_jacobian_fun
        self.__g_bounds = g_bounds
        self.__Outputs = Outputs
        self.__Outputs_fun = Outputs_fun
        self.__Integral_outputs = Integral_outputs
        self.__Integral_outputs_fun = Integral_outputs_fun
        self.__n_k = nlp_options['n_k']
        self.__d = nlp_options['collocation']['d']
        self.__options = nlp_options
        self.__discretization = nlp_options['discretization']
        self.__time_grids = time_grids
        self.__Collocation = Collocation
        self.__Multiple_shooting = Multiple_shooting

        return None

    def __generate_variable_bounds(self, nlp_options, model):

        logging.info('generate variable bounds...')
        [vars_lb, vars_ub] = var_bounds.get_variable_bounds(nlp_options, self.__V, model)

        self.__V_bounds = {'lb': vars_lb, 'ub': vars_ub}

        return None

    def __generate_objective(self, nlp_options, model):

        logging.info('generate objective... ')
        timer = time.time()

        [component_cost_function, component_cost_structure, f_fun, f_jacobian_fun, f_hessian_fun] = objective.get_cost_function_and_structure(nlp_options, self.__V, self.__P, model.variables, model.parameters, self.__Xdot(self.__Xdot_fun(self.__V)), model.outputs, model, self.__Integral_outputs(self.__Integral_outputs_fun(self.__V, self.__P)))

        self.__timings['objective'] = time.time()-timer

        self.__component_cost_fun = component_cost_function
        self.__component_cost_struct = component_cost_structure
        self.__f_fun = f_fun
        self.__f_jacobian_fun = f_jacobian_fun
        self.__f_hessian_fun = f_hessian_fun

        return None

    def get_nlp(self):

        # construct constraints
        g = self.__g_fun(self.__V, self.__P)
        f = self.__f_fun(self.__V, self.__P)

        # fill in nlp dict
        nlp = {'x': self.__V, 'p': self.__P, 'f': f, 'g': g}

        return nlp

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, value):
        logging.warning('Cannot set status object.')

    @property
    def output_components(self):
        return [self.__Outputs, self.__Outputs_fun]

    @output_components.setter
    def output_components(self, value):
        logging.warning('Cannot set outputs object.')

    @property
    def integral_output_components(self):
        return [self.__Integral_outputs, self.__Integral_outputs_fun]

    @integral_output_components.setter
    def integral_output_components(self, value):
        logging.warning('Cannot set integral outputs object.')

    @property
    def V_bounds(self):
        return self.__V_bounds

    @V_bounds.setter
    def V_bounds(self, value):
        logging.warning('Cannot set V_bounds object')

    @property
    def g_bounds(self):
        return self.__g_bounds

    @g_bounds.setter
    def g_bounds(self, value):
        logging.warning('Cannont set g_bounds object')

    @property
    def cost_components(self):
        return self.__component_cost_fun, self.__component_cost_struct

    @cost_components.setter
    def cost_components(self, value):
        logging.warning('Cannot set cost_components object.')

    @property
    def g(self):
        return self.__g

    @g.setter
    def g(self, value):
        logging.warning('Cannot set g object.')

    @property
    def g_fun(self):
        return self.__g_fun

    @g_fun.setter
    def g_fun(self, value):
        logging.warning('Cannot set g_fun object.')

    @property
    def g_jacobian_fun(self):
        return [self.__g_fun, self.__g_jacobian_fun]

    @g_jacobian_fun.setter
    def g_jacobian_fun(self, value):
        logging.warning('Cannot set g_jacobian_fun object.')

    @property
    def f_jacobian_fun(self):
        return self.__f_fun, self.__f_jacobian_fun, self.__f_hessian_fun

    @f_jacobian_fun.setter
    def f_jacobian_fun(self, value):
        logging.warning('Cannot set f_jacobian_fun object.')

    @property
    def n_k(self):
        return self.__n_k

    @n_k.setter
    def n_k(self, value):
        logging.warning('Cannot set n_k object.')

    @property
    def d(self):
        return self.__d

    @d.setter
    def d(self, value):
        logging.warning('Cannot set d object.')

    @property
    def V(self):
        return self.__V

    @V.setter
    def V(self, value):
        logging.warning('Cannot set V object.')

    @property
    def Xdot(self):
        return self.__Xdot

    @property
    def Xdot_fun(self):
        return self.__Xdot_fun

    @Xdot_fun.setter
    def Xdot_fun(self, value):
        logging.warning('Cannot set Xdot_fun object.')

    @Xdot.setter
    def Xdot(self, value):
        logging.warning('Cannot set Xdot object.')

    @property
    def P(self):
        return self.__P

    @P.setter
    def P(self, value):
        logging.warning('Cannot set P object.')

    @property
    def Outputs_fun(self):
        return self.__Outputs_fun

    @Outputs_fun.setter
    def Outputs_fun(self, value):
        logging.warning('Cannot set Outputs_fun object.')

    @property
    def Outputs(self):
        return self.__Outputs

    @Outputs.setter
    def Outputs(self, value):
        logging.warning('Cannot set Outputs object.')

    @property
    def timings(self):
        return self.__timings

    @timings.setter
    def timings(self, value):
        logging.warning('Cannot set timings object.')

    @property
    def discretization(self):
        return self.__discretization

    @discretization.setter
    def discretization(self, value):
        logging.warning('Cannot set discretization object.')

    @property
    def time_grids(self):
        return self.__time_grids

    @time_grids.setter
    def time_grids(self, value):
        logging.warning('Cannot set time_grids object.')

    @property
    def Multiple_shooting(self):
        """Multiple shooting object"""
        return self.__Multiple_shooting

    @property
    def Collocation(self):
        return self.__Collocation

    @Collocation.setter
    def Collocation(self, value):
        logging.warning('Cannot set Collocation object.')

    @property
    def options(self):
        return self.__options

    @options.setter
    def options(self, value):
        logging.warning('Cannot set options object.')
