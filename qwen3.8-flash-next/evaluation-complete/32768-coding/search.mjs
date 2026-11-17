export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestId = 0;
    this._resetId = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;
    const requestId = ++this._requestId;
    const resetId = this._resetId;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore responses from stale requests (superseded by a newer query)
      // or requests that completed after a reset (must not repopulate cleared rows).
      if (requestId !== this._requestId || resetId !== this._resetId) {
        return this.rows;
      }
      this.rows = rows;
      return this.rows;
    } finally {
      // Only clear loading if this request is still the latest one and no
      // reset has occurred; a newer request or reset manages the state now.
      if (requestId === this._requestId && resetId === this._resetId) {
        this.loading = false;
      }
    }
  }

  reset() {
    this._resetId++;
    this._requestId++; // invalidate any in-flight requests
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}