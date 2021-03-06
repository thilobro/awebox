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
######################################
# This file stores all quality tests
# Author: Thilo Bronnenmeyer, Kiteswarms, 2018
######################################

import numpy as np
import logging
import awebox.tools.struct_operations as struct_op
import pdb

def test_numerics(trial, test_param_dict, results):
    """
    Test whether optimal parameters are chosen in a reasonable way
    :return: None
    """

    # test if t_f makes sense
    t_f_min = test_param_dict['t_f_min']
    t_f = np.array(trial.optimization.V_final['theta','t_f']).sum() # compute sum in case of phase fix
    if t_f < t_f_min:
        logging.warning('Final time < ' + str(t_f_min) + ' s for trial ' + trial.name)
        results['t_f_min'] = False
    else:
        results['t_f_min'] = True

    # test if t_f/k_k ratio makes sense
    max_control_interval = test_param_dict['max_control_interval']
    n_k = trial.nlp.n_k
    if t_f / float(n_k) > max_control_interval:
        logging.warning('t_f/n_k ratio is > ' + str(max_control_interval) + ' s for trial ' + trial.name)
        results['max_control_interval'] = False
    else:
        results['max_control_interval'] = True

    return results

def test_invariants(trial, test_param_dict, results):
    """
    Test whether invariants reasonably sized
    :return: test results
    """
    # get discretization
    discretization = trial.options['nlp']['discretization']

    # set test parameters from dictionary
    c_max = test_param_dict['c_max']
    dc_max = test_param_dict['dc_max']
    ddc_max = test_param_dict['ddc_max']

    # get architecture
    architecture = trial.model.architecture
    number_of_nodes = architecture.number_of_nodes
    parent_map = architecture.parent_map

    # loop over nodes
    for node in range(1,number_of_nodes):
        for i in [0, 1]:
            parent = parent_map[node]
            if discretization == 'direct_collocation':
                c_list = trial.visualization.plot_dict['output_vals'][i]['coll_outputs', :, :, 'tether_length', 'c' + str(node) + str(parent)]
                dc_list = trial.visualization.plot_dict['output_vals'][i]['coll_outputs', :, :, 'tether_length', 'dc' + str(node) + str(parent)]
                ddc_list = trial.visualization.plot_dict['output_vals'][i]['coll_outputs', :, :, 'tether_length','ddc' + str(node) + str(parent)]
            elif discretization == 'multiple_shooting':
                c_list = trial.visualization.plot_dict['output_vals'][i]['outputs', :, 'tether_length', 'c' + str(node) + str(parent)]
                dc_list = trial.visualization.plot_dict['output_vals'][i]['outputs', :, 'tether_length', 'dc' + str(node) + str(parent)]
                ddc_list = trial.visualization.plot_dict['output_vals'][i]['outputs', :, 'tether_length', 'ddc' + str(node) + str(parent)]
            c_avg = np.average(abs(np.array(c_list)))
            dc_avg = np.average(abs(np.array(dc_list)))
            ddc_avg = np.average(abs(np.array(ddc_list)))

            # test whether invariants are small enough
            if i == 0:
                suffix = 'init'
            elif i == 1:
                suffix = ''
                if c_avg > c_max:
                    logging.warning('Invariant c' + str(node) + str(parent) + ' > ' + str(c_max) + ' of V' + suffix + ' for trial ' + trial.name)
                    results['c' + str(node) + str(parent)] = False
                else:
                    results['c' + str(node) + str(parent)] = True

                if dc_avg > dc_max:
                    logging.warning('Invariant dc' + str(node) + str(parent) + ' > ' + str(dc_max) + ' of V' + suffix + '  for trial ' + trial.name)
                    results['dc' + str(node) + str(parent)] = False
                else:
                    results['dc' + str(node) + str(parent)] = True

                if ddc_avg > ddc_max:
                    logging.warning('Invariant ddc' + str(node) + str(parent) + ' > ' + str(ddc_max) + ' of V' + suffix + ' for trial ' + trial.name)
                    results['ddc' + str(node) + str(parent)] = False
                else:
                    results['ddc' + str(node) + str(parent)] = True

    return results

def test_outputs(trial, test_param_dict, results):
    """
    Test whether outputs are of reasonable size/have correct signs
    :return: test results
    """

    # get discretization
    discretization = trial.options['nlp']['discretization']

    # check if loyd factor is sensible
    max_loyd_factor = test_param_dict['max_loyd_factor']
    if discretization == 'direct_collocation':
        loyd_factor = np.array(trial.optimization.output_vals[1]['coll_outputs', :, :, 'performance', 'loyd_factor'])
    elif discretization == 'multiple_shooting':
        loyd_factor = np.array(trial.optimization.output_vals[1]['outputs', :, 'performance', 'loyd_factor'])
    avg_loyd_factor = np.average(loyd_factor)
    if avg_loyd_factor > max_loyd_factor:
        logging.warning('Average Loyd factor > ' + str(max_loyd_factor) + ' for trial ' + trial.name)
        results['loyd_factor'] = False
    else:
        results['loyd_factor'] = True

    # check if loyd factor is sensible
    max_power_harvesting_factor = test_param_dict['max_power_harvesting_factor']
    if discretization == 'direct_collocation':
        power_harvesting_factor = np.array(trial.optimization.output_vals[1]['coll_outputs', :, :, 'performance', 'phf'])
    elif discretization == 'multiple_shooting':
        power_harvesting_factor = np.array(trial.optimization.output_vals[1]['outputs', :, 'performance', 'phf'])
    avg_power_harvesting_factor = np.average(power_harvesting_factor)
    if avg_power_harvesting_factor > max_power_harvesting_factor:
        logging.warning('Average power harvesting factor > ' + str(max_loyd_factor) + ' for trial ' + trial.name)
        results['power_harvesting_factor'] = False
    else:
        results['power_harvesting_factor'] = True

    # check if maximum tether stress is sensible
    max_tension = test_param_dict['max_tension']
    l_t = trial.visualization.plot_dict['xd']['l_t']
    lambda10 = trial.visualization.plot_dict['xa']['lambda10']
    main_tension = l_t[0] * lambda10[0]
    tension = np.max(main_tension)
    if tension > max_tension:
        logging.warning('Max main tether tension > ' + str(max_tension*1e-6) + ' MN for trial ' + trial.name)
        results['tau_max'] = False
    else:
        results['tau_max'] = True

    return results

