"""
Barber Shop Telegram Bot — Production Build
Features: 6-language i18n, admin style upload, Chapa payments, waitlist
"""
import re
import os
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)

# ================================================================
# 1. CONFIGURATION
# ================================================================
TOKEN = os.getenv("BOT_TOKEN")
BARBER_ID = int(os.getenv("BARBER_ID", "0"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "").rstrip("/")

WORKING_HOURS = [
    "09:00", "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00", "16:00", "17:00"
]

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ADD_STYLE_PHOTO = 1

# ================================================================
# 2. INTERNATIONALIZATION
# ================================================================
LANGS = {
    "en": {"flag": "🇬🇧", "label": "English"},
    "am": {"flag": "🇪🇹", "label": "አማርኛ"},
    "om": {"flag": "🟢", "label": "Afaan Oromoo"},
    "ti": {"flag": "🔵", "label": "ትግርኛ"},
    "so": {"flag": "⭐", "label": "Soomaali"},
    "aa": {"flag": "🔴", "label": "Qafaraf"},
}

L = {
    "en": {
        "welcome": "Welcome to the Barber Shop!",
        "choose_lang": "Please choose your language:",
        "main_menu": "Welcome! What would you like to do today?",
        "book_btn": "✂️ Choose Style & Book",
        "info_btn": "📍 Shop Info & Hours",
        "info": "📍 *Our Location:*\nAdama, Main Street\n\n🕒 *Working Hours:*\nMon-Sat: 9:00 AM – 5:00 PM\nSunday: Closed\n\n📞 *Contact:* +251 911 234 567",
        "back": "🔙 Back",
        "deposit": "💳 *Deposit Paid:* 50 ETB via Chapa",
        "remaining": "💶 *Remaining:* {amt} ETB (pay at shop)",
        "cancel_btn": "❌ Sorry, I can't make it (Cancel)",
        "processing": "⏳ *Payment Processing...*\n\nEthiopian banks (Telebirr / CBE) sometimes take 1-3 minutes to confirm. Your slot is safely held!\n\nYou'll get your confirmation here automatically.",
        "pay_failed": "❌ Payment failed or was canceled. Try again from the menu.",
        "book_error": "❌ Error finding your booking in our system.",
        "canceled_ok": "✅ Your appointment has been canceled.",
        "not_active": "This appointment is no longer active.",
        "admin_on": "Admin mode activated.",
        "dashboard": "👨‍💻 *Admin Dashboard*",
        "open_dash": "👨‍💻 Open Dashboard",
        "today": "📅 Today's Schedule",
        "add_break": "⏸️ Add Break",
        "end_break": "▶️ End Break Early",
        "upcoming": "📆 All Upcoming",
        "earnings": "💰 View Earnings",
        "no_today": "No paid appointments for today.",
        "no_upcoming": "No upcoming paid appointments.",
        "end_list": "— End of list —",
        "done": "✅ Done",
        "no_show": "❌ No Show",
        "marked_done": "✅ Appointment #{id} marked Completed.",
        "marked_cancel": "❌ Appointment #{id} canceled.",
        "break_start": "Select START time for break:",
        "break_end": "Select END time:",
        "break_added": "✅ Break added: {s} → {e}",
        "break_ended": "▶️ Break ended early.",
        "pick_period": "Select period:",
        "p_today": "Today",
        "p_week": "This Week",
        "p_month": "This Month",
        "earn_title": "📊 *Earnings ({p})*",
        "earn_total": "💸 Total: *{a} ETB*",
        "earn_count": "✂️ Haircuts: *{c}*",
        "unauth": "❌ Not authorized.",
        "wl_offer": "🎉 *Good News {n}!*\n\nA spot opened up!\n\n💈 *Service:* {s} ({p} ETB)\n📅 *When:* {d} at {t}\n\nClaim it?",
        "wl_yes": "✅ Yes, I'll take it!",
        "wl_no": "❌ No, I can't make it",
        "wl_ok": "✅ *Booking Confirmed!*\n\nYou got the spot!\n💈 {s}\n📅 {d} at {t}",
        "wl_out": "No problem! Removed from waitlist.",
        "wl_expired": "This waitlist offer is no longer valid.",
        "wl_taken": "Sorry, someone else just booked this slot!",
        "cust_cancel_note": "ℹ️ Customer canceled {d} at {t}. Checking waitlist…",
        "late_ok": "👍 Noted! The barber knows you're on your way.",
        "late_note": "🏃 Customer *{n}* says they're coming.",
        "late_canceled": "✅ Appointment canceled.",
        "late_cancel_note": "❌ Customer *{n}* canceled.",
        "noshow_note": "⚠️ Your appointment was marked 'No Show' by the barber.",
        "break_cancel_note": "⚠️ *{n}*, your {t} appointment was canceled due to a shop break. Please rebook.",
        "add_style_msg": "📸 *Send me a photo of the hairstyle.*\n\nInclude a caption in this exact format:\n`Name | Price | Description | Est. Time`\n\nExample:\n`Low Taper Fade | 250 | Clean professional look | 30 mins`\n\nSend /cancel to abort.",
        "style_added": "✅ *Style Added!*\n\n💈 {n}\n💰 {p} ETB\n📝 {d}\n⏱️ {t}",
        "style_parse_err": "❌ Couldn't parse caption. Use:\n`Name | Price | Description | Est. Time`",
        "manage": "🎨 Manage Styles",
        "add_new": "➕ Add New Style",
        "del_style": "🗑️ Delete a Style",
        "pick_del": "Pick a style to delete:",
        "style_del_ok": "✅ Style deleted.",
        "no_styles": "No styles in the system yet.",
        "cancel_op": "Operation canceled.",
        "paid_tag": "*(Paid via Chapa)*",
        "late_q": "⏰ *{n}*, the barber is waiting. Are you coming?",
        "im_coming": "🏃 I'm coming!",
        "cant_make": "😭 I can't make it",
        "noti_sent": "Notification sent!",
        "noti_fail": "Failed to message.",
        "w_title": "Choose a Style",
        "w_when": "When do you want to come?",
        "w_today": "Today",
        "w_tomorrow": "Tomorrow",
        "w_pick_date": "📆 Pick Specific Date",
        "w_select_time": "Select Time",
        "w_pay": "Pay 50 ETB Deposit",
        "w_test": "🛠️ Test: Skip Payment",
        "w_verifying": "Verifying Payment…",
        "w_verifying_sub": "Waiting for bank confirmation.\nPlease don't close this page.",
        "w_no_times": "No times available for this date.",
        "w_loading": "Loading times…",
        "w_est": "Est. Time",
        "w_complete": "Please complete all steps above.",
        "w_connecting": "Connecting to Chapa…",
        "w_net_err": "Network error. Check connection and retry.",
        "w_pay_fail": "Payment failed. Please try again.",
        "w_testing": "Processing test…",
        "w_no_styles": "No styles available yet.\nThe barber is setting things up — check back soon!",
        "share_phone": "📱 Share Phone Number",
        "phone_ask": "✅ *Payment confirmed!*\n\nJust one last thing — we need your phone number so the barber can reach you if needed.\n\nTap the button below to share it securely (no typing needed):",
        "phone_invalid": "⚠️ That doesn't look like a valid phone number. Please use the button above, or type your number like: +251911234567",
        "phone_thanks": "✅ Got it!",
    },
    "am": {
        "welcome": "እንኳን ወደ ባርበር ሾፕ በደህና መጡ!",
        "choose_lang": "እባክዎ ቋንቋ ይምረጡ:",
        "main_menu": "እንኳን በደህና መጡ! ዛሬ ምን ላገልግልዎ?",
        "book_btn": "✂️ ዘይቤ ይምረጡ እና ይዘጋጁ",
        "info_btn": "📍 አድራሻ እና የስራ ሰዓት",
        "info": "📍 *አድራሻ:* አዳማ, ዋና መንገድ\n\n🕒 *የስራ ሰዓት:* ሰኞ-ቅዳሜ: ጠዋት 9:00 – ምሽት 5:00\nእሁድ: ይዘጋል\n\n📞 *ስልክ:* +251 911 234 567",
        "back": "🔙 ተመለስ",
        "deposit": "💳 *ቅድሚያ ክፍያ:* 50 ብር ቻፓ በኩል",
        "remaining": "💶 *ቀሪው:* {amt} ብር (በሱቅ ይከፍሉ)",
        "cancel_btn": "❌ አይመጣም ሰርቼያለሁ (ሰርዝ)",
        "processing": "⏳ *ክፍያ በሂደት ላይ…*\n\nባንኮች 1-3 ደቂቃ ይወስዳሉ። ቦታዎ ደህና ነው!",
        "pay_failed": "❌ ክፍያው አልተሳካም። እባክዎ ይሞክሩ።",
        "book_error": "❌ ቦታዎን ማግኘት አልተቻለም።",
        "canceled_ok": "✅ ቦታዎ ተሰርዟል።",
        "not_active": "ይህ ቦታ የቀረ አይደለም።",
        "admin_on": "አስተዳዳሪ ሁነታ ተጀምሯል።",
        "dashboard": "👨‍💻 *አስተዳዳሪ ዳሽቦርድ*",
        "open_dash": "👨‍💻 ዳሽቦርድ ክፈት",
        "today": "📅 የዛሬ መርሃ ግብር",
        "add_break": "⏸️ ክፍተት ጨምር",
        "end_break": "▶️ ክፍተት ቀንስ",
        "upcoming": "📆 ሁሉም መጪዎች",
        "earnings": "💰 ገቢ ርእሲ",
        "no_today": "ዛሬ የተከፈለ ቦታ የለም።",
        "no_upcoming": "መጪ የተከፈለ ቦታ የለም።",
        "end_list": "— ዝርዝሩ መጨረሻ —",
        "done": "✅ ተጠናቀቀ",
        "no_show": "❌ አልመጣም",
        "marked_done": "✅ ቦታ #{id} ተጠናቀቀ።",
        "marked_cancel": "❌ ቦታ #{id} ተሰርዟል።",
        "break_start": "ክፍተት የሚጀምር ሰዓት ይምረጡ:",
        "break_end": "የሚያበቃ ሰዓት ይምረጡ:",
        "break_added": "✅ ክፍተት: {s} → {e}",
        "break_ended": "▶️ ክፍተት ቀንሷል።",
        "pick_period": "ጊዜ ይምረጡ:",
        "p_today": "ዛሬ",
        "p_week": "የዚህ ሳምንት",
        "p_month": "የዚህ ወር",
        "earn_title": "📊 *ገቢ ({p})*",
        "earn_total": "💸 ጠቅላላ: *{a} ብር*",
        "earn_count": "✂️ ቆርጦዎች: *{c}*",
        "unauth": "❌ ፈቃድ የለም።",
        "wl_offer": "🎉 *ጥሩ ዜና {n}!*\n\nቦታ ተከፈተ!\n💈 *አገልግሎት:* {s} ({p} ብር)\n📅 *መቼ:* {d} ላይ {t}\n\nይውሰዳሉ?",
        "wl_yes": "✅ አዎ, እወስዳለሁ!",
        "wl_no": "❌ አይ, አልመጣም",
        "wl_ok": "✅ *ቦታ ተረጋግጧል!*\n\n💈 {s}\n📅 {d} ላይ {t}",
        "wl_out": "ከዝርዝሩ ተወግዷል።",
        "wl_expired": "ይህ ቦታ የቀረ አይደለም።",
        "wl_taken": "ሌላ ሰው ቀስታ ያዘጋጃል!",
        "cust_cancel_note": "ℹ️ ደንበኛ {d} ላይ {t} ሰርዶል።",
        "late_ok": "👍 ተረድቷል!",
        "late_note": "🏃 ደንበኛ *{n}* መጣለል ብሎል።",
        "late_canceled": "✅ ተሰርዟል።",
        "late_cancel_note": "❌ ደንበኛ *{n}* ሰርዶል።",
        "noshow_note": "⚠️ 'አልመጣም' ብሎ ተሰርድዎል።",
        "break_cancel_note": "⚠️ *{n}*, የ{t} ቦታዎ በክፍተት ምክንያት ተሰርዶል።",
        "add_style_msg": "📸 *የዘይቤ ፎቶ ይላኩ።*\n\n`ስም | ዋጋ | ዝርዝር | ጊዜ`\n\nለምሳሌ:\n`ፌድ ቆርጥ | 250 | ንጹህ ፌድ | 30 ደቂቃ`\n\n/cancel ለመሰረዝ",
        "style_added": "✅ *ዘይቤ ተጨምሯል!*\n\n💈 {n}\n💰 {p} ብር\n📝 {d}\n⏱️ {t}",
        "style_parse_err": "❌ ማንበብ አልተቻለም።\n`ስም | ዋጋ | ዝርዝር | ጊዜ`",
        "manage": "🎨 ዘይቤዎች አስተዳዳር",
        "add_new": "➕ አዲስ ዘይቤ",
        "del_style": "🗑️ ዘይቤ ሰርዝ",
        "pick_del": "ለመሰረዝ ዘይቤ ይምረጡ:",
        "style_del_ok": "✅ ተሰርዟል።",
        "no_styles": "እስካሁን ዘይቤ የለም።",
        "cancel_op": "ተሰርዟል።",
        "paid_tag": "*(ቻፓ በኩል ተከፈል)*",
        "late_q": "⏰ *{n}*, ባርበሩ በጠባብ ነው። ይመጣሉ?",
        "im_coming": "🏃 እመጣለሁ!",
        "cant_make": "😭 አልመጣም",
        "noti_sent": "መልዕክት ተልኳል!",
        "noti_fail": "መልዕክት አልተላከም።",
        "w_title": "ዘይቤ ይምረጡ",
        "w_when": "መቼ ይመጡ?",
        "w_today": "ዛሬ",
        "w_tomorrow": "ነገ",
        "w_pick_date": "📆 ቀን ይምረጡ",
        "w_select_time": "ሰዓት ይምረጡ",
        "w_pay": "50 ብር ቅድሚያ ክፍያ",
        "w_test": "🛠️ ፈተና: ክፍያ ዝለል",
        "w_verifying": "ክፍያ በሂደት ላይ…",
        "w_verifying_sub": "ከባንክ ማረጋገጫ በመጠባበቅ ላይ።",
        "w_no_times": "ለዚህ ቀን ሰዓት የለም።",
        "w_loading": "ሰዓታትን በማምጣት ላይ…",
        "w_est": "የሚወስደው ጊዜ",
        "w_complete": "እባክዎ ሁሉንም ደረጃዎች ይጠንቀቁ።",
        "w_connecting": "ቻፓ ጋር በማገናኘት ላይ…",
        "w_net_err": "አውታር ችግር። እባክዎ ይሞክሩ።",
        "w_pay_fail": "ክፍያ አልተሳካም።",
        "w_testing": "ፈተና በሂደት ላይ…",
        "w_no_styles": "እስካሁን ዘይቤ የለም።\nባርበሩ በማዘጋጀት ላይ ነው — ቆይተው ይመልልሱ!",
        "share_phone": "📱 ስልክ ቁጥር አጋራ",
        "phone_ask": "✅ *ክፍያ ተረጋግጧል!*\n\nየመጨረሻው — ባርበሩ እንዲያገናኝ ስልክ ቁጥርዎን እንፈልጋለን።\n\nከታች ባዶውን ይጫኑ (ምንም ይጻፋሉም):",
        "phone_invalid": "⚠️ ቁጥሩ ትክክል አይደለም። ቁልፉን ተጠቀሙ ወይም ይጻፉ (+251911234567)",
        "phone_thanks": "✅ ተቀብሏል!",
    },
    "om": {
        "welcome": "Baga nagaan dhuftan Kuusaa Qalaa!",
        "choose_lang": "Afaan isin filadhu:",
        "main_menu": "Baga nagaan dhuftan! Har'a maal gaafadhu?",
        "book_btn": "✂️ Qabxii Filadhu",
        "info_btn": "📍 Teessoo fi Sa'aati",
        "info": "📍 *Teessoo:* Adaama, Bula Wajjiin\n\n🕒 *Sa'aati:* Gurba-Qaxxamar: 9-5\nDilbata: Cufamti\n\n📞 *Bilbila:* +251 911 234 567",
        "back": "🔙 Deebi'i",
        "deposit": "💳 *Dabarsaa:* 50 ETB",
        "remaining": "💶 *Hafe:* {amt} ETB",
        "cancel_btn": "❌ Hin dhufne (Balleessi)",
        "processing": "⏳ *Qalbiin jechuun jira…*",
        "pay_failed": "❌ Qalbiin hin milkaa'ne.",
        "book_error": "❌ Qabadhaa hin arganne.",
        "canceled_ok": "✅ Balleefameera.",
        "not_active": "Qabadhaan hin jiru.",
        "admin_on": "Bulchiinsa fufe.",
        "dashboard": "👨‍💻 *Dasboordii*",
        "open_dash": "👨‍💻 Dasboordii Bana",
        "today": "📅 Har'aa",
        "add_break": "⏸️ Bu'aa Dabali",
        "end_break": "▶️ Bu'aa Xumuri",
        "upcoming": "📆 Dhufaa Hunda",
        "earnings": "💰 Hordoffii",
        "no_today": "Har'a qabadhaa hin jiru.",
        "no_upcoming": "Dhufaa hin jiru.",
        "end_list": "— Dhuma —",
        "done": "✅ Xumure",
        "no_show": "❌ Hin dhufne",
        "marked_done": "✅ #{id} xumureera.",
        "marked_cancel": "❌ #{id} balleefameera.",
        "break_start": "Bu'aan jalqabu saa'a:",
        "break_end": "Bu'aan xumuru saa'a:",
        "break_added": "✅ Bu'aa: {s} → {e}",
        "break_ended": "▶️ Bu'aa xumureera.",
        "pick_period": "Yeroo filadhu:",
        "p_today": "Har'a",
        "p_week": "Torban Kana",
        "p_month": "Ji'a Kana",
        "earn_title": "📊 *Hordoffii ({p})*",
        "earn_total": "💸 Waliigalaa: *{a} ETB*",
        "earn_count": "✂️ Qorannoo: *{c}*",
        "unauth": "❌ Xaq hin jiru.",
        "wl_offer": "🎉 *Rakkoo {n}!*\n\nBakka banaa'e!\n💈 {s} ({p} ETB)\n📅 {d} saa {t}",
        "wl_yes": "✅ Eeyyee, fudha!",
        "wl_no": "❌ Rakkoo, hin dhufne",
        "wl_ok": "✅ *Mirkanaa'e!*\n💈 {s}\n📅 {d} saa {t}",
        "wl_out": "Listii irraa haqneerra.",
        "wl_expired": "Bakka hin jiru.",
        "wl_taken": "Tokko biraa qabatee jira!",
        "cust_cancel_note": "ℹ️ Miggaasa {d} saa {t} balleese.",
        "late_ok": "👍 Beekameera!",
        "late_note": "🏃 *{n}* dhufaa jira.",
        "late_canceled": "✅ Balleefameera.",
        "late_cancel_note": "❌ *{n}* balleese.",
        "noshow_note": "⚠️ 'Hin dhufne' jedhame balleefameera.",
        "break_cancel_note": "⚠️ *{n}*, {t} bu'aa dhaabbataa balleefameera.",
        "add_style_msg": "📸 Suura ergaa.\n`Maqaa | Qiyyaa | Beekumsa | Sa'aati`\n\n/cancel deebi'i",
        "style_added": "✅ *Qabxii Dabame!*\n💈 {n}\n💰 {p} ETB\n📝 {d}\n⏱️ {t}",
        "style_parse_err": "❌ Hin fudhatame.",
        "manage": "🎨 Qabxii Torbee",
        "add_new": "➕ Haaraa",
        "del_style": "🗑️ Balleessi",
        "pick_del": "Balleessuuf filadhu:",
        "style_del_ok": "✅ Balleefameera.",
        "no_styles": "Qabxii hin jiru.",
        "cancel_op": "Balleefameera.",
        "paid_tag": "*(Qalame)*",
        "late_q": "⏰ *{n}*, kuusaa eegaa.",
        "im_coming": "🏃 Dhufaa!",
        "cant_make": "😭 Hin dhufne",
        "noti_sent": "Ergaa dhufee!",
        "noti_fail": "Ergaa hin dhufne.",
        "w_title": "Qabxii Filadhu",
        "w_when": "Yoo dhufatta?",
        "w_today": "Har'a",
        "w_tomorrow": "Boru",
        "w_pick_date": "📆 Guyyaa Filadhu",
        "w_select_time": "Sa'aati Filadhu",
        "w_pay": "50 ETB Dabarsaa",
        "w_test": "🛠️ Qalbiin Olkaa'i",
        "w_verifying": "Qalbiin jechuun jira…",
        "w_verifying_sub": "Mirkanaa'uu eegaa.",
        "w_no_times": "Sa'aati hin jiru.",
        "w_loading": "Sa'aati gargaaru…",
        "w_est": "Sa'aati",
        "w_complete": "Hunda xumuri.",
        "w_connecting": "Chapa waliin…",
        "w_net_err": "Dogoggora.",
        "w_pay_fail": "Qalbiin hin milkaa'ne.",
        "w_testing": "Qalbiin olkaa'uu…",
        "w_no_styles": "Qabxii hin jiru.\nKuusaa filatuu jiraachu — booda deebi'i!",
        "share_phone": "📱 La wadaag Taleefanka",
        "phone_ask": "✅ *Lacag bixiyay!*\n\nXigtaada — xajmaha kuu soo wacaa taleefankaaga loo baahan yahay.\n\nHoos taabo:",
        "phone_invalid": "⚠️ Lambar sax maaha. Hoos taabo ama qor (+251911234567)",
        "phone_thanks": "✅ Waan qaatay!",
    },
    "ti": {
        "welcome": "እንቋዕ ናብ ባርበር ሾፕ ብደሓን መጻእኩም!",
        "choose_lang": "ቋንቋ ምረጽ፡",
        "main_menu": "እንቋዕ ብደሓን! ሎሚ ምን ክሕግዘኩም?",
        "book_btn": "✂️ ዓይነት ምረጽ",
        "info_btn": "📍 ኣብነት ንሰዓት",
        "info": "📍 *ኣብነት:* ኣዳማ\n\n🕒 *ሰዓት:* ሰኑይ-ቀዳም: 9-5\nሕዳር: ይዕገስ\n\n📞 *ተሌፎን:* +251 911 234 567",
        "back": "🔙 ተመለስ",
        "deposit": "💳 *ቅድሚያ:* 50 ብር",
        "remaining": "💶 *ቀሪ:* {amt} ብር",
        "cancel_btn": "❌ ኣይመጽእን (ንምሰርስ)",
        "processing": "⏳ *ክፍያ ኣብነት ኣብ ሂደት…*",
        "pay_failed": "❌ ክፍያ ኣይተሳእን።",
        "book_error": "❌ ምዝገባይ ኣይነባን።",
        "canceled_ok": "✅ ተሰርስዩ።",
        "not_active": "ዘለዎ ኣይኮነን።",
        "admin_on": "ኣድሚን ፈርቂ።",
        "dashboard": "👨‍💻 *ዳሽቦርድ*",
        "open_dash": "👨‍💻 ፈትን",
        "today": "📅 ሎሚ",
        "add_break": "⏸️ ክፍተት ወስኽ",
        "end_break": "▶️ ክፍተት ንምውጻእ",
        "upcoming": "📆 ዝመጽእ",
        "earnings": "💰 ገቢ",
        "no_today": "ሎሚ ምዝገባይ ዘለዎ ኣይኮነን።",
        "no_upcoming": "ዝመጽእ ዘለዎ ኣይኮነን።",
        "end_list": "— መዐቀኒ —",
        "done": "✅ ተዛዚሙ",
        "no_show": "❌ ኣይመጻእን",
        "marked_done": "✅ #{id} ተዛዚሙ።",
        "marked_cancel": "❌ #{id} ተሰርስዩ።",
        "break_start": "ክፍተት ዝጀምር ሰዓት:",
        "break_end": "ዝዛዘም ሰዓት:",
        "break_added": "✅ ክፍተት: {s} → {e}",
        "break_ended": "▶️ ተወስኻ።",
        "pick_period": "ዕለት ምረጽ:",
        "p_today": "ሎሚ",
        "p_week": "እዚ ሰሙን",
        "p_month": "እዚ ወርሂ",
        "earn_title": "📊 *ገቢ ({p})*",
        "earn_total": "💸 ኩሉ: *{a} ብር*",
        "earn_count": "✂️ ቆርጦታት: *{c}*",
        "unauth": "❌ ፈቃድ የለን።",
        "wl_offer": "🎉 *ጽቡቕ ዜና {n}!*\n\n bistu ተኸፊትዩ!\n💈 {s} ({p} ብር)\n📅 {d} ኣብ {t}",
        "wl_yes": "✅ አዎ, ክወስእ!",
        "wl_no": "❌ ኣይመጻእን",
        "wl_ok": "✅ *ተረጋጊጹ!*\n💈 {s}\n📅 {d} ኣብ {t}",
        "wl_out": "ካብ ዝርዝር ተወግደዩ።",
        "wl_expired": "ዘለዎ ኣይኮነን።",
        "wl_taken": "ሰብ ኻልእ ተዛዚሙ!",
        "cust_cancel_note": "ℹ️ ደንበኛ {d} ኣብ {t} ሰርስዩ።",
        "late_ok": "👍 ተፈሪኹ!",
        "late_note": "🏃 *{n}* ይመጻእ እዩ።",
        "late_canceled": "✅ ተሰርስዩ።",
        "late_cancel_note": "❌ *{n}* ሰርስዩ።",
        "noshow_note": "⚠️ 'ኣይመጻእን' ተባሂልት።",
        "break_cancel_note": "⚠️ *{n}*, {t} ብክፍተት ተሰርስዩ።",
        "add_style_msg": "📸 ስእሊሊል ስደድ።\n`ስም | ዋጋ | ዝርዝር | ሰዓት`\n\n/cancel ንምሰርስ",
        "style_added": "✅ *ዓይነት ወስእ!*\n💈 {n}\n💰 {p} ብር\n📝 {d}\n⏱️ {t}",
        "style_parse_err": "❌ ኣልተሪየድን።",
        "manage": "🎨 ዓይነታት",
        "add_new": "➕ ሓድሽ",
        "del_style": "🗑️ ሰርስዩ",
        "pick_del": "ንምሰርስ ምረጽ:",
        "style_del_ok": "✅ ተሰርስዩ።",
        "no_styles": "ዓይነት የለን።",
        "cancel_op": "ተሰርስዩ።",
        "paid_tag": "*(ተከፈል)*",
        "late_q": "⏰ *{n}*, ባርበር ይጸልይ።",
        "im_coming": "🏃 እመጻእ!",
        "cant_make": "😭 ኣይክእልን",
        "noti_sent": "መልእኽት ተላእ!",
        "noti_fail": "መልእኽት ኣይተላእን።",
        "w_title": "ዓይነት ምረጽ",
        "w_when": "መቼ ክመጻእ?",
        "w_today": "ሎሚ",
        "w_tomorrow": "ጽባዕ",
        "w_pick_date": "📆 ዕለት ምረጽ",
        "w_select_time": "ሰዓት ምረጽ",
        "w_pay": "50 ብር ቅድሚያ",
        "w_test": "🛠️ ፈተና",
        "w_verifying": "ክፍያ ኣብሂደት…",
        "w_verifying_sub": "ካብ ባንክ ማረጋገጫ ብምጽባይ።",
        "w_no_times": "ሰዓት የለን።",
        "w_loading": "ሰዓታት ብምጽባይ…",
        "w_est": "ሰዓት",
        "w_complete": "ኩሉ ምልክት ኣሊያይ።",
        "w_connecting": "ቻፓ ጋር…",
        "w_net_err": "ናይ ኢንተርነት ችግር።",
        "w_pay_fail": "ክፍያ ኣይተሳእን።",
        "w_testing": "ፈተና ኣብ ሂደት…",
        "w_no_styles": "ዓይነት የለን።\nባርበሩ ኣብ ምዝጋጀት እዩ — ብደሓን ተመልልሱ!",
        "share_phone": "📱 ተሌፎን ኣጋራ",
        "phone_ask": "✅ *ክፍያ ተረጋግጧል!*\n\nዝመሓየስ — ባርበሩ ክንስሕብካ ተሌፈው ይድረግዎ።\n\nታሕቲኡ ጸቕጢ ገይሩ:",
        "phone_invalid": "⚠️ ቑፍሪ ትክክል ኣይኮነን። ጸቕጢ ተጠቐሙ (+251911234567)",
        "phone_thanks": "✅ ተቐብሉ!",
    },
    "so": {
        "welcome": "Ku soo dhawow Xajmaha Koor!",
        "choose_lang": "Dooro luqadda:",
        "main_menu": "Ku soo dhawow! Maanta waxaad rabtaa?",
        "book_btn": "✂️ Dooro Nooca",
        "info_btn": "📍 Xogta Dukaanka",
        "info": "📍 *Meel:* Adama\n\n🕒 *Saacad:* Sat-Mon: 9-5\nSun: Xir\n\n📞 *Tell:* +251 911 234 567",
        "back": "🔙 Ku noqo",
        "deposit": "💳 *Deposita:* 50 ETB",
        "remaining": "💶 *Haraaga:* {amt} ETB",
        "cancel_btn": "❌ Ma imaan karin (Tirtir)",
        "processing": "⏳ *Lacag bixinta…*",
        "pay_failed": "❌ Way fashilantay.",
        "book_error": "❌ Lama helin.",
        "canceled_ok": "✅ Waa la tirtiray.",
        "not_active": "Waa la xiray.",
        "admin_on": "Maamulka waa la furay.",
        "dashboard": "👨‍💻 *Maamulka*",
        "open_dash": "👨‍💻 Fur",
        "today": "📅 Maanta",
        "add_break": "⏸️ Dhamaystir",
        "end_break": "▶️ Dhamaystir Dhammee",
        "upcoming": "📆 Dhammaan",
        "earnings": "💰 Lacag",
        "no_today": "Maanta buug ma jiro.",
        "no_upcoming": "Soo socda ma jiro.",
        "end_list": "— Dhamaad —",
        "done": "✅ Dhamaystiran",
        "no_show": "❌ Ma Imdid",
        "marked_done": "✅ #{id} dhamaystiran.",
        "marked_cancel": "❌ #{id} tirtiran.",
        "break_start": "Saacadda bilaabmista:",
        "break_end": "Saacadda dhammaadka:",
        "break_added": "✅ Dhamaystir: {s} → {e}",
        "break_ended": "▶️ Waa la dhammeeyay.",
        "pick_period": "Waqtiga doorto:",
        "p_today": "Maanta",
        "p_week": "Toddobaadkan",
        "p_month": "Bishaan",
        "earn_title": "📊 *Lacag ({p})*",
        "earn_total": "💸 Wadarta: *{a} ETB*",
        "earn_count": "✂️ Qod: *{c}*",
        "unauth": "❌ Xaq ma leedahay.",
        "wl_yes": "✅ Haa!",
        "wl_no": "❌ Maya",
        "wl_ok": "✅ *La xaqiijiyay!*",
        "wl_out": "Liiska ka saaray.",
        "wl_expired": "Waa la xiray.",
        "wl_taken": "Nin kale qabtay!",
        "cust_cancel_note": "ℹ️ Miig {d} saac {t} tirtiray.",
        "late_ok": "👍 Waan fahmay!",
        "late_canceled": "✅ Tirtiran.",
        "noshow_note": "⚠️ 'Ma imdin' lagu qiyaasay.",
        "add_style_msg": "📸 Sawir dir.\n`Magaca | Qiimaha | Faahfaahin | Waqtiga`\n\n/cancel tirtir",
        "style_added": "✅ *Nooc Cusub!*",
        "style_parse_err": "❌ Khalad.",
        "manage": "🎨 Maamul Noocyada",
        "add_new": "➕ Cusub",
        "del_style": "🗑️ Tirtir",
        "pick_del": "Tirtirto dooro:",
        "style_del_ok": "✅ Waa la tirtiray.",
        "no_styles": "Nooc ma jiro.",
        "cancel_op": "Waa la tirtiray.",
        "paid_tag": "*(La bixiyay)*",
        "late_q": "⏰ *{n}*, xajmahu waa sugan yahay.",
        "im_coming": "🏃 Imaanayaa!",
        "cant_make": "😭 Ma Karin",
        "noti_sent": "La diray!",
        "noti_fail": "Lama dirin.",
        "w_title": "Dooro Nooca",
        "w_when": "Goorta?",
        "w_today": "Maanta",
        "w_tomorrow": "Berri",
        "w_pick_date": "📆 Taariikh",
        "w_select_time": "Saacad Doorto",
        "w_pay": "50 ETB Deposita",
        "w_test": "🛠️ Test",
        "w_verifying": "Lacag bixinta…",
        "w_verifying_sub": "Bankiga sugaya.",
        "w_no_times": "Saacad ma jiro.",
        "w_loading": "Saacad la soo dejinayo…",
        "w_est": "Waqtiga",
        "w_complete": "Dhammaan buuxi.",
        "w_connecting": "Chapa…",
        "w_net_err": "Network error.",
        "w_pay_fail": "Way fashilantay.",
        "w_testing": "Test…",
        "w_no_styles": "Nooc ma jiro.\nDukaanka diyaarinaya — dib u soo laabo!",
        "share_phone": "📱 La wadaag Taleefanka",
        "phone_ask": "✅ *Lacag bixiyay!*\n\nXigtaada — xajmaha kuu soo wacaa taleefankaaga loo baahan yahay.\n\nHoos taabo:",
        "phone_invalid": "⚠️ Lambar sax maaha. Hoos taabo ama qor (+251911234567)",
        "phone_thanks": "✅ Waan qaatay!",
    },
    "aa": {
        "welcome": "Yalli kaa kee faca qorri!",
        "choose_lang": "Qafaraf qussaa:",
        "main_menu": "Yalli! Tani gaa imi?",
        "book_btn": "✂️ Qacca filtoo",
        "info_btn": "📍 Qorri xagaa",
        "info": "📍 *Meel:* Adama\n\n🕒 *Saaca:* San-Sat: 9-5\nSun: Xisaa\n\n📞 *Tell:* +251 911 234 567",
        "back": "🔙 Diggah",
        "deposit": "💳 *Lacag:* 50 ETB",
        "remaining": "💶 *Baaqee:* {amt} ETB",
        "cancel_btn": "❌ Ma imin (Xisii)",
        "processing": "⏳ *Lacag…*",
        "pay_failed": "❌ Rakkisaa.",
        "book_error": "❌ Hin jirin.",
        "canceled_ok": "✅ Ka xisee.",
        "not_active": "Hin jirin.",
        "admin_on": "Maamul firaa.",
        "dashboard": "👨‍💻 *Maamul*",
        "open_dash": "👨‍💻 Fur",
        "today": "📅 Tani",
        "add_break": "⏸️ Qasa",
        "end_break": "▶️ Qasa dambiiq",
        "upcoming": "📆 Kullu",
        "earnings": "💰 Lacag",
        "no_today": "Tani hin jirin.",
        "no_upcoming": "Dambiil hin jirin.",
        "end_list": "— Dhamaad —",
        "done": "✅ Xume",
        "no_show": "❌ Ma imin",
        "marked_done": "✅ #{id} xume.",
        "marked_cancel": "❌ #{id} ka xisee.",
        "break_start": "Qasa bilaab:",
        "break_end": "Qasa dambi:",
        "break_added": "✅ Qasa: {s} → {e}",
        "break_ended": "▶️ Dambiiq.",
        "pick_period": "Waqtiga:",
        "p_today": "Tani",
        "p_week": "Usuk kana",
        "p_month": "Lakat kana",
        "earn_title": "📊 *Lacag ({p})*",
        "earn_total": "💸 Wadartu: *{a} ETB*",
        "earn_count": "✂️ Qod: *{c}*",
        "unauth": "❌ Xaq hin jirin.",
        "wl_yes": "✅ Haa!",
        "wl_no": "❌ Maya",
        "wl_ok": "✅ *Cabee!*",
        "wl_out": "Ka qaad.",
        "wl_expired": "Hin jirin.",
        "wl_taken": "Nabay qabatoo!",
        "cust_cancel_note": "ℹ️ {d} saa {t} ka xisee.",
        "late_ok": "👍 Fahmay!",
        "late_canceled": "✅ Ka xisee.",
        "noshow_note": "⚠️ 'Ma imin'.",
        "add_style_msg": "📸 Suura dir.\n`Magaca | Qiima | Yalla | Saaca`\n\n/cancel xisii",
        "style_added": "✅ *Qacca cusub!*",
        "style_parse_err": "❌ Khalad.",
        "manage": "🎨 Qacca",
        "add_new": "➕ Cusub",
        "del_style": "🗑️ Xisii",
        "pick_del": "Xisa fii:",
        "style_del_ok": "✅ Ka xisee.",
        "no_styles": "Qacca hin jirin.",
        "cancel_op": "Ka xisee.",
        "paid_tag": "*(La bixiyay)*",
        "late_q": "⏰ *{n}*, qorri sugaa.",
        "im_coming": "🏃 Imaanaa!",
        "cant_make": "😭 Ma karin",
        "noti_sent": "Dir!",
        "noti_fail": "Ma dirin.",
        "w_title": "Qacca filtoo",
        "w_when": "Sessiyaa?",
        "w_today": "Tani",
        "w_tomorrow": "Caleel",
        "w_pick_date": "📆 Guyyaa",
        "w_select_time": "Saaca filtoo",
        "w_pay": "50 ETB Lacag",
        "w_test": "🛠️ Test",
        "w_verifying": "Lacag…",
        "w_verifying_sub": "Sugaya.",
        "w_no_times": "Saaca hin jirin.",
        "w_loading": "Saaca…",
        "w_est": "Saaca",
        "w_complete": "Dhammaan buuxi.",
        "w_connecting": "Chapa…",
        "w_net_err": "Dogoggora.",
        "w_pay_fail": "Rakkisaa.",
        "w_testing": "Test…",
        "w_no_styles": "Qacca hin jirin.\nQorri filatuu jiraachu — booda deebi'i!",
        "share_phone": "📱 Tellii wadaag",
        "phone_ask": "✅ *Lacag kee qabte!*\n\nQasaah — qorri kaa sinni tellii barraadnaa.\n\nGita fafaa taqe:",
        "phone_invalid": "⚠️ Lambarri sinna xaq ma leh. Gita taqe ama qor (+251911234567)",
        "phone_thanks": "✅ Qabte!",
    },
}


def tr(key: str, lang: str = "en", **kw) -> str:
    text = L.get(lang, L["en"]).get(key, L["en"].get(key, key))
    try:
        return text.format(**kw) if kw else text
    except (KeyError, ValueError):
        return text


def user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")


# ================================================================
# 3. DATABASE
# ================================================================
def init_db():
    conn = sqlite3.connect("barber_shop.db", timeout=10)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'en')")
    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY, chat_id INTEGER, client_name TEXT, phone TEXT, service TEXT, price REAL,
        appointment_date TEXT, appointment_time TEXT, status TEXT DEFAULT 'booked',
        chapa_tx_ref TEXT UNIQUE, payment_status TEXT DEFAULT 'unpaid', reminded INTEGER DEFAULT 0
    """)
    c.execute("CREATE TABLE IF NOT EXISTS waitlist (
        id INTEGER PRIMARY KEY, appt_date TEXT, appt_time TEXT, chat_id INTEGER, client_name TEXT,
        phone TEXT, service TEXT, price REAL, status TEXT DEFAULT 'waiting'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT, est_time TEXT,
        image_path TEXT, file_id TEXT, is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime')
    """)
    c.execute("""CREATE TABLE IF NOT EXISTS pending_web_data (
        chat_id INTEGER PRIMARY KEY, tx_ref TEXT, image_url TEXT,
        style_name TEXT, style_desc TEXT
    )""")
    conn.commit()
    conn.close()


