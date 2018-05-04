import json
from datetime import datetime

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render

from . import utils
from .models import Fileset, NodeExpt, CloudExpt, EmuExpt, Perf


def index(request):
    if request.method != 'GET':
        return render(request, 'pantheon/index.html')

    recent_results = Fileset.objects.order_by('-time_created')[:10]
    if not recent_results:
        return render(request, 'pantheon/index.html')

    context = {}
    context['params'] = ''
    context['expt_type'] = 'node'

    page = request.GET.get('page', 1)
    page_obj = utils.prepare_paged_results(context, recent_results, page, 1)
    context['page_obj'] = page_obj
    return render(request, 'pantheon/index.html', context)


def overview(request):
    return render(request, 'pantheon/overview.html')


def faq(request):
    return render(request, 'pantheon/faq.html')


def measurements(request, expt_type):
    render_page = 'pantheon/%s_measurements.html' % expt_type

    if request.method != 'GET':
        return render(request, render_page)

    context = {'expt_type': expt_type, 'emu_type': Fileset.EMU_EXPT}

    req = request.GET.get

    results = utils.get_measurement_results(context, req, expt_type)
    if not results:
        return render(request, render_page, context)

    page = req('page', 1)
    page_obj = utils.prepare_paged_results(context, results, page, 1)
    context['page_obj'] = page_obj
    return render(request, render_page, context)


def result(request, result_id):
    fileset = get_object_or_404(Fileset, pk=result_id)
    context = {'fileset': fileset, 'emu_type': Fileset.EMU_EXPT}
    return render(request, 'pantheon/result.html', context)


def rankings(request):
    """ Renders the rankings page, a table of experiments X schemes,
    displaying a color indicating its relative score in an experiment.
    """
    schemes = utils.order_schemes()
    context = {'schemes': schemes}

    # Only can rank experiments with 1 flow
    expt_ids = (Fileset.objects.exclude(expt_type=Fileset.EMU_EXPT)
                .filter(flows=1)
                .order_by('-time_created')
                .values_list('id'))
    page = request.GET.get('page', 1)
    per_page = 20
    expt_page = utils.prepare_paged_results(context, expt_ids, page, per_page)
    ids_list = list(expt_page.object_list)

    valid_rankings = Perf.objects.filter(expt_id__in=ids_list)
    expt_scores = utils.aggregate_expt_scores(valid_rankings, schemes)

    expt_colors = utils.convert_scores_to_colors(expt_scores)
    expt_colors = sorted(expt_colors.items(),
                         key=lambda expt, data : data['time_created'],
                         reverse=True)

    context['expt_colors'] = expt_colors
    context['expts'] = expt_page
    return render(request, 'pantheon/summary.html', context)


def update(request, expt_type):
    if request.method == 'GET':
        return render(request, 'pantheon/update.html', {'expt_type': expt_type})
    elif request.method == 'POST':
        p = request.POST.get

        time_created = datetime.strptime(p('time_created'), '%Y-%m-%dT%H-%M')
        experiment = None

        if expt_type == 'node':
            experiment = NodeExpt.objects.create(
                expt_type=Fileset.NODE_EXPT, node=p('node'), cloud=p('cloud'),
                to_node=p('to_node'), link=p('link'),
                time_created=time_created, logs=p('log'), report=p('report'),
                graph1=p('graph1'), graph2=p('graph2'), time=p('time'),
                runs=p('runs'), scenario=p('scenario'))
        elif expt_type == 'cloud':
            experiment = CloudExpt.objects.create(
                expt_type=Fileset.CLOUD_EXPT, src=p('src'), dst=p('dst'),
                time_created=time_created, logs=p('log'), report=p('report'),
                graph1=p('graph1'), graph2=p('graph2'), time=p('time'),
                runs=p('runs'), scenario=p('scenario'))
        elif expt_type == 'emu':
            experiment = EmuExpt.objects.create(
                expt_type=Fileset.EMU_EXPT, emu_scenario=p('emu_scenario'),
                emu_cmd=p('emu_cmd'), emu_desc=p('emu_desc'),
                time_created=time_created, logs=p('log'), report=p('report'),
                graph1=p('graph1'), graph2=p('graph2'), time=p('time'),
                runs=p('runs'), scenario=p('scenario'))

        if experiment is None or p('pantheon_perf.json') is None:
            return

        perf_data = json.loads(p('pantheon_perf.json'))
        print(perf_data)
        #experiment.perf_set.create()

        return HttpResponseRedirect('/')
