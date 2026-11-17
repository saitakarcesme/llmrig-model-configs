export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestId = 0;
    this._pending = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    const requestId = ++this._requestId;
    this._pending++;
    this.loading = true;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore stale responses: a newer request was started, a reset happened,
      // or this request is no longer the latest one.
      if (requestId !== this._requestId) return this.rows;
      this.rows = rows;
      return this.rows;
    } finally {
      this._pending--;
      // Only clear loading if this request is still the latest one; a newer
      // request may still be in flight and owns the loading state.
      if (requestId === this._requestId) this.loading = this._pending > 0;
    }
  }

  reset() {
    // Invalidate in-flight requests so completed-after-reset responses
    // cannot repopulate the cleared rows.
    this._requestId++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}