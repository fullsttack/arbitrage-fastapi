پیش‌گفتار
سندی که پیش روی شماست، راهنمایی‌ست برای معامله‌گرهای حرفه‌ای تا با استفاده از APIهای فراهم‌شده، بیشترین بهره را از حساب کاربری والکس خود ببرند. این راهنما مستندی رسمی‌ست و متناسب با آخرین تغییرات APIهای والکس بروز می‌شود.

پیش‌نیازها
تمام اندپوینت‌هایی که در ادامه به آنها پرداخته شده، تنها از طریق نشانی https://api.wallex.ir دردسترس‌اند.
خروجی تمام اندپوینت‌ها در قالب JSON به فراخوان ارائه خواهند شد.
اندپوینت‌های مرتبط با دریافت/ارسال اطلاعات شخصی توسط کلیدهای API محافظت شده‌اند.
انواع داده
عدد (number) مانند 3.75
رشته (string) مانند "BTC"
عددرشته (number string) مانند "3.000001"
جهت تراکشن (direction) شامل دو مقدار "BUY" و "SELL"
تاریخ و زمان (datetime) با قالب ISO-8601
تایم‌استمپ (timestamp) با قالب Unix Time
بولی (boolean) شامل دو مقدار true و false
شیوهٔ ارسال درخواست
برای درخواست‌های GET باید پارامترهای مورد نیاز در بخش کوئری URL ارسال شود.
برای درخواست‌های PUT و POST و PATCH پارامترها را می‌توان در بخش کوئری یا در بخش بدنهٔ درخواست ارسال کرد. همچنین هدر Content-Type باید متناسب با قالب اطلاعات ارسالی، برابر با x-www-form-urlencoded یا application/json، تنظیم گردد.
 اندپوینت‌های ارائه شده توسط والکس محدودیت فراخوانی ۱۰۰ درخواست در ثانیه دارند. مگر جایی که محدودیت دیگری تصریح شده باشد.
ساخت و مدیریت کلیدهای API
برای ساخت و مدیریت کلیدهای API کاربران باید به بخش مدیریت API سایت والکس مراجعه کرده؛ و برای ساخت کلید جدید کافیست بر روی دکمهٔ «ساخت API» کلیک کنند.

مدیریت API والکس

در بخش ساخت API، لازم است که برای کلید جدید نامی منحصربه‌فرد و دلخواه انتخاب کنید. زمان اعتبار هر کلید جدید حداکثر تا ۹۰ روز قابل انتخاب است و قابل تمدید نیست. بعد از گذشت زمان اعتبار، کلید به صورت خودکار منقضی خواهد شد و نیاز است تا کلید جدیدی ایجاد شود.

 در حال حاضر ساختن بیش از ۳ کلید API در هر حساب کاربری ممکن نیست.
برای امنیت بیشتر در انتخاب مجوزهای دسترسی دقت کافی داشته و در صورت امکان فهرستی از IPهای مجاز که با استفاده از کلید می‌توانند به اندپوینت‌های شخصی دسترسی داشته باشند، وارد کنید. بدیهی‌ست که خالی گذاشتن لیست IPهای مجاز به معنای اعطای مجوز به تمام IPهاست.

 برای کلیدهایی که مجوز «برداشت» دارند، وارد کردن لیست IPهای مجاز اجباری‌ست.
 در حفاظت از کلیدهای API خود دقت کافی داشته و آن را با دیگران به اشتراک نگذارید. اگر به طور ناخواسته دیگران به کلید API شما دسترسی یافتند، از طریق سایت والکس اقدام به حذف کلید افشاشده و ساخت کلید جدید کنید.
استفاده از کلید API
برای درخواست‌های HTTP کلید API را در هدر X-API-Key قرار دهید:

curl 'https://api.wallex.ir/...' -H 'X-API-Key: <api-key>'
برای ارسال درخواست به اندپوینت‌های محافظت‌شده کافی‌ست یک هدر X-API-Key به درخواست HTTP افزوده، و مقدار آن را برابر با کلیدی که در بخش قبل ایجاد کرده‌اید، قرار دهید.

بازارها
لیست بازارها
curl 'https://api.wallex.ir/v1/markets'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "symbols": {
      "BTCUSDT": {
        "symbol": "BTCUSDT",
        "baseAsset": "BTC",
        "baseAssetPrecision": 8,
        "quoteAsset": "USDT",
        "quotePrecision": 8,
        "faName": "بیت کوین - تتر",
        "faBaseAsset": "بیت کوین",
        "faQuoteAsset": "تتر",
        "stepSize": 6,
        "tickSize": 2,
        "minQty": 1e-06,
        "minNotional": 10,
        "stats": {
          "bidPrice": "20900.0000000000000000",
          "askPrice": "21097.7400000000000000",
          "24h_ch": -0.04,
          "7d_ch": -29.87,
          "24h_volume": "1.9666210000000000",
          "7d_volume": "25.4612910000000000",
          "24h_quoteVolume": "41471.0065635500000000",
          "24h_highPrice": "22888.0000000000000000",
          "24h_lowPrice": "20349.0000000000000000",
          "lastPrice": "20991.4300000000000000",
          "lastQty": "20991.4300000000000000",
          "lastTradeSide": "BUY",
          "bidVolume": "14.8397900000000000",
          "askVolume": "7.1529210000000000",
          "bidCount": 124,
          "askCount": 349,
          "direction": {
            "SELL": 51,
            "BUY": 49
          }
        },
        "createdAt": "2020-04-01T00:00:00.000000Z"
      },
      ...
    }
  }
}
با درخواست زیر می‌توانید لیستی از بازارها و وضعیت آنها دریافت کنید:

GET https://api.wallex.ir/v1/markets

