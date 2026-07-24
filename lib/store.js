// lib/store.js
const { db } = require('../db');

// prepared statements
const qGetOffer      = db.prepare('SELECT * FROM offers WHERE id = ?');
const qGetMerchant   = db.prepare('SELECT * FROM merchants WHERE id = ?');
const qInsertCode    = db.prepare('INSERT INTO codes (id, offer_id, state, issued_at) VALUES (?, ?, "issued", datetime("now"))');
const qGetCode       = db.prepare('SELECT * FROM codes WHERE id = ?');
const qRedeemCode    = db.prepare('UPDATE codes SET state = "redeemed", redeemed_at = datetime("now") WHERE id = ?');

const qListMerchants = db.prepare('SELECT * FROM merchants ORDER BY provider');
const qListOffers    = db.prepare('SELECT * FROM offers ORDER BY created_at DESC');

// public API
function getOfferById(id)        { return qGetOffer.get(id) || null; }
function getMerchantById(id)     { return qGetMerchant.get(id) || null; }
function createCode({ id, offer_id }) { qInsertCode.run(id, offer_id); return getCodeById(id); }
function getCodeById(id)         { return qGetCode.get(id) || null; }
function redeemCode(id)          { qRedeemCode.run(id); return getCodeById(id); }

function listMerchants()         { return qListMerchants.all(); }
function listOffers()            { return qListOffers.all(); }

/**
 * Insert merchants/offers/codes in one shot.
 * Auto-creates class_id if missing.
 */
function newEntries({ merchants = [], offers = [], codes = [], issuerId = '3388000000023034731' }) {
  const insMerchant = db.prepare(`
    INSERT OR IGNORE INTO merchants (id, provider, redemption_channel, class_id)
    VALUES (@id, @provider, @redemption_channel, @class_id)
  `);
  const insOffer = db.prepare(`
    INSERT OR IGNORE INTO offers (id, merchant_id, title, starts_at, expires_at, max_redemptions, is_active)
    VALUES (@id, @merchant_id, @title, @starts_at, @expires_at, @max_redemptions, 1)
  `);
  const insCode = db.prepare(`
    INSERT OR IGNORE INTO codes (id, offer_id, state, issued_at)
    VALUES (@id, @offer_id, 'issued', datetime('now'))
  `);

  const tx = db.transaction(() => {
    merchants.forEach(m => {
      const class_id = m.class_id || `${issuerId}.offer_${m.id}`;
      insMerchant.run({ ...m, class_id });
    });
    offers.forEach(o => insOffer.run(o));
    codes.forEach(c => insCode.run(c));
  });
  tx();
}

module.exports = {
  // reads/writes
  getOfferById, getMerchantById, getCodeById, createCode, redeemCode,
  listMerchants, listOffers,
  // admin
  newEntries,
};