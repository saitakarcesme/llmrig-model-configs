export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestId = 0;
    this._resetId = 0;
    this._pending = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    const requestId = ++this._requestId;
    const resetId = this._resetId;
    this.loading = true;
    this._pending++;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore stale responses: a newer request superseded this one,
      // or a reset happened while this request was in flight.
      if (resetId !== this._resetId || requestId !== this._requestId) {
        return this.rows;
      }
      this.rows = rows;
      return this.rows;
    } finally {
      this._pending--;
      // Only clear loading if no newer in-flight request owns it,
      // and don't resurrect loading state after a reset.
      if (resetId === this._resetId && requestId === this._requestId && this._pending === 0) {
        this.loading = false;
      }
    }
  }

  reset() {
    this._resetId++;
    this._requestId++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}