خروجی
خروجی این درخواست شامل نگاشتی از بازارهاست و هر بازار شامل اطلاعاتی به شرح زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
baseAsset	رشته	ارز پایه
baseAssetPrecision	عدد	تعداد اعشار ارز پایه
quoteAsset	رشته	ارز تجاری
quoteAssetPrecision	عدد	تعداد اعشار ارز تجاری
faName	رشته	نام فارسی بازار
faBaseAsset	رشته	نام فارسی ارز پایه
faQuoteAsset	رشته	نام فارسی ارز تجاری
stepSize	عدد	تعداد اعشار افزایش/کاهش حجم تراکنش
tickSize	عدد	تعداد اعشار افزایش/کاهش مبلغ تراکنش
minQty	عدد	حداقل حجم تراکنش
maxQty	عدد	حداکثر حجم تراکنش
minNotional	عدد	حداقل مبلغ تراکنش
stats	متغیر	اطلاعات آماری بازار
همچنین آمارهای هر بازار شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
bidPrice	عددرشته	بیشترین قیمت سفارش‌های خرید
bidVolume	عددرشته	مجموع حجم سفارش‌های خرید
bidCount	عدد	تعداد سفارش‌های خرید
askPrice	عددرشته	کمترین قیمت سفارش‌های فروش
askVolume	عددرشته	مجموع حجم سفارش‌های فروش
askCount	عدد	تعداد سفارش‌های فروش
24h_ch	عدد	درصد تغییرات قیمت در ۲۴ ساعت گذشته
24h_volume	عددرشته	حجم تراکنش‌ها در ۲۴ ساعت گذشته
24h_quoteVolume	عددرشته	مبلغ تراکنش‌ها در ۲۴ ساعت گذشته
24h_highPrice	عددرشته	بیشترین قیمت در ۲۴ ساعت گذشته
24h_lowPrice	عددرشته	کمترین قیمت در ۲۴ ساعت گذشته
7d_ch	عدد	درصد تغییرات قیمت در ۷ روز گذشته
7d_volume	عددرشته	حجم تراکنش‌ها در ۷ روز گذشته
lastPrice	عددرشته	آخرین قیمت تراکنش
lastQty	عددرشته	آخرین حجم تراکنش
lastTradeSide	جهت	جهت آخرین تراکنش
direction.BUY	عدد	درصد سفارش‌های خرید به کل سفارش‌ها
direction.SELL	عدد	درصد سفارش‌های فروش به کل سفارش‌ها
آمار جهانی رمزارزها
curl 'https://api.wallex.ir/v1/currencies/stats'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    {
      "key": "BTC",
      "name": "بیت کوین",
      "name_en": "BITCOIN",
      "rank": 1,
      "dominance": 40.012750289139,
      "volume_24h": 34963217199.777,
      "market_cap": 801033354010.49,
      "ath": 69045,
      "ath_change_percentage": -46.00463,
      "ath_date": "2021-11-10T14:24:11Z",
      "price": 37276,
      "daily_high_price": 38300,
      "daily_low_price": 36832,
      "weekly_high_price": 38232.178732177,
      "weekly_low_price": 36774.00714224,
      "percent_change_1h": 0.2238585,
      "percent_change_24h": -1.92522,
      "percent_change_7d": 2.67127,
      "percent_change_14d": -13.55187,
      "percent_change_30d": -19.52389,
      "percent_change_60d": -34.79681,
      "percent_change_200d": 13.37576,
      "percent_change_1y": 8.99642,
      "price_change_24h": -956.17873217708,
      "price_change_7d": 969.5905595353,
      "price_change_14d": -5843.7921430803,
      "price_change_30d": -9043.6510880525,
      "price_change_60d": -19893.371993811,
      "price_change_200d": 4397.4981264285,
      "price_change_1y": 3076.480189637,
      "max_supply": 21000000,
      "total_supply": 18928912,
      "circulating_supply": 18928912,
      "created_at": "2022-01-09T04:25:16Z",
      "updated_at": "2022-01-31T10:10:29Z"
    },
    ...
  ]
}
با این درخواست می‌توانید آخرین آمار جهانی رمزارزها را دریافت کنید:

GET https://api.wallex.ir/v1/currencies/stats

خروجی
خروجی این درخواست فهرستی از آمار جهانی رمزارزهاست و هر آمار شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
key	رشته	کد رمزارز
name	رشته	نام فارسی رمزارز
name_en	رشته	نام انگلیسی رمزارز
rank	عدد	رتبه رمزارز در بازار
dominance	عدد	درصد تسلط رمزارز
volume_24h	عدد	حجم تراکنش‌ها در ۲۴ ساعت گذشته
market_cap	عدد	ارزش سرمایهٔ موجود در بازار
ath	عدد	بالاترین قیمت ثبت شده
ath_change_percentage	عدد	درصد تغییر نسبت به بالاترین قیمت ثبت شده
ath_date	رشته	تاریخ ثبت بالاترین قیمت
price	عدد	قیمت رمزارز در حال حاضر
daily_high_price	عدد	بالاترین قیمت در ۲۴ ساعت گذشته
daily_low_price	عدد	پایین‌ترین قیمت در ۲۴ ساعت گذشته
weekly_high_price	عدد	بالاترین قیمت در ۷ روز گذشته
weekly_low_price	عدد	قیمت پایین‌ترین در ۷ روز گذشته
percent_change_1h	عدد	درصد تغییر قیمت در یگ ساعت گذشته
percent_change_24h	عدد	درصد تغییر قیمت در ۲۴ ساعت گذشته
percent_change_7d	عدد	درصد تغییر قیمت در ۷ روز گذشته
percent_change_14d	عدد	درصد تغییر قیمت در ۱۴ روز گذشته
percent_change_30d	عدد	درصد تغییر قیمت در ۳۰ روز گذشته
percent_change_60d	عدد	درصد تغییر قیمت در ۶۰ روز گذشته
percent_change_200d	عدد	درصد تغییر قیمت در ۲۰۰ روز گذشته
percent_change_1y	عدد	درصد تغییر قیمت در یک سال گذشته
price_change_24h	عدد	تغییر قیمت در ۲۴ ساعت گذشته
price_change_7d	عدد	تغییر قیمت در ۷ روز گذشته
price_change_14d	عدد	تغییر قیمت در ۱۴ روز گذشته
price_change_30d	عدد	تغییر قیمت در ۳۰ روز گذشته
price_change_60d	عدد	تغییر قیمت در ۶۰ روز گذشته
price_change_200d	عدد	تغییر قیمت در ۲۰۰ روز گذشته
price_change_1y	عدد	تغییر قیمت در یک سال گذشته
max_supply	عدد	حداکثر حجم رمزارزهای ممکن
total_supply	عدد	حجم رمزارزهای موجود
circulating_supply	عدد	حجم رمزارزهای در گردش
لیست سفارش‌های باز
curl 'https://api.wallex.ir/v1/depth?symbol=BTCUSDT'
نمونهٔ خروجی

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "ask": [
      {
        "price": "21300.0000000000000000",
        "quantity": 0.005,
        "sum": "106.5"
      },
      {
        "price": "21400.0000000000000000",
        "quantity": 0.005,
        "sum": "107"
      },
      ...
    ],
    "bid": [
      {
        "price": "21100.0000000000000000",
        "quantity": 1e-06,
        "sum": "0.0211"
      },
      {
        "price": "20889.8100000000000000",
        "quantity": 0.001472,
        "sum": "30.74980032"
      },
      ...
    ]
  }
}
با درخواست زیر می‌توانید لیست سفارش‌های باز (Order Book) هر بازار را دریافت کنید:

‍GET https://api.wallex.ir/v1/depth

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
خروجی
خروجی این درخواست شامل فهرستی از سفارش‌های فروش (ask) و خرید (bid) است که هر کدام شامل اطلاعات زیرند:

پارامتر	نوع	توضیحات
price	عددرشته	قیمت واحد
quantity	عدد	حجم خرید/فروش
sum	عددرشته	مجموع قیمت
لیست سفارش‌های باز تمام بازارها
curl 'https://api.wallex.ir/v1/depth?symbol=BTCUSDT'
نمونهٔ خروجی

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "BTCUSDT": {
      "ask": [
        {
          "price": "21300.0000000000000000",
          "quantity": 0.005,
          "sum": "106.5"
        },
        {
          "price": "21400.0000000000000000",
          "quantity": 0.005,
          "sum": "107"
        },
        ...
      ],
      "bid": [
        {
          "price": "21100.0000000000000000",
          "quantity": 1e-06,
          "sum": "0.0211"
        },
        {
          "price": "20889.8100000000000000",
          "quantity": 0.001472,
          "sum": "30.74980032"
        },
        ...
      ]
    },
    "SHIBUSDT": { ... },
    "USDTTMN": { ... },
    ...
  }
}
با درخواست زیر می‌توانید لیست سفارش‌های باز (Order Book) تمام بازارها را یکجا دریافت کنید:

