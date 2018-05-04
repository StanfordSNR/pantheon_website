import re
import json
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
    results = (expt_obj.objects.filter(**filters)
                               .order_by('-time_created', '-fileset_ptr_id'))
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


def convert_scores_to_colors(results):
    """ Takes a dictionary with form
    {expt_id: {tput: {scheme: [], ...}, delay: ..., loss: ..., other: ...}}

    Creates a list zipping scores, tput, delay, and loss together.

    The colors are linearly interpolated to form a "gradient"
    """

    for expt in results:
        best, cutoff, worst, scores = compute_score_stats(results[expt])

        # Linearly interpolate each score to between 3 colors
        best_color = (68, 234, 68)
        median_color = (21, 124, 21)
        worst_color = (0, 0, 0)
        colors = []
        for scheme in scores:
            score = scores[scheme]

            if score >= cutoff:
                rgb_tuple = interp_rgb_tuple(score,
                                             best, cutoff,
                                             best_color, median_color)
            else:
                rgb_tuple = interp_rgb_tuple(score,
                                             cutoff, worst,
                                             median_color, worst_color)
            colors.append(rgb_tuple)

        stats_and_colors = zip(scores, colors,
                               results[expt]['tput'],
                               results[expt]['delay'],
                               results[expt]['loss'])
        results[expt]['stats'] = stats_and_colors
        entries_to_remove = ('scores', 'tput', 'delay', 'loss')
        for k in entries_to_remove:
            results[expt].pop(k, None)

    return results


def compute_score_stats(experiment):
    """ Given an experiment with a list of scheme scores,
    average each list of scores to produce the actual mean score.
    Returns the updated score list and the best, worst, and a cutoff score.
    """
    tputs = experiment['tput']
    delays = experiment['delay']
    losses = experiment['loss']

    best_score = float('-inf')

    score_dict = {}
    for scheme in tputs:
        mean_score = np.log(np.mean(tputs[scheme])) - np.log(np.mean(delays[scheme]))
        best_score = max(best_score, mean_score)
        score_dict[scheme] = mean_score

    # Determine the best, worst, middle scores for interpolation
    worst_score = best_score - 5
    cutoff = np.percentile(score_list, 50)

    # Handle lack of scores (i.e. many schemes didn't run).
    if np.isnan(cutoff) or np.isinf(cutoff):
        possible_cutoffs = []
        for scheme in score_dict:
            score = score_dict[scheme]
            if score != float('-inf'):
                possible_cutoffs.append(score)

        cutoff = min(possible_cutoffs) if possible_cutoffs else float('-inf')
        worst_score = float('-inf')

    # prepare the mean tputs/delays/losses to display
    experiment['tput'] = [np.mean(tputs[scheme]) for scheme in tputs]
    experiment['delay'] = [np.mean(delays[scheme]) for scheme in delays]
    experiment['loss'] = [np.mean(losses[scheme]) for scheme in losses]

    return best_score, cutoff, worst_score, score_dict


def interp_rgb_tuple(val, best_val, worst_val, best_color, worst_color):
    rgb_tuple = tuple(int(interpolate(val,
                                      best_val, worst_val,
                                      best_color[j], worst_color[j]))
                      for j in xrange(3))
    return '(%d, %d, %d)' % rgb_tuple


def interpolate(val, best, worst, end, start):
    # Indicate white as sentinel for "no run"
    if val == float('-inf') or best == float('-inf'):
        return 255

    # Edge case if there is only one value, by default it's the best.
    if val == best == worst:
        return end

    val = min(max(val, worst), best)
    rate_of_change = (1.0 * (end - start) / (best - worst))
    interp_val = rate_of_change * (val - worst) + start
    return interp_val


def aggregate_expt_scores(perfs):
    """ Given a QuerySet of perfs, returns a dictionary of experiment results.
    The dictionary has the form:
    {expt_id: {scheme: {tput: {}, delay: {}, loss: {}}, other_metadata: ...}}

    Does not record invalid scores (run didn't complete, negative delay)
    """

    results = {}

    for perf in perfs:
        fileset = perf.expt
        expt_id = fileset.pk
        scheme = perf.scheme

        if expt_id not in results:
            results[expt_id] = {}

            results[expt_id][scheme] = {}
            results[expt_id][scheme]['tput'] = []
            results[expt_id][scheme]['delay'] = []
            results[expt_id][scheme]['loss'] = []
            results[expt_id]['time_created'] = fileset.time_created

            desc = 'No experiment description'
            try:
                expt = None

                if fileset.expt_type == Fileset.NODE_EXPT:
                    expt = NodeExpt.objects.get(fileset_ptr_id=expt_id)
                elif fileset.expt_type == Fileset.CLOUD_EXPT:
                    expt = CloudExpt.objects.get(fileset_ptr_id=expt_id)
                elif fileset.expt_type == Fileset.EMU_EXPT:
                    expt = EmuExpt.objects.get(fileset_ptr_id=expt_id)

                if expt is not None:
                    desc = expt.description()

            except ObjectDoesNotExist:
                pass

            results[expt_id]['desc'] = desc

        if perf.throughput > 0 and perf.delay > 0:
            results[expt_id][scheme]['tput'].append(perf.throughput)
            results[expt_id][scheme]['delay'].append(perf.delay)
            results[expt_id][scheme]['loss'].append(perf.loss)

    return results
