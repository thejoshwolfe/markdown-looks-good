#!/usr/bin/env python3

import sys, re, io
from collections import Counter

allowed_toc_levels = (0, 2, 3, 4)
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", metavar="input.md", help=
        "Give - for stdin.")
    parser.add_argument("-o", "--output", metavar="output.html", default="-", help=
        "Without --template, output does not include any <html><body> etc. "
        "Give - for stdout. Default: %(default)s")

    parser.add_argument("--template", metavar="base.html", help=
        "Path to a template html file that contains the bytes {{GENERATED_HTML_GOES_HERE}} "
        "which will be replaced by the generated html. "
        "The --output will be the result of this replacement instead of just the markdown-generated html. "
        "Note that this feature is very limited and not recommended for 'production' use cases, "
        "but it's convenient for generating the README.html and other hello-world-esque demonstrations.")

    parser.add_argument("--toc-levels", type=int, default=3, choices=allowed_toc_levels, help=
        "The number of levels to include in the table of contents. "
        "e.g. --toc-levels=4 would include #### headings. "
        "Give --toc-levels=0 to disable. "
        "Default: %(default)d")
    parser.add_argument("--no-internal-links", action="store_true")

    args = parser.parse_args()

    if args.input == "-":
        input_contents = std.stdin.read()
    else:
        with open(args.input) as f:
            input_contents = f.read()

    html = markdown_to_html(input_contents,
        do_internal_links=not args.no_internal_links,
        toc_levels=args.toc_levels,
    )

    if args.template:
        with open(args.template) as f:
            template_contents = f.read()
        split_template = template_contents.split("{{GENERATED_HTML_GOES_HERE}}")
        if len(split_template) != 2:
            sys.exit("ERROR: template must contain the bytes {{GENERATED_HTML_GOES_HERE}} exactly once: " + args.template)
        html = split_template[0] + html + split_template[1]

    if args.output == "-":
        print(html, end="")
    else:
        with open(args.output, "w") as f:
            f.write(html)

# Used in a first pass to preview what should be a link.
definition_re = re.compile(
    r'(?P<heading>^(?P<heading_hashes>#+) (?P<heading_inner>.*?)$)|'
    r'(?P<bold>\*\*(?P<bold_inner>.+?)\*\*)',
    re.MULTILINE
)

# Paragraphs, code blocks, headings, lists
structural_re = re.compile(
    r'(?P<heading>^(?P<heading_hashes>#+) (?P<heading_inner>.*?)(?P<heading_newlines>\n+))|'
    r'(?P<code_block>^```(?P<code_block_language>.*)\n(?P<code_block_body>(?:.*\n)*?)```$)|'
    r'(?P<unordered_list>^(?:\* .*\n)+)|'
    r'(?P<ordered_list>^(?:[0-9]+\. .*\n)+)|'
    r'(?P<other>^.*?$)'
    , re.MULTILINE
)
# Major syntax is contained within a structural element and can contain minor syntax.
major_syntax_re_template = (
    r'(?P<bold>\*\*(?P<bold_inner>.+?)\*\*)|'
    r'(?P<italics>_(?P<italics_inner>.+?)_)|'
    r'(?P<external_link>https?://\S+)|'

    # Then a dynamic set of internal links from definition_re. something like:
    # r'(?P<internal_link>Endnote `Something`|`MyStruct`|...)'
    r'(?P<internal_link>(?<!\w)(?:%s)(?!\w))|'

    # Then finally the same thing as minor_syntax_re.
    # This has to come after links which might also count as `code`.
    r'(?P<code>`(?P<code_inner>.+?)`)'
)
# Minor syntax can appear within major syntax, e.g. **bold with `code`**
minor_syntax_re = re.compile(
    r'(?P<code>`(?P<code_inner>.+?)`)'
)