GET https://api.wallex.ir/v2/depth/all

خروجی
خروجی این درخواست شامل فهرستی از سفارش‌های فروش (ask) و خرید (bid) است.

لیست آخرین معاملات
curl 'https://api.wallex.ir/v1/trades?symbol=BTCUSDT'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "latestTrades": [
      {
        "symbol": "BTCUSDT",
        "quantity": "0.0000010000000000",
        "price": "21100.0000000000000000",
        "sum": "0.0211000000000000",
        "isBuyOrder": true,
        "timestamp": "2022-06-17T11:53:02Z"
      },
      {
        "symbol": "BTCUSDT",
        "quantity": "0.1200620000000000",
        "price": "21100.0000000000000000",
        "sum": "2533.3082000000000000",
        "isBuyOrder": true,
        "timestamp": "2022-06-17T11:50:06Z"
      },
      ...
    ]
  }
}
با درخواست زیر می‌توانید فهرستی از آخرین معاملات بازار والکس را دریافت کنید:

GET https://api.wallex.ir/v1/trades

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
خروجی
خروجی این درخواست شامل فهرستی از آخرین معاملات بازار و هر معامله شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
quantity	عدد	حجم معامله
price	عددرشته	قیمت واحد معامله
sum	عددرشته	مجموع قیمت معامله
timestamp	زمان	زمان ثبت معامله
کندل‌ها (آمار OHLC بازارها)
curl 'https://api.wallex.ir/v1/udf/history?symbol=BTCTMN&resolution=60&from=1654350171&to=1655502171'
نمونهٔ خروجی:

{
  "s": "ok",
  "t": [
    1654351200,
    1654354800,
    ...
  ],
  "c": [
    "948896452.0000000000000000",
    "960015360.0000000000000000",
    ...
  ],
  "o": [
    "950625912.0000000000000000",
    "948896452.0000000000000000",
    ...
  ],
  "h": [
    "954590146.0000000000000000",
    "961381312.0000000000000000",
    ...
  ],
  "l": [
    "948896452.0000000000000000",
    "948896452.0000000000000000",
    ...
  ],
  "v": [
    "0.2314400000000000",
    "0.3148050000000000",
    ...
  ]
}

با این درخواست می‌توانید کندل‌های بازارهای والکس را در بازهٔ زمانی مشخص دریافت کنید:

GET https://api.wallex.ir/v1/udf/history

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
resolution	رشته	بله	دقت در تعیین بازهٔ زمانی کندل‌ها
from	تایم‌استمپ	بله	زمان شروع بازهٔ زمانی کندل‌ها
to	تایم‌استمپ	بله	زمان پایان بازهٔ زمانی کندل‌ها
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
 مقادیر مجاز برای دقت در تعیین بازهٔ زمانی کندل‌ها برابرند با:
1 برای کندل‌های دقیقه‌ای
60 برای کندل‌های ساعتی
180 برای کندل‌های ۳ ساعته
360 برای کندل‌های ۶ ساعته
720 برای کندل‌های ۱۲ ساعته
1D برای کندل‌های روزانه
خروجی
خروجی این درخواست شامل فهرستی از کندل‌ها بازار شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
t	تایم‌استمپ	زمان شروع کندل‌ها
o	عددرشته	اولین قیمت کندل‌ها
h	عددرشته	بالاترین قیمت کندل‌ها
l	عددرشته	پایین‌ترین قیمت کندل‌ها
c	عددرشته	آخرین قیمت کندل‌ها
v	عددرشته	حجم معاملات کندل‌ها
حساب کاربری
 دسترسی به اطلاعات حساب کاربری نیاز به احراز هویت توسط کلید API دارد.
پروفایل
curl 'https://api.wallex.ir/v1/account/profile'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "tracking_id": 1000012345,
    "first_name": "مجید",
    "last_name": "حسینی",
    "national_code": "4899****547",
    "face_image": "...",
    "birthday": "1990-01-01T00:00:00Z",
    "address": { ... },
    "phone_number": {
      "area_code": "021",
      "main_number": "22222222",
    },
    "mobile_number": "0912****789",
    "verification": "UNVERIFIED",
    "email": "as*******@g****.com",
    "invite_code": "...",
    "avatar": null,
    "commission": 25,
    "settings": { ... },
    "status": { ... },
    "kyc_info": { ... },
    "meta": { ... }
  }
}
با این درخواست می‌توانید پروفایل کاربری خود را دریافت کنید:

GET https://api.wallex.ir/v1/account/profile

خروجی
خروجی این درخواست، شامل اطلاعات شخصی کاربر همچون اطلاعات هویتی و اطلاعات تماس است.

سطح کاربری و کارمزد
curl 'https://api.wallex.ir/v1/account/fee'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    "BTCTMN": {
      "makerFeeRate": "0.00200000",
      "takerFeeRate": "0.00200000",
      "recent_days_sum": 250000000.00
    },
    "BTCUSDT": {
      "makerFeeRate": "0.00200000",
      "takerFeeRate": "0.00200000",
      "recent_days_sum": 0
    },
    ...
  ]
}
با این درخواست می‌توانید میزان کارمزد معاملات هر بازار را دریافت کنید:

GET https://api.wallex.ir/v1/account/fee

خروجی
خروجی این درخواست نگاشتی از بازارهای والکس و میزان کارمزد دریافتی هر بازار است. هر بازار شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
makerFeeRate	عددرشته	ضریب کارمزد دریافتی از فروشنده
takerFeeRate	عددرشته	ضریب کارمزد دریافتی از خریدار
recent_days_sum	عدد	مجموع معاملات در ۳ ماه گذشته
شماره‌های کارت‌های بانکی
curl 'https://api.wallex.ir/v1/account/card-numbers'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    {
      "id": 999999,
      "card_number": "6219**********82",
      "owners": [
        "مجید حسینی / فعال"
      ],
      "status": "ACCEPTED",
      "is_default": 1
    }
  ]
}
با این درخواست می‌توانید لیست شماره‌های کارت‌های بانکی خود را دریافت کنید:

GET https://api.wallex.ir/v1/account/card-numbers

خروجی
خروجی این درخواست فهرستی از شماره‌های کارت‌های بانکی ثبت شده برای کاربر است.

شماره‌های شبای بانکی
curl 'https://api.wallex.ir/v1/account/ibans'
نمونهٔ خروجی

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    {
      "id": 999999,
      "iban": "IR5905****************3001",
      "owners": [
        "مجید حسینی / فعال"
      ],
      "bank_name": "سامان",
      "status": "ACCEPTED",
      "is_default": 1,
      "bank_details": {
        "code": "SABCIR",
        "label": "بانک سامان"
      }
    }
  ]
}
با این درخواست می‌توانید لیست شماره‌های شبای بانکی خود را دریافت کنید:

GET https://api.wallex.ir/v1/account/ibans

خروجی
خروجی این درخواست فهرستی از شماره‌های شبای بانکی ثبت شده برای کاربر است.

