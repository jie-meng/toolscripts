import sys
import os
from PyPDF2 import PdfMerger


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('please input pdf file path as argument')
        sys.exit(-1)

    pdf_path = os.path.realpath(sys.argv[1])
    pdfs = list(filter(lambda x: x.endswith('.pdf'), os.listdir(pdf_path)))
    pdfs.sort()

    merger = PdfMerger()

    for pdf in pdfs:
        print(pdf)
        merger.append(pdf)

    merger.write("result.pdf")
    merger.close()

    print('done')

