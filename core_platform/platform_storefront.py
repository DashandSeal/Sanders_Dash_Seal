"""Platform storefronts — every platform's own public face.

Built under the Founder's orders of 2026-11-26: "Finish the platforms
and their storefronts" (23:11 MST), on the storefront standard he ruled
the same day — when a person opens a platform they get the full suite
of services through that platform, not a static scaled-down feel; the
platforms connect people around the globe; workflows connect industries
together globally, in real time; and the platforms sell access globally.

WHAT THIS MODULE DOES

* render_storefront(platform_id) renders one platform's storefront
  from its definition of record (core_platform/platform_definitions.py):
  who it is, why it exists, whom it serves, its six NACI industries,
  its full service suite, its business model, its ties to the four
  companies, and its access path — its Stripe product and price of
  record where they exist, and an honest statement where they do not.
* render_directory() renders the directory of every platform of
  record, each opening into its own storefront.

The app serves these at /platforms and /platforms/<platform_id>
(app/customer_app.py). The pages are presented the Sanders way —
marble and jade, under both seals: the Headquarters seal and the
company seal are the exact original seal files, served by the app at
/assets/seal-corporate-hq.png and the company asset paths, sized by
CSS only. No seal is generated, redrawn, or approximated here; this
module only references the served originals, exactly as the existing
platform pages (Lil Mama, Baby Girl) do.

ACCESS, stated honestly: where a platform holds a live Stripe product,
the storefront names the product and its price of record, and the
purchase door is the house’s own — the client portal and appointments
— because in the examined set no self-serve payment link exists for
any platform product and the app’s checkout is the operator-mediated
case checkout. Where a price of record stands without a Stripe
product yet (the prices ruled in the Founder’s deliberation program
of 2026-11-27, whose Stripe products land separately), the storefront
shows the price of record itself. Where the Founder has ruled no
shelf price (Daedalus — enterprise agreements only), the storefront
shows no price and says why. No price is invented anywhere in this
module.
"""

import html

from .platform_definitions import DEFINITIONS, definition_for

_HQ_SEAL = '/assets/seal-corporate-hq.png'
_COMPANY_SEALS = (
    ('/assets/seal-corporate-hq.png',
     'Sanders Corporate Headquarters seal, carried for S & G Security Inc. '
     'as corporate headquarters'),
    ('/assets/seal-home-healthcare.png',
     'Sanders Home Healthcare & Caregivers LLC seal'),
    ('/assets/seal-senior-living.png',
     'Sanders Senior Living LLC seal'),
    ('/assets/seal-legal-helpers.png',
     'Sanders Legal Helpers LLC seal'),
)

_COMPANIES_LINE = ('S & G Security Inc. · Sanders Home Healthcare & '
                   'Caregivers LLC · Sanders Senior Living LLC · '
                   'Sanders Legal Helpers LLC')


def _esc(text):
    return html.escape(str(text), quote=True)


def _head(title, description):
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>%s</title>\n'
        '<meta name="description" content="%s">\n'
        '<link rel="stylesheet" href="/assets/business-faces.css">\n'
        '<link rel="stylesheet" href="/assets/platform-storefront.css">\n'
        '</head>\n<body>\n'
    ) % (_esc(title), _esc(description))


def _topbar(name):
    return (
        '<header class="topbar">\n'
        '  <a class="brand" href="/platforms" aria-label="%s">\n'
        '    <span class="seal-pair">\n'
        '      <span class="medallion"><img src="%s" alt="Sanders Corporate '
        'Headquarters seal, carried for S &amp; G Security Inc. as corporate '
        'headquarters"></span>\n'
        '      <span class="medallion"><img src="%s" alt="S &amp; G Security '
        'Inc. company seal"></span>\n'
        '    </span>\n'
        '    <span class="brand-word">\n'
        '      <strong>%s</strong>\n'
        '      <small>S &amp; G Security Inc.</small>\n'
        '    </span>\n'
        '  </a>\n'
        '  <nav class="topnav" aria-label="Primary">\n'
        '    <a href="#why">Why It Exists</a>\n'
        '    <a href="#suite">Service Suite</a>\n'
        '    <a href="#access">Access</a>\n'
        '    <a class="nav-cta" href="/appointments">Book an appointment</a>\n'
        '    <a href="/auth/login">Client sign in</a>\n'
        '  </nav>\n'
        '</header>\n'
    ) % (_esc(name), _HQ_SEAL, _HQ_SEAL, _esc(name))


