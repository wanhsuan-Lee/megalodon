import sys

from megalodon import mapping, megalodon_helper as mh, variants
from ._extras_parsers import get_parser_variants_atomize


HEADER = ['##fileformat=VCFv4.1', '##source=megalodon_atomized']
CONTIG_HEADER_LINE = "##contig=<ID={},length={}>"
COMMAND_HEADER_LINE = '##command="{}"'
FIELDS_LINE = ('#CHROM	POS	ID	REF	ALT	QUAL	FILTER' +
               '	INFO	FORMAT	SAMPLE')
RECORD_LINE = ('{chrm}\t{pos}\t{rid}\t{ref}\t{alts}\t.\t.\t{info}\t.\t.\n')


def _main(args):
    sys.stderr.write('Loading reference\n')
    aligner = mapping.alignerPlus(
        str(args.reference), preset=str('map-ont'), best_n=1)
    aligner.add_ref_lens()
    sys.stderr.write('Loading variants\n')
    var_data = variants.VarData(
        args.in_vcf, args.max_indel_size, keep_var_fp_open=True,
        aligner=aligner)
    contigs = var_data.variants_idx.header.contigs.values()
    sys.stderr.write('Atomizing variants\n')
    with open(args.out_vcf, 'w') as out_vars:
        out_vars.write('\n'.join(
            HEADER +
            [CONTIG_HEADER_LINE.format(ctg.name, ctg.length)
             for ctg in contigs] +
            [variants.CONTEXT_BASE_MI_LINE,
             COMMAND_HEADER_LINE.format(' '.join(sys.argv)),
             FIELDS_LINE]) + '\n')
        for ctg in contigs:
            chrm_seq = aligner.seq(ctg.name)
            if len(chrm_seq) != ctg.length:
                sys.stderr.write((
                    'WARNING: Mismatched contig lengths ({}) between ' +
                    'reference ({}) and input VCF ({})\n').format(
                        ctg.name, len(chrm_seq), ctg.length))
            map_pos = mapping.MAP_POS(
                chrm=ctg.name, strand=None, start=0, end=len(chrm_seq),
                q_trim_start=None, q_trim_end=None)
            for var in var_data.fetch_read_variants(
                    map_pos, mh.seq_to_int(chrm_seq)):
                out_vars.write(RECORD_LINE.format(
                    chrm=ctg.name, pos=var.ref_start + 1, rid=var.id,
                    ref=var.ref, alts=','.join(var.alts),
                    info=variants.HAS_CONTEXT_BASE_TAG
                    if var.has_context_base else '.'))

    sys.stderr.write('Indexing output variant file\n')
    variants.index_variants(args.out_vcf)


if __name__ == '__main__':
    _main(get_parser_variants_atomize().parse_args())