def markdown_to_html(contents, *, do_internal_links, toc_levels):
    assert toc_levels in allowed_toc_levels, repr((toc_levels, allowed_toc_levels))

    # Preview to collect the set of all anchors that exist.
    internal_anchors = Counter()
    toc_levels_and_texts = [
        # e.g: (4, "`InfoZipUnicodePath` (`0x7075`)"),
    ]
    text_of_all_anchors = []
    for match in definition_re.finditer(contents):
        if match.group("heading") != None:
            hashes, text = match.group("heading_hashes"), match.group("heading_inner")
            slug = format_slug(text, add_to=internal_anchors)
            toc_levels_and_texts.append((len(hashes), text))
            text_of_all_anchors.append(text)
        elif match.group("bold") != None:
            text = match.group("bold_inner")
            slug = format_slug(text, add_to=internal_anchors)
            text_of_all_anchors.append(text)
        else: assert False, match.group()

    duplicate_anchors = [slug for slug, count in internal_anchors.items() if count > 1]
    if duplicate_anchors:
        sys.exit("\n".join("ERROR: duplicate anchor: " + slug for slug in duplicate_anchors))

    # Generate toc_html
    out = io.StringIO()
    def set_indentation(level):
        return # TODO: add ul/li nesting for TOC for better screen reader support.
    for level, text in toc_levels_and_texts:
        if level > toc_levels: continue
        if out.tell() == 0:
            out.write("<ul class=custom>\n")
        set_indentation(level)
        plain, formatted = format_minor_syntax(text)
        out.write("<li><span class=symbol>{}&nbsp;</span><a class=internal href=#{}>{}</a></li>\n".format(
            "#" * level,
            format_slug(plain),
            formatted,
        ))
    if out.tell() != 0:
        out.write("</ul>\n")
        toc_html = "<div class=label>Contents</div>\n" + out.getvalue()
        out = io.StringIO()
    else:
        toc_html = ""
    set_indentation(1)


    # Construct major_syntax_re including all found links.
    text_of_all_anchors.sort(key=lambda s: len(s), reverse=True)
    major_syntax_re = re.compile(major_syntax_re_template % "|".join(re.escape(text) for text in text_of_all_anchors))

    internal_anchors_again = Counter() # asserted same as internal_anchors
    internal_links = set()

    currently_in_paragraph = False
    def ensure_paragraph():
        nonlocal currently_in_paragraph
        if not currently_in_paragraph:
            out.write("<p>\n")
            currently_in_paragraph = True
    def flush_paragraph():
        nonlocal currently_in_paragraph
        if currently_in_paragraph:
            out.write("</p>\n")
            currently_in_paragraph = False

    def write_major_syntax(text):
        while True:
            match = major_syntax_re.search(text)
            if match == None:
                out.write(escape_text(text))
                return
            out.write(escape_text(text[:match.span()[0]]))

            if match.group("external_link"):
                out.write("<a class=external href={}>{}</a>".format(
                    escape_attribute(match.group()),
                    escape_text(match.group()),
                ))
            elif match.group("bold"):
                plain, formatted = format_minor_syntax(match.group("bold_inner"))
                slug = format_slug(plain, add_to=internal_anchors_again)
                out.write("<strong id={}>{}{}{}</strong>".format(
                    slug,
                    "<a class=self-link href=#{}><span class=symbol>**</span></a>".format(slug),
                    formatted,
                    "<span class=symbol>**</span>",
                ))
            elif match.group("italics"):
                plain, formatted = format_minor_syntax(match.group("italics_inner"))
                out.write("<span class=symbol>_</span><em>{}</em><span class=symbol>_</span>".format(formatted))
            elif match.group("internal_link"):
                plain, formatted = format_minor_syntax(match.group())
                if do_internal_links:
                    out.write("<a class=internal href=#{}>{}</a>".format(
                        format_slug(plain, add_to=internal_links),
                        formatted,
                    ))
                else:
                    out.write(formatted)
            elif match.group("code"):
                out.write("{}<code>{}</code>{}".format(
                    "<span class=symbol>`</span>",
                    escape_text(match.group("code_inner")),
                    "<span class=symbol>`</span>",
                ))
            else: assert False, match.group()

            text = text[match.span()[1]:]

    found_first_non_h1_heading = False

    for structure in structural_re.finditer(contents):
        if structure.group("heading") != None:
            assert not currently_in_paragraph, "Need a blank line before a # heading: " + repr(structure.group())
            newlines = structure.group("heading_newlines")
            assert len(newlines) == 2, "Need exactly one blank line after # heading" + repr(structure.group())
            hashes, text = structure.group("heading_hashes"), structure.group("heading_inner")
            h_number = len(hashes)
            assert 1 <= h_number <= 4

            if h_number > 1 and not found_first_non_h1_heading:
                found_first_non_h1_heading = True
                if toc_html:
                    out.write("<div id=toc class=no-print>\n" + toc_html + "\n</div>\n")

            plain, formatted = format_minor_syntax(text)
            if h_number > 1:
                out.write("<br class=firefox-only>")
            slug = format_slug(plain, add_to=internal_anchors_again)
            out.write("<h{} id={}><a class=self-link href=#{}><span class=symbol>{}</span></a> {}</h{}>".format(
                h_number,
                slug,
                slug,
                hashes,
                formatted,
                h_number,
            ))
            out.write("<br class=chrome-only>")

        elif structure.group("code_block") != None:
            language = structure.group("code_block_language")
            assert not language, "TODO: code block syntax highlighting"
            flush_paragraph()
            out.write("<pre><span class=symbol>```</span>\n")
            out.write(escape_text(structure.group("code_block_body")))
            out.write("<span class=symbol>```</span></pre>")

        elif structure.group("unordered_list") != None:
            flush_paragraph()
            lines = structure.group().rstrip().split("\n")
            out.write("<ul class=custom>\n")
            for line in lines:
                line = line.split(" ", 1)[1]
                out.write("<li class=custom><span class=symbol>*</span> ")
                write_major_syntax(line)
                out.write("</li>\n")
            out.write("</ul>\n")

        elif structure.group("ordered_list") != None:
            flush_paragraph()
            lines = structure.group().rstrip().split("\n")
            out.write("<ol class=custom>\n")
            expected_number = 1
            for line in lines:
                out.write("<li class=custom>")
                found_number = int(line.split(". ")[0])
                assert found_number == expected_number, "Non-sequential ordered list: " + line
                expected_number += 1
                write_major_syntax(line)
                out.write("</li>\n")
            out.write("</ol>\n")

        elif structure.group("other") != None:
            text = structure.group()
            if text:
                # Regular paragraph text.
                ensure_paragraph()
                write_major_syntax(text)
                out.write("\n")
            else:
                # Blank line terminates a paragraph.
                flush_paragraph()
        else: assert False

    # EOF terminates a paragraph.
    flush_paragraph()

    assert internal_anchors == internal_anchors_again

    broken_links = [slug for slug in internal_links if slug not in internal_anchors.keys()]
    for slug in sorted(broken_links):
        print("WARNING: broken link: " + slug, file=sys.stderr)

    body_html = out.getvalue()

    return body_html