دارایی‌های کیف پول
curl 'https://api.wallex.ir/v1/account/balances'
نمونهٔ خروجی

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "balances": {
      "TMN": {
        "asset": "TMN",
        "faName": "تومان",
        "fiat": true,
        "value": "10000000",
        "locked": "0"
      },
      "USDT": {
        "asset": "USDT",
        "faName": "تتر",
        "fiat": false,
        "value": "10.00000000",
        "locked": "0.00000000"
      },
      ...
    }
  }
}
با این درخواست می‌توانید دارایی‌های کیف پول خود را به تفکیک ارز/رمزارز دریافت کنید:

GET https://api.wallex.ir/v1/account/balances

خروجی
خروجی این درخواست نگاشتی از دارایی‌های کیف پول کاربر برای هر ارز/رمزارز است. هر دارایی شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
asset	رشته	نماد رمزارز
faName	رشته	نام فارسی رمزارز
fiat	بولی	آیا دارایی یک ارز است؟
value	عددرشته	مقدار دارایی
locked	عددرشته	دارایی فریزشده
ثبت برداشت تومان
curl -X POST -H "Content-Type: application/json" -d '{
  "iban": 1000001,
  "value": 100000,
}' 'https://api.wallex.ir/v1/account/money-withdrawal'
نمونهٔ خروجی:

{
    "result": {
        "amount": 50000,
        "fee": 500,
        "tracking_code": "abcdefg",
        "created_at": "2023-02-21T13:15:06Z",
        "status": "pending",
        "iban": {
            "id": 1000001,
            "withdraw_available_amount": null,
            "iban": "IR590********************1",
            "owners": [
                "حسین حسینی / فعال"
            ],
            "bank_name": "سامان",
            "status": "ACCEPTED",
            "is_default": 1,
            "bank_details": {
                "code": "SABCIR",
                "label": "بانک سامان"
            }
        },
        "details": [
            {
                "value": 49500,
                "status": "pending"
            }
        ]
    },
    "message": "درخواست برداشت ثبت شد",
    "success": true
}
با این درخواست می‌توانید درخواست برداشت تومان را ثبت کنید:

POST https://api.wallex.ir/v1/account/money-withdrawal

 اندپوینت ثبت درخواست برداشت محدودیت فراخوانی ۶ درخواست در ثانیه دارد.
 به دستور پلیس فتا، برای برداشت کوین IP شما باید کشور ایران باشد.
بدنهٔ درخواست
پارامتر	نوع	اجباری	توضیحات
iban	عدد	بله	شناسهٔ شبای بانکی مقصد
value	عدد	بله	مقدار برداشت تومان
خروجی
خروجی این درخواست اطلاعات درخواست برداشت ثبت شدهٔ کاربر است.

لیست واریزهای رمزارز
curl 'https://api.wallex.ir/v1/account/crypto-withdrawal'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    {
      "asset": "SHIB",
      "amount": "70000.0000000000000000",
      "txHash": "man-0000000000000000000",
      "block_explorer_link": "https://etherscan.io/tx/man-0000000000000000000",
      "confirmations": 1,
      "min_confirmation": 1,
      "coin_type": {
        "key": "SHIB",
        "name": "شیبا",
        "name_en": "Shiba inu",
        "type": "CRYPTO",
        "deposit_availability": "ENABLE",
        "withdrawal_availability": "ENABLE",
        "deposit_unavailability_reason": null,
        "withdrawal_unavailability_reason": null
      },
      "network": {
        "name": "ERC20",
        "message": null,
        "type": "ADDRESS",
        "deposit_availability": "ENABLE",
        "withdrawal_availability": "ENABLE"
      },
      "status": "confirmed",
      "time": "2022-05-10T00:33:21Z",
      "wallet": {
        "address": "0x0123456789abcdef0123456789abcdef01234567",
        "memo_base": false,
        "memo": null
      },
      "deposit_type": "GIFT"
    },
    ...
  ],
  "result_info": {
    "page": 1,
    "per_page": 10,
    "count": 2,
    "total_count": 19
  }
}
با این درخواست می‌توانید فهرستی از واریزهای رمزارز را دریافت کنید:

GET https://api.wallex.ir/v1/account/crypto-deposit

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
page	عدد	خیر	شمارهٔ صفحه
per_page	عدد	خیر	تعداد آیتم در هر صفحه
خروجی
خروجی این درخواست، فهرستی از واریزهای رمزارز کاربر است.

لیست برداشت‌های رمزارز
curl 'https://api.wallex.ir/v1/account/crypto-withdrawal'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": [
    {
      "id": 2000123456,
      "asset": "USDT",
      "amount": "62.0000000000000000",
      "wallet_address": "abcdefghijklmnopqrstuvwxyz01234567",
      "memo": null,
      "fee": "1",
      "txHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "block_explorer_link": "https://tronscan.org/#/transaction/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "status": "Accomplished",
      "coin": {
        "id": 22,
        "key": "USDT",
        "name": "تتر",
        "type": "CRYPTO",
        "status": 1,
        "min_confirmation_rate": null,
        "transaction_fee": null,
        "deposit_availability": "ENABLE",
        "withdrawal_availability": "ENABLE",
        "deposit_unavailability_reason": null,
        "withdrawal_unavailability_reason": null,
        "configs": {
          "type": "address",
          "service": "alpha"
        }
      },
      "network": {
        "name": "TRC20",
        "message": null,
        "type": "ADDRESS",
        "deposit_availability": "ENABLE",
        "withdrawal_availability": "ENABLE"
      },
      "time": "2022-03-09T20:44:00Z"
    },
    ...
  ],
  "result_info": {
    "page": 1,
    "per_page": 10,
    "count": 1,
    "total_count": 10
  }
}
با این درخواست می‌توانید فهرستی از برداشت‌های رمزارز را دریافت کنید:

GET https://api.wallex.ir/v1/account/crypto-withdrawal

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
page	عدد	خیر	شمارهٔ صفحه
per_page	عدد	خیر	تعداد آیتم در هر صفحه
خروجی
خروجی این درخواست، فهرستی از برداشت‌های رمزارز کاربر است.

ثبت برداشت رمزارز
curl -X POST -H "Content-Type: application/json" -d '{
  "coin": "USDT",
  "network": "TRC20"
  "value": 100,
  "wallet_address": "abcdefghijklmnopqrstuvwxyz01234567"
}' 'https://api.wallex.ir/v1/account/crypto-withdrawal'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "id": 2000123456,
    "asset": "USDT",
    "amount": "100.0000000000000000",
    "wallet_address": "abcdefghijklmnopqrstuvwxyz01234567",
    "memo": null,
    "fee": "1",
    "txHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "block_explorer_link": "https://tronscan.org/#/transaction/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "status": "Accomplished",
    "coin": {
      "id": 22,
      "key": "USDT",
      "name": "تتر",
      "type": "CRYPTO",
      "status": 1,
      "min_confirmation_rate": null,
      "transaction_fee": null,
      "deposit_availability": "ENABLE",
      "withdrawal_availability": "ENABLE",
      "deposit_unavailability_reason": null,
      "withdrawal_unavailability_reason": null,
      "configs": {
        "type": "address",
        "service": "alpha"
      }
    },
    "network": {
      "name": "TRC20",
      "message": null,
      "type": "ADDRESS",
      "deposit_availability": "ENABLE",
      "withdrawal_availability": "ENABLE"
    },
    "time": "2022-03-09T20:44:00Z"
  }
}
با این درخواست می‌توانید درخواست برداشت رمزارز را ثبت کنید:

