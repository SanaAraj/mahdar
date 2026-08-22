MESSAGES: dict[str, str] = {
    "stage.convert": "تحويل التسجيل",
    "stage.transcribe": "التفريغ الصوتي",
    "stage.diarize": "فصل المتحدثين",
    "stage.assemble": "تجميع الجمل",
    "stage.analyze": "تحليل المحضر",
    "diarize.skipped": "أُنجز التفريغ دون فصل المتحدثين، أضف HF_TOKEN لتفعيله",
    "speaker.unknown": "أحد المتحدثين غير موجود في هذا الاجتماع",
    "speaker.empty_label": "اسم المتحدث لا يمكن أن يكون فارغًا",
    "speaker.label_too_long": "اسم المتحدث يتجاوز الحد المسموح",
    "speaker.bad_body": "صيغة الطلب غير صحيحة",
    "app.title": "محضر",
    "audio.ffmpeg_missing": "أدوات معالجة الصوت غير متوفرة على الخادم",
    "audio.corrupt": "تعذّرت قراءة ملف الصوت، يبدو أنه تالف أو بصيغة غير صالحة",
    "upload.unsupported_extension": (
        "صيغة الملف غير مدعومة، الصيغ المقبولة: webm, ogg, wav, mp3, m4a, mp4"
    ),
    "upload.bad_signature": "محتوى الملف لا يشبه ملفًا صوتيًا، تأكد من رفع تسجيل صحيح",
    "upload.file_too_large": "حجم الملف يتجاوز الحد المسموح به",
    "rate.limited": "طلبات كثيرة خلال وقت قصير، انتظر قليلًا ثم أعد المحاولة",
    "server.busy": "الخادم مشغول حاليًا، أعد المحاولة بعد قليل",
    "job.not_found": "هذا الاجتماع غير موجود",
    "audio.not_ready": "الصوت المعالج غير جاهز بعد",
    "groq.key_missing": "مفتاح GROQ_API_KEY غير مضبوط في ملف .env",
    "groq.rate_limit": "تجاوزنا حد الطلبات المجانية مؤقتًا، أعد المحاولة بعد قليل",
    "groq.unavailable": "تعذّر الوصول إلى خدمة التفريغ الصوتي، تحقّق من الاتصال بالإنترنت",
    "groq.failed": "فشل التفريغ الصوتي",
    "cohere.key_missing": "مفتاح COHERE_API_KEY غير مضبوط في ملف .env",
    "cohere.rate_limit": "تجاوزنا حد طلبات Cohere مؤقتًا، أعد المحاولة بعد قليل",
    "cohere.unavailable": "تعذّر الوصول إلى خدمة Cohere، تحقّق من الاتصال بالإنترنت",
    "cohere.failed": "فشل التفريغ الصوتي عبر Cohere",
    "local_llm.key_missing": "مزود التحليل المحلي غير متاح",
    "local_llm.rate_limit": "مزود التحليل المحلي مشغول مؤقتًا، أعد المحاولة بعد قليل",
    "local_llm.unavailable": (
        "تعذّر الوصول إلى خادم التحليل المحلي، تأكد من تشغيله عبر docker compose --profile local up"
    ),
    "local_llm.failed": "فشل التحليل عبر المزود المحلي",
    "local_stt.failed": "فشل التفريغ الصوتي عبر المزود المحلي",
    "config.unknown_provider": (
        "قيمة المزود غير معروفة، خيارات STT: groq أو cohere أو local، وخيارات LLM: groq أو local"
    ),
    "transcription.unexpected": "فشل التفريغ الصوتي بشكل غير متوقع",
    "transcription.empty": "لم يعثر التفريغ على أي كلام مسموع في هذا التسجيل",
    "assembly.failed": "حدث خطأ أثناء تجميع الجمل",
    "audio.split_failed": "تعذّر تقسيم الملف الطويل",
    "analysis.failed": "تعذّر استخلاص المحضر من النص، تستطيع إعادة المحاولة من صفحة النتيجة",
    "analysis.transcript_missing": "تعذّر التحليل لأن التفريغ غير محفوظ بعد",
    "analysis.too_long": (
        "التفريغ أطول من الحد الذي يمكن تحليله في طلب واحد على الطبقة المجانية، "
        "جزّئ التسجيل إلى اجتماعات أقصر وحاول من جديد"
    ),
    "analysis.unexpected": "حدث خطأ غير متوقع أثناء التحليل",
    "export.title_prefix": "محضر اجتماع",
    "export.date": "التاريخ",
    "export.date_gregorian": "ميلادي",
    "export.date_hijri": "هجري",
    "export.duration": "المدة",
    "export.attendees": "الحضور",
    "export.topics": "المواضيع",
    "export.topics_empty": "لم تُذكر مواضيع محددة في هذا الاجتماع",
    "export.decisions": "القرارات",
    "export.decisions_empty": "لم تُتخذ قرارات في هذا الاجتماع",
    "export.directives": "التوجيهات",
    "export.directives_empty": "لم تصدر توجيهات في هذا الاجتماع",
    "export.tasks": "جدول المهام",
    "export.tasks_empty": "لا توجد مهام مستخلصة من هذا الاجتماع",
    "export.col_task": "المهمة",
    "export.col_owner": "المسؤول",
    "export.col_due": "الاستحقاق",
    "export.col_priority": "الأولوية",
    "export.owner_unknown": "غير محدد",
    "export.no_due": "بلا موعد",
    "export.transcript": "نص التفريغ",
    "export.speaker_unknown": "متحدث",
    "export.attendees_separator": "، ",
    "export.no_analysis": (
        "تعذّر استخلاص المحضر التحليلي لهذا الاجتماع، فيتضمن هذا الملف "
        "بيانات الاجتماع ونص التفريغ فقط"
    ),
}


def resolve(message_key: str, *, params: dict[str, str] | None = None) -> str:

    if message_key == "analysis.model_deprecated":
        available = (params or {}).get("available", "")
        return (
            "نموذج التحليل المضبوط لم يعد متاحًا لدى Groq. النماذج المتاحة حاليًا: " + available + "."
        )
    return MESSAGES.get(message_key, MESSAGES["analysis.unexpected"])


def default_speaker_label(index: int) -> str:

    return f"المتحدث {index + 1}"
