from django.db import models

from functools import reduce


class Fileset(models.Model):
    # experiment type
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
    logs = models.URLField()
    report = models.URLField()
    graph1 = models.URLField()
    graph2 = models.URLField()
    time = models.IntegerField()
    runs = models.IntegerField()

    # flow scenario
    ONE_FLOW = '1_flow'
    THREE_FLOWS = '3_flows'
    SCENARIO_CHOICES = (
        (ONE_FLOW, '1 flow'),
        (THREE_FLOWS, '3 flows'),
    )
    scenario = models.CharField(choices=SCENARIO_CHOICES, max_length=16)


class NodeExpt(Fileset):
    node = models.CharField(max_length=64)
    cloud = models.CharField(max_length=64)
    to_node = models.BooleanField()
    link = models.CharField(max_length=64)

    def __str__(self):
        if self.to_node:
            src = self.cloud
            dst = self.node
        else:
            src = self.node
            dst = self.cloud

        link = self.link.title()

        return '{} to {}, {}'.format(prettify(src), prettify(dst), link)

    def description(self):
        return self.__str__()


class CloudExpt(Fileset):
    src = models.CharField(max_length=64)
    dst = models.CharField(max_length=64)

    def __str__(self):
        return '{} to {}, Ethernet'.format(
            prettify(self.src), prettify(self.dst))

    def description(self):
        return self.__str__()


class EmuExpt(Fileset):
    # emulation scenario
    EMU_SCENARIO_CHOICES = (
        (1, 'Calibrated emulator (Nepal to AWS India)'),
        (2, 'Calibrated emulator (Mexico cellular to AWS California)'),
        (3, 'Calibrated emulator (AWS Brazil to Colombia cellular)'),
        (4, 'Calibrated emulator (India to AWS India)'),
        (5, 'Calibrated emulator (AWS Korea to China)'),
        (6, 'Calibrated emulator (AWS California to Mexico)'),
        (7, 'Token-bucket based policer (bandwidth 12mbps, RTT 20ms)'),
        (8, 'Token-bucket based policer (bandwidth 60mbps, RTT 20ms)'),
        (9, 'Token-bucket based policer (bandwidth 108mbps, RTT 20ms)'),
        (10, 'Token-bucket based policer (bandwidth 12mbps, RTT 100ms)'),
        (11, 'Token-bucket based policer (bandwidth 60mbps, RTT 100ms)'),
        (12, 'Token-bucket based policer (bandwidth 108mbps, RTT 100ms)'),
        (13, 'Severe ACK aggregation (1 ACK every 100ms)'),
        (14, 'Severe ACK aggregation (10 ACKs every 200ms)'),
        (15, 'Bottleneck buffer = BDP/10'),
        (16, 'Bottleneck buffer = BDP/3'),
        (17, 'Bottleneck buffer = BDP/2'),
        (18, 'Bottleneck buffer = BDP'),
    )
    emu_scenario = models.IntegerField(choices=EMU_SCENARIO_CHOICES)

    emu_cmd = models.CharField(max_length=512)
    emu_desc = models.CharField(max_length=512)

    def __str__(self):
        return 'scenario {}, {}'.format(self.emu_scenario, self.emu_desc)

    def description(self):
        return self.__str__()


class Perf(models.Model):
    expt = models.ForeignKey(Fileset, on_delete=models.CASCADE)
    scheme = models.CharField(max_length=32)
    run = models.IntegerField()
    flow = models.IntegerField()
    throughput = models.FloatField()
    delay = models.FloatField()
    loss = models.FloatField()

    def __str__(self):
        return ('Expt {}, {}, run {}, flow {}: '
                '[throughput {}, delay {}, loss {}]'.format(
                self.expt_id, self.scheme, self.run, self.flow,
                self.throughput, self.delay, self.loss))


def prettify(name):
    repls = ('_', ' '), ('Aws', 'AWS'), ('Gce', 'GCE')
    return reduce(lambda a, kv: a.replace(*kv), repls, name.title())