POST https://api.wallex.ir/v1/account/crypto-withdrawal

 اندپوینت ثبت درخواست برداشت محدودیت فراخوانی ۶ درخواست در ثانیه دارد.
 به دستور پلیس فتا، برای برداشت کوین IP شما باید کشور ایران باشد.
 ارسال کوین به آدرس به شبکه‌‌ای غیر از شبکه انتخاب شده ممکن است منجر به از دست دادن آن برای همیشه شود.
بدنهٔ درخواست
پارامتر	نوع	اجباری	توضیحات
coin	رشته	بله	نماد (انگلیسی) رمزارز
network	رشته	بله	نوع (انگلیسی) شبکهٔ انتقال رمزارز
value	عدد	بله	مقدار برداشت رمزارز
wallet_address	رشته	بله	آدرس مقصد
memo	رشته	خیر	مموی آدرس؛ در صورت نیاز شبکه
خروجی
خروجی این درخواست اطلاعات درخواست برداشت ثبت شدهٔ کاربر است.

سفارش‌ها و معاملات
 دسترسی به سفارش‌ها و معاملات کاربر نیاز به احراز هویت توسط کلید API دارد.
ثبت سفارش
curl -X POST -H "Content-Type: application/json" -d '{
  "symbol": "BTCUSDT",
  "type": "LIMIT"
  "side": "BUY",
  "price": "10000",
  "quantity": "0.001",
}' 'https://api.wallex.ir/v1/account/orders'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "symbol": "BTCUSDT",
    "type": "LIMIT",
    "side": "BUY",
    "price": "10000.000000",
    "origQty": "0.001000",
    "origSum": "10.000000",
    "executedPrice": "62999995.0000000000000000",
    "executedQty": "0.0000000000000000",
    "executedSum": "0.0000000000000000",
    "executedPercent": 0,
    "status": "NEW",
    "active": true,
    "clientOrderId": "LIMIT-670f7c34-d609-40d3-b98e-0150640d79cb",
    "created_at": "2022-06-18T13:45:08.000000Z"
  }
}
با این درخواست می‌توانید سفارش جدیدی برای خرید/فروش رمزارز ثبت کنید:

POST https://api.wallex.ir/v1/account/orders

 اندپوینت ثبت سفارش محدودیت فراخوانی ۱۰ درخواست در ثانیه دارد.
بدنهٔ درخواست
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
type	رشته	بله	نوع سفارش
side	جهت	بله	جهت خرید/فروش
price	عددرشته	بله	قیمت واحد
quantity	عددرشته	بله	حجم سفارش
client_id	رشته	خیر	شناسهٔ یکتای سفارش
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
 مقادیر مجاز برای نوع سفارش شامل مقدارهای زیر است:
LIMIT برای سفارش‌هایی با قیمتی که با price محدود می‌شود
MARKET برای سفارش‌هایی با قیمتی که در بازار مشخص می‌شود
 اگر شناسهٔ یکتای سفارش در بدنهٔ درخواست ارائه نشود، یک شناسهٔ یکتا تولید خواهد شد.
خروجی
خروجی درخواست ثبت سفارش اطلاعات سفارش ثبت شده و شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
type	رشته	نوع سفارش
side	جهت	جهت خرید/فروش
price	عددرشته	قیمت واحد
origQty	عددرشته	حجم سفارش
origSum	عددرشته	مجموع قیمت سفارش
executedPrice	عددرشته	قیمت محقق شده
executedQty	عددرشته	حجم محقق شده
executedSum	عددرشته	مجموع قیمت محقق شده
executedPercent	عدد	درصد تحقق سفارش
status	رشته	وضعیت سفارش
active	بولی	سفارش فعال یا غیرفعال
clientOrderId	رشته	شناسهٔ یکتای سفارش
created_at	تاریخ	زمان ثبت سفارش
 وضعیت سفارش ممکن است یکی از مقادیر زیر باشد:
NEW سفارش باز
FILLED سفارش تکمیل شده
CANCELED سفارش لغو شده
 در صورتی که ثبت سفارش به دلیل داده‌های نامعتبر با خطای 422 متوقف شود، برای پردازش ساده‌تر، در بخش result کد خطایی با عنوان error_code باز خواهد گشت که مقدار آن به صورت زیر قابل تفسیر است:
1001: دقت اعشار قیمت سفارش قابل پذیرش نیست
1002: دقت اعشار حجم سفارش قابل پذیرش نیست
1003: سفارش‌های MARKET نمی‌توانند قیمت داشته باشند
1004: حجم سفارش کمتر از حد مجاز است
1005: حجم سفارش یا مجموع قیمت سفارش الزامی است
1006: موجودی کافی نیست
1007: قیمت توقف الزامی است
1008: قیمت سفارش الزامی است
1009: دقت اعشار قیمت توقف قابل پذیرش نیست
1010: حجم و مجموع قیمت سفارش نباید همزمان تعیین شوند
1011: دقت اعشار مجموع قیمت سفارش قابل پذیرش نیست
اطلاعات سفارش
curl 'https://api.wallex.ir/v1/account/orders/LIMIT-670f7c34-d609-40d3-b98e-0150640d79cb'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "symbol": "BTCUSDT",
    "type": "LIMIT",
    "side": "BUY",
    "price": "10000.000000",
    "origQty": "0.001000",
    "origSum": "10.000000",
    "executedPrice": "62999995.0000000000000000",
    "executedQty": "0.0000000000000000",
    "executedSum": "0.0000000000000000",
    "executedPercent": 0,
    "status": "NEW",
    "active": true,
    "clientOrderId": "LIMIT-670f7c34-d609-40d3-b98e-0150640d79cb",
    "created_at": "2022-06-18T13:45:08.000000Z"
  }
}
با این درخواست می‌توانید اطلاعات یک سفارش ثبت شده را دریافت کنید:

GET https://api.wallex.ir/v1/account/orders/{clientOrderId}

خروجی
خروجی این درخواست، درست مشابه «ثبت سفارش» است.

لغو سفارش
curl -X DELETE 'https://api.wallex.ir/v1/account/orders?clientOrderId=LIMIT-670f7c34-d609-40d3-b98e-0150640d79cb'
با این درخواست می‌توانید یک سفارش فعال را لغو کنید:

DELETE https://api.wallex.ir/v1/account/orders

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
clientOrderId	رشته	بله	شناسهٔ یکتای سفارش
لیست سفارش‌های فعال کاربر
curl 'https://api.wallex.ir/v1/account/openOrders'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "orders": [
      {
        "symbol": "BTCUSDT",
        "type": "LIMIT",
        "side": "BUY",
        "price": "10000.000000",
        "origQty": "0.001000",
        "origSum": "10.000000",
        "executedPrice": "62999995.0000000000000000",
        "executedQty": "0.0000000000000000",
        "executedSum": "0.0000000000000000",
        "executedPercent": 0,
        "status": "NEW",
        "active": true,
        "clientOrderId": "LIMIT-670f7c34-d609-40d3-b98e-0150640d79cb",
        "created_at": "2022-06-18T13:45:08.000000Z"
      },
      ...
    ]
  }
}
با این درخواست می‌توانید لیستی از سفارش‌های فعال را دریافت کنید:

