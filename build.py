import os
import sys
import json
import subprocess
import shutil
import argparse
import zipfile
from pathlib import Path

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback progress function
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.n = 0
            self.total = total
            if desc:
                print(f"\n{desc}")
        
        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)
        
        def update(self, n=1):
            self.n += n
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass

# Configuration
BUILD_DIR = Path("build")
OUTPUT_FILE = Path("output.pdf")
RENDERER_FILE = "renderer.typ"

def check_dependencies():
    if shutil.which("typst") is None:
        print("Error: 'typst' executable not found in PATH.")
        sys.exit(1)
    if shutil.which("pdfinfo") is None:
        print("Error: 'pdfinfo' executable not found in PATH.")
        print("Install with: brew install poppler")
        sys.exit(1)

def get_pdf_page_count(pdf_path):
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
        return 0
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting page count for {pdf_path}: {e}")
        return 0


def extract_hierarchy():
    print("Extracting document hierarchy...")
    
    temp_file = Path("extract_hierarchy.typ")
    temp_file.write_text('#import "config.typ": hierarchy\n#metadata(hierarchy) <hierarchy>')
    
    try:
        result = subprocess.run(
            ["typst", "query", str(temp_file), "<hierarchy>"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data[0]["value"]
    except subprocess.CalledProcessError as e:
        print(f"Error extracting hierarchy: {e.stderr}")
        sys.exit(1)
    finally:
        if temp_file.exists():
            temp_file.unlink()

def compile_target(target, output_path, page_offset=None, page_map=None, quiet=True):
    cmd = [
        "typst", "compile", 
        RENDERER_FILE, 
        str(output_path),
        "--input", f"target={target}"
    ]
    
    if page_offset is not None:
        cmd.extend(["--input", f"page-offset={page_offset}"])
    
    if page_map is not None:
        # Pass JSON string without escaping quotes since we're using single quotes in shell
        page_map_json_str = json.dumps(page_map)
        cmd.extend(["--input", f"page-map={page_map_json_str}"])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(f"Error compiling {target}:")
            print(e.stderr.decode())
        raise

def merge_pdfs_with_command(pdf_files, output_path):
    # Filter out non-existent files
    existing_files = [str(pdf) for pdf in pdf_files if pdf.exists()]
    
    if not existing_files:
        print("No PDF files to merge!")
        return
    
    print(f"Merging {len(existing_files)} files into {output_path}...")
    
    # Try pdfunite first (from poppler-utils)
    if shutil.which("pdfunite"):
        cmd = ["pdfunite"] + existing_files + [str(output_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Successfully merged PDFs using pdfunite")
            return
        except subprocess.CalledProcessError as e:
            print(f"pdfunite failed: {e.stderr.decode()}")
    
    # Try ghostscript as fallback
    if shutil.which("gs"):
        cmd = [
            "gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
            f"-sOutputFile={output_path}"
        ] + existing_files
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Successfully merged PDFs using ghostscript")
            return
        except subprocess.CalledProcessError as e:
            print(f"ghostscript failed: {e.stderr.decode()}")
    
    # If both fail, print warning
    print("Warning: No PDF merge tool found (tried pdfunite and gs)")
    print("Individual PDFs are available in the build/ directory")
    print("To install a merge tool:")
    print("  - macOS: brew install poppler")
    print("  - Linux: apt-get install poppler-utils or ghostscript")

def zip_build_directory(build_dir, output_file="build_pdfs.zip"):
    print(f"Zipping build directory to {output_file}...")
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(build_dir.parent)
                zipf.write(file_path, arcname)
    print(f"Created {output_file}")

def create_pdf_metadata(hierarchy, page_map, output_file="bookmarks.txt"):
    """Create PDF bookmarks file for adding TOC metadata to the final PDF"""
    print(f"Creating PDF bookmarks file: {output_file}...")
    
    bookmarks = []
    
    # Add cover and preface
    if "cover" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Cover")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['cover']}")
    
    if "preface" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Preface")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['preface']}")
    
    if "outline" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Table of Contents")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['outline']}")
    
    # Add chapters and pages
    for chapter in hierarchy:
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        # Chapter bookmark
        if f"chapter-{chapter_id}" in page_map:
            bookmarks.append(f"BookmarkBegin")
            bookmarks.append(f"BookmarkTitle: {chapter['title']}")
            bookmarks.append(f"BookmarkLevel: 1")
            bookmarks.append(f"BookmarkPageNumber: {page_map[f'chapter-{chapter_id}']}")
        
        # Page bookmarks (as sub-items of chapter)
        for page in chapter["pages"]:
            page_id = page["id"]
            if page_id in page_map:
                bookmarks.append(f"BookmarkBegin")
                bookmarks.append(f"BookmarkTitle: {page['title']}")
                bookmarks.append(f"BookmarkLevel: 2")
                bookmarks.append(f"BookmarkPageNumber: {page_map[page_id]}")
    
    # Write bookmarks file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bookmarks))
    
    print(f"✓ Created bookmarks file with {len(bookmarks)//4} entries")
    return output_file

def apply_pdf_metadata(pdf_path, bookmarks_file, title="Noteworthy Framework", author=""):
    """Apply metadata and bookmarks to PDF using pdftk or ghostscript"""
    temp_pdf = BUILD_DIR / "temp_with_metadata.pdf"
    
    # Try pdftk first (best quality)
    if shutil.which("pdftk"):
        try:
            # Update metadata
            info_file = BUILD_DIR / "pdf_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"InfoBegin\n")
                f.write(f"InfoKey: Title\n")
                f.write(f"InfoValue: {title}\n")
                if author:
                    f.write(f"InfoKey: Author\n")
                    f.write(f"InfoValue: {author}\n")
            
            # First add metadata
            subprocess.run([
                "pdftk", str(pdf_path), "update_info", str(info_file), 
                "output", str(temp_pdf)
            ], check=True, capture_output=True)
            
            # Then add bookmarks
            temp_pdf2 = BUILD_DIR / "temp_with_bookmarks.pdf"
            subprocess.run([
                "pdftk", str(temp_pdf), "update_info", str(bookmarks_file),
                "output", str(temp_pdf2)
            ], check=True, capture_output=True)
            
            shutil.move(temp_pdf2, pdf_path)
            print("✓ Applied PDF metadata and bookmarks using pdftk")
            return True
        except subprocess.CalledProcessError as e:
            print(f"pdftk failed: {e.stderr.decode()}")
    
    # Fallback: Try ghostscript with pdfmark
    if shutil.which("gs"):
        try:
            # Convert bookmarks to pdfmark format
            pdfmark_file = BUILD_DIR / "bookmarks.pdfmark"
            with open(bookmarks_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            pdfmarks = []
            pdfmarks.append("[ /Title (%s) /Author (%s) /DOCINFO pdfmark" % (title, author))
            
            i = 0
            while i < len(lines):
                if lines[i].strip() == "BookmarkBegin":
                    title_line = lines[i+1].strip()
                    level_line = lines[i+2].strip()
                    page_line = lines[i+3].strip()
                    
                    bm_title = title_line.split(": ", 1)[1] if ": " in title_line else ""
                    bm_level = level_line.split(": ", 1)[1] if ": " in level_line else "1"
                    bm_page = page_line.split(": ", 1)[1] if ": " in page_line else "1"
                    
                    pdfmarks.append(f"[ /Title ({bm_title}) /Page {bm_page} /Count 0 /OUT pdfmark")
                    i += 4
                else:
                    i += 1
            
            with open(pdfmark_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(pdfmarks))
            
            # Apply with ghostscript
            subprocess.run([
                "gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
                f"-sOutputFile={temp_pdf}",
                str(pdf_path),
                str(pdfmark_file)
            ], check=True, capture_output=True)
            
            shutil.move(temp_pdf, pdf_path)
            print("✓ Applied PDF metadata using ghostscript")
            return True
        except subprocess.CalledProcessError as e:
            print(f"ghostscript metadata failed: {e.stderr.decode()}")
    
    print("⚠ Warning: Could not apply PDF metadata (pdftk or gs required)")
    print("  Install with: brew install pdftk-java")
    return False

def add_toc_links(pdf_path, page_map, hierarchy, toc_page=2):
    """Add clickable link annotations to the TOC page using pypdf"""
    try:
        # Try importing pypdf (newer) or PyPDF2 (older)
        try:
            from pypdf import PdfReader, PdfWriter
            from pypdf.generic import DictionaryObject, ArrayObject, NumberObject, NameObject, TextStringObject
        except ImportError:
            try:
                from PyPDF2 import PdfReader, PdfWriter
                from PyPDF2.generic import DictionaryObject, ArrayObject, NumberObject, NameObject, TextStringObject
            except ImportError:
                print("⚠ Warning: pypdf or PyPDF2 not installed. Cannot add TOC links.")
                print("  Install with: pip3 install pypdf")
                return False
        
        print(f"Adding clickable links to TOC page {toc_page + 1}...")
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # First, copy all pages to writer
        for page in reader.pages:
            writer.add_page(page)
        
        #Copy metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)
        
        # Calculate approximate line positions for TOC entries
        # TOC starts around y=650 and each entry is ~25 points apart
        y_start = 650
        line_height = 25
        chapter_spacing = 60
        
        current_y = y_start
        link_annotations = []
        
        # Add links for each chapter and its pages
        for chapter in hierarchy:
            first_page = chapter["pages"][0]
            chapter_id = first_page["id"][:2]
            
            # Chapter link
            if f"chapter-{chapter_id}" in page_map:
                chapter_page = page_map[f"chapter-{chapter_id}"] - 1  # 0-indexed
                
                # Create link annotation for chapter title (full width)
                link = DictionaryObject()
                link.update({
                    NameObject("/Type"): NameObject("/Annot"),
                    NameObject("/Subtype"): NameObject("/Link"),
                    NameObject("/Rect"): ArrayObject([
                        NumberObject(50),   # left
                        NumberObject(current_y - 5),  # bottom
                        NumberObject(550),  # right
                        NumberObject(current_y + 20), # top
                    ]),
                    NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
                    NameObject("/Dest"): ArrayObject([
                        writer.pages[chapter_page].indirect_reference,
                        NameObject("/XYZ"),
                        NumberObject(0),
                        NumberObject(842),
                        NumberObject(0)
                    ])
                })
                link_annotations.append(link)
                current_y -= line_height + 10
            
            # Page/section links
            for page in chapter["pages"]:
                page_id = page["id"]
                if page_id in page_map:
                    target_page = page_map[page_id] - 1  # 0-indexed
                    
                    # Create link annotation for each section entry
                    link = DictionaryObject()
                    link.update({
                        NameObject("/Type"): NameObject("/Annot"),
                        NameObject("/Subtype"): NameObject("/Link"),
                        NameObject("/Rect"): ArrayObject([
                            NumberObject(70),    # left (indented)
                            NumberObject(current_y - 5),   # bottom
                            NumberObject(550),   # right
                            NumberObject(current_y + 15),  # top
                        ]),
                        NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
                        NameObject("/Dest"): ArrayObject([
                            writer.pages[target_page].indirect_reference,
                            NameObject("/XYZ"),
                            NumberObject(0),
                            NumberObject(842),
                            NumberObject(0)
                        ])
                    })
                    link_annotations.append(link)
                    current_y -= line_height
            
            current_y -= chapter_spacing  # Extra space between chapters
        
        # Add annotations to TOC page
        if "/Annots" in writer.pages[toc_page]:
            writer.pages[toc_page][NameObject("/Annots")].extend(link_annotations)
        else:
            writer.pages[toc_page][NameObject("/Annots")] = ArrayObject(link_annotations)
        
        # Write output
        temp_pdf = BUILD_DIR / "temp_with_links.pdf"
        with open(temp_pdf, "wb") as output_file:
            writer.write(output_file)
        
        shutil.move(temp_pdf, pdf_path)
        print(f"✓ Added {len(link_annotations)} clickable links to TOC")
        return True
        
    except Exception as e:
        print(f"⚠ Warning: Could not add TOC links: {e}")
        print("  The PDF will still work, but TOC entries won't be clickable")
        return False

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy framework documentation")
    parser.add_argument(
        "--leave-individual",
        action="store_true",
        help="Keep individual PDFs as a zip file instead of deleting them"
    )
    args = parser.parse_args()
    
    check_dependencies()
    
    print("\n" + "="*60)
    print("NOTEWORTHY BUILD SYSTEM")
    print("="*60)
    
    # Clean build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    
    hierarchy = extract_hierarchy()
    
    # Calculate total compilation tasks
    total_sections = 2 + 1  # cover + preface + outline
    for chapter in hierarchy:
        total_sections += 1 + len(chapter["pages"])  # chapter cover + pages
    
    print(f"\nDocument structure: {len(hierarchy)} chapters, {total_sections} total sections\n")
    
    print("="*60)
    print("PASS 1: Initial Compilation & Page Tracking")
    print("="*60 + "\n")
    
    # Page tracking
    page_map = {}  # {section_id: starting_page}
    current_page = 1
    pdf_files = []
    
    # Create progress bar for pass 1
    with tqdm(total=total_sections, desc="Compiling sections", unit="section", ncols=80) as pbar:
        # 1. Cover
        target = "cover"
        output = BUILD_DIR / "00_cover.pdf"
        pbar.set_description("Cover page")
        compile_target(target, output)
        pdf_files.append(output)
        page_map["cover"] = current_page
        page_count = get_pdf_page_count(output)
        current_page += page_count
        pbar.update(1)
        
        # 2. Preface
        target = "preface"
        output = BUILD_DIR / "01_preface.pdf"
        pbar.set_description("Preface")
        compile_target(target, output)
        pdf_files.append(output)
        page_map["preface"] = current_page
        page_count = get_pdf_page_count(output)
        current_page += page_count
        pbar.update(1)
        
        # 3. Placeholder Outline (will be regenerated)
        target = "outline"
        output = BUILD_DIR / "02_outline.pdf"
        pbar.set_description("Table of Contents")
        compile_target(target, output)
        pdf_files.append(output)
        page_map["outline"] = current_page
        page_count = get_pdf_page_count(output)
        current_page += page_count
        pbar.update(1)
        
        # 4. Chapters
        for i, chapter in enumerate(hierarchy):
            first_page = chapter["pages"][0]
            chapter_id = first_page["id"][:2]
            
            # Chapter Cover
            target = f"chapter-{chapter_id}"
            output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
            pbar.set_description(f"Chapter {chapter_id}")
            compile_target(target, output)
            pdf_files.append(output)
            page_map[f"chapter-{chapter_id}"] = current_page
            page_count = get_pdf_page_count(output)
            current_page += page_count
            pbar.update(1)
            
            # Pages
            for page in chapter["pages"]:
                page_id = page["id"]
                target = page_id
                output = BUILD_DIR / f"20_page_{page_id}.pdf"
                pbar.set_description(f"Section {page_id}")
                compile_target(target, output)
                pdf_files.append(output)
                page_map[page_id] = current_page
                page_count = get_pdf_page_count(output)
                current_page += page_count
                pbar.update(1)
    
    # Write page map to JSON
    page_map_file = BUILD_DIR / "page_map.json"
    with open(page_map_file, 'w') as f:
        json.dump(page_map, f, indent=2)
    
    print(f"\n✓ Total pages: {current_page - 1}")
    
    print("\n" + "="*60)
    print("PASS 2: Regenerating with Page Numbers")
    print("="*60 + "\n")
    
    # Create progress bar for pass 2
    with tqdm(total=total_sections, desc="Regenerating", unit="section", ncols=80) as pbar:
        # Skip cover and preface (no page numbers needed)
        pbar.update(2)
        
        # 5. Regenerate Outline with page numbers
        target = "outline"
        output = BUILD_DIR / "02_outline.pdf"
        pbar.set_description("TOC with page numbers")
        compile_target(target, output, page_offset=page_map["outline"], page_map=page_map)
        pbar.update(1)
        
        # 6. Recompile chapters with page offsets
        for i, chapter in enumerate(hierarchy):
            first_page = chapter["pages"][0]
            chapter_id = first_page["id"][:2]
            
            # Chapter Cover with offset
            target = f"chapter-{chapter_id}"
            output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
            page_offset = page_map[f"chapter-{chapter_id}"]
            pbar.set_description(f"Chapter {chapter_id}")
            compile_target(target, output, page_offset=page_offset)
            pbar.update(1)
            
            # Pages with offset
            for page in chapter["pages"]:
                page_id = page["id"]
                target = page_id
                output = BUILD_DIR / f"20_page_{page_id}.pdf"
                page_offset = page_map[page_id]
                pbar.set_description(f"Section {page_id}")
                compile_target(target, output, page_offset=page_offset)
                pbar.update(1)
    
    # Merge all PDFs
    print("\n" + "="*60)
    print("Merging PDFs")
    print("="*60 + "\n")
    merge_pdfs_with_command(pdf_files, OUTPUT_FILE)
    print(f"✓ Successfully created {OUTPUT_FILE}")
    
    # Add PDF metadata and bookmarks
    print("\n" + "="*60)
    print("Adding PDF Metadata & Bookmarks")
    print("="*60 + "\n")
    bookmarks_file = BUILD_DIR / "bookmarks.txt"
    create_pdf_metadata(hierarchy, page_map, bookmarks_file)
    
    # Extract title and authors from hierarchy/config
    title = "Noteworthy Framework"
    author = "Sihoo Lee, Lee Hojun"  # Update this to match config.typ
    apply_pdf_metadata(OUTPUT_FILE, bookmarks_file, title, author)
    
    # Cleanup or archive build directory
    print("\n" + "="*60)
    print("Cleanup")
    print("="*60 + "\n")
    
    if args.leave_individual:
        zip_build_directory(BUILD_DIR)
        print(f"✓ Individual PDFs archived in build_pdfs.zip")
    
    # Always remove build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print("✓ Build directory cleaned up")
    
    print("\n" + "="*60)
    print("BUILD COMPLETE!")
    print("="*60)
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Total pages: {current_page - 1}")
    print(f"Chapters: {len(hierarchy)}\n")

if __name__ == "__main__":
    main()
