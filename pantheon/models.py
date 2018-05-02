from django.db import models


class Fileset(models.Model):
    NODE_EXPT = 'node'
    CLOUD_EXPT = 'cloud'
    EMU_EXPT = 'emu'
    EXPT_CHOICES = (
        (NODE_EXPT, 'node'),
        (CLOUD_EXPT, 'cloud'),
        (EMU_EXPT, 'emu'),
    )
    expt_type = models.CharField(choices=EXPT_CHOICES, max_length=8)

    time_created = models.DateTimeField()
    log = models.URLField()
    report = models.URLField()
    graph1 = models.URLField()  # performance summary graph
    graph2 = models.URLField()  # performance summary graph (mean of all runs)
    flows = models.IntegerField()
    runs = models.IntegerField()


class NodeExpt(Fileset):
    node = models.CharField(max_length=64)
    cloud = models.CharField(max_length=64)
    to_node = models.BooleanField()
    link = models.CharField(max_length=64)

    def __str__(self):
        start = prettify_endpoint(self.node)
        end = prettify_endpoint(self.cloud)
        link = self.link.title()
        if self.to_node:
            start, end = end, start

        desc_str = '{} to {}, {} link, {} run'
        if self.runs > 1:
            desc_str += 's'
        desc_str += ', {} flow'
        if self.flows > 1:
            desc_str += 's'

        return desc_str.format(start, end, link, self.runs, self.flows)

    def description(self):
        return self.__str__()

class CloudExpt(Fileset):
    src = models.CharField(max_length=64)
    dst = models.CharField(max_length=64)

    def __str__(self):
        src = prettify_endpoint(self.src)
        dst = prettify_endpoint(self.dst)

        desc_str = '{} Ethernet to {} Ethernet, {} run'
        if self.runs > 1:
            desc_str += 's'
        desc_str += ', {} flow'
        if self.flows > 1:
            desc_str += 's'

        return desc_str.format(src, dst, self.runs, self.flows)

    def description(self):
        return self.__str__()


class EmuExpt(Fileset):
    scenario = models.IntegerField()
    emu_cmd = models.CharField(max_length=255)
    desc = models.CharField(max_length=255)

    def __str__(self):
        desc_str = '{}, {}, {}'
        return desc_str.format(self.scenario, self.emu_cmd, self.desc)

    def description(self):
        desc_str = '{}, {} run'
        if self.runs > 1:
            desc_str += 's'
        desc_str += ', {} flow'
        if self.flows > 1:
            desc_str += 's'

        return desc_str.format(self.desc, self.runs, self.flows)


class Ranking(models.Model):
    expt = models.ForeignKey(Fileset, on_delete=models.CASCADE)
    scheme = models.CharField(max_length=32)
    run = models.IntegerField()
    flow = models.IntegerField()
    throughput = models.FloatField()
    delay = models.FloatField()
    loss = models.FloatField()

    def __str__(self):
        return ('Expt {}, {}, run #{}, flow#{}: '
               '[throughput (Mbps): {}, 95th-%tile delay (ms): {}, '
               'loss %: {}]'.format(self.expt_id, self.scheme, self.run,
                                    self.flow, self.throughput, self.delay,
                                    self.loss))


def prettify_endpoint(name):
    repls = ('_', ' '), ('Aws', 'AWS'), ('Gce', 'GCE')
    return reduce(lambda a, kv: a.replace(*kv), repls, name.title())
