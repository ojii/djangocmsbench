# -*- coding: utf-8 -*-
from unipath import DIRS, FSPath as Path
from djangocmsbench import perf
import argparse
import email
import subprocess
import tempfile
import virtualenv
import simplejson
import sys

__version__ = '0.1'

DEFAULT_BENCMARK_DIR = Path(__file__).parent.child('benchmarks').absolute()


class SkipBenchmark(Exception):
    pass


def run_benchmarks(control, experiment, benchmark_dir, benchmarks, trials,
                   record_dir, profile_dir):
    
    if benchmarks:
        print "Running benchmarks: %s" % " ".join(benchmarks)
    else:
        print "Running all benchmarks"

    if record_dir:
        record_dir = Path(record_dir).expand().absolute()
        if not record_dir.exists():
            raise ValueError('Recording directory "%s" does not exist' % record_dir)
        print "Recording data to '%s'" % record_dir


    print "Control: %s" % control 
    print "Experiment: %s" % experiment
    print
    
    control_env_dir = tempfile.mkdtemp()
    experiment_env_dir = tempfile.mkdtemp()
    
    # create envs
    virtualenv.create_environment(control_env_dir, False)
    virtualenv.create_environment(experiment_env_dir, False)
    
    control_python = setup_env(control_env_dir, control)
    experiment_python = setup_env(experiment_env_dir, experiment)

    control_env = {
        'PYTHONPATH': '%s:%s:%s' % (Path.cwd().absolute(), Path(benchmark_dir), Path(__file__).parent.parent.absolute()),
    }
    experiment_env = control_env.copy()

    for benchmark in discover_benchmarks(benchmark_dir):
        if not benchmarks or benchmark.name in benchmarks:
            print "Running '%s' benchmark ..." % benchmark.name
            settings_mod = '%s.settings' % benchmark.name
            control_env['DJANGO_SETTINGS_MODULE'] = settings_mod
            experiment_env['DJANGO_SETTINGS_MODULE'] = settings_mod
            if profile_dir is not None:
                control_env['DJANGOBENCH_PROFILE_FILE'] = Path(profile_dir, "con-%s" % benchmark.name)
                experiment_env['DJANGOBENCH_PROFILE_FILE'] = Path(profile_dir, "exp-%s" % benchmark.name)
            try:
                control_data = run_benchmark(benchmark, trials, control_env, control_python)
                experiment_data = run_benchmark(benchmark, trials, experiment_env, experiment_python)
            except SkipBenchmark, reason:
                print "Skipped: %s\n" % reason
                continue

            options = argparse.Namespace(
                track_memory = False,
                diff_instrumentation = False,
                benchmark_name = benchmark.name,
                disable_timelines = True,
                control_label = control,
                experiment_label = experiment,
            )
            result = perf.CompareBenchmarkData(control_data, experiment_data, options)
            if record_dir:
                record_benchmark_results(
                    dest = record_dir.child('%s.json' % benchmark.name),
                    name = benchmark.name,
                    result = result,
                    control = control,
                    experiment = experiment,
                    control_data = control_data,
                    experiment_data = experiment_data,
                )
            print format_benchmark_result(result, len(control_data.runtimes))
            print
    Path(control_env_dir).rmtree()
    Path(experiment_env_dir).rmtree()

def record_benchmark_results(dest, **kwargs):
    kwargs['version'] = __version__
    simplejson.dump(kwargs, open(dest, 'w'), default=json_encode_custom)

def json_encode_custom(obj):
    if isinstance(obj, perf.RawData):
        return obj.runtimes
    if isinstance(obj, perf.BenchmarkResult):
        return {
            'min_base'    : obj.min_base,
            'min_changed' : obj.min_changed,
            'delta_min'   : obj.delta_min,
            'avg_base'    : obj.avg_base,
            'avg_changed' : obj.avg_changed,
            'delta_avg'   : obj.delta_avg,
            't_msg'       : obj.t_msg,
            'std_base'    : obj.std_base,
            'std_changed' : obj.std_changed,
            'delta_std'   : obj.delta_std,
        }
    if isinstance(obj, perf.SimpleBenchmarkResult):
        return {
            'base_time'    : obj.base_time,
            'changed_time' : obj.changed_time,
            'time_delta'   : obj.time_delta,
        }
    raise TypeError("%r is not JSON serializable" % obj)

def run_benchmark(benchmark, trials, env, executable):
    """
    Similar to perf.MeasureGeneric, but modified a bit for our purposes.
    """
    # Remove Pycs, then call the command once to prime the pump and
    # re-generate fresh ones. This makes sure we're measuring as little of
    # Python's startup time as possible.
    perf.RemovePycs()
    command = [executable, '%s/benchmark.py' % benchmark]
    out, _, _ = perf.CallAndCaptureOutput(command + ['-t', 1], env, track_memory=False, inherit_env=[])
    if out.startswith('SKIP:'):
        raise SkipBenchmark(out.replace('SKIP:', '').strip())

    # Now do the actual mesurements.
    output = perf.CallAndCaptureOutput(command + ['-t', str(trials)], env, track_memory=False, inherit_env=[])
    stdout, stderr, mem_usage = output
    message = email.message_from_string(stdout)
    data_points = [float(line) for line in message.get_payload().splitlines()]
    return perf.RawData(data_points, mem_usage, inst_output=stderr)