GET https://api.wallex.ir/v1/account/openOrders

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	خیر	نماد (انگلیسی) بازار
خروجی
خروجی این درخواست فهرستی از سفارش‌های فعال است که اطلاعات هر سفارش مشابه اطلاعاتی‌ست که در درخواست ثبت سفارش گفته شد.

لیست آخرین معاملات کاربر
curl 'https://api.wallex.ir/v1/account/trades'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "AccountLatestTrades": [
      {
        "symbol": "PAXGTMN",
        "quantity": "0.0032340000000000",
        "price": "61133333.0000000000000000",
        "sum": "197705.1989220000000000",
        "fee": "0.0000097020000000",
        "feeCoefficient": "0.0030000000000000",
        "feeAsset": "PAXG",
        "isBuyer": true,
        "timestamp": "2022-06-18T17:22:25Z"
      },
      ...
    ]
  }
}
با این درخواست می‌توانید لیستی از سفارش‌های فعال را دریافت کنید:

GET https://api.wallex.ir/v1/account/trades

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	خیر	نماد (انگلیسی) بازار
side	جهت	خیر	جهت معامله
خروجی
خروجی این درخواست فهرستی از آخرین معاملات انجام شده است که هر معامله شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
price	عددرشته	قیمت واحد معامله
quantity	عددرشته	حجم معامله
sum	عددرشته	مجموع قیمت معامله
fee	عددرشته	کارمزد معامله
feeCoefficient	عددرشته	ضریب کارمزد معامله
feeAsset	عددرشته	ارز کارمزد معامله
isBuyer	بولی	آیا معامله خرید است؟
timestamp	زمان	زمان ثبت معامله
معاملات آنی
 دسترسی به API های دریافت قیمت و ثبت سفارش نیاز به احراز هویت توسط کلید API دارد.
لیست بازارهای معامله‌ آنی
curl 'https://api.wallex.ir/v1/otc/markets'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "symbols": {
      "BTCUSDT": {
        "symbol": "BTCUSDT",
        "baseAsset": "BTC",
        "baseAssetPrecision": 8,
        "quoteAsset": "USDT",
        "quotePrecision": 8,
        "faName": "بیت کوین - تتر",
        "faBaseAsset": "بیت کوین",
        "faQuoteAsset": "تتر",
        "stepSize": 6,
        "tickSize": 2,
        "minQty": 0.000001,
        "minNotional": 5,
        "maxNotional": 500,
        "stats": {
          "24h_ch": 6.56,
          "lastPrice": 20353.33,
          "24h_highPrice": 20500,
          "24h_lowPrice": 19100
        },
        "buyStatus": "ENABLE",
        "sellStatus": "ENABLE",
        "createdAt": "2022-06-28T13:19:16.000000Z"
      },
      ...
    }
  }
}
با درخواست زیر می‌توانید لیست بازارها و وضعیت آنها به ازای هرجهت سفارش دریافت کنید:

GET https://api.wallex.ir/v1/otc/markets

خروجی
خروجی این درخواست شامل نگاشتی از بازارهاست و هر بازار شامل اطلاعاتی به شرح زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
baseAsset	رشته	ارز پایه
baseAssetPrecision	عدد	تعداد اعشار ارز پایه
quoteAsset	رشته	ارز تجاری
quotePrecision	عدد	تعداد اعشار ارز تجاری
faName	رشته	نام فارسی بازار
faBaseAsset	رشته	نام فارسی ارز پایه
faQuoteAsset	رشته	نام فارسی ارز تجاری
stepSize	عدد	تعداد اعشار افزایش/کاهش حجم تراکنش
tickSize	عدد	تعداد اعشار افزایش/کاهش مبلغ تراکنش
minQty	عدد	حداقل حجم تراکنش
maxQty	عدد	حداکثر حجم تراکنش
minNotional	عدد	حداقل مبلغ تراکنش
stats	متغیر	اطلاعات آماری بازار
buyStatus	رشته	وضعیت امکان خرید در این بازار
sellStatus	رشته	وضعیت امکان فروش در این بازار
createdAt	رشته	زمان ایجاد بازار
همچنین آمارهای هر بازار شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
24h_ch	عدد	درصد تغییرات قیمت در ۲۴ ساعت گذشته
24h_highPrice	عدد	بیشترین قیمت در ۲۴ ساعت گذشته
24h_lowPrice	عدد	کمترین قیمت در ۲۴ ساعت گذشته
lastPrice	عدد	آخرین قیمت تراکنش
 مقادیر وضعیت امکان خرید/فروش در هر بازار شامل مقدارهای زیر است:
ENABLE قابلیت امکان ثبت سفارش
DISABLE عدم امکان ثبت سفارش به صورت موقت
دریافت قیمت
curl -X GET -H "Content-Type: application/json" \ -H "x-api-key: your_api_key" \ -d '{
  "symbol": "BTCUSDT",
  "side": "BUY",
}' 'https://api.wallex.ir/v1/account/otc/price'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "price": "20288.99471291",
    "price_expires_at": "2022-08-30T09:21:08Z"
  }
}
با این درخواست می‌توانید قیمت خرید/فروش رمزارزهای معامله آنی را به ازای هر بازار دریافت کنید:

GET https://api.wallex.ir/v1/account/otc/price

 قیمت دریافت شده به ازای هر بازار و جهت معامله حداکثر تا زمان مشخص شده در مقدار کلید بازگشتی price_expires_at معتبر می باشد. پس از گذشت این زمان نیاز است دوباره قیمت جدید دریافت شود.
بدنهٔ درخواست
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
side	جهت	بله	جهت خرید/فروش
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارهای معامله آنی به دست می‌آید.
 مقادیر مجاز برای جهت سفارش شامل مقدارهای زیر است:
BUY جهت سفارش برای خرید یک رمزارز
SELL جهت سفارش برای فروش یک رمزارز
خروجی
خروجی درخواست دریافت قیمت شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
price	عددرشته	قیمت واحد
price_expires_at	تاریخ	زمان منقضی شدن قیمت
ثبت سفارش آنی
 قبل از ثبت سفارش با API زیر نیاز است با استفاده از API دریافت قیمت، قیمت رمز ارز مورد نظر برای ثبت سفارش را در بازار و جهت سفارش درخواستی دریافت کنید و قبل از منقضی شدن آن سفارش خود را ثبت نمایید.
curl -X POST -H "Content-Type: application/json" \ -H "x-api-key: your_api_key" \ -d '{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "amount": 0.01,
}' 'https://api.wallex.ir/v1/account/otc/orders'
نمونهٔ خروجی:

{
  "success": true,
  "message": "عملیات با موفقیت انجام شد",
  "result": {
    "symbol": "BTCUSDT",
    "type": "OTC",
    "side": "BUY",
    "clientOrderId": "OTC-xxxxx-xxx-xxx-xxx-xxxxxxx",
    "transactTime": 0,
    "price": "20288.99471291",
    "origQty": "0.01",
    "executedSum": "202.88994713",
    "executedQty": "0.01",
    "executedPrice": "20288.99471291",
    "sum": "202.88994713",
    "executedPercent": 100,
    "status": "FILLED",
    "active": false,
    "fills": [
      {
        "price": "20288.99471291",
        "quantity": "0.01",
        "fee": "0.1988000000000000",
        "feeCoefficient": "0.0040000000000000",
        "feeAsset": "BTC",
        "timestamp": "2022-05-18T11:10:30Z",
        "symbol": "BTCUSDT",
        "sum": "109290.3000000000000000",
        "makerFeeCoefficient": "0E-8",
        "takerFeeCoefficient": "0.00400000",
        "isBuyer": true
      }
    ]
  }
}
با این درخواست می‌توانید سفارش جدیدی برای خرید/فروش آنی رمزارز ثبت کنید:

