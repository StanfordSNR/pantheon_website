import json
from datetime import datetime
import numpy as np
import urllib

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template.defaulttags import register

from . import utils
from .models import Fileset, NodeExpt, CloudExpt, EmuExpt, Perf


def index(request):
    if request.method != 'GET':
        return render(request, 'pantheon/index.html')

    recent_results = Fileset.objects.order_by('-time_created')[:10]
    if not recent_results:
        return render(request, 'pantheon/index.html')

    context = {}
    page = request.GET.get('page', 1)
    # fill in context['pages'] and context['page_obj']
    utils.prepare_paged_results(context, recent_results, page, 1)

    return render(request, 'pantheon/index.html', context)


def overview(request):
    return render(request, 'pantheon/overview.html')


def faq(request):
    return render(request, 'pantheon/faq.html')


def measurements(request, expt_type):
    render_page = 'pantheon/%s_measurements.html' % expt_type

    if request.method != 'GET':
        return render(request, render_page)

    context = {'expt_type': expt_type}
    req = request.GET.get

    # fill in context['params'] and context['params_json']
    results = utils.get_measurement_results(context, req, expt_type)
    if not results:
        return render(request, render_page, context)

    page = req('page', 1)
    # fill in context['pages'] and context['page_obj']
    utils.prepare_paged_results(context, results, page, 1)

    return render(request, render_page, context)


def result(request, result_id):
    fileset = get_object_or_404(Fileset, pk=result_id)
    context = {'fileset': fileset}
    return render(request, 'pantheon/result.html', context)


def update(request, expt_type):
    if request.method == 'GET':
        return render(request, 'pantheon/update.html',
                      {'expt_type': expt_type})
    elif request.method == 'POST':
        p = request.POST.get

        time_created = datetime.strptime(p('time_created'), '%Y-%m-%dT%H-%M')
        experiment = None

        fields = {
            'time_created': time_created,
            'logs': p('logs'),
            'uid_logs': p('uid_logs'),
            'report': p('report'),
            'graph1': p('graph1'),
            'graph2': p('graph2'),
            'perf_file': p('perf_file'),
            'time': p('time'),
            'runs': p('runs'),
            'scenario': p('scenario')
        }

        if expt_type == 'node':
            fields['expt_type'] = Fileset.NODE_EXPT
            fields['node'] = p('node')
            fields['cloud'] = p('cloud')
            fields['to_node'] = p('to_node')
            fields['link'] = p('link')

            experiment = NodeExpt.objects.create(**fields)
        elif expt_type == 'cloud':
            fields['expt_type'] = Fileset.CLOUD_EXPT
            fields['src'] = p('src')
            fields['dst'] = p('dst')

            experiment = CloudExpt.objects.create(**fields)
        elif expt_type == 'emu':
            fields['expt_type'] = Fileset.EMU_EXPT
            fields['emu_scenario'] = p('emu_scenario')
            fields['emu_cmd'] = p('emu_cmd')
            fields['emu_desc'] = p('emu_desc')

            experiment = EmuExpt.objects.create(**fields)

        if experiment is None:
            return HttpResponseRedirect('/')

        # load performance data file and save into the model "Perf"
        perf_data = json.loads(urllib.request.urlopen(p('perf_file')).read())

        for cc in perf_data:
            for run_id in perf_data[cc]:
                # aggregate performance of all flows
                if 'all' in perf_data[cc][run_id]:
                    perf = perf_data[cc][run_id]['all']

                    experiment.perf_set.create(
                        scheme=cc,
                        run=int(run_id),
                        throughput=float(perf['tput']),
                        delay=float(perf['delay']),
                        loss=float(perf['loss']))

        return HttpResponseRedirect('/')


def summary(request):
    """ Renders the rankings page, a table of experiments X schemes,
    displaying a color indicating its relative score in an experiment.
    """

    real_expts = (Fileset.objects.exclude(expt_type=Fileset.EMU_EXPT)
                  .order_by('-time_created'))

    # get results from Fileset
    context = {}
    page = request.GET.get('page', 1)
    # fill in context['pages'] and context['page_obj']
    page_obj = utils.prepare_paged_results(context, real_expts, page, 20)

    config = utils.parse_config()['schemes']

    # for results in a given page, look up perf data from Perf
    scheme_set = set()
    data = {}
    metadata = {}
    metadata['default_rgb'] = '(255, 255, 255)'

    for expt_obj in page_obj:
        i = expt_obj.id
        data[i] = {}
        metadata[i] = {}

        for perf in expt_obj.perf_set.all():
            s = perf.scheme
            if s not in config:
                continue

            scheme_set.add(s)

            if s not in data[i]:
                data[i][s] = {}
                data[i][s]['tput'] = []
                data[i][s]['delay'] = []
                data[i][s]['loss'] = []

            if perf.throughput > 0 and perf.delay > 0:
                data[i][s]['tput'].append(perf.throughput)
                data[i][s]['delay'].append(perf.delay)
                data[i][s]['loss'].append(perf.loss)

        # save mean performance only
        for s in data[i]:
            if data[i][s]['tput'] and data[i][s]['delay'] and data[i][s]['loss']:
                data[i][s]['tput'] = np.mean(data[i][s]['tput'])
                data[i][s]['delay'] = np.mean(data[i][s]['delay'])
                data[i][s]['loss'] = np.mean(data[i][s]['loss'])

                # log of Kleinrock's power metric
                if data[i][s]['delay'] > 0:
                    data[i][s]['score'] = np.log(data[i][s]['tput'] /
                                                 data[i][s]['delay'])

        # fill in data[i][s]['color'] (not for sure)
        # require data[i][s]['score'], etc. to be floats
        utils.convert_scores_to_colors(data[i])

        # convert data to string with 3 decimal places
        for s in data[i]:
            for c in ['tput', 'delay', 'loss', 'score']:
                if c in data[i][s]:
                    if data[i][s][c] == []:
                        continue

                    if data[i][s][c] < 0:
                        data[i][s][c] = '&minus;%.3f' % abs(data[i][s][c])
                    else:
                        data[i][s][c] = '%.3f' % data[i][s][c]

        metadata[i]['time_created'] = expt_obj.time_created.strftime('%m/%d/%Y')
        metadata[i]['desc']  = utils.get_expt_description(expt_obj)

    # scheme names
    scheme_names = {}
    for scheme in scheme_set:
        scheme_names[scheme] = config[scheme]['name']

    context['scheme_set'] = sorted(scheme_set)
    context['scheme_names'] = scheme_names
    context['data'] = data

    context['metadata'] = metadata

    return render(request, 'pantheon/summary.html', context)


# get value by key in templates
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
