
// FULL DESCRIPTION OF SETUP HERE: ** https://docs.google.com/document/d/1RcZhiWCG7dK4qYw8-aTt46qilTpxXeZallokNh2YdRs/edit?tab=t.0




// server.js
const express = require('express');
const QRCode = require('qrcode');
const jwt = require('jsonwebtoken'); // QR token + Google Wallet JWT
const bwipjs = require('bwip-js');
const { v4: uuidv4 } = require('uuid');

// ---- DB (SQLite via better-sqlite3) ----
const { db, migrate, seed } = require('./db');

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// ------------ Core config ------------
const PORT = Number(process.env.PORT || 3000);
const LISTEN_HOST = process.env.LISTEN_HOST || '127.0.0.1';
const HOST = process.env.HOST || `http://localhost:${PORT}`;
const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-do-not-use';

// ------------ Google Wallet ------------
const walletKey = require('./keys/wallet-sa.json'); // service account JSON
const ISSUER_ID = '3388000000023034731';            // your Issuer ID
const ISSUER_NAME = 'Valor';                        // your org (issuer), NOT the merchant

// ------------ DB boot (after constants) ------------
migrate();
seed({ issuerId: ISSUER_ID });





// ------------ temporary debug route ------------
app.get('/admin/dump', (req, res) => {
  const merchants = db.prepare('SELECT * FROM merchants').all();
  const offers = db.prepare('SELECT * FROM offers').all();
  const codes = db.prepare('SELECT * FROM codes').all();
  res.json({ merchants, offers, codes });
});


// ------------ DB helpers (prepared statements) ------------
const qGetOffer    = db.prepare("SELECT * FROM offers WHERE id = ?");
const qGetMerchant = db.prepare("SELECT * FROM merchants WHERE id = ?");
const qInsertCode  = db.prepare("INSERT INTO codes (id, offer_id, state, issued_at) VALUES (?, ?, 'issued', ?)");
const qGetCode     = db.prepare("SELECT * FROM codes WHERE id = ?");
const qRedeemCode  = db.prepare("UPDATE codes SET state = 'redeemed', redeemed_at = ? WHERE id = ?");

// ------------ Admin: generate QR for an offer ------------
app.get('/admin/qr/:offerId', async (req, res) => {
  const offer = qGetOffer.get(req.params.offerId);
  if (!offer) return res.status(404).send('Offer not found');

  const token = jwt.sign(
    { offerId: offer.id, iat: Math.floor(Date.now() / 1000) },
    JWT_SECRET,
    { expiresIn: '15m' }
  );

  const url = `${HOST}/o/${offer.id}?t=${encodeURIComponent(token)}`;
  const png = await QRCode.toBuffer(url, { width: 512, margin: 1 });

  res.type('png').send(png);
});

// ------------ Landing after scan ------------
app.get('/o/:offerId', (req, res) => {
  const { offerId } = req.params;
  const { t } = req.query;

  try { jwt.verify(t, JWT_SECRET); }
  catch { return res.status(401).send('Link expired or invalid.'); }

  const offer = qGetOffer.get(offerId);
  if (!offer) return res.status(404).send('Offer not found');
  if (!offer.is_active) return res.status(400).send('Offer inactive.');

  const now = Date.now();
  if (now < Date.parse(offer.starts_at) || now > Date.parse(offer.expires_at)) {
    return res.status(400).send('Offer not active.');
  }

  const codeId = uuidv4();
  qInsertCode.run(codeId, offer.id, new Date().toISOString());

  res.type('html').send(`
    <!doctype html>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${offer.title}</title>
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto;max-width:520px;margin:24px auto;padding:16px">
      <h1 style="font-size:20px;margin:0 0 12px">${offer.title}</h1>
      <p style="margin:0 0 16px">Your single-use code is below. Show this at checkout.</p>
      <img alt="barcode" src="/barcode/${codeId}.png" style="display:block;width:100%;max-width:420px;margin:12px auto" />
      <div style="display:flex;gap:12px;margin-top:12px">
        <a href="/wallet/apple/${codeId}" style="flex:1;text-align:center;padding:12px;border:1px solid #ddd;border-radius:12px;text-decoration:none">Add to Apple Wallet</a>
        <a href="/wallet/google/${codeId}" style="flex:1;text-align:center;padding:12px;border:1px solid #ddd;border-radius:12px;text-decoration:none">Save to Google Wallet</a>
      </div>
      <p style="color:#666;font-size:12px;margin-top:10px">Code: ${codeId}</p>
    </div>
  `);
});

// ------------ Home ------------
app.get('/', (req, res) =>
  res.send('Server up. Try /admin/qr/offer-abc or /admin/qr/offer-taco')
);

