// Defense in depth for reviewed offline examples, not a sandbox for hostile code.
'use strict';
const {syncBuiltinESMExports} = require('node:module');
function denied() { throw new Error('release-packager: network access is disabled'); }
for (const name of ['net', 'tls', 'dgram', 'dns', 'http', 'https', 'http2']) {
  const api = require('node:' + name);
  for (const key of Object.keys(api)) {
    if (typeof api[key] === 'function') {
      Object.defineProperty(api, key, {value: denied, configurable: true, writable: true});
    }
  }
  if (api.promises) {
    for (const key of Object.keys(api.promises)) {
      if (typeof api.promises[key] === 'function') api.promises[key] = denied;
    }
  }
}
globalThis.fetch = denied;
globalThis.WebSocket = denied;
syncBuiltinESMExports();
