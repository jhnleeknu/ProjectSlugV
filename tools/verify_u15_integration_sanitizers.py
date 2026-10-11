"""Reproduce integrated U15b/U15c undefined-behavior checks in a fresh output directory."""
import subprocess,sys,json,hashlib,shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools'))
import verify_animation_machine as common
out=root/'build/sanitize-u15review';out.mkdir(parents=True,exist_ok=False)
compiler=shutil.which('clang++');flags=['-std=c++11','-O1','-g','-Wall','-Wextra','-pedantic','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(root/'engine/include')]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
names=[root/'engine/src'/n for n in common.SOURCES]
headers=list((root/'engine/include').rglob('*.h'))+[root/'engine/src/animation_machine_internal.h']
inputs={str(p.relative_to(root)):sha(p) for p in names+headers}
commands=[]
def compile_one(source):
 obj=out/(source.stem+'.o');command=[compiler]+flags+['-c',str(source),'-o',str(obj)]
 run=subprocess.run(command,capture_output=True,text=True)
 (out/(source.stem+'.log')).write_text(run.stdout+run.stderr)
 assert run.returncode==0 and not run.stdout and not run.stderr,(source,run.returncode,run.stderr)
 return obj,command
with ThreadPoolExecutor(max_workers=2) as pool:compiled=list(pool.map(compile_one,names))
commands=[command for obj,command in compiled];objects=[str(obj) for obj,command in compiled]
results=[]
for n in ['u15b','u15c']:
 source=root/('engine/tests/animation_machine_objects_'+n+'_test.cpp');inputs[str(source.relative_to(root))]=sha(source)
 binary=out/('animation_machine_objects_'+n+'_test');command=[compiler]+flags+objects+[str(source),'-o',str(binary)]
 run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==0 and not run.stdout and not run.stderr,run.stderr
 commands.append(command);run=subprocess.run([str(binary)],capture_output=True,text=True)
 (out/(n+'-run.log')).write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr,(run.returncode,run.stderr)
 results.append({'test':n,'command':[str(binary)],'exit':run.returncode,'output':run.stdout,'binary_sha256':sha(binary)})
for name,digest in inputs.items():assert sha(root/name)==digest,name
(out/'verification.json').write_text(json.dumps({'inputs':inputs,'compiler':compiler,'compiler_sha256':sha(Path(compiler).resolve()),'commands':commands,'results':results,'all_inputs_unchanged':True},indent=2))
print(json.dumps(results),flush=True)