// ------------ Barcode image ------------
app.get('/barcode/:codeId.png', async (req, res) => {
  const rec = qGetCode.get(req.params.codeId);
  if (!rec) return res.status(404).send('Code not found');

  try {
    const png = await bwipjs.toBuffer({
      bcid: 'code128',
      text: rec.id,
      scale: 3,
      height: 15,
      includetext: true,
      textxalign: 'center',
    });
    res.type('png').send(png);
  } catch {
    res.status(500).send('Barcode error');
  }
});

// ------------ Apple Wallet (stub) ------------
app.get('/wallet/apple/:codeId', (req, res) => {
  const rec = qGetCode.get(req.params.codeId);
  if (!rec) return res.status(404).send('Code not found');
  res.send('Apple Wallet pass would be generated here (.pkpass).');
});

// ------------ Google Wallet: Save link ------------
app.get('/wallet/google/:codeId', (req, res) => {
  const rec = qGetCode.get(req.params.codeId);
  if (!rec) return res.status(404).send('Code not found');

  const offer = qGetOffer.get(rec.offer_id);
  if (!offer) return res.status(404).send('Offer not found');

  const merchant = qGetMerchant.get(offer.merchant_id);
  if (!merchant) return res.status(404).send('Merchant not found');

  // ONE CLASS PER MERCHANT (stable, stored in merchants.class_id)
  const classId  = merchant.class_id;
  const objectId = `${ISSUER_ID}.${rec.id}`; // one object per issued code

  const jwtPayload = {
    iss: walletKey.client_email,
    aud: 'google',
    typ: 'savetoandroidpay',
    payload: {
      // Class = merchant (chip shows "[TEST ONLY] <title>")
      offerClasses: [{
        id: classId,
        issuerName: ISSUER_NAME,
        title: merchant.provider,                 // chip title (merchant name)
        provider: merchant.provider,
        redemptionChannel: merchant.redemption_channel, // INSTORE | ONLINE | BOTH
        reviewStatus: 'underReview'
      }],
      // Object = specific pass/code for that merchant
      offerObjects: [{
        id: objectId,
        classId,
        state: 'ACTIVE',
        title: offer.title,                       // big bold line (offer)
        header: { defaultValue: { language: 'en', value: merchant.provider }}, // small subtitle
        barcode: { type: 'CODE_128', value: rec.id, alternateText: rec.id },
        validTimeInterval: {
          start: { date: offer.starts_at },
          end:   { date: offer.expires_at }
        }
      }]
    }
  };

  const token = jwt.sign(jwtPayload, walletKey.private_key, { algorithm: 'RS256' });
  res.redirect(`https://pay.google.com/gp/v/save/${token}`);
});

// ------------ Redeem ------------
app.post('/redeem/:codeId', (req, res) => {
  const rec = qGetCode.get(req.params.codeId);
  if (!rec) return res.status(404).json({ ok: false, error: 'not_found' });
  if (rec.state === 'redeemed') {
    return res.json({ ok: true, status: 'already_redeemed', redeemed_at: rec.redeemed_at });
  }

  const nowIso = new Date().toISOString();
  qRedeemCode.run(nowIso, rec.id);
  res.json({ ok: true, status: 'redeemed', redeemed_at: nowIso });
});



// ------------ Admin: create merchant ------------
app.post('/admin/merchant', (req, res) => {
  const { id, provider, redemption_channel } = req.body;
  if (!id || !provider || !redemption_channel) {
    return res.status(400).json({ ok: false, error: 'id, provider, redemption_channel required' });
  }

  const class_id = `${ISSUER_ID}.offer_${id}`;
  try {
    db.prepare(`
      INSERT INTO merchants (id, provider, redemption_channel, class_id)
      VALUES (?, ?, ?, ?)
    `).run(id, provider, redemption_channel, class_id);

    res.json({ ok: true, id, class_id });
  } catch (e) {
    res.status(400).json({ ok: false, error: e.message });
  }
});

// ------------ Admin: create offer ------------
app.post('/admin/offer', (req, res) => {
  const { id, merchant_id, title, starts_at, expires_at, max_redemptions, is_active = 1 } = req.body;
  if (!id || !merchant_id || !title || !starts_at || !expires_at || !max_redemptions) {
    return res.status(400).json({ ok: false, error: 'missing required fields' });
  }

  try {
    db.prepare(`
      INSERT INTO offers (id, merchant_id, title, starts_at, expires_at, max_redemptions, is_active)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(id, merchant_id, title, starts_at, expires_at, max_redemptions, is_active ? 1 : 0);

    res.json({ ok: true, id });
  } catch (e) {
    res.status(400).json({ ok: false, error: e.message });
  }
});



// ------------ Health & listen ------------
app.get('/ping', (req, res) => res.send('pong'));

app.listen(PORT, LISTEN_HOST, () => console.log(`Up on ${HOST}`));

// Admin shortcuts:
// http://192.168.100.7:3000/admin/qr/offer-abc
// http://192.168.100.7:3000/admin/qr/offer-taco
