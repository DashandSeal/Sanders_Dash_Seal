/* The Portals — client machinery (2026-11-25, founder portals band).
 *
 * Every interactive portal on the Sanders websites runs through this
 * one script against /api/portals/. Submissions are cases: the answer
 * a person gets is a reference ID and a standing (AWAITING_HUMAN_REVIEW)
 * — never a publication. Publication is the operator's recorded
 * decision, and the public surfaces below render only what that
 * decision made public.
 */
(function () {
  'use strict';

  var CONSENT_VERSION = 'wall-of-valor-consent-2026-11-25';

  function esc(text) {
    var div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  function post(path, payload) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    }).then(function (resp) {
      return resp.json().then(function (data) {
        if (!resp.ok) {
          var err = new Error(data.detail || data.error || 'request_failed');
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function get(path) {
    return fetch(path, { credentials: 'same-origin' }).then(function (resp) {
      return resp.json().then(function (data) {
        if (!resp.ok) {
          var err = new Error(data.detail || data.error || 'request_failed');
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  /* A tribute photograph rides as base64 JSON. Downscale on the
   * device first — the wall accepts up to 6 MB; a framed web copy
   * honors better than a raw phone file and travels honestly. */
  function photoPayload(file) {
    return new Promise(function (resolve, reject) {
      if (!file) { resolve(null); return; }
      if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
        reject(new Error('The photograph must be a JPEG, PNG, or WebP image.'));
        return;
      }
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        URL.revokeObjectURL(url);
        var max = 1920;
        var scale = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
        if (scale === 1 && file.size <= 5 * 1024 * 1024) {
          var reader = new FileReader();
          reader.onload = function () {
            resolve(String(reader.result).split(',')[1]);
          };
          reader.onerror = function () { reject(new Error('The photograph could not be read.')); };
          reader.readAsDataURL(file);
          return;
        }
        var canvas = document.createElement('canvas');
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.87).split(',')[1]);
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error('The photograph could not be read.'));
      };
      img.src = url;
    });
  }

  function field(form, name) {
    var el = form.elements[name];
    return el ? el.value.trim() : '';
  }

  function wireSubmissionForm(form) {
    var kind = form.getAttribute('data-portal-form');
    var company = form.getAttribute('data-company');
    var status = form.querySelector('.portal-status');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      status.textContent = 'Placing your record in the review queue…';
      var payload = {
        company: (form.elements.company && form.elements.company.value) || company,
        name: field(form, 'name'),
        contact: field(form, 'contact'),
        subject: field(form, 'subject'),
        body: field(form, 'body')
      };
      var done = Promise.resolve(null);
      if (kind === 'wall-of-valor') {
        payload.honoree = field(form, 'honoree');
        payload.relationship = field(form, 'relationship');
        payload.consent = form.elements.consent.checked === true;
        payload.consent_version = CONSENT_VERSION;
        var fileEl = form.elements.photo;
        var file = fileEl && fileEl.files ? fileEl.files[0] : null;
        done = photoPayload(file).then(function (b64) {
          if (b64) { payload.photo_b64 = b64; }
        });
      }
      done.then(function () {
        return post('/api/portals/submissions/' + kind, payload);
      }).then(function (data) {
        form.reset();
        status.innerHTML = 'On the record. Your reference ID is ' +
          '<span class="ref">' + esc(data.case.ref) + '</span> — standing: ' +
          esc(data.case.status.replace(/_/g, ' ')) +
          '. A person reviews every record before anything further happens. ' +
          'Keep the reference ID; it is how your record is found.';
      }).catch(function (err) {
        status.textContent = 'The record was not placed: ' + err.message +
          ' Nothing was submitted. Check the form and try again, or reach ' +
          'the company through its contact page.';
      });
    });
  }

  function renderWall(el) {
    get('/api/portals/wall').then(function (data) {
      if (!data.wall.length) {
        el.innerHTML = '<p class="portal-note">The public wall opens with ' +
          'the first tribute a reviewer approves. Submissions stand in ' +
          'review until then — nothing appears here on its own.</p>';
        return;
      }
      el.innerHTML = data.wall.map(function (entry) {
        var photo = entry.photo_url
          ? '<img src="' + esc(entry.photo_url) + '" alt="Photograph honoring ' +
            esc(entry.honoree) + '" loading="lazy">'
          : '';
        return '<article class="tribute">' + photo + '<h3>' + esc(entry.honoree) +
          '</h3>' +
          (entry.relationship ? '<p><em>' + esc(entry.relationship) + '</em></p>' : '') +
          '<p>' + esc(entry.story) + '</p></article>';
      }).join('');
    }).catch(function () {
      el.innerHTML = '<p class="portal-note">The wall could not be read just now.</p>';
    });
  }

  function renderSpotlights(el) {
    get('/api/portals/spotlights').then(function (data) {
      if (!data.spotlights.length) {
        el.innerHTML = '<p class="portal-note">No spotlight has been recorded ' +
          'yet. A spotlight exists only when a selection is made and recorded ' +
          'by the house — the first one will stand here.</p>';
        return;
      }
      el.innerHTML = data.spotlights.map(function (s) {
        return '<article><h3>' + esc(s.contractor_name) + '</h3><p><em>' +
          (s.period_type === 'YEAR' ? 'Spotlight of the Year' : 'Spotlight of the Month') +
          ' · ' + esc(s.period_label) + '</em></p><p>' + esc(s.citation) +
          '</p></article>';
      }).join('');
    }).catch(function () {
      el.innerHTML = '<p class="portal-note">The spotlight record could not be read just now.</p>';
    });
  }

  function renderFigures(el) {
    get('/api/portals/how-were-doing').then(function (data) {
      el.innerHTML = data.figures.map(function (f) {
        return '<article><div class="figure-value">' + esc(f.value) + '</div>' +
          '<div class="figure-label">' + esc(f.label) + '</div>' +
          '<p class="figure-source">' + esc(f.source) + '</p></article>';
      }).join('');
    }).catch(function () {
      el.innerHTML = '<p class="portal-note">The figures could not be read just now.</p>';
    });
  }

  function wireCaseLookup(form) {
    var status = form.querySelector('.portal-status');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var ref = field(form, 'ref').toUpperCase();
      get('/api/portals/cases/' + encodeURIComponent(ref)).then(function (data) {
        status.innerHTML = 'Reference <span class="ref">' + esc(data.case.ref) +
          '</span> — standing: ' + esc(data.case.status.replace(/_/g, ' ')) + '.';
      }).catch(function () {
        status.textContent = 'No case stands under that reference ID. Check the ID exactly as it was given.';
      });
    });
  }

  function renderContractor(el) {
    get('/api/portals/contractor/me').then(function (data) {
      var c = data.contractor;
      var rows = c.records.map(function (r) {
        return '<tr><td>' + esc(r.ref) + '</td><td>' + esc(r.kind.replace(/_/g, ' ')) +
          '</td><td>' + esc(r.status.replace(/_/g, ' ')) + '</td></tr>';
      }).join('');
      el.innerHTML =
        '<p>Signed in as <strong>' + esc(c.identity) + '</strong>.</p>' +
        '<p>Independent Contractors Handbook: version ' + esc(c.handbook_version) +
        ' — ' + (c.handbook_acknowledged
          ? 'your acknowledgment stands on the record.'
          : 'not yet acknowledged. <button class="button" id="ackHandbook" type="button">Acknowledge the Handbook</button>') +
        '</p>' +
        (c.records.length
          ? '<table class="review-table"><thead><tr><th>Reference</th><th>Kind</th><th>Standing</th></tr></thead><tbody>' + rows + '</tbody></table>'
          : '<p class="portal-note">No records stand under your sign-in yet. Your expressions of interest, made while signed in, will stand here.</p>');
      var ack = document.getElementById('ackHandbook');
      if (ack) {
        ack.addEventListener('click', function () {
          post('/api/portals/contractor/me', {}).then(function () {
            renderContractor(el);
          }).catch(function (err) {
            window.alert('The acknowledgment was not recorded: ' + err.message);
          });
        });
      }
    }).catch(function (err) {
      if (err.data && err.data.error === 'sign_in_required') {
        el.innerHTML = '<p class="portal-note">The contractors portal stands behind ' +
          'the platform sign-in. <a href="/auth/login">Sign in</a> — your own record ' +
          'is the only one it will ever show you.</p>';
      } else {
        el.innerHTML = '<p class="portal-note">Your record could not be read just now.</p>';
      }
    });
  }

  function renderQueue(el) {
    get('/api/portals/operator/queue').then(function (data) {
      if (!data.queue.length) {
        el.innerHTML = '<p class="portal-note">The review queue is empty. Every portal case a person submits will stand here until your decision is recorded.</p>';
        return;
      }
      el.innerHTML = '<table class="review-table"><thead><tr><th>Reference</th>' +
        '<th>Kind</th><th>From</th><th>Record</th><th>Decision</th></tr></thead><tbody>' +
        data.queue.map(function (r) {
          var record = '<strong>' + esc(r.subject || r.honoree) + '</strong><br>' +
            esc(r.body) +
            (r.honoree && r.subject ? '' : '') +
            (r.kind === 'WALL_OF_VALOR'
              ? '<br><em>Honoree: ' + esc(r.honoree) + (r.relationship ? ' · ' + esc(r.relationship) : '') +
                ' · Consent recorded: ' + (r.consent ? 'yes' : 'no') +
                (r.photo_ref ? ' · Photograph held' : ' · No photograph') + '</em>'
              : '');
          return '<tr><td>' + esc(r.ref) + '</td><td>' + esc(r.kind.replace(/_/g, ' ')) +
            '</td><td>' + esc(r.submitter_name) + '<br>' + esc(r.submitter_contact) +
            '</td><td>' + record + '</td><td>' +
            '<button class="button" type="button" data-review="' + esc(r.ref) + '" data-decision="APPROVE">Approve</button>' +
            '<button class="button secondary" type="button" data-review="' + esc(r.ref) + '" data-decision="REJECT">Reject</button>' +
            (r.kind === 'SUPPORT' || r.kind === 'COMPLAINT'
              ? '<button class="button secondary" type="button" data-resolve="' + esc(r.ref) + '">Resolve</button>'
              : '') +
            '</td></tr>';
        }).join('') + '</tbody></table>';
      el.querySelectorAll('[data-review]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          post('/api/portals/operator/cases/' + btn.getAttribute('data-review') + '/review',
            { decision: btn.getAttribute('data-decision'), note: '' })
            .then(function () { renderQueue(el); })
            .catch(function (err) { window.alert('The decision was not recorded: ' + err.message); });
        });
      });
      el.querySelectorAll('[data-resolve]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          post('/api/portals/operator/cases/' + btn.getAttribute('data-resolve') + '/resolve',
            { note: '' })
            .then(function () { renderQueue(el); })
            .catch(function (err) { window.alert('The resolution was not recorded: ' + err.message); });
        });
      });
    }).catch(function (err) {
      if (err.data && err.data.error === 'sign_in_required') {
        el.innerHTML = '<p class="portal-note">Sign in with the operator account to work the review queue. <a href="/auth/login">Sign in</a></p>';
      } else if (err.data && err.data.error === 'portals_forbidden') {
        el.innerHTML = '<p class="portal-note">This queue answers to the operator only. Your sign-in does not carry operator authority.</p>';
      } else {
        el.innerHTML = '<p class="portal-note">The queue could not be read just now.</p>';
      }
    });
  }

  function wireSpotlightForm(form) {
    var status = form.querySelector('.portal-status');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      post('/api/portals/operator/spotlights', {
        contractor_name: field(form, 'contractor_name'),
        period_type: field(form, 'period_type'),
        period_label: field(form, 'period_label'),
        citation: field(form, 'citation'),
        company: form.getAttribute('data-company') || 'headquarters'
      }).then(function (data) {
        form.reset();
        status.innerHTML = 'Selection recorded: <span class="ref">' + esc(data.spotlight.ref) +
          '</span>. It stands on the public spotlight now, as recorded.';
      }).catch(function (err) {
        status.textContent = 'The selection was not recorded: ' + err.message +
          ' Spotlight selections are recorded by the operator only.';
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-portal-form]').forEach(wireSubmissionForm);
    document.querySelectorAll('form[data-case-lookup]').forEach(wireCaseLookup);
    document.querySelectorAll('form[data-spotlight-form]').forEach(wireSpotlightForm);
    var wall = document.querySelector('[data-wall]');
    if (wall) { renderWall(wall); }
    var spotlights = document.querySelector('[data-spotlights]');
    if (spotlights) { renderSpotlights(spotlights); }
    var figures = document.querySelector('[data-figures]');
    if (figures) { renderFigures(figures); }
    var contractor = document.querySelector('[data-contractor]');
    if (contractor) { renderContractor(contractor); }
    var queue = document.querySelector('[data-review-queue]');
    if (queue) { renderQueue(queue); }
  });
})();
