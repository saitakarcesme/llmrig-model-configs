export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestToken = 0;
    this._resetToken = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;

    const requestToken = ++this._requestToken;
    const resetToken = this._resetToken;

    let rows;
    try {
      rows = await this.fetcher(query, page);
    } catch (err) {
      if (requestToken === this._requestToken && resetToken === this._resetToken) {
        this.loading = false;
      }
      throw err;
    }

    // Discard stale responses: a newer query started, or a reset happened while in flight.
    if (requestToken !== this._requestToken || resetToken !== this._resetToken) {
      return this.rows;
    }

    this.rows = rows;
    this.loading = false;
    return this.rows;
  }

  reset() {
    this._resetToken++;
    this._requestToken++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}