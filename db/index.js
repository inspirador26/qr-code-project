const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const dbPath = path.join(__dirname, 'data.sqlite');
const db = new Database(dbPath);
db.pragma('foreign_keys = ON');

function migrate() {
  const schema = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
  db.exec(schema);
}

function seed({ issuerId }) {
    const count = db.prepare('SELECT COUNT(*) as c FROM merchants').get().c;
    if (count > 0) return;

    const merchants = [
        { id: 'valor',     provider: 'Valor',     redemption_channel: 'BOTH'    },
        { id: 'taco_jack', provider: 'Taco Jack', redemption_channel: 'INSTORE' },
        { id: 'shop_xyz',  provider: 'Shop XYZ',  redemption_channel: 'ONLINE'  },
    ];

    const insMerchant = db.prepare(`
        INSERT INTO merchants (id, provider, redemption_channel, class_id)
        VALUES (@id, @provider, @redemption_channel, @class_id)
    `);

    const insOffer = db.prepare(`
        INSERT INTO offers (id, merchant_id, title, starts_at, expires_at, max_redemptions, is_active)
        VALUES (@id, @merchant_id, @title, @starts_at, @expires_at, @max_redemptions, 1)
    `);

    const classIdForMerchant = (id) => `${issuerId}.offer_${id}`;
    const now = Date.now();

    const offers = [
        {
        id: 'offer-abc',
        merchant_id: 'valor',
        title: '20% off your order',
        starts_at: new Date(now - 3600_000).toISOString(),
        expires_at: new Date(now + 7*24*3600_000).toISOString(),
        max_redemptions: 1000,
        },
        {
        id: 'offer-taco',
        merchant_id: 'taco_jack',
        title: '2x1 tacos al pastor',
        starts_at: new Date(now - 3600_000).toISOString(),
        expires_at: new Date(now + 3*24*3600_000).toISOString(),
        max_redemptions: 500,
        },
    ];

    const tx = db.transaction(() => {
        merchants.forEach(m => insMerchant.run({ ...m, class_id: classIdForMerchant(m.id) }));
        offers.forEach(o => insOffer.run(o));
    });
    tx();
}

module.exports = { db, migrate, seed };
