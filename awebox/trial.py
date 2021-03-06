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
###################################
# Class Trial contains information and methods to perform one
# optimization of a tree-structured multiple-kite system
###################################

import awebox.tools.print_operations as print_op
import awebox.trial_funcs as trial_funcs
import awebox.ocp.nlp as nlp
import awebox.opti.optimization as optimization
import awebox.sim as sim
import awebox.mdl.model as model
import awebox.mdl.architecture as archi
import awebox.ocp.formulation as formulation
import awebox.viz.visualization as visualization
import awebox.quality as quality
import awebox.tools.data_saving as data_tools
import awebox.opts.options as options
import awebox.tools.struct_operations as struct_op
import logging
import copy

class Trial(object):
    __isfrozen = False
    def __setattr__(self, key, value):
        if self.__isfrozen and not hasattr(self, key):
            raise TypeError( "%r is a frozen class" % self )
        object.__setattr__(self, key, value)

    def _freeze(self):
        self.__isfrozen = True

    def __init__(self, seed, name = 'trial'):

        # check if constructed with dict
        if type(seed) == dict:

            self.__solution_dict = seed['solution_dict']
            self.__visualization = visualization.Visualization()
            self.__visualization.options = seed['solution_dict']['options']
            self.__visualization.plot_dict = seed['plot_dict']
            self.__visualization.create_plot_logic_dict()
            self.__options = seed['solution_dict']['options']

        # check if constructed with options
        elif type(seed) == options.Options:

            self.__options        = seed
            self.__model          = model.Model()
            self.__formulation    = formulation.Formulation()
            self.__nlp            = nlp.NLP()
            self.__simulation     = sim.Simulation(self.__options['simulation'])
            self.__optimization   = optimization.Optimization()
            self.__visualization  = visualization.Visualization()
            self.__quality        = quality.Quality()
            self.__name           = name    #todo: names used as unique identifiers in sweep. smart?
            self.__type           = 'Trial'
            self.__status         = None
            self.__timings        = {}
            self.__solution_dict  = {}
            self.__save_flag      = False

            self.__return_status_numeric = -1

            self._freeze()

    def build(self, is_standalone_trial=True):

        if is_standalone_trial:
            print_op.log_license_info()

        logging.info('')

        logging.info('Building trial (%s) ...', self.__name)
        logging.info('')

        architecture = archi.Architecture(self.__options['user_options']['system_model']['architecture'])
        self.__options.build(architecture)
        self.__model.build(self.__options['model'], architecture)
        self.__formulation.build(self.__options['formulation'], self.__model)
        self.__nlp.build(self.__options['nlp'], self.__model, self.__formulation)
        self.__optimization.build(self.__options['solver'], self.__nlp, self.__model, self.__formulation, self.__name)
        self.__visualization.build(self.__model, self.__nlp, self.__name, self.__options)
        self.__quality.build(self.__options['quality'], self.__name)
        self.set_timings('construction')
        logging.info('Trial (%s) built.', self.__name)
        logging.info('Trial construction time: %s',print_op.print_single_timing(self.__timings['construction']))
        logging.info('')

    def optimize(self, options = [], final_homotopy_step = 'final',
                 warmstart_file = None, debug_flags = [],
                 debug_locations = [], save_flag = False):

        if not options:
            options = self.__options

        # get save_flag
        self.__save_flag = save_flag

        logging.info('Optimizing trial (%s) ...', self.__name)
        logging.info('')

        self.__optimization.solve(options['solver'], self.__nlp, self.__model,
                                  self.__formulation, self.__visualization,
                                  final_homotopy_step, warmstart_file,
                                  debug_flags = debug_flags, debug_locations =
                                  debug_locations)
        self.__solution_dict = self.generate_solution_dict()

        self.set_timings('optimization')

        self.__return_status_numeric = self.__optimization.return_status_numeric['optimization']

        if self.__optimization.solve_succeeded:
            logging.info('Trial (%s) optimized.', self.__name)
            logging.info('Trial optimization time: %s',print_op.print_single_timing(self.__timings['optimization']))

        else:

            logging.info('WARNING: Optimization of Trial (%s) failed.', self.__name)

        cost_fun = self.nlp.cost_components[0]
        cost = struct_op.evaluate_cost_dict(cost_fun, self.optimization.V_opt, self.optimization.p_fix_num)
        self.visualization.recalibrate(self.optimization.V_opt, self.visualization.plot_dict, self.optimization.output_vals, self.optimization.integral_outputs_final, self.options, self.optimization.time_grids, cost, self.name)

        # perform quality check
        self.__quality.check_quality(self)

        # save trial if option is set
        if self.__save_flag is True or self.__options['solver']['save_trial'] == True:
            self.save()

        logging.info('')

    def plot(self, flags, V_plot=None, cost=None, parametric_options=None, output_vals=None, sweep_toggle=False, fig_num = None):

        if V_plot is None:
            V_plot = self.__solution_dict['V_opt']
        if parametric_options is None:
            parametric_options = self.__options
        if output_vals == None:
            output_vals = self.__solution_dict['output_vals']
        if cost == None:
            cost = self.__solution_dict['cost']
        time_grids = self.__solution_dict['time_grids']
        integral_outputs_final = self.__solution_dict['integral_outputs_final']
        trial_name = self.__solution_dict['name']

        self.__visualization.plot(V_plot, parametric_options, output_vals, integral_outputs_final, flags, time_grids, cost, trial_name, sweep_toggle,'plot',fig_num)

        return None

    def simulate(self):

        logging.info('Simulating trial (%s) ...', self.__name)
        logging.info('')

        self.__simulation.build_integrator(self.__options['simulation'], self.__model)

        x0 = generate_initial_state(self.__model, self.__optimization.V_init)
        self.__simulation.run(x0, self.__optimization.V_init['u'], self.__optimization.V_init['theta'], self.__optimization.V_init['phi'])
        logging.info('Trial (%s) simulated.', self.__name)
        logging.info('')

    def set_timings(self, timing):
        if timing == 'construction':
            self.__timings['construction'] = self.model.timings['overall'] + self.formulation.timings['overall'] \
                                            + self.nlp.timings['overall'] + self.optimization.timings['setup']
        elif timing == 'optimization':
            self.__timings['optimization'] = self.optimization.timings['optimization']

    def save(self, saving_method = 'dict', fn = None):

        # log saving method
        logging.info('Saving trial ' + self.__name + ' using ' + saving_method)

        # set savefile name to trial name if unspecified
        if not fn:
            fn = self.__name

        # choose correct function for saving method
        if saving_method == 'awe':
            self.save_to_awe(fn)
        elif saving_method == 'dict':
            self.save_to_dict(fn)
        else:
            logging.error(saving_method + ' is not a supported saving method. Trial ' + self.__name + ' could not be saved!')

        # log that save is complete
        logging.info('Trial (%s) saved.', self.__name)
        logging.info('')
        logging.info(print_op.hline('&'))
        logging.info(print_op.hline('&'))
        logging.info('')
        logging.info('')

    def save_to_awe(self, fn):

        # reset multiple_shooting trial
        if self.__options['nlp']['discretization'] == 'multiple_shooting':
            self.__nlp = nlp.NLP()
            self.__optimization = optimization.Optimization()
            self.__visualization = visualization.Visualization()

        # pickle data
        data_tools.pickle_data(self, fn, 'awe')

    def save_to_dict(self, fn):

        # create dict to be saved
        data_to_save = {}

        # store necessary information
        data_to_save['solution_dict'] = self.generate_solution_dict()
        data_to_save['plot_dict'] = self.__visualization.plot_dict

        # pickle data
        data_tools.pickle_data(data_to_save, fn, 'dict')
        
    def generate_solution_dict(self):

        solution_dict = {}

        # seeding data
        solution_dict['time_grids'] = self.__optimization.time_grids
        solution_dict['name'] = self.__name

        # parametric sweep data
        solution_dict['V_opt'] = self.__optimization.V_opt
        solution_dict['V_final'] = self.__optimization.V_final
        solution_dict['options'] = self.__options
        solution_dict['output_vals'] = [
            copy.deepcopy(self.__optimization.output_vals[0]),
            copy.deepcopy(self.__optimization.output_vals[1])
        ]
        solution_dict['integral_outputs_final'] = self.__optimization.integral_outputs_final
        solution_dict['stats'] = self.__optimization.stats
        solution_dict['iterations'] = self.__optimization.iterations
        solution_dict['timings'] = self.__optimization.timings
        cost_fun = self.__nlp.cost_components[0]
        cost = struct_op.evaluate_cost_dict(cost_fun, self.__optimization.V_opt, self.__optimization.p_fix_num)
        solution_dict['cost'] = cost

        # warmstart data
        solution_dict['final_homotopy_step'] = self.__optimization.final_homotopy_step
        solution_dict['Xdot_opt'] = self.__nlp.Xdot(self.__nlp.Xdot_fun(self.__optimization.V_opt))
        solution_dict['g_opt'] = self.__nlp.g(self.__nlp.g_fun(self.__optimization.V_opt, self.__optimization.p_fix_num))
        solution_dict['opt_arg'] = self.__optimization.arg

        return solution_dict

    def write_to_csv(self, file_name=None, frequency=30., rotation_representation='euler'):

        if file_name is None:
            file_name = self.name
        trial_funcs.generate_trial_data_csv(self, file_name, frequency, rotation_representation)

        return None

    def generate_optimal_model(self):
        return trial_funcs.generate_optimal_model(self)

    @property
    def options(self):
        return self.__options

    @options.setter
    def options(self, value):
        print('Cannot set options object.')

    @property
    def status(self):
        status_dict = {}
        status_dict['model'] = self.__model.status
        status_dict['nlp'] = self.__nlp.status
        status_dict['optimization'] = self.__optimization.status
        status_dict['simulation'] = self.__simulation.status
        return status_dict

    @status.setter
    def status(self, value):
        print('Cannot set status object.')

    @property
    def model(self):
        return self.__model

    @model.setter
    def model(self, value):
        print('Cannot set model object.')

    @property
    def nlp(self):
        return self.__nlp

    @nlp.setter
    def nlp(self, value):
        print('Cannot set nlp object.')

    @property
    def optimization(self):
        return self.__optimization

    @optimization.setter
    def optimization(self, value):
        print('Cannot set optimization object.')

    @property
    def formulation(self):
        return self.__formulation

    @formulation.setter
    def formulation(self, value):
        print('Cannot set formulation object.')

    @property
    def type(self):
        return self.__type

    @type.setter
    def type(self, value):
        print('Cannot set type object.')

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        print('Cannot set name object.')

    @property
    def timings(self):
        return self.__timings

    @timings.setter
    def timings(self, value):
        print('Cannot set timings object.')

    @property
    def simulation(self):
        return self.__simulation

    @simulation.setter
    def simulation(self, value):
        print('Cannot set simulation object.')

    @property
    def visualization(self):
        return self.__visualization

    @visualization.setter
    def visualization(self, value):
        print('Cannot set visualization object.')

    @property
    def quality(self):
        return self.__quality

    @quality.setter
    def quality(self, value):
        print('Cannot set quality object.')

    @property
    def return_status_numeric(self):
        return self.__return_status_numeric

    @return_status_numeric.setter
    def return_status_numeric(self, value):
        print('Cannot set return_status_numeric object.')

def generate_initial_state(model, V_init):
    x0 = model.struct_list['xd'](0.)
    for name in list(model.struct_list['xd'].keys()):
        x0[name] = V_init['xd',0,0,name]
    return x0