def test_variables(trial, test_param_dict, results):
    """
    Test whether variables are of reasonable size and have correct signs
    :return: test results
    """

    # get discretization
    discretization = trial.options['nlp']['discretization']

    # get trial solution
    V_final = trial.optimization.V_final

    # extract system architecture
    architecture = trial.model.architecture
    number_of_nodes = architecture.number_of_nodes
    parent_map = architecture.parent_map

    # test if height of all nodes is positive
    for node in range(1, number_of_nodes):
        parent = parent_map[node]
        node_str = 'q' + str(node) + str(parent)
        heights_xd = np.array(V_final['xd',:,node_str,2])
        if discretization == 'direct_collocation':
            heights_coll_var = np.array(V_final['coll_var',:,:,'xd',node_str,2])
            if np.min(heights_coll_var) < 0.:
                coll_height_flag = True
        if np.min(heights_xd) < 0.:
            logging.warning('Node ' + node_str + ' has negative height for trial ' + trial.name)
            results['min_node_height'] = False
        if discretization == 'direct_collocation':
            if np.min(heights_coll_var) < 0:
                logging.warning('Node ' + node_str + ' has negative height for trial ' + trial.name)
                results['min_node_height'] = False
        else:
            results['min_node_height'] = True

    return results

def test_power_balance(trial, test_param_dict, results):
    """Test whether conservation of energy holds at all nodes and for the entire system.
    :return: test results
    """

    # extract info
    tgrid = trial.visualization.plot_dict['time_grids']['ip']
    power_balance = trial.visualization.plot_dict['outputs']['power_balance']

    # energy balance for all nodes
    balance = {}
    max_system_power = 0
    for node in range(1, trial.model.architecture.number_of_nodes):
        max_node_power = 0
        P_total = np.zeros(tgrid.shape)

        # sum all node-related power in-/outputs
        for name in list(power_balance.keys()):
            if name[-len(str(node)):] == str(node):
                P_total += power_balance[name][0]
                max_single_power = np.max(np.abs(power_balance[name][0]))
                # find largest power component
                max_node_power = np.max([max_single_power, max_node_power])

        # subtract tether power terms coming from node children
        if node in list(trial.model.architecture.children_map.keys()):
            children = trial.model.architecture.children_map[node]
            for child in children:
                max_single_power = np.max(np.abs(power_balance['P_tether'+str(child)][0]))
                # find largest power component
                max_node_power = np.max([max_single_power, max_node_power])
                P_total = P_total - power_balance['P_tether'+str(child)]

        balance[node] = np.linalg.norm(P_total)/max_node_power
        # find largest system power component
        max_system_power = np.max([max_node_power, max_system_power])

    # balance for entire system
    P_total = np.zeros(tgrid.shape)
    for name in list(power_balance.keys()):
        if (name[:8] != 'P_tether') or (name == 'P_tether1') or (name[:12] == 'P_tetherdrag'):
            P_total += power_balance[name][0]

    balance['total'] = np.linalg.norm(P_total)/max_system_power

    for node in list(balance.keys()):
        if balance[node] > test_param_dict['power_balance_tresh']:
            logging.warning('energy balance for node ' + str(node) + ' of trial ' + trial.name +  ' not consistent. ' + str(balance[node]) + ' > ' + str(test_param_dict['power_balance_tresh']))
            results['energy_balance' + str(node)] = False
        else:
            results['energy_balance' + str(node)] = True

    return results

def generate_test_param_dict(options):
    """
    Set parameters relevant for testing
    :return: dictionary with test parameters
    """

    test_param_dict = {}
    test_param_dict['c_max'] = options['test_param']['c_max']
    test_param_dict['dc_max'] = options['test_param']['dc_max']
    test_param_dict['ddc_max'] = options['test_param']['ddc_max']
    test_param_dict['max_loyd_factor'] = options['test_param']['max_loyd_factor']
    test_param_dict['max_power_harvesting_factor'] = options['test_param']['max_power_harvesting_factor']
    test_param_dict['max_tension'] = options['test_param']['max_tension']
    test_param_dict['max_velocity'] = options['test_param']['max_velocity']
    test_param_dict['t_f_min'] = options['test_param']['t_f_min']
    test_param_dict['max_control_interval'] = options['test_param']['max_control_interval']
    test_param_dict['power_balance_tresh'] = options['test_param']['power_balance_tresh']

    return test_param_dict


