import os
import sys
import json
import subprocess
import shutil
import argparse
import zipfile
from pathlib import Path

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

def compile_target(target, output_path, page_offset=None, page_map=None):
    print(f"Compiling target: {target} -> {output_path}")
    
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
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {target}:")
        print(e.stderr.decode())
        sys.exit(1)

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

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy framework documentation")
    parser.add_argument(
        "--leave-individual",
        action="store_true",
        help="Keep individual PDFs as a zip file instead of deleting them"
    )
    args = parser.parse_args()
    
    check_dependencies()
    
    # Clean build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    
    hierarchy = extract_hierarchy()
    
    print("\n" + "="*60)
    print("PASS 1: Compiling sections and tracking page counts")
    print("="*60 + "\n")
    
    # Page tracking
    page_map = {}  # {section_id: starting_page}
    current_page = 1
    pdf_files = []
    
    # 1. Cover
    target = "cover"
    output = BUILD_DIR / "00_cover.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    page_map["cover"] = current_page
    page_count = get_pdf_page_count(output)
    print(f"  Cover: {page_count} pages (starting at {current_page})")
    current_page += page_count
    
    # 2. Preface
    target = "preface"
    output = BUILD_DIR / "01_preface.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    page_map["preface"] = current_page
    page_count = get_pdf_page_count(output)
    print(f"  Preface: {page_count} pages (starting at {current_page})")
    current_page += page_count
    
    # 3. Placeholder Outline (will be regenerated)
    target = "outline"
    output = BUILD_DIR / "02_outline.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    page_map["outline"] = current_page
    page_count = get_pdf_page_count(output)
    print(f"  Outline: {page_count} pages (starting at {current_page})")
    current_page += page_count
    
    # 4. Chapters
    for i, chapter in enumerate(hierarchy):
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        # Chapter Cover
        target = f"chapter-{chapter_id}"
        output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
        compile_target(target, output)
        pdf_files.append(output)
        page_map[f"chapter-{chapter_id}"] = current_page
        page_count = get_pdf_page_count(output)
        print(f"  Chapter {chapter_id} cover: {page_count} pages (starting at {current_page})")
        current_page += page_count
        
        # Pages
        for page in chapter["pages"]:
            page_id = page["id"]
            target = page_id
            output = BUILD_DIR / f"20_page_{page_id}.pdf"
            compile_target(target, output)
            pdf_files.append(output)
            page_map[page_id] = current_page
            page_count = get_pdf_page_count(output)
            print(f"  {page_id}: {page_count} pages (starting at {current_page})")
            current_page += page_count
    
    # Write page map to JSON
    page_map_file = BUILD_DIR / "page_map.json"
    with open(page_map_file, 'w') as f:
        json.dump(page_map, f, indent=2)
    print(f"\n✓ Page map written to {page_map_file}")
    print(f"✓ Total pages: {current_page - 1}\n")
    
    print("\n" + "="*60)
    print("PASS 2: Regenerating TOC and chapters with page numbers")
    print("="*60 + "\n")
    
    # 5. Regenerate Outline with page numbers
    target = "outline"
    output = BUILD_DIR / "02_outline.pdf"
    # Pass page map as JSON string
    # We'll need to modify compile_target to handle this
    compile_target(target, output, page_offset=page_map["outline"], page_map=page_map)
    print(f"  Regenerated outline with page numbers")
    
    # 6. Recompile chapters with page offsets
    for i, chapter in enumerate(hierarchy):
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        # Chapter Cover with offset
        target = f"chapter-{chapter_id}"
        output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
        page_offset = page_map[f"chapter-{chapter_id}"]
        compile_target(target, output, page_offset=page_offset)
        print(f"  Recompiled chapter {chapter_id} cover (page {page_offset})")
        
        # Pages with offset
        for page in chapter["pages"]:
            page_id = page["id"]
            target = page_id
            output = BUILD_DIR / f"20_page_{page_id}.pdf"
            page_offset = page_map[page_id]
            compile_target(target, output, page_offset=page_offset)
            print(f"  Recompiled {page_id} (page {page_offset})")
    
    # Merge all PDFs
    print("\n" + "="*60)
    print("Merging PDFs")
    print("="*60 + "\n")
    merge_pdfs_with_command(pdf_files, OUTPUT_FILE)
    print(f"✓ Successfully created {OUTPUT_FILE}")
    
    # Cleanup or archive build directory
    if args.leave_individual:
        zip_build_directory(BUILD_DIR)
        print(f"✓ Individual PDFs archived in build_pdfs.zip")
    
    # Always remove build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print("✓ Build directory cleaned up")

if __name__ == "__main__":
    main()