def _footer():
    seals = '\n'.join(
        '      <span class="medallion"><img src="%s" alt="%s"></span>'
        % (path, _esc(alt)) for path, alt in _COMPANY_SEALS)
    return (
        '<footer>\n'
        '  <div class="seal-strip">\n%s\n  </div>\n'
        '  <p class="footer-lines">%s</p>\n'
        '  <p class="footer-tagline">Native by Design. Global by Design.</p>\n'
        '</footer>\n'
        '</body>\n</html>\n'
    ) % (seals, _esc(_COMPANIES_LINE))


def _price_branch(defn):
    """The price branch of a definition, by the prefix logic the
    Access panel has always used — shared here so the directory
    shelf and the storefront Access panel can never disagree about
    which branch a platform stands on. Returns (branch, price,
    stripe): branch is one of 'live', 'of_record', 'enterprise',
    'not_settled', 'unruled', or 'none'."""
    price = defn.price_of_record or ''
    stripe = defn.stripe_product or ''
    if stripe.startswith('YES'):
        return ('live', price, stripe)
    if price.startswith('OF RECORD'):
        return ('of_record', price, stripe)
    if price.startswith('ENTERPRISE AGREEMENTS'):
        return ('enterprise', price, stripe)
    if price.startswith('NOT SETTLED'):
        return ('not_settled', price, stripe)
    if price.startswith('UNRULED'):
        return ('unruled', price, stripe)
    return ('none', price, stripe)


def _price_line(defn):
    """The directory card's price line, or None where no price
    line stands. The string shown is the platform's own price of
    record, exactly as its Access panel prints it — nothing is
    relabeled, repriced, or invented here. Daedalus carries no
    shelf price by ruling; her card says so instead. A platform
    with no price of record shows no price line at all."""
    branch, price, _stripe = _price_branch(defn)
    if branch in ('live', 'of_record'):
        return price
    if branch == 'enterprise':
        return 'Enterprise agreements only \u2014 no shelf price.'
    return None


def _access_block(defn):
    branch, price, stripe = _price_branch(defn)
    if branch == 'live':
        body = (
            '<p>This platform\'s access is a live product of record: '
            '<strong>%s</strong>, at <strong>%s</strong>.</p>\n'
            '<p>Access is completed with the house — book an appointment or '
            'open the client portal and name this platform; the engagement '
            'is confirmed by a person, and payment runs through the '
            'house\'s own checkout of record.</p>'
        ) % (_esc(stripe), _esc(price))
    elif branch == 'of_record':
        body = (
            '<p>This platform\'s price of record: '
            '<strong>%s</strong>.</p>\n'
            '<p>Access is completed with the house — book an appointment '
            'or open the client portal and name this platform; the '
            'engagement is confirmed by a person, and payment runs '
            'through the house\'s own checkout of record.</p>'
        ) % _esc(price)
    elif branch == 'enterprise':
        body = (
            '<p><strong>No shelf price is shown for this platform.</'
            'strong> This platform works under enterprise agreements '
            'only — engagements are scoped and signed with the house '
            'directly, and no self-serve price stands.</p>')
    elif branch == 'not_settled':
        body = (
            '<p><strong>No price is shown for this platform yet.</strong> '
            'Two designed figures stand in conflict in its record, and the '
            'Founder\'s ruling settles it. Until he rules, access is '
            'arranged with the house directly.</p>')
    elif branch == 'unruled':
        body = (
            '<p><strong>No price is shown for this platform.</strong> Her '
            'public prices are the Founder\'s to rule, under his standard '
            'that everyone should be able to afford her public facing '
            'business model. Engagements begin through the house.</p>')
    else:
        body = (
            '<p>No price of record stands for this platform yet. Access is '
            'arranged with the house directly — book an appointment and '
            'name this platform.</p>')
    return (
        '<section id="access" class="section">\n'
        '  <p class="eyebrow">Access</p>\n'
        '  <h2>Sell access, globally.</h2>\n'
        '  <div class="access-panel">\n%s\n  </div>\n'
        '  <div class="hero-actions">\n'
        '    <a class="button gold" href="/appointments">Book an appointment</a>\n'
        '    <a class="button ghost" href="/client-portal">Client portal</a>\n'
        '  </div>\n'
        '</section>\n'
    ) % body


_NUMBER_WORDS = {6: 'Six', 8: 'Eight', 10: 'Ten'}


def _industries_eyebrow(defn):
    """The industries eyebrow, honest about the count: most
    platforms carry six codes; SEIC carries eight; Headquarters
    carries ten (Founder ruling, 2026-11-27)."""
    n = len(defn.naics_codes) if defn.naics_codes else 0
    if n in _NUMBER_WORDS:
        return 'Its %s Industries' % _NUMBER_WORDS[n]
    return 'Its Industries'