def db():
    return sqlite3.connect("barber_shop.db", timeout=10)


def save_lang(chat_id: int, lang: str):
    c = db()
    c.cursor().execute("INSERT OR REPLACE INTO users (chat_id, language) VALUES (?, ?)", (chat_id, lang))
    c.commit(); c.close()


def load_lang(chat_id: int) -> str:
    c = db()
    row = c.cursor().execute("SELECT language FROM users WHERE chat_id=?", (chat_id,)).fetchone()
    c.close()
    return row[0] if row else "en"


# ── Appointment helpers ──
def is_time_taken(date_s: str, time_s: str) -> bool:
    c = db()
    r = c.cursor().execute(
        "SELECT 1 FROM appointments WHERE appointment_date=? AND appointment_time=? "
        "AND status IN ('booked','break') AND payment_status IN ('paid','pending')", (date_s, time_s)).fetchone()
    c.close()
    return r is not None


def get_appt(id_: int):
    c = db()
    r = c.cursor().execute(
        "SELECT id, chat_id, client_name, service, appointment_date, appointment_time, status FROM appointments WHERE id=?", (id_,)).fetchone()
    c.close()
    return r


def set_appt_status(id_: int, status: str):
    c = db()
    c.cursor().execute("UPDATE appointments SET status=? WHERE id=?", (status, id_))
    c.commit(); c.close()


