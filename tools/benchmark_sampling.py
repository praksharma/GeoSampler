"""Measure complete fresh-worker sampling, including imports and result transfer."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry',type=Path)
    parser.add_argument('--mode',choices=('multicore','reproducible','both'),default='multicore')
    parser.add_argument('--cores',type=int,default=4)
    parser.add_argument('--resolution',type=int,choices=(16,32,64),default=32)
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--method',default='random')
    parser.add_argument('--face',type=int,help='Sample this face instead of the domain interior')
    args=parser.parse_args()
    path=args.geometry.resolve()
    request={'source':str(path),'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),
             'document':'benchmark','label':'benchmark','target':'selection' if args.face else 'interior',
             'entities':[[2,args.face]] if args.face else [],'count':args.count,'method':args.method,
             'resolution':args.resolution,'seed':42,'cpu_threads':args.cores}
    modes=('reproducible','multicore') if args.mode=='both' else (args.mode,)
    for mode in modes:
        request['compute_mode']=mode
        started=time.perf_counter()
        process=subprocess.run([sys.executable,'-m','jorvik.sampling'],
                               input=json.dumps(request),capture_output=True,text=True,check=True,timeout=300)
        elapsed=time.perf_counter()-started
        result=json.loads(process.stdout)
        print(json.dumps({'mode':mode,'cores':result['cpu_threads'],'resolution':args.resolution,
                          'points':result['count'],'method':args.method,'seconds':round(elapsed,3),
                          'mesh_algorithm_3d':result['mesh_algorithm_3d']}),flush=True)


if __name__=='__main__':
    main()
