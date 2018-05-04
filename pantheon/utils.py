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
    # fill in context['params'] and context['params_json']
    if expt_type == 'node':
        full_param_list = [
            'node', 'link', 'direction', 'flows', 'year', 'month']
    elif expt_type == 'cloud':
        full_param_list = ['src', 'dst', 'flows', 'year', 'month']
    elif expt_type == 'emu':
        full_param_list = ['scenario', 'flows', 'year', 'month']

    params = {k: req(k, 'any') for k in full_param_list}

    if params:
        context['params'] = urllib.parse.urlencode(params) + '&'  # &page=?
    else:
        context['params'] = ''

    context['params_json'] = json.dumps(params)

    # create filters and filter measurement results
    filters = {}

    if expt_type == 'node':
        if params['node'] != 'any':
            filters['node'] = params['node']

        if params['link'] != 'any':
            filters['link'] = params['link']

        if params['direction'] != 'any':
            to_node = True if params['direction'] == 'to_node' else False
            filters['to_node'] = to_node

    elif expt_type == 'cloud':
        if params['src'] != 'any':
            filters['src'] = params['src']

        if params['dst'] != 'any':
            filters['dst'] = params['dst']

    elif expt_type == 'emu':
        if params['scenario'] != 'any':
            filters['scenario'] = int(params['scenario'])

    # common filters
    if params['flows'] != 'any':
        filters['flows'] = int(params['flows'])

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

    return page_obj


def convert_scores_to_colors(results):
    """ Takes a dictionary with form
    {experiment1: {tput: [[]], delay: [[]], loss: [[]], other: ...}}
    where the tput, delay, loss lists are each populated, index i in
    the outer list represents the list of throughputs/delays/losses for
    scheme[i].

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
        for score in scores:
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

    score_list = [float('-inf')] * len(tputs)

    for idx in xrange(len(tputs)):
        scheme_tputs = tputs[idx]
        if scheme_tputs:
            mean_score = np.log(np.mean(tputs[idx]) / np.mean(delays[idx]))
            best_score = max(best_score, mean_score)
            score_list[idx] = mean_score

    # Determine the best, worst, middle scores for interpolation
    worst_score = best_score - 5
    cutoff = np.percentile(score_list, 50)

    # Handle lack of scores (i.e. many schemes didn't run).
    if np.isnan(cutoff) or np.isinf(cutoff):
        possible_cutoffs = [x for x in score_list if x != float('-inf')]
        cutoff = min(possible_cutoffs) if possible_cutoffs else float('-inf')
        worst_score = float('-inf')

    # prepare the mean tputs/delays/losses to display
    experiment['tput'] = [np.mean(tput_list) for tput_list in tputs]
    experiment['delay'] = [np.mean(delay_list) for delay_list in delays]
    experiment['loss'] = [np.mean(loss_list) for loss_list in losses]

    return best_score, cutoff, worst_score, score_list


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


def aggregate_expt_scores(rankings, schemes):
    """ Given a QuerySet of rankings and sorted list of schemes,
    returns a dictionary of experiment results.
    The dictionary has the form:
    {experiment1: {tput: [], delay: [], loss: [], other_metadata: ...}}

    Does not record invalid scores (run didn't complete, negative delay)
    """

    results = {}
    scheme_to_idx = {scheme: idx for idx, scheme in enumerate(schemes)}

    for ranking in rankings:
        if ranking.scheme not in scheme_to_idx:
            continue

        fileset = ranking.expt
        expt_id = fileset.pk
        if expt_id not in results:
            results[expt_id] = {}
            results[expt_id]['tput'] = [[] for i in xrange(len(schemes))]
            results[expt_id]['delay'] = [[] for i in xrange(len(schemes))]
            results[expt_id]['loss'] = [[] for i in xrange(len(schemes))]
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

        if ranking.throughput > 0 and ranking.delay > 0:
            score_idx = scheme_to_idx[ranking.scheme]
            results[expt_id]['tput'][score_idx].append(ranking.throughput)
            results[expt_id]['delay'][score_idx].append(ranking.delay)
            results[expt_id]['loss'][score_idx].append(ranking.loss)

    return results


def order_schemes():
    """ Return an ordered list of schemes to display on the rankings page. """
    schemes = [
        'TCP Cubic',
        'TCP BBR',
        'TCP Vegas',
        'QUIC Cubic',
        'TaoVA-100x',
        'PCC',
        'Verus',
        'Sprout',
        'LEDBAT',
        'SCReAM',
        'WebRTC media',
        'Copa',
        'FillP',
        'Vivace-latency',
        'Vivace-loss',
        'Vivace-LTE',
        'Indigo-1-32'
    ]

    schemes = [scheme.encode('utf-8') for scheme in schemes]

    return schemes


def parse_run_stats(stats):
    """ Takes in a list of stats split by line seen in pantheon_report.pdf,
    describing a run's statistics. Returns a dictionary in the form of
    {flow#: (tput, delay, rate)}

    Assumes the stats list is well-formed.
    For multiple flows, the sentinel flow # of 0 represents the total stats.
    """
    flow_stats = {}

    re_total = lambda x: re.match(r'-- Total of (.*?) flow', x)
    re_flow = lambda x: re.match(r'-- Flow (.*?):', x)
    re_tput = lambda x: re.match(r'Average throughput: (.*?) Mbit/s', x)
    re_delay = lambda x: re.match(
        r'95th percentile per-packet one-way delay: (.*?) ms', x)
    re_loss = lambda x: re.match(r'Loss rate: (.*?)%', x)

    flow_num = 0
    total_flows = 1
    idx = -1
    while idx < len(stats) - 1 and flow_num < total_flows:
        idx += 1
        line = stats[idx]

        flow_ret = re_total(line) or re_flow(line)
        if flow_ret is None or (re_total(line) is not None
                                and flow_ret.group(1) == '1'):
            continue

        if re_flow(line) is not None:
            flow_num = int(flow_ret.group(1))
        else:
            total_flows = int(flow_ret.group(1))

        if idx + 3 >= len(stats):
            break

        avg_tput_ret = re_tput(stats[idx + 1])
        if avg_tput_ret is None:
            continue

        owd_ret = re_delay(stats[idx + 2])
        if owd_ret is None:
            continue

        loss_ret = re_loss(stats[idx + 3])
        if loss_ret is None:
            continue

        flow_stats[flow_num] = (float(avg_tput_ret.group(1)),
                                float(owd_ret.group(1)),
                                float(loss_ret.group(1)))
    return flow_stats
