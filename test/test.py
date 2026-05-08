#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, argparse, shutil
sys.path.append('..')
from core import config, index, spec, bom, sds, stamp, output, schematic

def main():
    old_path = os.getcwd()
    prog_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(prog_path, '..'))
    if os.name == 'nt':
        sys.stdout.reconfigure(encoding='utf-8')
    config.load('settings.conf')
    # convert paths to absolute
    config.set('output', 'latex_path', os.path.abspath(config.get('output', 'latex_path')))
    config.set('output', 'template_path', os.path.abspath(config.get('output', 'template_path')))
    os.chdir(old_path)
    parser = argparse.ArgumentParser(sys.argv)
    parser.add_argument('input', help='input filename')
    parser.add_argument('output', help='output filename')
    parser.add_argument('-t', '--type', default = 'index', help='doc type (index|spec|bom)')
    args = parser.parse_args()
    do(args.input, args.output, args.type)
#    sch = schematic.Schematic(args.input)

def do(sch, out, doc):
    if doc == 'index':
        table = index.build(sch)
    elif doc == 'spec':
        table = spec.build(sch)
    elif doc == 'bom':
        table = bom.build(sch)
    elif doc == 'sds':
        table = sds.build(sch)
    stamp_dict = stamp.build(sch, doc)
    if out[-3:] == 'tex':
        output.latex(table, stamp_dict, out)
        latex_path = config.get('output', 'latex_path')
        shutil.copy(os.path.join(latex_path, 'eskdextraspec.sty'), '.')
        shutil.copy(os.path.join(latex_path, 'eskdextratab.cls'), '.')
    elif out[-3:] == 'pdf':
        out_tex = out[:-3] + 'tex'  
        output.latex(table, stamp_dict, out_tex)
        latex_path = config.get('output', 'latex_path')
        shutil.copy(os.path.join(latex_path, 'eskdextraspec.sty'), '.')
        shutil.copy(os.path.join(latex_path, 'eskdextratab.cls'), '.')
        os.system('pdflatex -halt-on-error "%s"'%out_tex)
        os.system('pdflatex -halt-on-error "%s"'%out_tex)
        os.system('rm -f eskdextraspec.sty')
        os.system('rm -f eskdextratab.cls')
        os.system('rm -f *.aux')
        os.system('rm -f *.log')
        os.system('rm -f *.out')
        os.system('rm -f *-converted-to.pdf')
        os.system('rm -f %s'%out_tex)
    elif out[-3:] == 'csv':
        output.csv(table, stamp_dict, out)
    elif out[-3:] == 'xls':
        output.xls(table, stamp_dict, out)
    output.screen(table, stamp_dict)

if __name__ == "__main__":
    main()
