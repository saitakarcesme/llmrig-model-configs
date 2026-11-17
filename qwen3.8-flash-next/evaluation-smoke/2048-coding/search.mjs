export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestSeq = 0;
    this._resetSeq = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;
    const requestId = ++this._requestSeq;
    const resetId = this._resetSeq;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore stale responses: a newer request started, or a reset happened
      // after this request was issued.
      if (resetId !== this._resetSeq || requestId !== this._requestSeq) {
        return this.rows;
      }
      this.rows = rows;
      return this.rows;
    } finally {
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