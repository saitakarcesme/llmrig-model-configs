export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestSeq = 0;
    this._resetSeq = 0;
    this._pending = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;

    const requestId = ++this._requestSeq;
    const resetId = this._resetSeq;
    this._pending++;

    try {
      const rows = await this.fetcher(query, page);

      // A reset happened during the request: keep cleared state, do not repopulate rows.
      if (resetId !== this._resetSeq) {
        return this.rows;
      }

      // A newer request superseded this one: do not overwrite newer rows/state.
      if (requestId !== this._requestSeq) {
        return this.rows;
      }

      this.rows = rows;
      // Preserve latest query/page state (do not clobber with stale values).
      this.query = query;
      this.page = page;
      return this.rows;
    } finally {
      this._pending--;
      // Only clear loading when the latest request (from the current reset era) is done.
      if (resetId === this._resetSeq && requestId === this._requestSeq) {
        this.loading = false;
      }
    }
  }

  reset() {
    this._resetSeq++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}