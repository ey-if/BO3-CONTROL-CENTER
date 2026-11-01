BO3 Control Center - حزمة تجهيز EXE

الهدف: إنتاج ملف BO3-Control-Center.exe مستقل يعمل على Windows 10 دون تثبيت Python على جهاز المستخدم النهائي.

مهم: هذه الحزمة ليست ملف EXE جاهزاً. لم يتم تجميعها على Windows في بيئة البناء الحالية.

خيار البناء على جهاز Windows:
1) يلزم وجود Python على جهاز البناء فقط.
2) شغّل build_windows.bat.
3) بعد نجاح البناء ستجد الملف في dist\BO3-Control-Center.exe.
4) انقل ملف EXE إلى جهاز Windows 10 المستهدف؛ لا يحتاج جهاز الاستخدام إلى Python.

خيار البناء عبر GitHub Actions:
يوجد ملف .github/workflows/build-windows.yml للبناء على Windows runner. ارفع ملفات هذه الحزمة إلى مستودع GitHub ثم شغّل Actions > Build Windows EXE، وبعدها نزّل Artifact باسم BO3-Control-Center-Windows10.

ملاحظة: قد تعرض بعض برامج الحماية تحذيراً لملفات EXE غير الموقعة. لا تشغّل الملف إلا إذا بنيته بنفسك أو تحققت من مصدره.