def get_appts_by_date(date_s: str):
    c = db()
    r = c.cursor().execute(
        "SELECT id, client_name, phone, service, appointment_time FROM appointments "
        "WHERE appointment_date=? AND status='booked' AND payment_status='paid' ORDER BY appointment_time", (date_s,)).fetchall()
    c.close()
    return r


def get_all_upcoming():
    c = db()
    r = c.cursor().execute(
        "SELECT id, client_name, phone, service, appointment_date, appointment_time "
        "FROM appointments WHERE status='booked' AND payment_status='paid' "
        "ORDER BY appointment_date, appointment_time").fetchall()
    c.close()
    return r


def get_earnings(days: int):
    c = db()
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    tot = c.cursor().execute(
        "SELECT COALESCE(SUM(price),0) FROM appointments WHERE status='completed' "
        "AND payment_status='paid' AND appointment_date>=?", (start,)).fetchone()[0]
    cnt = c.cursor().execute(
        "SELECT COUNT(id) FROM appointments WHERE status='completed' "
        "AND payment_status='paid' AND appointment_date>=?", (start,)).fetchone()[0]
    c.close()
    return tot, cnt


# ── Waitlist helpers ──
def add_waitlist(chat_id, name, phone, service, price, date_s, time_s):
    c = db()
    c.cursor().execute(
        "INSERT INTO waitlist (appt_date,appt_time,chat_id,client_name,phone,service,price) VALUES (?,?,?,?,?,?,?)",
        (date_s, time_s, chat_id, name, phone, service, price))
    c.commit(); c.close()