def setup_env(env, giturl):
    pip = str(Path(env).child('bin').child('pip'))
    subprocess.call([pip, 'install', '-e', '%s#egg=django-cms' % giturl])
    subprocess.call([pip, 'install', 'PIL'])
    return str(Path(env).child('bin').child('python'))
    
def discover_benchmarks(benchmark_dir):
    for app in Path(benchmark_dir).listdir(filter=DIRS):
        if app.child('benchmark.py').exists() and app.child('settings.py').exists():
            yield app

def supports_color():
    return sys.platform != 'win32' and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

class colorize(object):
    GOOD = INSIGNIFICANT = SIGNIFICANT = BAD = ENDC = ''
    if supports_color():
        GOOD = '\033[92m'
        INSIGNIFICANT = '\033[94m'
        SIGNIFICANT = '\033[93m'
        BAD = '\033[91m'
        ENDC = '\033[0m'

    @classmethod
    def colorize(cls, color, text):
        return "%s%s%s" % (color, text, cls.ENDC)

    @classmethod
    def good(cls, text):
        return cls.colorize(cls.GOOD, text)

    @classmethod
    def significant(cls, text):
        return cls.colorize(cls.SIGNIFICANT, text)

    @classmethod
    def insignificant(cls, text):
        return cls.colorize(cls.INSIGNIFICANT, text)

    @classmethod
    def bad(cls, text):
        return cls.colorize(cls.BAD, text)

def format_benchmark_result(result, num_points):
    if isinstance(result, perf.BenchmarkResult):
        output = ''
        delta_min = result.delta_min
        if 'faster' in delta_min:
            delta_min = colorize.good(delta_min)
        elif 'slower' in result.delta_min:
            delta_min = colorize.bad(delta_min)
        output += "Min: %f -> %f: %s\n" % (result.min_base, result.min_changed, delta_min)

        delta_avg = result.delta_avg
        if 'faster' in delta_avg:
            delta_avg = colorize.good(delta_avg)
        elif 'slower' in delta_avg:
            delta_avg = colorize.bad(delta_avg)
        output += "Avg: %f -> %f: %s\n" % (result.avg_base, result.avg_changed, delta_avg)

        t_msg = result.t_msg
        if 'Not significant' in t_msg:
            t_msg = colorize.insignificant(t_msg)
        elif 'Significant' in result.t_msg:
            t_msg = colorize.significant(t_msg)
        output += t_msg

        delta_std = result.delta_std
        if 'larger' in delta_std:
            delta_std = colorize.bad(delta_std)
        elif 'smaller' in delta_std:
            delta_std = colorize.good(delta_std)
        output += "Stddev: %.5f -> %.5f: %s" %(result.std_base, result.std_changed, delta_std)
        output += " (N = %s)" % num_points
        output += result.get_timeline()
        return output
    else:
        return str(result)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--control',
        default = 'git://github.com/divio/django-cms.git@master',
        help = "Git URL to the repository to use as control."
    )
    parser.add_argument(
        '--experiment',
        default = 'git://github.com/divio/django-cms.git@develop',
        help = "Git URL to the repository to use as experiment."
    )
    parser.add_argument(
        '-t', '--trials',
        type = int,
        default = 50,
        help = 'Number of times to run each benchmark.'
    )
    parser.add_argument(
        '-r', '--record',
        default = None,
        metavar = 'PATH',
        help = 'Directory to record detailed output as a series of JSON files.',
    )

    parser.add_argument(
        '--benchmark-dir',
        dest = 'benchmark_dir',
        metavar = 'PATH',
        default = DEFAULT_BENCMARK_DIR,
        help = ('Directory to inspect for benchmarks. Defaults to the '
                'benchmarks included with djangocmsbench.'),
    )
    parser.add_argument(
        'benchmarks',
        metavar = 'name',
        default = None,
        help = "Benchmarks to be run.  Defaults to all.",
        nargs = '*'
    )
    parser.add_argument(
        '-p',
        '--profile-dir',
        dest = 'profile_dir',
        default = None,
        metavar = 'PATH',
        help = 'Directory to record profiling statistics for the control and experimental run of each benchmark'
    )

    args = parser.parse_args()
    
    run_benchmarks(
        control = args.control,
        experiment = args.experiment,
        benchmark_dir = args.benchmark_dir,
        benchmarks = args.benchmarks,
        trials = args.trials,
        record_dir = args.record,
        profile_dir = args.profile_dir
    )

if __name__ == '__main__':
    main()