def render_storefront(platform_id):
    """Render one platform's storefront.

    Returns (status, body_bytes): '200 OK' with the page for a platform
    of record, '404 Not Found' with a plain statement otherwise.
    """
    defn = definition_for(platform_id)
    if defn is None:
        return ('404 Not Found',
                b'No platform of record stands under that name.\n')
    if defn.naics_codes is None:
        codes_html = (
            '<p>The NACI industries of this platform are the '
            'Founder\'s to rule; none is composed in this record, '
            'and none is shown until he rules.</p>')
    elif len(defn.naics_codes) == 0:
        codes_html = (
            '<p>This platform carries no NACI codes, as ruled \u2014 its '
            'record stands at none, exactly as the Founder ruled it.</p>')
    else:
        codes_html = '<p class="code-row">' + ''.join(
            '<span class="code-chip">%s</span>' % _esc(c)
            for c in defn.naics_codes) + '</p>'
    suite_html = '\n'.join(
        '      <article class="card"><p>%s</p></article>' % _esc(line)
        for line in defn.service_suite)
    body = ''.join((
        _head('%s | Sanders Dash & Seal' % defn.name, defn.who),
        _topbar(defn.name),
        '<main>\n',
        '<section class="hero">\n',
        '  <p class="eyebrow">%s</p>\n' % _esc(defn.name),
        '  <h1>%s</h1>\n' % _esc(defn.name),
        '  <p class="lead">%s</p>\n' % _esc(defn.who),
        '  <aside class="register-plaque" aria-label="Global by design">\n'
        '    <p class="plaque-title">Global By Design</p>\n'
        '    <p>This platform connects people around the globe, and its '
        'workflows connect industries together in real time \u2014 the '
        'standard of this house, carried in full on every surface.</p>\n'
        '  </aside>\n'
        '</section>\n',
        '<section id="why" class="section">\n'
        '  <p class="eyebrow">Why It Exists</p>\n'
        '  <h2>Its purpose, of record.</h2>\n'
        '  <p>%s</p>\n'
        '  <p>%s</p>\n'
        '</section>\n' % (_esc(defn.why), _esc(defn.serves)),
        '<section id="industries" class="section">\n',
        '  <p class="eyebrow">%s</p>\n' % _industries_eyebrow(defn),
        '  <h2>Built by NACI codes.</h2>\n'
        '  %s\n'
        '</section>\n' % codes_html,
        '<section id="suite" class="section">\n'
        '  <p class="eyebrow">Service Suite</p>\n'
        '  <h2>The full suite, through this door.</h2>\n'
        '  <div class="cards">\n%s\n  </div>\n'
        '</section>\n' % suite_html,
        '<section id="model" class="section">\n'
        '  <p class="eyebrow">Business Model</p>\n'
        '  <h2>How this platform earns.</h2>\n'
        '  <p>%s</p>\n'
        '</section>\n' % _esc(defn.business_model),
        '<section id="companies" class="section">\n'
        '  <p class="eyebrow">The Four Companies</p>\n'
        '  <h2>Tied to the whole house.</h2>\n'
        '  <p>%s</p>\n'
        '  <p>%s</p>\n'
        '</section>\n' % (_esc(defn.company_tie), _esc(_COMPANIES_LINE)),
        _access_block(defn),
        '</main>\n',
        _footer(),
    ))
    return ('200 OK', body.encode('utf-8'))


def render_directory():
    """Render the directory of every platform of record. Each card
    is the shelf: the platform's name, who it is, and its price
    line where a price of record stands (Founder priority,
    2026-11-28 — products publicly visible with their prices)."""
    cards = []
    for pid in sorted(DEFINITIONS):
        defn = DEFINITIONS[pid]
        line = _price_line(defn)
        price_html = ('<p class="price-line">%s</p>' % _esc(line)
                      if line is not None else '')
        cards.append(
            '      <article class="card"><h3><a href="/platforms/%s">%s</a>'
            '</h3><p>%s</p>%s</article>'
            % (_esc(pid), _esc(defn.name), _esc(defn.who), price_html))
    body = ''.join((
        _head('Platforms | Sanders Dash & Seal',
              'Every platform of the Sanders house, each opening into '
              'its full service suite.'),
        _topbar('Platforms'),
        '<main>\n',
        '<section class="hero">\n'
        '  <p class="eyebrow">The Platforms</p>\n'
        '  <h1>Every platform, its own door.</h1>\n'
        '  <p class="lead">Each platform below is fully defined in its '
        'own record and opens into its full service suite \u2014 built by '
        'NACI codes, tied to the four companies, selling access '
        'globally.</p>\n'
        '</section>\n',
        '<section class="section">\n  <div class="cards">\n',
        '\n'.join(cards),
        '\n  </div>\n</section>\n',
        '</main>\n',
        _footer(),
    ))
    return body.encode('utf-8')