def next_waitlist(date_s: str, time_s: str):
    c = db()
    r = c.cursor().execute(
        "SELECT id, chat_id, client_name, service, price FROM waitlist "
        "WHERE appt_date=? AND appt_time=? AND status='waiting' ORDER BY id LIMIT 1", (date_s, time_s)).fetchone()
    c.close()
    return r


def set_wl_status(wl_id: int, status: str):
    c = db()
    c.cursor().execute("UPDATE waitlist SET status=? WHERE id=?", (status, wl_id))
    c.commit(); c.close()


def get_wl(wl_id: int):
    c = db()
    r = c.cursor().execute(
        "SELECT appt_date, appt_time, chat_id, client_name, phone, service, price, status FROM waitlist WHERE id=?", (wl_id,)).fetchone()
    c.close()
    return r


# ── Services helpers ──
def get_active_services():
    c = db()
    r = c.cursor().execute(
        "SELECT id, name, price, description, est_time, image_path "
        "FROM services WHERE is_active=1 ORDER BY id").fetchall()
    c.close()
    return r


def add_service(name, price, desc, est_time, image_path):
    c = db()
    c.cursor().execute(
        "INSERT INTO services (name, price, description, est_time, image_path) VALUES (?,?,?,?,?)", (name, price, desc, est_time, image_path))
    c.commit(); c.close()


