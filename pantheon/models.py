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
    logs = models.URLField()
    report = models.URLField()
    graph1 = models.URLField()
    graph2 = models.URLField()
    time = models.IntegerField()
    runs = models.IntegerField()
    scenario = models.CharField(max_length=64)


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

        return '{} to {}, {}'.format(src, dst, self.link)


class CloudExpt(Fileset):
    src = models.CharField(max_length=64)
    dst = models.CharField(max_length=64)

    def __str__(self):
        return '{} to {}'.format(self.src, self.dst)


class EmuExpt(Fileset):
    emu_scenario = models.IntegerField()
    emu_cmd = models.CharField(max_length=255)
    emu_desc = models.CharField(max_length=512)

    def __str__(self):
        return 'scenario {}, {}'.format(self.emu_scenario, self.emu_desc)


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