def format_minor_syntax(text):
    plain = io.StringIO()
    formatted = io.StringIO()
    while True:
        match = minor_syntax_re.search(text)
        if match == None:
            plain.write(text)
            formatted.write(escape_text(text))
            break
        plain.write(text[:match.span()[0]])
        formatted.write(escape_text(text[:match.span()[0]]))

        if match.group("code"):
            inner = match.group("code_inner")
            plain.write(inner)
            formatted.write("{}<code>{}</code>{}".format(
                "<span class=symbol>`</span>",
                escape_text(inner),
                "<span class=symbol>`</span>",
            ))
        else: assert False, match.group()

        text = text[match.span()[1]:]
    return plain.getvalue(), formatted.getvalue()

attribute_substitutions = {
    # https://www.w3.org/TR/2012/WD-html-markup-20120329/syntax.html#syntax-attr-unquoted
    '"': "&quot;",
    "'": "&apos;",
    "=": "&#61;",
    ">": "&gt;",
    "<": "&lt;",
    "`": "&#96;",
    "&": "&amp;",
}
attribute_escape_re = re.compile(r'[{}]'.format(r''.join(attribute_substitutions.keys())))
def escape_attribute(text):
    return attribute_escape_re.sub((lambda m: attribute_substitutions[m.group()]), text)
text_substitutions = {
    ">": "&gt;",
    "<": "&lt;",
    "&": "&amp;",
}
text_escape_re = re.compile(r'[{}]'.format(r''.join(text_substitutions.keys())))
def escape_text(text):
    return text_escape_re.sub((lambda m: text_substitutions[m.group()]), text)

def escape_cdata(text):
    return text.replace("]]>", "]]]]><![CDATA[>")

non_slug_text_re = re.compile(r'[^A-Za-z0-9]+')
def format_slug(text, add_to=None):
    slug = non_slug_text_re.sub("-", text).removeprefix("-").removesuffix("-")
    assert slug, repr(text)
    if add_to != None:
        # This works for set() and Counter()
        add_to.update([slug])
    return slug


if __name__ == "__main__":
    main()
