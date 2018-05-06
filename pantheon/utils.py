import os
import re
import json
import yaml
import urllib.parse
import numpy as np

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Fileset, NodeExpt, CloudExpt, EmuExpt, Perf


def get_expt_obj(expt_type):
    if expt_type == 'node':
        return NodeExpt
    elif expt_type == 'cloud':
        return CloudExpt
    elif expt_type == 'emu':
        return EmuExpt


def get_measurement_results(context, req, expt_type):
    if expt_type == 'node':
        full_param_list = [
            'node', 'direction', 'link', 'scenario', 'year', 'month']
    elif expt_type == 'cloud':
        full_param_list = ['src', 'dst', 'scenario', 'year', 'month']
    elif expt_type == 'emu':
        full_param_list = ['emu_scenario', 'scenario', 'year', 'month']

    params = {k: req(k, 'any') for k in full_param_list}

    if params:
        # add '&' in order to append '&page=X'
        context['params'] = urllib.parse.urlencode(params) + '&'
        context['params_json'] = json.dumps(params)

    # create filters and filter measurement results
    filters = {}

    if expt_type == 'node':
        if params['node'] != 'any':
            filters['node'] = params['node']

        if params['direction'] != 'any':
            if params['direction'] == 'download':
                filters['to_node'] = True
            elif params['direction'] == 'upload':
                filters['to_node'] = False
            else:
                # invalid direction
                return None

        if params['link'] != 'any':
            filters['link'] = params['link']

    elif expt_type == 'cloud':
        if params['src'] != 'any':
            filters['src'] = params['src']

        if params['dst'] != 'any':
            filters['dst'] = params['dst']

    elif expt_type == 'emu':
        if params['emu_scenario'] != 'any':
            filters['emu_scenario'] = int(params['emu_scenario'])

    # common filters
    if params['scenario'] != 'any':
        filters['scenario'] = params['scenario']

    if params['year'] != 'any':
        filters['time_created__year'] = int(params['year'])

    if params['month'] != 'any':
        filters['time_created__month'] = int(params['month'])

    expt_obj = get_expt_obj(expt_type)
    results = expt_obj.objects.filter(**filters).order_by('-time_created')

    return results


def prepare_paged_results(context, results, page_num, each_page):
    try:
        page_num = int(page_num)
    except ValueError:
        page_num = 1

    paginator = Paginator(results, each_page)
    num_pages = paginator.num_pages

    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(num_pages)

    if num_pages <= 10 or page_num <= 6:
        pages = range(1, min(num_pages + 1, 11))
    elif page_num > num_pages - 4:
        pages = range(num_pages - 9, num_pages + 1)
    else:
        pages = range(page_num - 5, page_num + 5)

    context['pages'] = pages
    context['page_obj'] = page_obj

    return page_obj


def parse_config():
    with open(os.path.join(os.path.dirname(__file__), 'config.yml')) as config:
        return yaml.load(config)


def interpolate(val, best, worst, end, start):
    val = min(max(val, worst), best)

    # edge case
    if best == worst:
        return end

    rate_of_change = 1.0 * (end - start) / (best - worst)
    return int(rate_of_change * (val - worst) + start)


def interpolate_rgb(val, best_val, worst_val, best_color, worst_color):
    rgb_tuple = [255, 255, 255]

    for j in range(3):
        rgb_tuple[j] = interpolate(val, best_val, worst_val,
                                   best_color[j], worst_color[j])

    return '(%d, %d, %d)' % tuple(rgb_tuple)


def get_expt_description(fileset_obj):
    """ Given a Fileset object, return the description of the experiment.
    """

    desc = 'No experiment description'

    try:
        expt_obj = None

        if fileset_obj.expt_type == Fileset.NODE_EXPT:
            expt_obj = NodeExpt.objects.get(fileset_ptr_id=fileset_obj.id)
        elif fileset_obj.expt_type == Fileset.CLOUD_EXPT:
            expt_obj = CloudExpt.objects.get(fileset_ptr_id=fileset_obj.id)
        elif fileset_ojb.expt_type == Fileset.EMU_EXPT:
            expt_obj = EmuExpt.objects.get(fileset_ptr_id=fileset_obj.id)

        if expt_obj is not None:
            desc = expt_obj.description()

    except ObjectDoesNotExist:
        pass

    return desc


def convert_scores_to_colors(data_i):
    """ Given a dictionary data_i (data for a specific experiment) with form
    {scheme1: {'score': XXX}, scheme2: {'score': XXX}, ...}
    fill in data_i[scheme]['color'].
    """

    score_list = []
    for s in data_i:
        if 'score' not in data_i[s]:
            continue

        score_list.append(data_i[s]['score'])

    if not score_list:
        return

    best_score = max(score_list)
    median_score = np.percentile(score_list, 50)
    worst_score = min(score_list)

    best_color = (68, 234, 68)
    median_color = (21, 124, 21)
    worst_color = (0, 0, 0)

    for s in data_i:
        if 'score' not in data_i[s]:
            continue

        score = data_i[s]['score']
        if score >= median_score:
            rgb_tuple = interpolate_rgb(score, best_score, median_score,
                                        best_color, median_color)
        else:
            rgb_tuple = interpolate_rgb(score, median_score, worst_score,
                                        median_color, worst_color)

        data_i[s]['color'] = rgb_tuple
