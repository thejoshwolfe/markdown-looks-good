# markdown-looks-good

a markdown to html renderer that shows **all** _the_ `syntax`

## Demo

Check out this readme as HTML here: https://wolfesoftware.com/markdown-looks-good-example/README.html

## Design

I like the look of markdown syntax, and I don't think it needs to be hidden in the rendering.
Furthermore, I'd like to get very close to supporting "just works" status for selecting and copy+pasting from the browser into plain text.

Try coping swaths of this document from the GitHub rendering into a text file, then try it with my HTML rendering.
It's not perfect (I think it can't be perfect due to browser differences), but it's pretty close, and that's pretty cool.

This is a single-file Python script with no dependencies beyond the stdlib.

## Usage

Command line:

```
./markdown_looks_good.py input.md --output fragment.html
```

Then use that fragment in your html context.
Check out `suggested-template.html` for CSS suggestions and document structure ideas,
although note that this example is not meant to be polished.

You can also import the python file and call `markdown_to_html()` directly.

I suggest using https://github.com/thejoshwolfe/git-vendor to manage simple dependencies like this program.

To generate the HTML for this readme located here: https://wolfesoftware.com/markdown-looks-good-example/README.html :

```
./markdown_looks_good.py README.md --template suggested-template.html -o README.html
```

## Cool Stuff

Here's a demonstration of some features.

* unordered
* lists

and

1. ordered
2. lists

### Heading 3

You can link to section headings with bare text that exactly matches like this: Cool Stuff.

#### Heading 4

4th level headings are omitted from the table of contents by default. Use the `--toc-levels` parameter to configure this.

### Bold is Definitions and Generates internal links

If a term is written in **bold**, then any exact text matches of that phrase (e.g. bold) becomes an internal link.
I use this for technical writing in the Common ZIP project: https://commonzip.org/

If you don't like this feature, sorry there's no off switch for it (yet?). Let me know if want this feature.
It can get pretty surprising and all.

## But how do you...

The following are not supported because it's impossible to do the "just works" copy+pasting thing with them:

* links with the url hidden `[text](url)`
* images `![caption](url)`
* tables

This doesn't work because it's too complicated:

* syntax clue for triple-backtick blocks: `'''python` (except that the `'` are backticks)

Just haven't gotten around to these:

* block quotes `>`
* the whitespace parsing is a little picky, sorry.