POST https://api.wallex.ir/v1/account/otc/orders

بدنهٔ درخواست
پارامتر	نوع	اجباری	توضیحات
symbol	رشته	بله	نماد (انگلیسی) بازار
side	جهت	بله	جهت خرید/فروش
amount	عدد	بله	حجم سفارش
 مقادیر مجاز برای نماد بازار شامل نمادهایی‌ست که از درخواست لیست بازارهای معامله آنی به دست می‌آید.
 مقادیر مجاز برای جهت سفارش شامل مقدارهای زیر است:
BUY جهت سفارش برای خرید یک رمزارز
SELL جهت سفارش برای فروش یک رمزارز
خروجی
خروجی درخواست ثبت سفارش اطلاعات سفارش ثبت شده و شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
symbol	رشته	نماد (انگلیسی) بازار
type	رشته	نوع سفارش
side	جهت	جهت خرید/فروش
clientOrderId	رشته	شناسهٔ یکتای سفارش
transactTime	تاریخ	زمان ثبت سفارش
price	عددرشته	قیمت واحد
origQty	عددرشته	حجم سفارش
executedSum	عددرشته	مجموع قیمت محقق شده
executedQty	عددرشته	حجم محقق شده
executedPrice	عددرشته	قیمت محقق شده
sum	عددرشته	مجموع قیمت سفارش
executedPercent	عدد	درصد تحقق سفارش
status	رشته	وضعیت سفارش
active	بولی	سفارش فعال یا غیرفعال
fills	متغیر	اطلاعات معامله انجام شده
 وضعیت سفارش همیشه برابر FILLED می باشد.
همچنین اطلاعات معامله انجام شده شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
price	عددرشته	قیمت معامله
quantity	عددرشته	حجم معامله
fee	عددرشته	کارمزد معامله
feeCoefficient	عددرشته	ضریب کارمزد معامله
feeAsset	رشته	نوع دارایی کارمزد کسر شده
timestamp	تاریخ	زمان انجام معامله
symbol	رشته	نماد (انگلیسی) بازار
sum	عددرشته	مجموع قیمت معامله
makerFeeCoefficient	عددرشته	ضریب کارمزد سفارش گذار
takerFeeCoefficient	عددرشته	ضریب کارمزد سفارش بردار
isBuyer	بولی	جهت سفارش معامله گذار
وب‌سوکت
اتصال به وب‌سوکت:

# See "javascript" section.
سابسکرایب کانال:

# See "javascript" section.
برای اتصال به سرویس وب‌سوکت باید از کلاینت socket.io (نسخهٔ v2.5.0، یا سازگار با آن) استفاده کنید.

برای دریافت هر یک از اطلاعاتی که در ادامه توضیحات آنها خواهد آمد، باید برروی کانال آن سابسکرایب کنید. برای این منظور پارامتر eventName را برابر subscribe تنظیم و آبجکتی را که مشخصات آن، بنا بر آنچه در ادامه گفته خواهد شد، مرتبط با نوع داده‌های دریافتی‌ست به عنوان پارامتر args ارسال کنید.

تفسیر داده‌های دریافتی مشابه آن چیزی‌ست که برای اندپوینت‌های مرتبط با هر کدام از این اطلاعات پیشتر گفته شده است.

سفارش‌های فعال
# See "javascript" section.
نمونهٔ پیام دریافتی:

{
  "0":{
    "quantity":214.86,
    "price":"31695.0000000000000000",
    "sum":6809987.7
  },
  "1":{
    "quantity":331.55,
    "price":"31669.0000000000000000",
    "sum":10499856.950000001
  },
  ...
}
برای دریافت سفارش‌های فعال خرید و فروش برای هر یک از بازارها، باید به‌ترتیب برروی کانال‌های SYMBOL@buyDepth و SYMBOL@sellDepth سابسکرایب کنید.

 مقادیر مجاز برای SYMBOL شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
معامله‌های انجام‌شده
# See "javascript" section.
نمونهٔ پیام دریافتی:

{
  "isBuyOrder":false,
  "quantity":"705.0000000000000000",
  "price":"31704.0000000000000000",
  "timestamp":"2022-06-26T11:14:09Z"
}
برای دریافت سفارش‌های انجام‌شده برای هر یک از بازارها باید برروی کانال SYMBOL@trade سابسکرایب کنید.

 مقادیر مجاز برای SYMBOL شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
اطلاعات زندهٔ بازار
# See "javascript" section.
نمونهٔ پیام دریافتی:

{
  "symbol":"USDTTMN",
  "24h_ch":-1.24,
  "7d_ch":-2.05,
  "24h_volume":"859806.8400000000000000",
  "7d_volume":"8607956.3700000000000000",
  "24h_quoteVolume":"27493903077.3600000000000000",
  "24h_highPrice":"32227.0000000000000000",
  "24h_lowPrice":"31650.0000000000000000",
  "lastPrice":"31653.0000000000000000",
  "lastQty":"94.0900000000000000",
  "bidPrice":"31653.0000000000000000",
  "askPrice":"31704.0000000000000000",
  "lastTradeSide":"BUY",
  "bidVolume":"268856.3300000000000000",
  "askVolume":"289262.0300000000000000",
  "bidCount":345,
  "askCount":378,
  "direction":{
    "SELL":58,
    "BUY":42
  },
  "createdAt":"2020-10-01T00:00:00.000000Z"
}
برای دریافت بروزترین اطلاعات هر یک از بازارها باید برروی کانال SYMBOL@marketCap سابسکرایب کنید.

 مقادیر مجاز برای SYMBOL شامل نمادهایی‌ست که از درخواست لیست بازارها به دست می‌آید.
وال‌گیت
 برای دسترسی به وب سرویسهای والگیت کاربر نیاز به احراز هویت دارد.
احراز هویت
curl -X POST -H "Content-Type: application/json" \
-d '{
    "username": "09123456789,
    "password": "P4$$w0rD"
}' 'https://api.wallgate.io/v1/store/oauth/token'
نمونهٔ خروجی:

{
  "data": {
    "token_type": "Bearer",
    "expires_in": 31622400,
    "access_token": "{access_token}"
  }
}
با این درخواست می‌توانید احراز هویت انجام دهید:

POST https://api.wallgate.io/v1/store/oauth/token

خروجی
خروجی درخواست شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
token_type	رشته	نوع توکن
expires_in	عدد	زمان انقضا
access_token	رشته	توکن احراز هویت
لیست دسته‌بندی‌ها
curl -X GET -H "Content-Type: application/json" \
'https://api.wallgate.io/v1/store/api/categories'
نمونهٔ خروجی:

