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
"""
Sweep helper functions to manipulate multiple trials at once

@author: jochem de schutter alu-freiburg 2018
"""

import awebox.tools.struct_operations as struct_op
from itertools import product
import copy

def process_sweep_opts(options, sweep_opts):

    trials_opts = []
    params_opts = []

    for sweep_option in sweep_opts:

        # get keys
        keys = sweep_option[0]
        sweep_type = struct_op.get_from_dict(options.help_dict, keys)[1]

        # sort sweep_opts to parameter and trial options
        if sweep_type == 's':

            params_opts.append(sweep_option)

        elif sweep_type == 't':

            trials_opts.append(sweep_option)

        elif sweep_type == 'x':

            trials_opts.append(sweep_option)

            # raise ValueError('sweeping over this option is not possible')
        else:
            raise ValueError('wrong sweep type found in options')

    return trials_opts, params_opts

def set_single_trial_options(base_options, sweep_options, name):

    options = copy.deepcopy(base_options)
    # set specific trial options
    for i in range(len(sweep_options)):
        # get keys and value for single option
        keys = sweep_options[i][0]
        value = sweep_options[i][1]
        # assign single option
        struct_op.set_in_dict(options, keys, value)
        # append option to name
        if type(keys[-1]) == str:
            keyname = keys[-1]
        else:
            keyname = keys[-2]
        name += '_' + str(keyname) + str(value)

    return options, name

def build_options_combinations(opts):

    # make list of lists with key + single value
    opts_lists = build_options_lists(opts)
    # generate all possible combinations
    combs = list(product(*opts_lists))

    return combs

def build_options_lists(opts):

    options_lists = []
    for option in opts:
        single_list = []
        key = option[0]
        values = option[1]
        for v in values:
            single_list += [(key,v)]
        options_lists += [single_list]

    return options_lists
