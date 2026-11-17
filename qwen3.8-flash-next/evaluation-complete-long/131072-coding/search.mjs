export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestId = 0;
  }

  async search(query, page = 1) {
    // Preserve latest state: capture the most recent query/page even if a
    // previous in-flight request resolves later.
    this.query = query;
    this.page = page;
    this.loading = true;

    const requestId = ++this._requestId;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore stale responses: an older request resolving after a newer one,
      // or any request completing after reset(), must not touch state.
      if (requestId !== this._requestId) return this.rows;
      this.rows = rows;
      return rows;
    } finally {
      if (requestId === this._requestId) this.loading = false;
    }
  }

  reset() {
    // Invalidate in-flight requests so they cannot repopulate cleared rows.
    this._requestId++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}