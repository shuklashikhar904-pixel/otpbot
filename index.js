const express = require("express");
const app = express();
app.use(express.json());

const BOT_TOKEN = "8936958039:AAF_F4f0VMzc_rZtdhqrKuunSnJ34FvuO94";
const PORT = process.env.PORT || 3000;
const WEBHOOK_PATH = "/webhook";

const NL = String.fromCharCode(10);

const BOT_USERNAME = "trusteddealers07bot";
const ADMIN_IDS = [8646237754];
const UPI_ID = "shikharshukla606@naviaxis";
const UPI_NAME = "Shikhar Shukla";
const SUPPORT = "@deathalive07";
const REFERRAL_BONUS = 0.40;
const MIN_ADD_FUND = 15.00;
const BONUS_THRESHOLD = 400.00;
const BONUS_PERCENT = 10;

const CHANNELS = [
  { user: "@trusteddealers07",  link: "https://t.me/trusteddealers07"  },
  { user: "@trusteddealers_07", link: "https://t.me/trusteddealers_07" }
];

const memStore = {};
function storeGet(k) { return memStore[k] !== undefined ? memStore[k] : null; }
function storeSet(k, v) { memStore[k] = String(v); }

async function apiSend(payload) {
  try {
    await fetch("https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) { console.log("send err", e.message); }
}

async function apiGetChatMember(payload) {
  try {
    const res = await fetch("https://api.telegram.org/bot" + BOT_TOKEN + "/getChatMember", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return await res.json();
  } catch (e) { return { ok: false }; }
}

async function handleUpdate(update) {
  if (!update || !update.message) return;
  const message = update.message;
  const chat = message.chat || {};
  const user = message.from || {};
  const UID = user.id || 0;
  const UFNAME = user.first_name || "user";
  const UNAME = user.username || "";
  const CHATID = chat.id || UID;
  const isAdmin = ADMIN_IDS.indexOf(UID) !== -1;

  let incoming = "";
  if (typeof message.text === "string") incoming = message.text;
  incoming = String(incoming || "").trim();
  const cmd = incoming.split("@")[0].trim();
  const low = cmd.toLowerCase();

  function bal() { return parseFloat(storeGet("balance_" + UID) || "0") || 0; }
  function nums() { try { return JSON.parse(storeGet("numbers") || "[]"); } catch (e) { return []; } }
  function setNums(v) { storeSet("numbers", JSON.stringify(v)); }
  function getSt() {
    try {
      const raw = storeGet("state_" + UID);
      if (!raw) return { step: "menu" };
      const p = JSON.parse(raw);
      if (!p.step) p.step = "menu";
      return p;
    } catch (e) { return { step: "menu" }; }
  }
  function setSt(s) { storeSet("state_" + UID, JSON.stringify(s)); }
  function users() { try { return JSON.parse(storeGet("all_users") || "[]"); } catch (e) { return []; } }
  function setUsers(u) { storeSet("all_users", JSON.stringify(u)); }
  function pend() { try { return JSON.parse(storeGet("pending_payments") || "[]"); } catch (e) { return []; } }
  function setPend(v) { storeSet("pending_payments", JSON.stringify(v)); }

  try {
    const allU = users();
    if (allU.indexOf(UID) === -1) { allU.push(UID); setUsers(allU); }
  } catch (e) {}

  function send(t, kb) {
    const p = { chat_id: CHATID, text: String(t), parse_mode: "html" };
    if (kb) p.reply_markup = kb;
    apiSend(p);
  }

  const userKb = { keyboard: [
    [{ text: "Buy Number" }, { text: "Add Fund" }],
    [{ text: "Wallet" }, { text: "Refer and Earn" }],
    [{ text: "Help" }]
  ], resize_keyboard: true };

  const adminKb = { keyboard: [
    [{ text: "Add Telegram" }, { text: "Add WhatsApp" }],
    [{ text: "Set OTP" }, { text: "Stock" }],
    [{ text: "Pending" }, { text: "Stats" }],
    [{ text: "Broadcast" }],
    [{ text: "Back to Menu" }]
  ], resize_keyboard: true };

  const menuKb = isAdmin ? adminKb : userKb;

  let joined = true;
  for (let ci = 0; ci < CHANNELS.length; ci++) {
    try {
      const m = await apiGetChatMember({ chat_id: CHANNELS[ci].user, user_id: UID });
      const st = (m && m.result && m.result.status) || "left";
      if (["creator", "administrator", "member", "restricted"].indexOf(st) === -1) { joined = false; break; }
    } catch (e) { joined = false; break; }
  }

  if (!joined) {
    const rows = [];
    for (let ri = 0; ri < CHANNELS.length; ri++) {
      rows.push([{ text: "Join Channel " + (ri + 1), url: CHANNELS[ri].link }]);
    }
    rows.push([{ text: "Verify Join", url: "https://t.me/" + BOT_USERNAME + "?start=verify" }]);
    send("Hey " + UFNAME + "," + NL + "Join both channels then tap Verify.", { inline_keyboard: rows });
    return;
  }

  const refMatch = incoming.match(/\/start[\s_]+ref[_ ]?(\d+)/i);
  if (refMatch) {
    const refId = parseInt(refMatch[1]);
    if (refId && refId !== UID && !storeGet("referred_by_" + UID)) {
      storeSet("referred_by_" + UID, refId);
      let rlist = [];
      try { rlist = JSON.parse(storeGet("ref_list_" + refId) || "[]"); } catch (e) {}
      if (rlist.indexOf(UID) === -1) {
        rlist.push(UID);
        storeSet("ref_list_" + refId, JSON.stringify(rlist));
        const rOld = parseFloat(storeGet("balance_" + refId) || "0") || 0;
        storeSet("balance_" + refId, rOld + REFERRAL_BONUS);
      }
    }
  }

  let st = getSt();
  if (!st.step) st.step = "menu";

  if (low === "/start" || low === "/menu" || low === "/cancel" || low === "back to menu" || low === "back" || cmd === "") {
    setSt({ step: "menu" });
    if (isAdmin) {
      let availA = 0;
      const allA = nums();
      for (let aa = 0; aa < allA.length; aa++) { if (!allA[aa].sold) availA++; }
      let wA = "ADMIN PANEL" + NL + NL;
      wA = wA + "Stock " + availA + NL;
      wA = wA + "Users " + users().length + NL;
      wA = wA + "Pending " + pend().length + NL + NL;
      wA = wA + "Tap a button.";
      send(wA, adminKb);
    } else {
      let wU = "Welcome " + UPI_NAME + NL + NL;
      wU = wU + "Balance Rs" + bal().toFixed(2);
      send(wU, userKb);
    }
    return;
  }

  if (isAdmin && low.indexOf("add telegram") !== -1) {
    setSt({ step: "addc", svc: "telegram" });
    send("Add Telegram step 1 of 3. Send country name.", adminKb);
    return;
  }

  if (isAdmin && low.indexOf("add whatsapp") !== -1) {
    setSt({ step: "addc", svc: "whatsapp" });
    send("Add WhatsApp step 1 of 3. Send country name.", adminKb);
    return;
  }

  if (isAdmin && st.step === "addc") {
    if (!incoming) { send("Send country.", adminKb); return; }
    st.step = "addn";
    st.country = incoming;
    setSt(st);
    let m1 = "Step 2 of 3" + NL + NL;
    m1 = m1 + "Service " + st.svc + NL;
    m1 = m1 + "Country " + st.country + NL + NL;
    m1 = m1 + "Send phone number with country code.";
    send(m1, adminKb);
    return;
  }

  if (isAdmin && st.step === "addn") {
    if (!incoming) { send("Send number.", adminKb); return; }
    st.step = "addp";
    st.number = incoming;
    setSt(st);
    let m2 = "Step 3 of 3" + NL + NL;
    m2 = m2 + "Number " + st.number + NL + NL;
    m2 = m2 + "Send price in rupees.";
    send(m2, adminKb);
    return;
  }

  if (isAdmin && st.step === "addp") {
    const price = parseFloat(incoming);
    if (isNaN(price)) { send("Send valid number.", adminKb); return; }
    const arr = nums();
    arr.push({ id: Date.now(), country: st.country, number: st.number, service: st.svc, otp: "", price: price, sold: false, soldTo: null });
    setNums(arr);
    setSt({ step: "menu" });
    let m3 = "Number added!" + NL + NL;
    m3 = m3 + "Service " + st.svc + NL;
    m3 = m3 + "Number " + st.number + NL;
    m3 = m3 + "Price Rs" + price + NL + NL;
    m3 = m3 + "Stock " + arr.length;
    send(m3, adminKb);
    return;
  }

  if (isAdmin && low.indexOf("set otp") !== -1) {
    const waiting = [];
    const allN = nums();
    for (let wi = 0; wi < allN.length; wi++) {
      if (allN[wi].sold && !allN[wi].otp) waiting.push(allN[wi]);
    }
    if (!waiting.length) { send("No sold numbers waiting.", adminKb); return; }
    setSt({ step: "setid" });
    const wl = [];
    const wstart = waiting.length > 15 ? waiting.length - 15 : 0;
    for (let wi2 = wstart; wi2 < waiting.length; wi2++) {
      wl.push("#" + waiting[wi2].id + " " + waiting[wi2].number);
    }
    let m4 = "Set OTP step 1 of 2" + NL + NL;
    m4 = m4 + "Waiting:" + NL + wl.join(NL) + NL + NL;
    m4 = m4 + "Send number ID.";
    send(m4, adminKb);
    return;
  }

  if (isAdmin && st.step === "setid") {
    const nid = String(incoming).replace("#", "").trim();
    let found = null;
    const allL = nums();
    for (let fi = 0; fi < allL.length; fi++) {
      if (String(allL[fi].id) === nid) { found = allL[fi]; break; }
    }
    if (!found) { send("ID not found.", adminKb); return; }
    st.step = "setcode";
    st.nid = nid;
    setSt(st);
    send("Send OTP code.", adminKb);
    return;
  }

  if (isAdmin && st.step === "setcode") {
    const arrO = nums();
    let target = null;
    for (let ti = 0; ti < arrO.length; ti++) {
      if (String(arrO[ti].id) === st.nid) { target = arrO[ti]; break; }
    }
    if (!target) { setSt({ step: "menu" }); send("Lost track.", adminKb); return; }
    target.otp = incoming;
    setNums(arrO);
    setSt({ step: "menu" });
    send("OTP set for " + target.number, adminKb);
    if (target.soldTo) {
      try { apiSend({ chat_id: target.soldTo, text: "OTP Received: " + incoming }); } catch (e) {}
    }
    return;
  }

  if (isAdmin && low.indexOf("stock") !== -1 && low.indexOf("buy") === -1) {
    const arrS = nums();
    if (!arrS.length) { send("No numbers.", adminKb); return; }
    const sl = [];
    for (let si = 0; si < arrS.length; si++) {
      let sline = "#" + arrS[si].id;
      sline = sline + " " + arrS[si].number;
      sline = sline + " Rs" + arrS[si].price;
      sline = sline + " " + (arrS[si].sold ? "SOLD" : "OK");
      sl.push(sline);
    }
    send("STOCK" + NL + NL + sl.join(NL), adminKb);
    return;
  }

  if (isAdmin && low.indexOf("pending") !== -1) {
    const p = pend();
    if (!p.length) { send("No pending.", adminKb); return; }
    const pl = [];
    for (let pi = 0; pi < p.length; pi++) {
      pl.push("[" + (pi + 1) + "] " + p[pi].uid + " Rs" + p[pi].amount);
    }
    st.step = "pendact";
    st.list = p;
    setSt(st);
    const mP = "Pending" + NL + NL + pl.join(NL + NL) + NL + NL + "Reply OK 1 or NO 1";
    send(mP, adminKb);
    return;
  }

  if (isAdmin && st.step === "pendact") {
    const pm = incoming.match(/^(OK|NO)\s+(\d+)$/i);
    if (!pm) { send("Reply OK 1 or NO 1.", adminKb); return; }
    const pact = pm[1].toUpperCase();
    const pidx = parseInt(pm[2]) - 1;
    const item = (st.list || [])[pidx];
    if (!item) { send("Bad index.", adminKb); return; }
    const pall = pend();
    const pnew = [];
    for (let pk = 0; pk < pall.length; pk++) {
      if (!(pall[pk].uid === item.uid && pall[pk].amount === item.amount)) pnew.push(pall[pk]);
    }
    setPend(pnew);
    if (pact === "OK") {
      const oldBal = parseFloat(storeGet("balance_" + item.uid) || "0") || 0;
      let bonus = 0;
      if (item.amount >= BONUS_THRESHOLD) bonus = item.amount * BONUS_PERCENT / 100;
      const newBal = oldBal + item.amount + bonus;
      storeSet("balance_" + item.uid, newBal);
      let msgA = "Payment Approved!" + NL + NL;
      msgA = msgA + "Recharged Rs" + item.amount.toFixed(2) + NL;
      if (bonus) msgA = msgA + "Bonus Rs" + bonus.toFixed(2) + NL;
      msgA = msgA + "Balance Rs" + newBal.toFixed(2);
      try { apiSend({ chat_id: item.uid, text: msgA }); } catch (e) {}
      send("Approved.", adminKb);
    } else {
      try { apiSend({ chat_id: item.uid, text: "Payment rejected." }); } catch (e) {}
      send("Rejected.", adminKb);
    }
    setSt({ step: "menu" });
    return;
  }

  if (isAdmin && low.indexOf("stats") !== -1) {
    const arrSt = nums();
    const usSt = users();
    let soldCount = 0, revenue = 0, tgStock = 0, waStock = 0;
    for (let sti = 0; sti < arrSt.length; sti++) {
      if (arrSt[sti].sold) { soldCount++; revenue += (arrSt[sti].price || 0); }
      else { if ((arrSt[sti].service || "telegram") === "telegram") tgStock++; else waStock++; }
    }
    let mS = "STATS" + NL + NL;
    mS = mS + "Users " + usSt.length + NL;
    mS = mS + "TG stock " + tgStock + NL;
    mS = mS + "WA stock " + waStock + NL;
    mS = mS + "Sold " + soldCount + NL;
    mS = mS + "Revenue Rs" + revenue.toFixed(2);
    send(mS, adminKb);
    return;
  }

  if (isAdmin && low.indexOf("broadcast") !== -1) {
    setSt({ step: "bc" });
    send("Broadcast mode. Send message. /cancel to abort.", adminKb);
    return;
  }

  if (isAdmin && st.step === "bc") {
    const bus = users();
    let ok = 0, fail = 0;
    for (let bi = 0; bi < bus.length; bi++) {
      try { await apiSend({ chat_id: bus[bi], text: incoming }); ok++; } catch (e) { fail++; }
    }
    setSt({ step: "menu" });
    send("Sent " + ok + " Failed " + fail, adminKb);
    return;
  }

  if (low.indexOf("buy number") !== -1 || low === "/buy") {
    const avail = [];
    const allAv = nums();
    for (let avi = 0; avi < allAv.length; avi++) {
      if (!allAv[avi].sold) avail.push(allAv[avi]);
    }
    if (!avail.length) { setSt({ step: "menu" }); send("No stock.", userKb); return; }
    const svcs = [];
    for (let svi = 0; svi < avail.length; svi++) {
      const s = avail[svi].service || "telegram";
      if (svcs.indexOf(s) === -1) svcs.push(s);
    }
    if (svcs.length > 1) {
      st.step = "svc";
      st.services = svcs;
      setSt(st);
      send("Choose service" + NL + NL + svcs.join(NL), userKb);
      return;
    }
    const svc1 = svcs[0];
    const ctry = [];
    for (let cj = 0; cj < avail.length; cj++) {
      if ((avail[cj].service || "telegram") === svc1 && ctry.indexOf(avail[cj].country) === -1) ctry.push(avail[cj].country);
    }
    st.step = "ctry";
    st.svc = svc1;
    st.countries = ctry;
    setSt(st);
    send(svc1 + " - Choose country" + NL + NL + ctry.join(NL), userKb);
    return;
  }

  if (st.step === "svc") {
    const svIdx = parseInt(cmd) - 1;
    const svcPick = (st.services || [])[svIdx];
    if (!svcPick) { send("Invalid.", userKb); return; }
    const ctry2 = [];
    const allC = nums();
    for (let cti2 = 0; cti2 < allC.length; cti2++) {
      if (!allC[cti2].sold && (allC[cti2].service || "telegram") === svcPick && ctry2.indexOf(allC[cti2].country) === -1) ctry2.push(allC[cti2].country);
    }
    st.step = "ctry";
    st.svc = svcPick;
    st.countries = ctry2;
    setSt(st);
    send(svcPick + " - Choose country" + NL + NL + ctry2.join(NL), userKb);
    return;
  }

  if (st.step === "ctry") {
    const cIdx = parseInt(cmd) - 1;
    const cPick = (st.countries || [])[cIdx];
    if (!cPick) { send("Invalid.", userKb); return; }
    const arrC = [];
    const allCC = nums();
    for (let cci = 0; cci < allCC.length; cci++) {
      if (allCC[cci].country === cPick && !allCC[cci].sold && (allCC[cci].service || "telegram") === st.svc) arrC.push(allCC[cci]);
    }
    if (!arrC.length) { setSt({ step: "menu" }); send("None available.", userKb); return; }
    const ids = [];
    const nl = [];
    for (let nli = 0; nli < arrC.length; nli++) {
      ids.push(arrC[nli].id);
      nl.push(arrC[nli].number + " Rs" + arrC[nli].price.toFixed(2));
    }
    st.step = "num";
    st.ids = ids;
    setSt(st);
    send(cPick + NL + NL + nl.join(NL), userKb);
    return;
  }

  if (st.step === "num") {
    const nIdx = parseInt(cmd) - 1;
    const nId = (st.ids || [])[nIdx];
    if (!nId) { send("Invalid.", userKb); return; }
    let itN = null;
    const allN2 = nums();
    for (let nii = 0; nii < allN2.length; nii++) {
      if (allN2[nii].id === nId && !allN2[nii].sold) { itN = allN2[nii]; break; }
    }
    if (!itN) { setSt({ step: "menu" }); send("Sold.", userKb); return; }
    if (bal() < itN.price) { setSt({ step: "menu" }); send("Low balance. Add fund.", userKb); return; }
    st.step = "cfm";
    st.nid = nId;
    setSt(st);
    let mQ = "Confirm" + NL + NL;
    mQ = mQ + "Number " + itN.number + NL;
    mQ = mQ + "Price Rs" + itN.price.toFixed(2) + NL + NL;
    mQ = mQ + "Reply YES or NO";
    send(mQ, userKb);
    return;
  }

  if (st.step === "cfm") {
    const ans = cmd.toUpperCase();
    if (ans === "NO" || ans === "N") { setSt({ step: "menu" }); send("Cancelled.", userKb); return; }
    if (ans !== "YES" && ans !== "Y") { send("Reply YES or NO.", userKb); return; }
    const allF = nums();
    let itF = null;
    for (let fii = 0; fii < allF.length; fii++) {
      if (allF[fii].id === st.nid && !allF[fii].sold) { itF = allF[fii]; break; }
    }
    if (!itF) { setSt({ step: "menu" }); send("Already sold.", userKb); return; }
    if (bal() < itF.price) { setSt({ step: "menu" }); send("Low balance.", userKb); return; }
    itF.sold = true;
    itF.soldTo = UID;
    setNums(allF);
    storeSet("balance_" + UID, bal() - itF.price);
    setSt({ step: "menu" });
    let mP2 = "Purchased!" + NL + NL;
    mP2 = mP2 + "Number " + itF.number + NL + NL;
    mP2 = mP2 + "OTP will arrive here.";
    send(mP2, userKb);
    for (let adi = 0; adi < ADMIN_IDS.length; adi++) {
      try { apiSend({ chat_id: ADMIN_IDS[adi], text: "Sale user " + UID + " number " + itF.number }); } catch (e) {}
    }
    return;
  }

  if (low.indexOf("add fund") !== -1 || low === "/addfund") {
    setSt({ step: "afamt" });
    let mAf = "Add Fund step 1 of 2" + NL + NL;
    mAf = mAf + "Min Rs" + MIN_ADD_FUND.toFixed(2) + NL;
    mAf = mAf + "Bonus " + BONUS_PERCENT + " percent above Rs" + BONUS_THRESHOLD.toFixed(0) + NL + NL;
    mAf = mAf + "UPI " + UPI_ID + NL;
    mAf = mAf + "Send amount in rupees.";
    send(mAf, userKb);
    return;
  }

  if (st.step === "afamt") {
    const amt = parseFloat(incoming);
    if (isNaN(amt) || amt < MIN_ADD_FUND) { send("Invalid. Min Rs" + MIN_ADD_FUND.toFixed(2), userKb); return; }
    st.step = "afutr";
    st.amt = amt;
    setSt(st);
    let mAf2 = "Amount Rs" + amt.toFixed(2) + NL + NL;
    if (amt >= BONUS_THRESHOLD) {
      const bprev = amt * BONUS_PERCENT / 100;
      mAf2 = mAf2 + "Bonus Rs" + bprev.toFixed(2) + NL + NL;
    }
    mAf2 = mAf2 + "Pay to UPI " + UPI_ID + NL;
    mAf2 = mAf2 + "Send UTR after paying.";
    send(mAf2, userKb);
    return;
  }

  if (st.step === "afutr") {
    if (!incoming) { send("Send UTR.", userKb); return; }
    const parr = pend();
    parr.push({ uid: UID, amount: st.amt, proof: incoming });
    setPend(parr);
    setSt({ step: "menu" });
    send("Submitted. Admin will verify.", userKb);
    for (let adi2 = 0; adi2 < ADMIN_IDS.length; adi2++) {
      try {
        let mA2 = "New payment" + NL + NL;
        mA2 = mA2 + "User " + UID + NL;
        mA2 = mA2 + "Amount Rs" + st.amt.toFixed(2) + NL;
        mA2 = mA2 + "UTR " + incoming;
        apiSend({ chat_id: ADMIN_IDS[adi2], text: mA2 });
      } catch (e) {}
    }
    return;
  }

  if (low.indexOf("wallet") !== -1) {
    setSt({ step: "menu" });
    send("Balance Rs" + bal().toFixed(2), userKb);
    return;
  }

  if (low.indexOf("refer") !== -1) {
    setSt({ step: "menu" });
    send("Your link https://t.me/" + BOT_USERNAME + "?start=ref_" + UID, userKb);
    return;
  }

  if (low.indexOf("help") !== -1) {
    setSt({ step: "menu" });
    let mH = "Support " + SUPPORT + NL;
    mH = mH + "UPI " + UPI_ID + NL;
    mH = mH + "Min Rs" + MIN_ADD_FUND.toFixed(2) + NL;
    mH = mH + "Bonus " + BONUS_PERCENT + " percent above Rs" + BONUS_THRESHOLD.toFixed(0);
    send(mH, userKb);
    return;
  }

  setSt({ step: "menu" });
  send("Unknown. Use buttons.", menuKb);
}

app.post(WEBHOOK_PATH, (req, res) => {
  handleUpdate(req.body).catch((e) => console.log("handleUpdate err", e.message));
  res.sendStatus(200);
});

app.get("/", (req, res) => res.send("bot alive"));

app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
  if (process.env.RAILWAY_PUBLIC_DOMAIN) {
    const url = "https://" + process.env.RAILWAY_PUBLIC_DOMAIN + WEBHOOK_PATH;
  