{
  "data": [
    {
      "id": 3,
      "title": "گیفت کارت اپل",
      "title_en": "Apple Gift Card",
      "image": "https://api.wallgate.io/v1/store/image/ytKxz02EG00qXMPZ"
    },
    {
      "id": 4,
      "title": "گیفت کارت گوگل پلی",
      "title_en": "GooglePlay Giftcard",
      "image": "https://api.wallgate.io/v1/store/image/NbvMJAjYJ2fV5dga"
    }
  ]
}
با این درخواست می‌توانید لیست دسته‌بندی‌ها را دریافت کنید:

GET https://api.wallgate.io/v1/store/api/categories

خروجی
خروجی درخواست شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
id	عدد	شناسهٔ یکتای دسته‌بندی
title	رشته	نام
title_en	رشته	نام انگلیسی
image	رشته	تصویر
لیست محصولات
curl -X GET -H "Content-Type: application/json" \
'https://api.wallgate.io/v1/store/api/products?page_size=20&page=1&category=3'
نمونهٔ خروجی:

{
  "data": {
    "total": 136,
    "per_page": 10,
    "current_page": 1,
    "last_page": 14,
    "from": 1,
    "to": 10,
    "data": [
      {
        "product_id": 164,
        "name": "مستر کارت مجازی آمریکایی",
        "image": "https://api.wallgate.io/v1/store/image/dg8CrxtZ56NZzqEu",
        "status": "in_stock",
        "category": {
          "id": 3,
          "title": "گیفت کارت اپل",
          "title_en": "Apple Gift Card",
          "image": "https://api.wallgate.io/v1/store/image/ytKxz02EG00qXMPZ"

        },        
        "variants": [
          {
            "id": 941,
            "title": "۳ دلار",
            "price": 290000,
            "status": "in_stock"
          }
        ]
      }
    ]
  }
}
با این درخواست می‌توانید لیست محصولات را دریافت کنید:

GET https://api.wallgate.io/v1/store/api/products?page_size=20&page=1

برای فیلتر محصولات بر اساس شناسه دسته بندی:

GET https://api.wallgate.io/v1/store/api/products?page_size=20&page=1&category=3

خروجی
خروجی درخواست شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
product_id	عدد	شناسهٔ یکتای محصول
name	رشته	نام
status	رشته	وضعیت
category	عدد	اطلاعات دسته‌بندی
variants	عدد	واریانت‌ها
دسته‌بندی:

پارامتر	نوع	توضیحات
id	عدد	شناسهٔ یکتای دسته‌بندی
title	رشته	نام
title_en	رشته	نام انگلیسی
image	رشته	تصویر
واریانت‌ها:

پارامتر	نوع	توضیحات
id	عدد	شناسهٔ یکتای محصول
title	رشته	نام
price	عدد	قیمت
status	رشته	وضعیت
ثبت سفارش وال‌گیت
curl -X POST -H "Content-Type: application/json" \
-H "Authorization: Bearer {access_token}" \
-d '{
    "variant_id": 941,
    "qty": 1,
    "account": "USDT" //USDT or TMN,
    "unique_id": "baa51145-22e8-4f13-a25b-421ca20ba298",
    "webhook_url": "https://webhook.site/9de0d858-8572-45b2-b532-138844760755"
}' 'https://api.wallgate.io/v1/store/api/order'
نمونهٔ خروجی:

{
  "data": {
    "order_id": 1,
    "unique_id": "baa51145-22e8-4f13-a25b-421ca20ba298",
    "name": "گیفت کارت استیم آمریکا (1 دلار)",
    "price": 48000,
    "qty": 1,
    "status_code": "pending",
    "card_type": "gift_card"
  }
}
با این درخواست می‌توانید سفارش ثبت کنید:

POST https://api.wallgate.io/v1/store/api/order

خروجی
خروجی درخواست شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
order_id	عدد	شناسهٔ یکتای سفارش
unique_id	رشته (UUID)	کد یکتای پیگیری مشتری
name	رشته	نام آیتم
price	عدد	قیمت
qty	عدد	مقدار
status_code	رشته	وضعیت
card_type	رشته	نوع کارت
مقادیر status_code:

code	وضعیت
pending	در انتظار پردازش
processing	در حال پردازش
processed	پردازش شده
failed	پردازش سفارش با خطا مواجه شده
refunded	هزینه آیتم بازپرداخت شده
در صورت ارسال مقدار webhook_url و پردازش و خطای سفارش درخواست با متد POST ارسال می‌شود که body درخواست به صورت زیر است:

پارامتر	نوع	توضیحات
order_id	عدد	شناسهٔ یکتای سفارش
unique_id	رشته (UUID)	کد یکتای پیگیری مشتری
name	رشته	نام آیتم
price	عدد	قیمت
qty	عدد	مقدار
status_code	رشته	وضعیت
card_type	رشته	نوع کارت
serials	متغیر	کدها
اطلاعات سفارش وال‌گیت
curl -X GET -H "Content-Type: application/json" \
-H "Authorization: Bearer {access_token}" \
'https://api.wallgate.io/v1/store/api/order/{unique_id}'
نمونهٔ خروجی:

{
  "data": {
    "order_id": 1,
    "unique_id": "baa51145-22e8-4f13-a25b-421ca20ba298",
    "name": "گیفت کارت استیم آمریکا (1 دلار)",
    "price": 48000,
    "qty": 1,
    "status_code": "processed",
    "card_type": "gift_card",
    "serials": [
      {
        "serial": "ABC543REERT"
      }
    ]
  }
}
با این درخواست می‌توانید یک سفارش را پیگیری کنید:

GET https://api.wallgate.io/v1/store/api/order/{unique_id}

پارامترهای کوئری
پارامتر	نوع	اجباری	توضیحات
unique_id	رشته (UUID)	بله	کد یکتای پیگیری مشتری
خروجی
خروجی درخواست شامل اطلاعات زیر است:

پارامتر	نوع	توضیحات
order_id	عدد	شناسهٔ یکتای سفارش
unique_id	رشته (UUID)	کد یکتای پیگیری مشتری
name	رشته	نام آیتم
price	عدد	قیمت
qty	عدد	مقدار
status_code	رشته	وضعیت
card_type	رشته	نوع کارت
serials	متغیر	کدها
مقادیر status_code:

code	وضعیت
pending	در انتظار پردازش
processing	در حال پردازش
processed	پردازش شده
failed	پردازش سفارش با خطا مواجه شده
refunded	هزینه آیتم بازپرداخت شده
کدها:

گیفت کارت:

پارامتر	نوع	توضیحات
serial	رشته	سریال
address	رشته	آدرس
owner	رشته	مالک
کارت اعتباری:

پارامتر	نوع	توضیحات
card_number	رشته	شماره کارت
expiration	رشته	تاریخ انقضا
cvv	عدد	CVV
owner	رشته	مالک
address	رشته	آدرس
zipcode	رشته	کد پستی
کدهای خطا
HTTP STATUS CODE	
200	درخواست موفق
400	درخواست اشتباه
401	توکن ارسالی نامعتبر است
402	موجودی کیف پول کافی نیست
403	دسترسی غیر مجاز
404	مسیر فراخوانی شده پیدا نشد
405	متد فراخوانی شده مجاز نیست
409	شناسه سفارش تکراری است
422	مقادیر ارسالی نامعتبر است
429	تعداد درخواست‌ها بیش از حد مجاز
500