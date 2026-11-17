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
    const id = ++this._requestId;
    this._pending++;
    this.loading = true;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore stale responses: a newer request superseded this one, or a
      // reset happened while this request was in flight.
      if (id !== this._requestId) return this.rows;
      this.rows = rows;
      return this.rows;
    } finally {
      this._pending--;
      if (id === this._requestId) {
        this.loading = this._pending > 0;
      }
    }
  }

  reset() {
    // Invalidate in-flight requests so their responses cannot repopulate rows.
    this._requestId++;
    this._pending = 0;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}