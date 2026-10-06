"""C++ runtime-data comparison adapter for original animation opcode probes."""
import struct
import subprocess


def check(root,directory,initial,expected,carry,script_size):
    directory.mkdir(parents=True,exist_ok=True)
    inp=directory/'input.bin';script=directory/'script.bin';out=directory/'output.bin';status=directory/'status.bin'
    inp.write_bytes(initial);script.write_bytes(initial[0x5800:0x5800+script_size])
    subprocess.run([str(root/'build/step_animation_data'),str(inp),str(script),str(out),str(status),'8192','0x105800',
                    str(root/'extracted/runtime/data_04a76c.ms5d'),str(root/'extracted/runtime/data_06431a.ms5d')],check=True)
    if out.read_bytes()!=expected or status.read_bytes()!=struct.pack('>I',carry):raise ValueError('C++ animation data operation mismatch')
