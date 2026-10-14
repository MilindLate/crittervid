"""
Stand-in for ffmpeg used by the tests. It understands just enough of the
command lines the pipeline builds to simulate success and failure:

- Convert: output is b'OK' + input. Input containing b'BAD' writes a partial
  output file and exits 1, like an encode that dies halfway.
- Concat (merge): output is b'OK' + all listed files. Fails like convert if any
  listed file contains b'BAD'.
- Decode to null (validate): exits 0 only if the file starts with b'OK'.

If FAKE_FFMPEG_LOG is set, each command line is appended to that file as JSON.
"""
import json
import os
import sys


def fail(out_path):
    with open(out_path, 'wb') as f:
        f.write(b'PARTIAL')
    print('fake ffmpeg: simulated failure', file=sys.stderr)
    sys.exit(1)


def main():
    args = sys.argv[1:]
    if os.environ.get('FAKE_FFMPEG_LOG'):
        with open(os.environ['FAKE_FFMPEG_LOG'], 'a', encoding='utf-8') as log:
            log.write(json.dumps(args) + '\n')
    out_path = args[-1]
    in_path = args[args.index('-i') + 1]

    if out_path == '-':
        with open(in_path, 'rb') as f:
            sys.exit(0 if f.read().startswith(b'OK') else 1)

    if '-f' in args and args[args.index('-f') + 1] == 'concat':
        data = b''
        with open(in_path) as filelist:
            for line in filelist:
                # Lines look like: file '<path>'
                with open(line.strip()[len("file '"):-1], 'rb') as f:
                    data += f.read()
    else:
        with open(in_path, 'rb') as f:
            data = f.read()

    if b'BAD' in data:
        fail(out_path)
    with open(out_path, 'wb') as f:
        f.write(b'OK' + data)


if __name__ == '__main__':
    main()