def delete_service(sid: int):
    c = db()
    row = c.cursor().execute("SELECT image_path FROM services WHERE id=?", (sid,)).fetchone()
    c.cursor().execute("DELETE FROM services WHERE id=?", (sid,))
    c.commit(); c.close()
    if row and row[0]:
        p = UPLOAD_DIR / row[0]
        if p.exists():
            p.unlink()


# ================================================================
# 4. CUSTOMER HANDLERS
# ================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = list(LANGS.keys())
    kb = [
        [InlineKeyboardButton(
            f"{LANGS[keys[i]]['flag']} {LANGS[keys[i]]['label']}",
            callback_data=f"lang_{keys[i]}"),
         InlineKeyboardButton(
            f"{LANGS[keys[i+1]]['flag']} {LANGS[keys[i+1]]['label']}",
            callback_data=f"lang_{keys[i+1]}")]
        for i in range(0, len(keys), 2)
    ]
    await update.message.reply_text(
        "Welcome / እንኳን ወደ ባርበር ሾፕ በደህናን መጡ!\n\n",
        reply_markup=InlineKeyboardMarkup(kb))


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("lang_"):
        lang = q.data.replace("lang_", "")
        context.user_data["lang"] = lang
        save_lang(q.message.chat_id, lang)
        await _show_main_menu(q, lang)
        return

    lang = user_lang(context)

    if q.data == "back_to_main":
        await _show_main_menu(q, lang)
    elif q.data == "menu_info":
        kb = [[InlineKeyboardButton(tr("back", lang), callback_data="back_to_main")]
        await q.edit_message_text(tr("info", lang), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def _show_main_menu(q, lang: str):
    url = f"{WEB_APP_URL}?lang={lang}"
    kb = [
        [InlineKeyboardButton(tr("book_btn", lang), web_app=WebAppInfo(url=url)],
        [InlineKeyboardButton(tr("info_btn", lang), callback_data="menu_info")],
    ]
    await q.edit_message_text(tr("main_menu", lang), reply_markup=InlineKeyboardMarkup(kb))


# ================================================================
# 5. WEB APP DATA — receives sendData() after payment
# ================================================================
async def _send_final_confirmation(update_msg, bot, pending, phone, lang):
    first_name = pending["first_name"]
    svc = pending["svc"]
    price = pending["price"]
    appt_date = pending["appt_date"]
    appt_time = appt_time = pending["appt_time"]
    image_url = pending["image_url"]
    style_desc = pending["style_desc"]
    appt_id = pending["appt_id"]

    c = db()
    c.cursor().execute("UPDATE appointments SET phone=? WHERE id=?", (phone, appt_id))
    c.cursor().execute("DELETE FROM pending_web_data WHERE chat_id=?", (pending["chat_id"],))
    c.commit()
    c.close()

    d_obj = datetime.strptime(appt_date, "%Y-%m-%d")
    t_obj = datetime.strptime(appt_time, "%H:%M")

    text = (
        f"✅ *Booking Confirmed, {first_name}!*\n\n"
        f"💳 *Deposit Paid:* 50 ETB via Chapa\n"
        f"💶 *Remaining:* {price - 50} ETB (Pay at shop)\n"
        f"💈 *Service:* {svc}\n"
    )
    if style_desc:
        text += f"📝 *Description:* {style_desc}\n"
    text += (
        f"📞 *Phone:* {phone}\n"
        f"\n📅 *When:* {d_obj.strftime('%a, %b %d')} at {t_obj.strftime('%I:%M %p')}\n\n"
        f"We will see you at the shop!"
    )

    kb = [[InlineKeyboardButton(tr("cancel_btn", lang), callback_data=f"cust_cancel_{appt_id}")]]

    if image_url:
        try:
            await update_msg.reply_photo(photo=image_url, caption=text,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            await update_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    try:
        await bot.send_message(BARBER_ID,
            f"✅ *New Booking*\n\n"
            f"👤 *Customer:* {first_name}\n"
            f"💈 *Service:* {svc}\n"
            f"💰 *Price:* {price} ETB\n"
            f"📅 *When:* {d_obj.strftime('%a, %b %d')} at {t_obj.strftime('%I:%M %p')}\n"
            f"📞 *Phone:* {phone}",
            parse_mode="Markdown")
    except Exception:
        pass


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = load_lang(chat_id)
    context.user_data["lang"] = lang

    c = db()
    already = c.cursor().execute("SELECT 1 FROM pending_web_data WHERE chat_id=?", (chat_id,)).fetchone()
    if already:
        c.close()
        return

    try:
        raw = update.message.web_app_data.data
        if not raw:
            await update.message.reply_text("No data received.")
            c.close()
            return

        data = json.loads(raw)
        tx_ref = data.get("tx_ref")
        image_url = data.get("image_url")
        style_name = data.get("style_name")
        style_desc = data.get("style_desc")
        first_name = update.effective_user.first_name

        row = c.cursor().execute(
            "SELECT payment_status, service, price, appointment_date, appointment_time, id "
            "FROM appointments WHERE chapa_tx_ref=?", (tx_ref,)).fetchone()

        if not row:
            await update.message.reply_text(tr("book_error", lang))
            c.close()
            return

        if row[0] != "paid":
            await update.message.reply_text(tr("pay_failed", lang))
            c.close()
            return

        svc = style_name or row[1]
        appt_id = row[5]

        c.cursor().execute("UPDATE appointments SET client_name=? WHERE id=?", (first_name, appt_id))
        c.cursor().execute(
            "INSERT OR REPLACE INTO pending_web_data "
            "(chat_id, tx_ref, image_url, style_name, style_desc) VALUES (?,?,?,?,?)",
            (chat_id, tx_ref, image_url, style_name, style_desc))

        phone_row = c.cursor().execute(
            "SELECT phone FROM appointments WHERE chat_id=? AND phone IS NOT NULL "
            "AND phone NOT IN ('N/A','Via WebApp') ORDER BY id DESC LIMIT 1", (chat_id,)).fetchone()
        known_phone = phone_row[0] if phone_row else None
        c.commit()
        c.close()

        pending_data = {
            "chat_id": chat_id, "first_name": first_name, "appt_id": appt_id,
            "svc": svc, "price": row[2], "appt_date": row[3], "appt_time": row[4],
            "image_url": image_url, "style_desc": style_desc,
        }

        if known_phone:
            await _send_final_confirmation(update.message, context.bot, pending_data, known_phone, lang)
        else:
            context.user_data["pending_confirmation"] = pending_data
            kb = [[KeyboardButton(tr("share_phone", lang), request_contact=True)]
            await update.message.reply_text(
                tr("phone_ask", lang),
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
                parse_mode="Markdown")

    except Exception as e:
        print(f"[WebApp] ERROR: {e}")
        try:
            await update.message.reply_text("Something went wrong. Please /start again.")
        except:
            pass


async def handle_phone_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending = context.user_data.get("pending_confirmation")

    if not pending:
        chat_id = update.effective_chat.id
        c = db()
        row = c.cursor().execute(
            "SELECT tx_ref, image_url, style_name, style_desc FROM pending_web_data WHERE chat_id=?", (chat_id,)).fetchone()
        if not row:
            c.close()
            return
        tx_ref_db = row[0]
        c.cursor().execute("DELETE FROM pending_web_data WHERE chat_id=?", (chat_id,))
        appt = c.cursor().execute(
            "SELECT id, client_name, service, price, appointment_date, appointment_time FROM appointments WHERE chapa_tx_ref=?", (tx_ref_db,)).fetchone()
        c.close()
        if not appt:
            return
        pending = {
            "chat_id": chat_id, "first_name": update.effective_user.first_name,
            "appt_id": appt[0], "svc": appt[2], "price": appt[3],
            "appt_date": appt[4], "appt_time": appt[5],
            "image_url": row[1], "style_desc": row[3],
        }

    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text:
        text = update.message.text.strip().replace(" ", "")
        if not re.match(r'^\+?\d{8,15}$', text):
            await update.message.reply_text(tr("phone_invalid", user_lang(context)))
            return
        phone = text
    else:
        return

    lang = user_lang(context)
    try:
        await update.message.reply_text(tr("phone_thanks", lang), reply_markup=ReplyKeyboardRemove())
    except:
        pass

    await _send_final_confirmation(update.message, context.bot, pending, phone, lang)
    context.user_data.pop("pending_confirmation", None)


# ================================================================
# 6. CUSTOMER CANCEL & WAITLIST
# ================================================================
async def cust_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = user_lang(context)
    aid = int(q.data.split("_")[2])
    appt = get_appt(aid)
    if not appt or appt[5] != "booked":
        await q.edit_message_text(tr("not_active", lang))
        return

    name = appt[2]
    svc = appt[3]
    appt_date = appt[4]
    appt_time = appt[5]

    d_obj = datetime.strptime(appt_date, "%Y-%m-%d")
    t_obj = datetime.strptime(appt_time, "%H:%M")

    set_appt_status(aid, "cancelled")

    try:
        await q.message.delete()
    except:
        pass

    await update.effective_chat.send_message(
        f"✅ *Booking Canceled*\n\n"
        f"💈 *Service:* {svc}\n"
        f"📅 *Was:* {d_obj.strftime('%a, %b %d')} at {t_obj.strftime('%I:%M %p')}\n\n"
        f"You can always book again from the menu!",
        parse_mode="Markdown")

    await context.bot.send_message(BARBER_ID,
        f"❌ *Booking Canceled*\n\n"
        f"👤 *Customer:* {name}\n"
        f"💈 *Service:* {svc}\n"
        f"📅 *Was:* {d_obj.strftime('%a, %b %d')} at {t_obj.strftime('%I:%M %p')}",
        parse_mode="Markdown")
    await _offer_waitlist(context, appt_date, appt_time)


async def _offer_waitlist(ctx: ContextTypes.DEFAULT_TYPE, d: str, t: str):
    wl = next_waitlist(d, t)
    if not wl:
        return
    wl_id, cid, name, svc, price = wl
    set_wl_status(wl_id, "offered")

    d_obj = datetime.strptime(d, "%Y-%m-%d")
    t_obj = datetime.strptime(t, "%H:%M")
    lang = load_lang(cid)
    kb = [
        [InlineKeyboardButton(tr("wl_yes", lang), callback_data=f"wl_accept_{wl_id}"),
         InlineKeyboardButton(tr("wl_no", lang), callback_data=f"wl_reject_{wl_id}")]
    ]
    try:
        await ctx.bot.send_message(cid, tr("wl_offer", lang,
            n=name, s=svc, p=price, d=d_obj.strftime("%a, %b %d"), t=t_obj.strftime("%I:%M %p")),
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception:
        set_wl_status(wl_id, "rejected")
        await _offer_waitlist(ctx, d, t)


async def wl_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = user_lang(context)
    wl_id = int(q.data.split("_")[2])
    wl = get_wl(wl_id)
    if not wl or wl[7] != "offered":
        await q.edit_message_text(tr("wl_expired", lang))
        return

    d, t, cid, name, phone, svc, price, _ = wl
    if q.data.startswith("wl_accept_"):
        if is_time_taken(d, t):
            await q.edit_message_text(tr("wl_taken", lang))
            set_wl_status(wl_id, "rejected")
            await _offer_waitlist(context, d, t)
            return
        c = db()
        c.cursor().execute(
            "INSERT INTO appointments (chat_id, client_name, phone, service, price, "
            "appointment_date, appointment_time, status, payment_status) "
            "VALUES (?,?,?,? ,?,?,?,?,'booked','paid')",
            (cid, name, phone, svc, price, d, t))
        c.commit()
        c.close()
        set_wl_status(wl_id, "converted")
        d_obj = datetime.strptime(d, "%Y-%m-%d")
        t_obj = datetime.strptime(t, "%H:%M")
        await q.edit_message_text(tr("wl_ok", lang,
            s=svc, d=d_obj.strftime("%a, %b %d"), t=t_obj.strftime("%I:%M %p")), parse_mode="Markdown")
    else:
        set_wl_status(wl_id, "rejected")
        await q.edit_message_text(tr("wl_out", lang))
        await _offer_waitlist(context, d, t)


async def late_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = user_lang(context)
    aid = int(q.data.split("_")[3])
    appt = get_appt(aid)
    if not appt:
        return
    name, d, t = appt[2], appt[4], appt[5]

    if q.data.startswith("cust_late_coming_"):
        await q.edit_message_text(tr("late_ok", lang))
        await context.bot.send_message(BARBER_ID, tr("late_note", "en", n=name))
    elif q.data.startswith("cust_late_cancel_"):
        set_appt_status(aid, "cancelled")
        await q.edit_message_text(tr("late_canceled", lang))
        await context.bot.send_message(BARBER_ID, tr("late_cancel_note", "en", n=name))


# ================================================================
# 7. ADMIN HANDLERS
# ================================================================
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BARBER_ID:
        await update.message.reply_text(tr("unauth", "en"))
        return
    kb = [[InlineKeyboardButton(tr("open_dash", "en")]]
    await update.message.reply_text(tr("admin_on", "en"), reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))


async def open_dashboard_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == BARBER_ID and update.message.text == tr("open_dash", "en"):
        kb = [
            [InlineKeyboardButton(tr("📅 Today's Schedule", callback_data="adm_today")],
            [InlineKeyboardButton("⏸️ Add Break", callback_data="adm_add_break"),
            [InlineKeyboardButton("▶️ End Break Early", callback_data="adm_end_break")],
            [InlineKeyboardButton("📆 All Upcoming", callback_data="adm_all")],
            [InlineKeyboardButton("💰 View Earnings", callback_data="adm_earn")],
            [InlineKeyboardButton("🎨 Manage Styles", callback_data="adm_styles")],
        ]
        await update.message.reply_text(tr("dashboard", "en"), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "adm_today":
        today = datetime.now().strftime("%Y-%m-%d")
        appts = get_appts_by_date(today)
        await q.delete_message()
        if not appts:
            await context.bot.send_message(q.message.chat_id, tr("no_today", "en"))
            return
        for i, a in enumerate(appts, 1):
            aid, name, phone, svc, time_s = a
            t_obj = datetime.strptime(time_s, "%H:%M")
            txt = (f"*{i}. {t_obj.strftime('%I:%M %p')}*\n👤 {name} | 📞 {phone}\n💈 {svc}\n*(Paid via Chapa)*"
            kb = [
                [InlineKeyboardButton("✅ Done", callback_data=f"adm_done_{aid}"),
                 InlineKeyboardButton("❌ No Show", callback_data=f"adm_noshow_{aid}")]
            await context.bot.send_message(q.message.chat_id, txt,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

        await context.bot.send_message(q.message.chat_id, tr("end_list", "en"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr("🔙 Back", callback_data="adm_back")]))

    elif d == "adm_all":
        appts = get_all_upcoming()
        await q.delete_message()
        if not appts:
            await context.bot.send_message(q.message.chat_id, tr("no_upcoming", "en"))
            return
        for i, a in enumerate(appts, 1):
            aid, name, phone, svc, date_s, time_s = a
            d_obj = datetime.strptime(date_s, "%Y-%m-%d")
            t_obj = datetime.strptime(time_s, "%H:%M")
            txt = f"*{i}. {d_obj.strftime('%b %d')} at {t_obj.strftime('%I:%M %p')}\n👤 {name} | 📞 {phone}\n💈 {svc}"
            kb = [
                [InlineKeyboardButton("✅ Done", callback_data=f"adm_done_{aid}"),
                 InlineKeyboardButton("❌ No Show", callback_data=f"adm_noshow_{aid}")]
            await context.bot.send_message(q.message.chat_id, txt,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        await context.bot.send_message(q.message.chat_id, tr("end_list", "en"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr("🔙 Back", callback_data="adm_back")]]))

    elif d == "adm_done":
        aid = int(d.split("_")[2])
        set_appt_status(aid, "completed")
        await q.edit_message_text(tr("marked_done", "en", id=aid))

    elif d == "adm_noshow":
        aid = int(d.split("_")[2])
        appt = get_appt(aid)
        if appt:
            set_appt_status(aid, "cancelled")
            try:
                await context.bot.send_message(appt[1], tr("noshow_note", "en"))
            except:
                pass
        await q.edit_message_text(tr("marked_cancel", "en", id=aid))

    elif d == "adm_late_":
        aid = int(d.split("_")[2])
        appt = get_appt(aid)
        if appt:
            cid, name = appt[1], name = appt[2]
            kb = [
                [InlineKeyboardButton(tr("im_coming", "en"), callback_data=f"cust_late_coming_{aid}"),
                 InlineKeyboardButton(tr("cant_make", "en"), callback_data=f"cust_late_cancel_{aid}")]
            try:
                await context.bot.send_message(cid,
                    tr("late_q", "en", n=name), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                await q.answer("Notification sent!", show_alert=True)
            except:
                await q.answer("Failed to message.", show_alert=True)

    elif d == "adm_add_break":
        kb = [
            [InlineKeyboardButton(datetime.strptime(t, "%H:%M").strftime("%I:%M %p"),
             callback_data=f"brk_s_{t}") for t in WORKING_HOURS]
        kb.append([InlineKeyboardButton(tr("🔙 Back", callback_data="adm_add_break")])
        await q.edit_message_text(tr("break_start", "en"), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("brk_s_"):
        context.user_data["brk_start"] = d.replace("brk_s_", "")
        await q.edit_message_text(tr("break_end", "en"))
        await q.answer()

    elif d.startswith("brk_e_"):
        end_time = d.replace("brk_e_", "")
        start_time = context.user_data.get("brk_start")
        if not start_time:
            await q.answer("No start time selected.", show_alert=True)
            return
        today = datetime.now().strftime("%Y-%m-%d")
        times_in_break = [t for t in WORKING_HOURS if start_time <= t < end_time]
        c = db()
        for t in times_in_break:
            existing = c.cursor().execute(
                "SELECT id, chat_id, client_name FROM appointments "
                "WHERE appointment_date=? AND appointment_time=? AND status='booked' AND payment_status='paid'", (today, t)).fetchone()
            if existing:
                aid, cid, cname = existing
                c.cursor().execute("UPDATE appointments SET status='cancelled' WHERE id=?", (aid,))
                try:
                    await context.bot.send_message(cid,
                        tr("break_cancel_note", "am", n=cname, t=t))
                except:
                    pass
            c.cursor().execute(
                "INSERT INTO appointments (chat_id, client_name, phone, service, price, "
                "appointment_date, appointment_time, status, payment_status) "
                "VALUES (0, 'BREAK', 'N/A', 'Break', 0, ?, ?, 'booked', 'na')", (today, t))
        c.commit(); c.close()
        await q.edit_message_text(tr("break_added", "en", s=start_time, e=end_time))

    elif d == "adm_end_break":
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%H:%M")
        c = db()
        c.cursor().execute(
            "DELETE FROM appointments WHERE appointment_date=? AND appointment_time>=? AND status='break'", (today, now))
        c.commit(); c.close()
        await q.edit_message_text(tr("break_ended", "en"))

    elif d == "adm_styles":
        kb = [
            [InlineKeyboardButton(tr("add_new", "en"), callback_data="adm_add_style")],
            [InlineKeyboardButton(tr("del_style", "en"), callback_data="adm_del_style")],
            [InlineKeyboardButton(tr("🔙 Back", "en"), callback_data="adm_back")]
        await q.edit_message_text("🎨 *Style Management*", reply_markup=InlineKeyboardMarkup(kb))

    elif d == "adm_del_style":
        services = get_active_services()
        if not services:
            await q.edit_message_text(tr("no_styles", "en"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr("🔙 Back", "en", callback_data="adm_styles")]]))
            return
        kb = [
            [InlineKeyboardButton(f"🗑️ {s[1]} ({s[2]} ETB)", callback_data=f"del_style_{s[0]}")]
            for s in services]
        kb.append([InlineKeyboardButton(tr("🔙 Back", "en", callback_data="adm_styles")])
        await q.edit_message_text(tr("pick_del", "en"), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("del_style_"):
        sid = int(d.split("_")[2])
        delete_service(sid)
        await q.edit_message_text(tr("style_del_ok", "en"))
        await q.answer("Deleted!", show_alert=True)

    elif d == "adm_back":
        kb = [
            [InlineKeyboardButton(tr("📅 Today's Schedule", callback_data="adm_today")],
            [InlineKeyboardButton("⏸️ Add Break", callback_data="adm_add_break"),
            [InlineKeyboardButton("▶️ End Break Early", callback_data="adm_end_break")],
            [InlineKeyboardButton("📆 All Upcoming", callback_data="adm_all")],
            [InlineKeyboardButton("💰 View Earnings", callback_data="adm_earn")],
            [InlineKeyboardButton("🎨 Manage Styles", callback_data="adm_styles")],
        ]
        await q.edit_message_text("👨‍💻 *Admin Dashboard*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "earn_":
        kb = [
            [InlineKeyboardButton(tr("p_today", "en"), callback_data="earn_0"),
             InlineKeyboardButton(tr("p_week", "en"), callback_data="earn_7")],
            [InlineKeyboardButton(tr("p_month", "en"), callback_data="earn_30")],
            [InlineKeyboardButton(tr("🔙 Back", "en"), callback_data="adm_earn")],
        ]
        await q.edit_message_text(tr("pick_period", "en"), reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("earn_"):
        days = int(d.split("_")[1])
        total, count = get_earnings(days)
        per = tr("p_today" if days == 0 else tr("p_week" if days == 7 else tr("p_month", "en", days=days))
        await q.edit_message_text(
            tr("earn_title", "en", p=per),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr("🔙 Back", "en", callback_data="adm_earn")]]),
            ], parse_mode="Markdown"
        )


# ================================================================
# 8. 30-MIN REMINDER JOB
# ================================================================
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    target = now + timedelta(minutes=30)
    target_time = target.strftime("%H:%M")
    target_date = target.strftime("%Y-%m-%d")

    conn = db()
    rows = conn.cursor().execute(
        "SELECT id, chat_id, client_name, service, appointment_time "
        "FROM appointments WHERE appointment_date=? AND appointment_time=? "
        "AND status='booked' AND payment_status='paid' AND reminded=0", 
    ).fetchall()
    conn.close()

    for row in rows:
        appt_id, chat_id, name, svc, time_str = row
        t_obj = datetime.strptime(time_str, "%H:%M")
        lang = load_lang(chat_id)
        try:
            await context.bot.send_message(chat_id,
                f"⏰ *Reminder, {name}!*\n\n"
                f"Your appointment is in 30 minutes!\n\n"
                f"💈 *Service:* {svc}\n"
                f"📅 *Time:* {t_obj.strftime('%I:%M %p')}\n\n"
                f"Please head to the shop now!"
            )
            conn2 = db()
            conn2.cursor().execute("UPDATE appointments SET reminded=1 WHERE id=?", (appt_id,))
            conn2.commit()
            conn2.close()
        except Exception:
            pass


# ================================================================
# 9. MAIN — SINGLE ENTRY POINT
# ================================================================
def run_flask():
    from chapa_server import app as flask_app
    port = int(os.getenv("PORT", "5000"))
    print(f"🌐 Flask starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


def main():
    if not TOKEN:
        print("❌ BOT_TOKEN not set"); return

    init_db()

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    from telegram.request import HTTPXRequest
    req = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0)
    app = Application.builder().token(TOKEN).request(req).build()

    style_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_style_entry, pattern="^adm_add_style$")],
        states={ADD_STYLE_PHOTO: [
            MessageHandler(filters.PHOTO, add_style_photo),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_style_wrong),
        ]},
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        per_chat=True, per_message=False,
    )

    app.add_handler(style_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.add_handler(CallbackQueryHandler(wl_response, pattern=r"^wl_(accept|reject)_"))
    app.add_handler(CallbackQueryHandler(cust_cancel, pattern=r"^cust_cancel_"))
    app.add_handler(CallbackQueryHandler(late_response, pattern=r"^cust_late_"))
    app.add_handler(CallbackQueryHandler(admin_act, pattern=r"^(adm_|earn_|brk_|del_style_)"))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern=r"^(lang_|menu_|back_to_main)"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_phone_share))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, open_dashboard_text))

    print("💈 Barber bot running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
