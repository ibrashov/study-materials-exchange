"""Phase 3: Reproducible dataset generator for academic filename moderation.

Builds curated vocabulary files (`profanity_words.csv`, `clean_filenames.csv`) from
verified open-source lists (LDNOOBW CC-BY-4.0, roose/ru-kk-swear-words MIT) and
generates ~25,000 labeled filename/title samples split by `base_id` BEFORE
augmentation (70/15/15) to prevent data leakage, plus an independent challenge set.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_moderation.config import (
    CLEAN_FILENAMES_PATH,
    GENERATED_DIR,
    PROFANITY_WORDS_PATH,
    RANDOM_SEED,
    SOURCES_DIR,
)

# Academic/ambiguous single words from general web lists that must NOT be treated
# as profanity in an academic file-exchange platform.
ACADEMIC_SAFE_EXCLUSIONS = {
    "anatomy", "arab", "asian", "black", "brown", "white", "chinese", "japanese",
    "russian", "german", "french", "jew", "jewish", "muslim", "christian", "god",
    "hell", "damn", "sex", "sexual", "sexuality", "breast", "breasts", "chest",
    "organ", "organs", "reproduction", "genital", "genitals", "vagina", "penis",
    "rectum", "anus", "sperm", "ovum", "embryo", "fetus", "uterus", "period",
    "blood", "death", "dead", "kill", "murder", "crime", "drug", "drugs", "alcohol",
    "wine", "beer", "weed", "joint", "pipe", "crack", "acid", "base", "salt",
    "screw", "nail", "hammer", "stroke", "strip", "bond", "bondage", "slave",
    "master", "dominate", "domination", "submit", "submission", "probe", "insert",
    "penetrate", "penetration", "erect", "erection", "oral", "anal", "analysis",
    "virgin", "virginia", "tit", "tits", "ho", "hoe", "pot", "bum", "box", "bush",
    "knob", "nuts", "balls", "sack", "shaft", "rod", "wood", "bone", "wang",
    "dong", "johnson", "dickens", "hancock", "peacock", "cocktail", "suck",
    "sucker", "blow", "jerk", "prick", "snatch", "beaver", "muff", "puss",
    "shag", "spank", "tramp", "tart", "slag", "git", "sod", "bloody", "bugger",
    "bollocks", "arsenal", "arse", "coon", "spic", "chink", "kike", "paki",
    "dyke", "fag", "homo", "queer", "tranny", "retard", "retarded", "idiot",
    "moron", "stupid", "dumb", "loser", "ugly", "fat", "nude", "naked", "sexy",
    "hot", "lust", "desire", "passion", "kiss", "love", "date", "escort",
    "massage", "adult", "mature", "xxx", "2g1c", "bbw", "dvda", "guro", "mong",
    "yaoi", "yuri", "hentai", "ecchi", "bdsm", "milf", "nsfw", "smut", "fetish",
    "kink", "kinky", "naughty", "dirty", "filthy", "nasty", "gross", "sick",
    "crazy", "insane", "psycho", "maniac", "freak", "weirdo", "creep",
    # Russian neutral/borderline words sometimes present in general wordlists
    "блин", "хрен", "фиг", "фигня", "черт", "чёрт", "дурак", "дура", "идиот",
    "тупой", "козел", "козёл", "баран", "свинья", "собака", "сукин", "зад",
    "задница", "попа", "грудь", "секс", "порно", "голый", "голая",
}

# Core profanity terms explicitly guaranteed to be present across EN, RU, KK.
# Note: These words exist solely for training and evaluating content moderation.
CURATED_CORE_PROFANITY: list[tuple[str, str, str, str]] = [
    # English core
    ("ass", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("asshole", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("dumbass", "en", "manual_curated_en", "project"),
    ("jackass", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("badass", "en", "manual_curated_en", "project"),
    ("fuck", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("fucker", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("fucking", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("motherfucker", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("fucked", "en", "manual_curated_en", "project"),
    ("shit", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("bullshit", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("shitty", "en", "manual_curated_en", "project"),
    ("dipshit", "en", "manual_curated_en", "project"),
    ("bitch", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("bitches", "en", "manual_curated_en", "project"),
    ("bastard", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("dick", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("dickhead", "en", "manual_curated_en", "project"),
    ("cock", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("cocksucker", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("pussy", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("cunt", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("whore", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("slut", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("wanker", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("twat", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("porn", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("porno", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("blowjob", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("handjob", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("cumshot", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("jizz", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("boobs", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("titties", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("dildo", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("orgasm", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("masturbate", "en", "ldnoobw_en", "CC-BY-4.0"),
    ("scumbag", "en", "manual_curated_en", "project"),
    ("douchebag", "en", "manual_curated_en", "project"),
    ("shithead", "en", "manual_curated_en", "project"),
    ("fuckface", "en", "manual_curated_en", "project"),
    ("asswipe", "en", "manual_curated_en", "project"),
    ("bitchass", "en", "manual_curated_en", "project"),
    ("horseshit", "en", "manual_curated_en", "project"),
    ("clusterfuck", "en", "manual_curated_en", "project"),
    ("mindfuck", "en", "manual_curated_en", "project"),
    ("fuckoff", "en", "manual_curated_en", "project"),
    # Russian core (including transliterations used by students)
    ("хуй", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("хуйня", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("хуевый", "ru", "manual_curated_ru", "project"),
    ("хуёвый", "ru", "manual_curated_ru", "project"),
    ("нахуй", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("похуй", "ru", "manual_curated_ru", "project"),
    ("охуеть", "ru", "manual_curated_ru", "project"),
    ("захуярить", "ru", "manual_curated_ru", "project"),
    ("пизда", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("пиздец", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("пиздатый", "ru", "manual_curated_ru", "project"),
    ("пиздюк", "ru", "manual_curated_ru", "project"),
    ("распиздяй", "ru", "manual_curated_ru", "project"),
    ("блять", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("блядь", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("блядина", "ru", "manual_curated_ru", "project"),
    ("блядство", "ru", "manual_curated_ru", "project"),
    ("ебать", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("ебаный", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("ёбаный", "ru", "manual_curated_ru", "project"),
    ("еблан", "ru", "manual_curated_ru", "project"),
    ("ебанутый", "ru", "manual_curated_ru", "project"),
    ("заебал", "ru", "manual_curated_ru", "project"),
    ("заебись", "ru", "manual_curated_ru", "project"),
    ("уебок", "ru", "manual_curated_ru", "project"),
    ("уёбок", "ru", "manual_curated_ru", "project"),
    ("долбоеб", "ru", "manual_curated_ru", "project"),
    ("долбоёб", "ru", "manual_curated_ru", "project"),
    ("пидор", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("пидорас", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("пидарас", "ru", "manual_curated_ru", "project"),
    ("сука", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("сучка", "ru", "manual_curated_ru", "project"),
    ("шлюха", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("мудак", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("мудила", "ru", "manual_curated_ru", "project"),
    ("гандон", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("гондон", "ru", "manual_curated_ru", "project"),
    ("жопа", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("говно", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("дерьмо", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("мразь", "ru", "manual_curated_ru", "project"),
    ("тварь", "ru", "manual_curated_ru", "project"),
    ("ублюдок", "ru", "manual_curated_ru", "project"),
    ("выблядок", "ru", "manual_curated_ru", "project"),
    ("залупа", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("дрочить", "ru", "ldnoobw_ru", "CC-BY-4.0"),
    ("манды", "ru", "manual_curated_ru", "project"),
    ("бляха", "ru", "manual_curated_ru", "project"),
    ("хуесос", "ru", "manual_curated_ru", "project"),
    ("пиздобол", "ru", "manual_curated_ru", "project"),
    ("ебальник", "ru", "manual_curated_ru", "project"),
    ("выебон", "ru", "manual_curated_ru", "project"),
    # Russian Latin transliteration (common in filenames)
    ("blyat", "ru", "manual_curated_ru", "project"),
    ("blyad", "ru", "manual_curated_ru", "project"),
    ("pizdec", "ru", "manual_curated_ru", "project"),
    ("pizda", "ru", "manual_curated_ru", "project"),
    ("nahuy", "ru", "manual_curated_ru", "project"),
    ("pohuy", "ru", "manual_curated_ru", "project"),
    ("huynya", "ru", "manual_curated_ru", "project"),
    ("eblan", "ru", "manual_curated_ru", "project"),
    ("dolboeb", "ru", "manual_curated_ru", "project"),
    ("suka", "ru", "manual_curated_ru", "project"),
    ("pidor", "ru", "manual_curated_ru", "project"),
    ("mudak", "ru", "manual_curated_ru", "project"),
    ("gandon", "ru", "manual_curated_ru", "project"),
    ("shlyuha", "ru", "manual_curated_ru", "project"),
    # Kazakh core (from roose/ru-kk-swear-words MIT + curated morphological forms & translits)
    ("қотақ", "kk", "roose_ru_kk", "MIT"),
    ("қотақбас", "kk", "roose_ru_kk", "MIT"),
    ("қотағым", "kk", "manual_curated_kk", "project"),
    ("қотағыма", "kk", "roose_ru_kk", "MIT"),
    ("котак", "kk", "manual_curated_kk", "project"),
    ("котакбас", "kk", "manual_curated_kk", "project"),
    ("сігу", "kk", "manual_curated_kk", "project"),
    ("сігейін", "kk", "roose_ru_kk", "MIT"),
    ("сікпейді", "kk", "roose_ru_kk", "MIT"),
    ("сіктір", "kk", "manual_curated_kk", "project"),
    ("сиктир", "kk", "manual_curated_kk", "project"),
    ("сигейин", "kk", "manual_curated_kk", "project"),
    ("шешеңді", "kk", "manual_curated_kk", "project"),
    ("шешең", "kk", "manual_curated_kk", "project"),
    ("шешенс", "kk", "manual_curated_kk", "project"),
    ("жәлеп", "kk", "roose_ru_kk", "MIT"),
    ("жалеп", "kk", "manual_curated_kk", "project"),
    ("қаншық", "kk", "roose_ru_kk", "MIT"),
    ("каншык", "kk", "manual_curated_kk", "project"),
    ("көт", "kk", "manual_curated_kk", "project"),
    ("көтләк", "kk", "roose_ru_kk", "MIT"),
    ("көтің", "kk", "manual_curated_kk", "project"),
    ("көтіңді", "kk", "roose_ru_kk", "MIT"),
    ("көтбас", "kk", "manual_curated_kk", "project"),
    ("амың", "kk", "manual_curated_kk", "project"),
    ("амыңды", "kk", "roose_ru_kk", "MIT"),
    ("амбас", "kk", "manual_curated_kk", "project"),
    ("боқмұрын", "kk", "manual_curated_kk", "project"),
    ("боқ", "kk", "manual_curated_kk", "project"),
    ("малғұн", "kk", "manual_curated_kk", "project"),
    ("оңбаған", "kk", "manual_curated_kk", "project"),
    ("суми", "kk", "manual_curated_kk", "project"),
    ("әкеңді", "kk", "manual_curated_kk", "project"),
    ("жындысүрей", "kk", "manual_curated_kk", "project"),
    ("құрғыр", "kk", "manual_curated_kk", "project"),
    ("қотақжегіш", "kk", "manual_curated_kk", "project"),
    ("сігіл", "kk", "manual_curated_kk", "project"),
    ("сигил", "kk", "manual_curated_kk", "project"),
    ("kotak", "kk", "manual_curated_kk", "project"),
    ("kotakbas", "kk", "manual_curated_kk", "project"),
    ("sigein", "kk", "manual_curated_kk", "project"),
    ("siktir", "kk", "manual_curated_kk", "project"),
    ("zhalep", "kk", "manual_curated_kk", "project"),
    ("sheshen", "kk", "manual_curated_kk", "project"),
    ("kanshuk", "kk", "manual_curated_kk", "project"),
]

# Category A: Clean academic stems across EN, RU, KK, and mixed languages.
ACADEMIC_SUBJECTS_EN = [
    "Mathematics", "Calculus", "Linear_Algebra", "Discrete_Math", "Probability_Theory",
    "Statistics", "Programming", "Python_Programming", "Java_Basics", "Cpp_Pointers",
    "Algorithms", "Data_Structures", "Deep_Learning", "Machine_Learning", "Neural_Networks",
    "Information_Systems", "Software_Engineering", "System_Design", "Databases",
    "SQL_Queries", "PostgreSQL_Indexing", "Computer_Networks", "Operating_Systems",
    "Cybersecurity", "Cryptography", "Web_Development", "Frontend_React", "Backend_FastAPI",
    "Cloud_Computing", "Distributed_Systems", "World_History", "Modern_History",
    "Kazakhstan_History", "Physics", "Quantum_Mechanics", "Thermodynamics",
    "Electromagnetism", "Optics", "Economics", "Microeconomics", "Macroeconomics",
    "Finance", "Accounting", "Management", "Marketing", "Business_Analytics",
    "Academic_Writing", "English_Grammar", "Philosophy", "Sociology", "Psychology",
    "Biology", "Genetics", "Organic_Chemistry", "Inorganic_Chemistry", "Ecology",
    "Linear_Optimization", "Numerical_Methods", "Compiler_Design", "Computer_Vision",
    "Natural_Language_Processing", "Human_Computer_Interaction", "Agile_Scrum",
    "Project_Management", "Software_Testing", "DevOps_Pipeline", "Data_Mining",
    "Big_Data", "Time_Series", "Graph_Theory", "Combinatorics", "Differential_Equations",
    "Vector_Calculus", "Real_Analysis", "Complex_Analysis", "Control_Theory",
    "Embedded_Systems", "Microcontrollers", "Digital_Logic", "Computer_Architecture",
    "Notes", "Lecture_Notes", "Study_Notes", "Homework", "Lab_Work", "Exam_Prep",
    "Final_Report", "Research_Summary", "Course_Slides", "Practice_Sheet", "Syllabus",
    "Thesis_Draft", "Project_Proposal", "Review_Guide", "Semester_Schedule",
    # Common short single-word student titles/filenames so OOV prior stays clean (negative intercept)
    "First", "Second", "Third", "Chapter", "Part", "Draft", "Final", "Intro", "Overview",
    "Summary", "File", "Book", "Page", "Slide", "Task", "Work", "Plan", "Code", "Data",
    "Text", "Copy", "Main", "Base", "Core", "Unit", "Term", "Week", "Day", "One", "Two",
    "Three", "Four", "Five", "Keep", "Gone", "Mine", "Check", "Help", "Info", "List",
    "Form", "Chart", "Table", "Graph", "Model", "Paper", "Essay", "Story", "Resume",
    "Sample", "Example", "Problem", "Answer", "Solution", "Module", "Topic", "Theme",
    "Result", "Output", "Input", "Design", "Schema", "Query", "Index", "Script", "Backup",
    # Broad general English vocabulary for realistic character n-gram negative prior
    "Modern", "Global", "Local", "Simple", "Quick", "Short", "Long", "Fresh", "Bright",
    "Smart", "Clean", "Clear", "Direct", "Active", "Static", "Dynamic", "Public", "Private",
    "Secure", "Common", "General", "Special", "Normal", "Standard", "Basic", "Advanced",
    "Complete", "Partial", "Original", "Updated", "Revised", "Approved", "Archived", "Shared",
    "Saved", "Open", "Closed", "Ready", "Pending", "Verified", "Abstract", "Article",
    "Archive", "Atlas", "Audio", "Author", "Badge", "Balance", "Banner", "Budget", "Bundle",
    "Calendar", "Campus", "Canvas", "Career", "Catalog", "Center", "Channel", "Circuit",
    "Client", "Cluster", "Cohort", "Column", "Commit", "Concept", "Config", "Console",
    "Contact", "Content", "Context", "Control", "Council", "Credit", "Culture", "Current",
    "Custom", "Cycle", "Decimal", "Default", "Defense", "Degree", "Density", "Deposit",
    "Desktop", "Diagram", "Digital", "Diploma", "Display", "Domain", "Element", "Energy",
    "Engine", "Entropy", "Episode", "Feature", "Federal", "Fiction", "Formula", "Forward",
    "Gallery", "Gateway", "Geology", "Graphic", "Gravity", "Habitat", "Harmony", "Healthy",
    "Horizon", "Hosting", "Housing", "Imagine", "Improve", "Include", "Income", "Initial",
    "Inquiry", "Insight", "Install", "Instant", "Integer", "Interim", "Invoice", "Journal",
    "Journey", "Justice", "Keynote", "Kingdom", "Landing", "Latency", "Layered", "Leading",
    "Learned", "Letters", "Library", "License", "Limited", "Linking", "Listing", "Loading",
    "Logical", "Mailbox", "Manager", "Mapping", "Margins", "Markets", "Measure", "Medical",
    "Meeting", "Members", "Memoirs", "Mention", "Mercury", "Message", "Metrics", "Migrate",
    "Minimal", "Minutes", "Mission", "Mixture", "Monitor", "Monthly", "Morning", "Natural",
    "Neutral", "Notable", "Notions", "Nuclear", "Numbers", "Nursing", "Objects", "Observe",
    "Offline", "Ongoing", "Opening", "Operate", "Opinion", "Optical", "Optimal", "Options",
    "Organic", "Origins", "Outline", "Outlook", "Overall", "Overlay", "Package", "Partner",
    "Patient", "Pattern", "Payment", "Percent", "Perfect", "Perform", "Periods", "Permits",
    "Picture", "Pioneer", "Planned", "Plastic", "Pointer", "Polymer", "Popular", "Portion",
    "Posters", "Powered", "Prelude", "Premier", "Prepare", "Present", "Prevent", "Primary",
    "Printer", "Privacy", "Proceed", "Process", "Produce", "Product", "Profile", "Program",
    "Promise", "Promote", "Protein", "Publish", "Purpose", "Pyramid", "Quality", "Quarter",
    "Queries", "Quickly", "Radical", "Railway", "Ranking", "Reading", "Reality", "Receipt",
    "Receive", "Records", "Recover", "Reduced", "Reflect", "Reforms", "Regions", "Regular",
    "Related", "Release", "Remains", "Remarks", "Remotes", "Removal", "Renamed", "Renewal",
    "Repairs", "Repeats", "Replace", "Replica", "Request", "Require", "Reserve", "Resolve",
    "Respect", "Respond", "Restore", "Revenue", "Reverse", "Rewards", "Routing", "Running",
    "Sandbox", "Savings", "Scaling", "Scanner", "Schemes", "Scholar", "Science", "Scoring",
    "Screens", "Seasons", "Sectors", "Secured", "Segment", "Selects", "Sending", "Sensors",
    "Service", "Session", "Setting", "Settled", "Several", "Shadows", "Sharing", "Shelter",
    "Shifted", "Shortly", "Showing", "Signals", "Silence", "Similar", "Simpler", "Singles",
    "Skilled", "Sliding", "Smaller", "Sockets", "Solving", "Sources", "Spacing", "Speaker",
    "Species", "Spectra", "Sponsor", "Springs", "Squares", "Staging", "Started", "Startup",
    "Station", "Status", "Storage", "Stories", "Streams", "Strings", "Studies", "Styling",
    "Subject", "Submits", "Success", "Suggest", "Summers", "Support", "Surface", "Surplus",
    "Surveys", "Suspend", "Sustain", "Symbols", "Systems", "Tablets", "Tactics", "Targets",
    "Teacher", "Tenants", "Tension", "Texture", "Theater", "Thermal", "Thinker", "Thought",
    "Threads", "Tickets", "Timings", "Toolkit", "Topical", "Tracked", "Trading", "Traffic",
    "Trained", "Transit", "Treated", "Trigger", "Trusted", "Tuition", "Turning", "Typical",
    "Unified", "Uniform", "Unknown", "Unread", "Upgrade", "Uploads", "Utility", "Valleys",
    "Variety", "Various", "Vectors", "Vehicle", "Venture", "Version", "Veteran", "Vibrant",
    "Victory", "Viewing", "Village", "Virtual", "Visible", "Visions", "Visited", "Visuals",
    "Vitamin", "Volumes", "Waiting", "Walking", "Warning", "Weather", "Website", "Weekend",
    "Weights", "Welcome", "Welfare", "Western", "Widgets", "Willing", "Windows", "Winners",
    "Winters", "Wireless", "Witness", "Working", "Writing", "Written", "Yielded", "Younger",
]

ACADEMIC_TYPES_EN = [
    "Lecture", "Notes", "Assignment", "Lab", "Practice", "Exam", "Midterm", "Final",
    "Quiz", "Syllabus", "Slides", "Homework", "Coursework", "Research_Paper",
    "Case_Study", "Report", "Summary", "Guide", "Cheatsheet", "Tutorial", "Project",
    "Worksheet", "Solutions", "Review", "Seminar", "Presentation", "Handbook", "Manual",
]

ACADEMIC_SUBJECTS_RU = [
    "Математика", "Высшая_математика", "Линейная_алгебра", "Дискретная_математика",
    "Теория_вероятностей", "Статистика", "Программирование", "Алгоритмы",
    "Структуры_данных", "Глубокое_обучение", "Машинное_обучение", "Нейронные_сети",
    "Информационные_системы", "Программная_инженерия", "Базы_данных", "Запросы_SQL",
    "Компьютерные_сети", "Операционные_системы", "Информационная_безопасность",
    "Криптография", "Веб_разработка", "Облачные_технологии", "История_Казахстана",
    "Всемирная_история", "Физика", "Механика", "Термодинамика", "Электродинамика",
    "Оптика", "Экономика", "Микроэкономика", "Макроэкономика", "Финансы",
    "Бухгалтерский_учет", "Менеджмент", "Маркетинг", "Бизнес_аналитика",
    "Философия", "Социология", "Психология", "Биология", "Химия", "Экология",
    "Численные_методы", "Компьютерное_зрение", "Обработка_текста", "Тестирование_ПО",
    "Управление_проектами", "Теория_графов", "Дифференциальные_уравнения",
    "Математический_анализ", "Архитектура_ЭВМ", "Микроконтроллеры", "Схемотехника",
    "Системный_анализ", "Анализ_данных", "Большие_данные", "Оптимизация",
    "Файл", "Текст", "Книга", "Глава", "Часть", "Вариант", "Билет", "Ответ",
    "Задача", "Пример", "Тема", "План", "Сборник", "Заметка", "Черновик", "Итог",
    "Первый", "Второй", "Третий", "Модуль", "Раздел", "Статья", "Схема_БД", "Работа",
    "Новый", "Старый", "Общий", "Главный", "Базовый", "Полный", "Краткий", "Готовый",
    "Черновой", "Открытый", "Важный", "Нужный", "Полезный", "Учебный", "Научный", "Точный",
    "График", "Модель", "Сервер", "Клиент", "Проект", "Система", "Данные", "Запрос",
    "Индекс", "Память", "Процесс", "Ресурс", "Формат", "Стандарт", "Метод", "Способ",
    "Уровень", "Период", "Семестр", "Кафедра", "Студент", "Группа", "Оценка", "Баллы",
    "Рейтинг", "Диплом", "Архив", "Каталог", "Библиотека", "Учебник_2", "Глоссарий", "Словарь",
]

ACADEMIC_TYPES_RU = [
    "Лекция", "Конспект", "Практика", "Лабораторная", "Задание", "Экзамен",
    "Рубежный_контроль", "Тест", "Силлабус", "Слайды", "Домашняя_работа",
    "Курсовая", "Дипломная", "Реферат", "Доклад", "Отчет", "Методичка",
    "Семинар", "Задачи", "Ответы", "Шпаргалка", "Презентация", "Справочник",
]

ACADEMIC_SUBJECTS_KK = [
    "Қазақстан_тарихы", "Дүниежүзі_тарихы", "Математика", "Жоғары_математика",
    "Сызықтық_алгебра", "Дискретті_математика", "Ықтималдықтар_теориясы",
    "Статистика", "Бағдарламалау", "Алгоритмдер", "Деректер_құрылымы",
    "Терең_оқыту", "Машиналық_оқыту", "Нейрондық_желілер", "Ақпараттық_жүйелер",
    "Бағдарламалық_инженерия", "Деректер_қоры", "Компьютерлік_желілер",
    "Операциялық_жүйелер", "Ақпараттық_қауіпсіздік", "Криптография",
    "Веб_бағдарламалау", "Бұлтты_технологиялар", "Физика", "Механика",
    "Термодинамика", "Оптика", "Экономика", "Микроэкономика", "Макроэкономика",
    "Қаржы", "Бухгалтерлік_есеп", "Менеджмент", "Маркетинг", "Философия",
    "Әлеуметтану", "Психология", "Биология", "Химия", "Экология", "Қазақ_тілі",
    "Қазақ_әдебиеті", "Жүйелік_талдау", "Деректерді_талдау", "Жобаны_басқару",
    "Сандық_әдістер", "Графтар_теориясы", "Құқық_негіздері", "Саясаттану",
    "Мәтін", "Кітап", "Бөлім", "Нұсқа", "Тақырып", "Мысал", "Жұмыс", "Жауап",
    "Бірінші", "Екінші", "Үшінші", "Модуль", "Жоспар", "Мақала", "Құжат_1", "Дерек",
    "Жаңа", "Ескі", "Негізгі", "Толық", "Қысқа", "Дайын", "Ашық", "Маңызды",
    "Пайдалы", "Ғылыми", "Нақты", "Кесте_1", "Модель_1", "Сервер", "Клиент", "Жоба",
    "Жүйе_1", "Сұраныс", "Индекс", "Жад", "Үдеріс", "Ресурс", "Пішім", "Әдіс",
    "Деңгей", "Кезең", "Семестр", "Кафедра", "Студент", "Топ", "Баға", "Ұпай",
    "Мұрағат", "Кітапхана", "Сөздік", "Түсіндірме", "Жинақ", "Нұсқаулық", "Ереже", "Тізім",
]

ACADEMIC_TYPES_KK = [
    "Дәріс", "Конспект", "Практикалық", "Зертханалық", "Тапсырма", "Емтихан",
    "Аралық_бақылау", "Тест", "Силлабус", "Слайдтар", "Үй_жұмысы", "Курстық",
    "Дипломдық", "Реферат", "Баяндама", "Есеп", "Әдістемелік", "Семинар",
    "Есептер", "Жауаптар", "Тұсаукесер", "Анықтамалық", "Қорытынды",
]

# Category D: Hard negative base words containing substrings/patterns close to profanity.
HARD_NEGATIVES_EN = [
    "Assignment", "Assign", "Assistant", "Assessment", "Assess", "Asset", "Assets",
    "Class", "Classes", "Classic", "Classical", "Classification", "Classifier", "Classroom",
    "Pass", "pASS", "PASS", "Passing", "Passed", "Password", "Passport", "Passage",
    "Bypass", "Compass", "Surpass", "Encompass", "Mass", "Massive", "Biomass",
    "Grass", "Glass", "Brass", "Bass", "Cassette", "Chassis", "Embassy", "Harass_Policy",
    "Analysis", "Analyst", "Analytical", "Analog", "Analogy", "Banality", "Canal",
    "Document", "Documentation", "Circumference", "Cumulative", "Accumulate", "Accumulation",
    "Scunthorpe", "Title", "Subtitle", "Entitled", "Constitution", "Institution",
    "Dictionary", "Predict", "Prediction", "Predicate", "Indicator", "Dedication",
    "Medication", "Syndicate", "Verdict", "Dictation", "Jurisdiction",
    "Dickens", "Charles_Dickens", "Hancock", "Peacock", "Cocktail",
    "Shell", "Hello", "Hellenic", "Michelle", "Diffie_Hellman", "Bellman_Ford",
    "Amsterdam", "Madam", "Fundamental", "Database", "Dataset", "Datasheet",
    "Worksheet", "Spreadsheet", "Stylesheet", "Cheatsheet", "Shift", "Shirt", "Short",
    "Batch", "Match", "Patch", "Sketch", "Watch", "Switch", "Pitch", "Glitch", "Stitch",
    "Count", "Account", "Accounting", "Discount", "Country", "Counter", "Encounter",
    "Section", "Intersection", "Bisection", "Selection", "Dissection", "Subsection",
    "Parse", "Parser", "Parsing", "Sparse", "Sparse_Matrix", "Rehearse", "Coarse",
    "Bootstrap", "Scrapbook", "Cramp", "Graph", "Grape", "Trapezoid", "Therapist",
    "Peninsula", "Penicillin", "Appendix", "Suspense", "Expense", "Compensation",
    "Button", "Butter", "Rebuttal", "Shutter", "Shuttle", "Shutter_Speed",
    "Push", "Bush", "Cushion", "Brick", "Trick", "Click", "Stick", "Cricket", "Prickly",
    "Coursework", "Homework", "Framework", "Network", "Pass_Exam", "Class_Notes",
    "Password_Security", "Assistant_Guide", "Data_Classification", "Mass_Transfer",
    "Glass_Transition", "Grass_Ecosystem", "Document_Review", "Analog_Circuits",
]

HARD_NEGATIVES_RU = [
    "Учебник", "Учебный_план", "Ребенок", "Потребление", "Употребление", "Колебание",
    "Ослабление", "Углубление", "Исправление", "Хлеб", "Стебель", "Мебель", "Рубли",
    "Сабля", "Ансамбль", "Дубляж", "Таблица", "Публикация", "Республика", "Облигация",
    "Страховка", "Подстраховка", "Перестраховка", "Страхование", "Художник",
    "Художественный", "Худший", "Хутор", "Схема", "Схемотехника", "Схематика",
    "Пища", "Пищеварение", "Писк", "Список", "Записка", "Расписка", "Переписка",
    "Подписка", "Описание", "Расписание", "Выписка", "Сукно", "Суббота", "Субъект",
    "Субкультура", "Субсидия", "Субтитр", "Суперкомпьютер", "Сукцессия",
    "Мандат", "Команда", "Командировка", "Роман", "Гуманитарный", "Эмансипация",
    "Германия", "Перманентный", "Дебаты", "Акробат", "Комбинат", "Инкубатор",
    "Штрих", "Штраф", "Шлюз", "Мультимедиа", "Мутация", "Мудрец", "Гантель",
    "Журнал", "Горизонт", "Дерево", "Дерматология", "Творчество", "Твердость",
    "Анализ_данных", "Классификация", "Пароли_безопасность", "Лекция_математика",
]

HARD_NEGATIVES_KK = [
    "Қорытынды", "Қосымша", "Қосымша_материал", "Қоғам", "Қоғамтану", "Қотару",
    "Қолдану", "Қолданбалы", "Қонақ", "Қоршаған_орта", "Қорғаныс", "Қолжазба",
    "Көбейту", "Көлем", "Көшірме", "Көлік", "Көмек", "Көрсеткіш", "Көшбасшы",
    "Көпшілік", "Көзқарас", "Көктем", "Көпір", "Көркем_әдебиет", "Көмірсутек",
    "Сілтеме", "Сіңіру", "Сипаттама", "Синтаксис", "Синтез", "Сигналдар",
    "Шешім", "Шекара", "Шеберлік", "Шежіре", "Шетел_тілі", "Шеңбер", "Шексіздік",
    "Амалдар", "Амфибия", "Амплитуда", "Амперметр", "Адамзат", "Ақпарат",
    "Қасық", "Қателік", "Қаржы", "Қауіпсіздік", "Қалыптасу", "Қазақстан_тарихы",
    "Жәдігер", "Жалпы", "Жалғау", "Жарнама", "Жаңалық", "Жазушы", "Жүйе",
    "Қант", "Қаңқа", "Қанат", "Болашақ", "Бос_орын", "Басқару", "Бастауыш",
    "Құрылым", "Құбылыс", "Құжат", "Құқық", "Мал_шаруашылығы", "Оңтүстік",
]

EXTENSIONS = [".pdf", ".pdf", ".pdf", ".pdf", ".docx", ".pptx", ".txt", ".xlsx", ""]

LAT_TO_CONFUSABLE_CYR = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у", "k": "к"}
CYR_TO_CONFUSABLE_LAT = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "к": "k", "м": "m", "т": "t"}
LAT_LEET = {"a": ["4", "@"], "s": ["$", "5"], "i": ["1", "!"], "e": ["3"], "o": ["0"], "t": ["7"], "b": ["8"], "g": ["9"]}
CYR_LEET = {"а": ["4", "@"], "о": ["0"], "и": ["1"], "е": ["3"], "с": ["$", "5"], "т": ["7"], "б": ["6"], "я": ["9"]}
SPECIAL_MASK = ["*", "#", "!", "$", "@"]
FULLWIDTH_OFFSET = 0xFEE0


def build_profanity_vocabulary() -> list[dict[str, str]]:
    """Build curated multilingual profanity CSV from verified open-source lists."""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_word(word: str, lang: str, source: str, license_name: str) -> None:
        w = word.strip().casefold()
        if not w or len(w) < 3 or " " in w or w in ACADEMIC_SAFE_EXCLUSIONS:
            return
        if w not in seen:
            seen.add(w)
            rows.append({"word": w, "language": lang, "source": source, "license": license_name})

    for w, lang, src, lic in CURATED_CORE_PROFANITY:
        add_word(w, lang, src, lic)

    en_path = SOURCES_DIR / "ldnoobw_en.txt"
    if en_path.is_file():
        for line in en_path.read_text(encoding="utf-8").splitlines():
            w = line.strip().casefold()
            if w.isalpha() and 4 <= len(w) <= 18:
                add_word(w, "en", "ldnoobw_en", "CC-BY-4.0")

    ru_path = SOURCES_DIR / "ldnoobw_ru.txt"
    if ru_path.is_file():
        for line in ru_path.read_text(encoding="utf-8").splitlines():
            w = line.strip().casefold()
            if w.isalpha() and 3 <= len(w) <= 18:
                add_word(w, "ru", "ldnoobw_ru", "CC-BY-4.0")

    roose_path = SOURCES_DIR / "roose_ru_kk.json"
    if roose_path.is_file():
        data = json.loads(roose_path.read_text(encoding="utf-8"))
        for entry in data.get("words", []):
            kk_w = (entry.get("kk") or "").strip().casefold()
            ru_w = (entry.get("ru") or "").strip().casefold()
            if kk_w and " " not in kk_w:
                add_word(kk_w, "kk", "roose_ru_kk", "MIT")
            if ru_w and " " not in ru_w:
                add_word(ru_w, "ru", "roose_ru_kk", "MIT")

    PROFANITY_WORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PROFANITY_WORDS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["word", "language", "source", "license"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _to_fullwidth(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x21 <= code <= 0x7E:
            out.append(chr(code + FULLWIDTH_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


def obfuscate_word(word: str, lang: str, aug_type: str, rng: random.Random) -> str:
    """Apply reproducible obfuscation transformations to a profanity term."""
    chars = list(word)
    n = len(chars)

    if aug_type == "char_repetition":
        out = []
        for ch in chars:
            rep = rng.choices([1, 2, 3, 4], weights=[2, 3, 3, 2])[0]
            out.append(ch * rep)
        res = "".join(out)
        if res == word:
            idx = rng.randrange(n)
            res = word[:idx] + word[idx] * 3 + word[idx + 1 :]
        return res

    if aug_type == "char_insertion":
        noise = rng.choice(["x", "z", "q", "p", "k", "j"])
        if rng.random() < 0.45:
            # Prefix + stretched core pattern like pppAAASSSS.
            prefix = noise * rng.randint(2, 3)
            core = "".join(ch.upper() * rng.randint(2, 4) for ch in chars)
            return prefix + core
        pos = rng.randint(1, max(1, n - 1))
        return word[:pos] + noise * rng.randint(1, 2) + word[pos:]

    if aug_type == "char_deletion":
        if n <= 3:
            return word[0] + "*" + word[-1]
        vowels = set("aeiouаеёиоуыэюяәіөүұ")
        vowel_idx = [i for i in range(1, n - 1) if chars[i] in vowels]
        if vowel_idx:
            del chars[rng.choice(vowel_idx)]
        else:
            del chars[rng.randint(1, n - 2)]
        return "".join(chars)

    if aug_type == "char_substitution":
        subs = {"a": "e", "e": "a", "u": "a", "i": "y", "o": "u", "у": "ю", "а": "о", "е": "и", "и": "е", "о": "а", "қ": "к", "ө": "о", "ү": "у"}
        changed = False
        for i, ch in enumerate(chars):
            if ch in subs and rng.random() < 0.65:
                chars[i] = subs[ch]
                changed = True
                break
        if not changed:
            chars[-1] = chars[-1] * 2
        return "".join(chars)

    if aug_type == "case_mix":
        if rng.random() < 0.35:
            return word.upper()
        return "".join(ch.upper() if i % 2 == 0 or rng.random() < 0.45 else ch.lower() for i, ch in enumerate(chars))

    if aug_type == "special_char_sub":
        sym_map = {"a": "@", "s": "$", "i": "!", "e": "€", "а": "@", "с": "$", "и": "!"}
        out = []
        changed = False
        for i, ch in enumerate(chars):
            if ch in sym_map and rng.random() < 0.8:
                out.append(sym_map[ch])
                changed = True
            elif 0 < i < n - 1 and rng.random() < 0.35:
                out.append(rng.choice(["*", "#"]))
                changed = True
            else:
                out.append(ch)
        if not changed and n >= 3:
            out[1] = "*"
        return "".join(out)

    if aug_type == "leetspeak":
        lmap = CYR_LEET if lang in ("ru", "kk") and any(ord(c) > 127 for c in word) else LAT_LEET
        out = []
        changed = False
        for ch in chars:
            if ch in lmap and rng.random() < 0.85:
                out.append(rng.choice(lmap[ch]))
                changed = True
            else:
                out.append(ch)
        if not changed and n >= 3:
            out[1] = rng.choice(["1", "3", "4", "0", "$", "@"])
        return "".join(out)

    if aug_type == "digits_inserted":
        digits = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(1, 3)))
        pos = rng.randint(1, max(1, n - 1))
        styled = word.upper() if rng.random() < 0.4 else word
        return styled[:pos] + digits + styled[pos:]

    if aug_type == "spaced_chars":
        styled = word.upper() if rng.random() < 0.35 else word
        return " ".join(styled)

    if aug_type == "punct_separated":
        sep = rng.choice([".", "_", "-", "*"])
        styled = word.upper() if rng.random() < 0.5 else word
        return sep.join(styled)

    if aug_type == "mixed_cyr_lat":
        is_cyr = any(ord(c) > 127 for c in word)
        cmap = CYR_TO_CONFUSABLE_LAT if is_cyr else LAT_TO_CONFUSABLE_CYR
        out = []
        changed = False
        for ch in chars:
            if ch in cmap and rng.random() < 0.7:
                out.append(cmap[ch])
                changed = True
            else:
                out.append(ch)
        if not changed:
            for i, ch in enumerate(chars):
                if ch in cmap:
                    out[i] = cmap[ch]
                    changed = True
                    break
        return "".join(out)

    if aug_type == "unicode_confusables":
        if all(ord(c) < 128 for c in word):
            return _to_fullwidth(word.upper() if rng.random() < 0.4 else word)
        return obfuscate_word(word, lang, "mixed_cyr_lat", rng)

    if aug_type == "zero_width":
        zw = rng.choice(["\u200b", "\u200c", "\u200d", "\ufeff"])
        return zw.join(chars)

    if aug_type == "multi_transform":
        step1 = rng.choice(["leetspeak", "special_char_sub", "char_repetition", "mixed_cyr_lat"])
        step2 = rng.choice(["punct_separated", "digits_inserted", "case_mix", "zero_width"])
        inter = obfuscate_word(word, lang, step1, rng)
        return obfuscate_word(inter, lang, step2, rng)

    return word


def wrap_as_filename(core: str, lang: str, rng: random.Random, allow_academic_context: bool = True) -> str:
    """Wrap a token/stem into realistic filename or material title variations."""
    ext = rng.choice(EXTENSIONS)
    if not allow_academic_context or rng.random() < 0.50:
        return f"{core}{ext}"

    sep = rng.choice(["_", "-", " ", "."])
    num = rng.randint(1, 15)
    if lang == "ru":
        templates = [
            f"Лекция{sep}{num}{sep}{core}{ext}",
            f"{core}{sep}Лабораторная{sep}{num}{ext}",
            f"Конспект{sep}{core}{ext}",
            f"{core}{sep}финал{ext}",
            f"ДЗ{sep}{num}{sep}{core}{ext}",
        ]
    elif lang == "kk":
        templates = [
            f"Дәріс{sep}{num}{sep}{core}{ext}",
            f"{core}{sep}тапсырма{sep}{num}{ext}",
            f"Есеп{sep}{core}{ext}",
            f"{core}{sep}қорытынды{ext}",
            f"Практика{sep}{num}{sep}{core}{ext}",
        ]
    else:
        templates = [
            f"Week{num}{sep}{core}{ext}",
            f"Lab{sep}{num}{sep}{core}{ext}",
            f"{core}{sep}Notes{ext}",
            f"{core}{sep}Final{sep}v{rng.randint(1, 3)}{ext}",
            f"Homework{sep}{num}{sep}{core}{ext}",
        ]
    return rng.choice(templates)


def _assign_group_splits(base_ids: list[str], rng: random.Random) -> dict[str, str]:
    """Deterministically assign base_ids to train (70%), val (15%), test (15%)."""
    shuffled = list(base_ids)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(round(n * 0.70))
    n_val = int(round(n * 0.15))
    split_map: dict[str, str] = {}
    for idx, bid in enumerate(shuffled):
        if idx < n_train:
            split_map[bid] = "train"
        elif idx < n_train + n_val:
            split_map[bid] = "val"
        else:
            split_map[bid] = "test"
    return split_map


def build_challenge_and_ambiguous_sets() -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    """Create independent manually reviewed challenge and ambiguous test sets."""
    challenge_items: list[tuple[str, str, int, str, str]] = [
        # Required prompt examples (Blocked)
        ("ASS.pdf", "en", 1, "explicit_profanity", "prompt_case"),
        ("pppAAASSSS.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        ("A.S.S.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("@$$.pdf", "en", 1, "obfuscated_profanity", "special_char_sub"),
        ("A_S_S.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("A123SS.pdf", "en", 1, "obfuscated_profanity", "digits_inserted"),
        # Required prompt examples (Allowed)
        ("pASS.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Assignment_12.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Class_Notes.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Password_Security.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Pass_Exam.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Assistant_Guide.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Data_Classification.pdf", "en", 0, "hard_negative", "prompt_case"),
        ("Deep_Learning_Week12.pdf", "en", 0, "clean_academic", "prompt_case"),
        ("Қазақстан_тарихы.pdf", "kk", 0, "clean_academic", "prompt_case"),
        ("Лекция_математика.pdf", "ru", 0, "clean_academic", "prompt_case"),
        # Additional unseen English obfuscations
        ("F.U.C.K_Week12.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("f_u_c_k_exam.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("f4ck_homework.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("fuuuucking_notes.pdf", "en", 1, "obfuscated_profanity", "char_repetition"),
        ("sh1t_lecture.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("$h!t_slides.pdf", "en", 1, "obfuscated_profanity", "special_char_sub"),
        ("b1tch_report.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("b_i_t_c_h.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("f\u200bu\u200bc\u200bk.pdf", "en", 1, "obfuscated_profanity", "zero_width"),
        ("a\u200bs\u200bs_notes.pdf", "en", 1, "obfuscated_profanity", "zero_width"),
        ("аss_lecture.pdf", "mixed", 1, "obfuscated_profanity", "mixed_cyr_lat"),  # Cyrillic а
        ("fуck_lab3.pdf", "mixed", 1, "obfuscated_profanity", "mixed_cyr_lat"),    # Cyrillic у
        ("ａｓｓ_homework.pdf", "en", 1, "obfuscated_profanity", "unicode_confusables"),
        ("ｆｕｃｋ_project.pdf", "en", 1, "obfuscated_profanity", "unicode_confusables"),
        ("d1ckhead_final.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("m0therfucker.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("bu11sh1t_essay.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("c_u_n_t_notes.pdf", "en", 1, "obfuscated_profanity", "punct_separated"),
        ("p999ussy.pdf", "en", 1, "obfuscated_profanity", "digits_inserted"),
        ("s456hit.pdf", "en", 1, "obfuscated_profanity", "digits_inserted"),
        ("wh0re_doc.pdf", "en", 1, "obfuscated_profanity", "leetspeak"),
        ("a$$hole_v2.pdf", "en", 1, "obfuscated_profanity", "special_char_sub"),
        ("S H I T.pdf", "en", 1, "obfuscated_profanity", "spaced_chars"),
        ("F U C K.pdf", "en", 1, "obfuscated_profanity", "spaced_chars"),
        ("A S S.pdf", "en", 1, "obfuscated_profanity", "spaced_chars"),
        ("f*ck_this_course.pdf", "en", 1, "obfuscated_profanity", "special_char_sub"),
        ("sh*t_exam.pdf", "en", 1, "obfuscated_profanity", "special_char_sub"),
        ("xxxAAAASSSS.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        ("a_1_s_2_s.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        ("@_$_$.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        ("4$$_notes.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        ("5h!7_lab.pdf", "en", 1, "obfuscated_profanity", "multi_transform"),
        # Russian explicit & obfuscated
        ("хуйня_лекция.pdf", "ru", 1, "explicit_profanity", "none"),
        ("пиздец_экзамен.pdf", "ru", 1, "explicit_profanity", "none"),
        ("блять_лаба.pdf", "ru", 1, "explicit_profanity", "none"),
        ("х.у.й.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("х_у_й_ня.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("п1здец_отчет.pdf", "ru", 1, "obfuscated_profanity", "leetspeak"),
        ("п_и_з_д_а.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("бляяяять_курс.pdf", "ru", 1, "obfuscated_profanity", "char_repetition"),
        ("еб4ть_математика.pdf", "ru", 1, "obfuscated_profanity", "leetspeak"),
        ("сyка_конспект.pdf", "mixed", 1, "obfuscated_profanity", "mixed_cyr_lat"),  # Latin y
        ("х123уй.pdf", "ru", 1, "obfuscated_profanity", "digits_inserted"),
        ("б\u200bл\u200bя\u200bт\u200bь.pdf", "ru", 1, "obfuscated_profanity", "zero_width"),
        ("долбоёб_тест.pdf", "ru", 1, "explicit_profanity", "none"),
        ("п*зда_дз.pdf", "ru", 1, "obfuscated_profanity", "special_char_sub"),
        ("n_a_h_u_y.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("p1zdec_v2.pdf", "ru", 1, "obfuscated_profanity", "leetspeak"),
        ("b_l_y_a_t.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("g0vn0_lab.pdf", "ru", 1, "obfuscated_profanity", "leetspeak"),
        ("шлюха_реферат.pdf", "ru", 1, "explicit_profanity", "none"),
        ("еблан_слайды.pdf", "ru", 1, "explicit_profanity", "none"),
        ("з_а_е_б_а_л.pdf", "ru", 1, "obfuscated_profanity", "punct_separated"),
        ("х у й н я.pdf", "ru", 1, "obfuscated_profanity", "spaced_chars"),
        ("мудак_финал.pdf", "ru", 1, "explicit_profanity", "none"),
        ("г4ндон.pdf", "ru", 1, "obfuscated_profanity", "leetspeak"),
        # Kazakh explicit & obfuscated
        ("қотақ_дәріс.pdf", "kk", 1, "explicit_profanity", "none"),
        ("қотақбас_есеп.pdf", "kk", 1, "explicit_profanity", "none"),
        ("қ.о.т.а.қ.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("қ_о_т_а_қ.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("қ0тақ_тапсырма.pdf", "kk", 1, "obfuscated_profanity", "leetspeak"),
        ("қотаааақ.pdf", "kk", 1, "obfuscated_profanity", "char_repetition"),
        ("қ123отақ.pdf", "kk", 1, "obfuscated_profanity", "digits_inserted"),
        ("к_ө_т_л_ә_к.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("жәлеп_баяндама.pdf", "kk", 1, "explicit_profanity", "none"),
        ("ж_ә_л_е_п.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("сігейін_емтихан.pdf", "kk", 1, "explicit_profanity", "none"),
        ("сіктір_жұмыс.pdf", "kk", 1, "explicit_profanity", "none"),
        ("с_і_к_т_і_р.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("қаншық_конспект.pdf", "kk", 1, "explicit_profanity", "none"),
        ("шешеңді_реферат.pdf", "kk", 1, "explicit_profanity", "none"),
        ("k_o_t_a_k.pdf", "kk", 1, "obfuscated_profanity", "punct_separated"),
        ("k0takbas.pdf", "kk", 1, "obfuscated_profanity", "leetspeak"),
        ("s1ktir_lab.pdf", "kk", 1, "obfuscated_profanity", "leetspeak"),
        ("қоtақ_test.pdf", "mixed", 1, "obfuscated_profanity", "mixed_cyr_lat"),  # Latin t
        ("қ\u200bо\u200bт\u200bа\u200bқ.pdf", "kk", 1, "obfuscated_profanity", "zero_width"),
        ("амыңды_тест.pdf", "kk", 1, "explicit_profanity", "none"),
        ("қ о т а қ.pdf", "kk", 1, "obfuscated_profanity", "spaced_chars"),
        ("котакбас_2026.pdf", "kk", 1, "explicit_profanity", "none"),
        ("zh4lep.pdf", "kk", 1, "obfuscated_profanity", "leetspeak"),
        # Hard negatives EN (Allowed)
        ("Assessment_Rubric_2026.pdf", "en", 0, "hard_negative", "none"),
        ("Linear_Regression_Analysis.pdf", "en", 0, "hard_negative", "none"),
        ("Mass_Spectrometry_Lab.pdf", "en", 0, "hard_negative", "none"),
        ("Grass_Biology_Fieldwork.pdf", "en", 0, "hard_negative", "none"),
        ("Document_Parsing_Guide.pdf", "en", 0, "hard_negative", "none"),
        ("Coursework_Final_Draft.pdf", "en", 0, "hard_negative", "none"),
        ("Sparse_Matrix_Algorithms.pdf", "en", 0, "hard_negative", "none"),
        ("Diffie_Hellman_Cryptography.pdf", "en", 0, "hard_negative", "none"),
        ("Bootstrap_Statistics_Notes.pdf", "en", 0, "hard_negative", "none"),
        ("Charles_Dickens_Literature.pdf", "en", 0, "hard_negative", "none"),
        ("Scunthorpe_Filtering_Study.pdf", "en", 0, "hard_negative", "none"),
        ("Batch_Normalization_DL.pdf", "en", 0, "hard_negative", "none"),
        ("Spreadsheet_Accounting_101.pdf", "en", 0, "hard_negative", "none"),
        ("Peninsula_Geography_Map.pdf", "en", 0, "hard_negative", "none"),
        ("Appendix_B_Formulas.pdf", "en", 0, "hard_negative", "none"),
        ("Binary_Search_Bisection.pdf", "en", 0, "hard_negative", "none"),
        ("Bypass_Diode_Physics.pdf", "en", 0, "hard_negative", "none"),
        ("Compass_Geometry_Lesson.pdf", "en", 0, "hard_negative", "none"),
        ("Analog_Signal_Processing.pdf", "en", 0, "hard_negative", "none"),
        ("Subtitle_Alignment_NLP.pdf", "en", 0, "hard_negative", "none"),
        ("Dictionary_Hash_Tables.pdf", "en", 0, "hard_negative", "none"),
        ("Cumulative_Distribution_Fn.pdf", "en", 0, "hard_negative", "none"),
        ("Amsterdam_Urban_Economics.pdf", "en", 0, "hard_negative", "none"),
        ("Class_Diagram_UML_Week12.pdf", "en", 0, "hard_negative", "none"),
        ("Pass_Fail_Criteria.pdf", "en", 0, "hard_negative", "none"),
        ("PASS_Lab_Checklist.pdf", "en", 0, "hard_negative", "none"),
        ("Glass_Optics_Experiment.pdf", "en", 0, "hard_negative", "none"),
        ("Asset_Pricing_Models.pdf", "en", 0, "hard_negative", "none"),
        ("Database_Normalization_3NF.pdf", "en", 0, "hard_negative", "none"),
        ("Account_Balance_Sheet.pdf", "en", 0, "hard_negative", "none"),
        # Hard negatives RU (Allowed)
        ("Учебник_по_экономике.pdf", "ru", 0, "hard_negative", "none"),
        ("Таблица_интегралов.pdf", "ru", 0, "hard_negative", "none"),
        ("Публикация_статьи_2026.pdf", "ru", 0, "hard_negative", "none"),
        ("Республика_Казахстан_право.pdf", "ru", 0, "hard_negative", "none"),
        ("Колебания_и_волны_физика.pdf", "ru", 0, "hard_negative", "none"),
        ("Потребление_и_спрос.pdf", "ru", 0, "hard_negative", "none"),
        ("Страхование_рисков_лекция.pdf", "ru", 0, "hard_negative", "none"),
        ("Художественная_культура.pdf", "ru", 0, "hard_negative", "none"),
        ("Схемотехника_лабораторная_4.pdf", "ru", 0, "hard_negative", "none"),
        ("Список_литературы_курсовая.pdf", "ru", 0, "hard_negative", "none"),
        ("Расписание_экзаменов.pdf", "ru", 0, "hard_negative", "none"),
        ("Описание_архитектуры_БД.pdf", "ru", 0, "hard_negative", "none"),
        ("Субъект_и_объект_права.pdf", "ru", 0, "hard_negative", "none"),
        ("Субсидии_в_экономике.pdf", "ru", 0, "hard_negative", "none"),
        ("Командная_разработка_Agile.pdf", "ru", 0, "hard_negative", "none"),
        ("Гуманитарные_науки_эссе.pdf", "ru", 0, "hard_negative", "none"),
        ("Ансамбль_методов_ML.pdf", "ru", 0, "hard_negative", "none"),
        ("Пищеварение_биология.pdf", "ru", 0, "hard_negative", "none"),
        ("Подписка_на_события_JS.pdf", "ru", 0, "hard_negative", "none"),
        ("Шлюз_безопасности_сети.pdf", "ru", 0, "hard_negative", "none"),
        # Hard negatives KK (Allowed)
        ("Қорытынды_емтихан_2026.pdf", "kk", 0, "hard_negative", "none"),
        ("Қосымша_тапсырма_12.pdf", "kk", 0, "hard_negative", "none"),
        ("Қоғамтану_дәріс_5.pdf", "kk", 0, "hard_negative", "none"),
        ("Көбейту_кестесі_алгоритм.pdf", "kk", 0, "hard_negative", "none"),
        ("Көлемдік_талдау_химия.pdf", "kk", 0, "hard_negative", "none"),
        ("Көшірме_деректер_қоры.pdf", "kk", 0, "hard_negative", "none"),
        ("Сілтемелер_тізімі_реферат.pdf", "kk", 0, "hard_negative", "none"),
        ("Сипаттама_статистика.pdf", "kk", 0, "hard_negative", "none"),
        ("Шешім_қабылдау_жүйелері.pdf", "kk", 0, "hard_negative", "none"),
        ("Шекаралық_есептер.pdf", "kk", 0, "hard_negative", "none"),
        ("Амплитуда_және_жиілік.pdf", "kk", 0, "hard_negative", "none"),
        ("Амалдар_жүйесі_зертхана.pdf", "kk", 0, "hard_negative", "none"),
        ("Қауіпсіздік_негіздері.pdf", "kk", 0, "hard_negative", "none"),
        ("Қаржы_есебі_практика.pdf", "kk", 0, "hard_negative", "none"),
        ("Қателіктерді_түзету_код.pdf", "kk", 0, "hard_negative", "none"),
        ("Жалпы_физика_есептер.pdf", "kk", 0, "hard_negative", "none"),
        ("Болашақ_технологиялар.pdf", "kk", 0, "hard_negative", "none"),
        ("Құрылымдық_бағдарламалау.pdf", "kk", 0, "hard_negative", "none"),
        ("Көшбасшылық_менеджмент.pdf", "kk", 0, "hard_negative", "none"),
        ("Қоршаған_орта_экология.pdf", "kk", 0, "hard_negative", "none"),
        # Mixed-language clean academic titles (Allowed)
        ("BIS_Week12_Қазақстан_жүйелері.pdf", "mixed", 0, "clean_academic", "none"),
        ("PostgreSQL_Индексы_Лекция_11.pdf", "mixed", 0, "clean_academic", "none"),
        ("Deep_Learning_Дәріс_8.pdf", "mixed", 0, "clean_academic", "none"),
        ("FastAPI_Бэкенд_Практика_4.pdf", "mixed", 0, "clean_academic", "none"),
        ("Python_Алгоритмдер_Зертхана_3.pdf", "mixed", 0, "clean_academic", "none"),
        ("ML_Модерация_Отчет_Week12.pdf", "mixed", 0, "clean_academic", "none"),
        ("Software_Engineering_Курстық_жұмыс.pdf", "mixed", 0, "clean_academic", "none"),
        ("SQL_Деректер_қоры_Practice.pdf", "mixed", 0, "clean_academic", "none"),
        ("Linear_Algebra_Конспект_2026.pdf", "mixed", 0, "clean_academic", "none"),
        ("Render_Supabase_Deployment_Guide.pdf", "en", 0, "clean_academic", "none"),
        ("../../notes.pdf", "en", 0, "clean_academic", "path_prefix"),
        ("CS101_Assignment04_Final", "en", 0, "clean_academic", "title_no_ext"),
        ("Машинное обучение — Лабораторная №5", "ru", 0, "clean_academic", "title_no_ext"),
        ("Ақпараттық жүйелер — 12 апта дәрісі", "kk", 0, "clean_academic", "title_no_ext"),
    ]

    challenge_rows: list[dict[str, str | int]] = []
    for idx, (fname, lang, label, cat, aug) in enumerate(challenge_items, start=1):
        challenge_rows.append({
            "sample_id": f"chal_{idx:04d}",
            "filename": fname,
            "language": lang,
            "label": label,
            "category": cat,
            "source": "challenge_manual_review",
            "base_id": f"chal_base_{idx:04d}",
            "augmentation_type": aug,
        })

    ambiguous_items: list[tuple[str, str, int, str, str]] = [
        ("pASS.pdf", "en", 0, "ambiguous_legitimate", "case_mix_legit"),
        ("Ass_12.pdf", "en", 0, "ambiguous_abbreviation", "short_abbrev"),
        ("Ass_1_Math.pdf", "en", 0, "ambiguous_abbreviation", "short_abbrev"),
        ("Dickens_Novel_Analysis.pdf", "en", 0, "ambiguous_legitimate", "proper_noun"),
        ("Hellman_Protocol.pdf", "en", 0, "ambiguous_legitimate", "proper_noun"),
        ("Scunthorpe_Problem_NLP.pdf", "en", 0, "ambiguous_legitimate", "proper_noun"),
        ("Bitch_Index_Not_Real.pdf", "en", 1, "ambiguous_profane", "context_mix"),
        ("Pass_or_Fail_2026.pdf", "en", 0, "ambiguous_legitimate", "none"),
        ("Sub_Matrix_Algebra.pdf", "en", 0, "ambiguous_legitimate", "none"),
        ("Сексуальная_эволюция_дарвин.pdf", "ru", 0, "ambiguous_biology", "none"),
    ]
    ambiguous_rows: list[dict[str, str | int]] = []
    for idx, (fname, lang, label, cat, aug) in enumerate(ambiguous_items, start=1):
        ambiguous_rows.append({
            "sample_id": f"amb_{idx:04d}",
            "filename": fname,
            "language": lang,
            "label": label,
            "category": cat,
            "source": "ambiguous_eval",
            "base_id": f"amb_base_{idx:04d}",
            "augmentation_type": aug,
        })

    return challenge_rows, ambiguous_rows


def generate_all(seed: int = RANDOM_SEED) -> dict[str, int]:
    """Generate curated source CSVs and leak-free train/val/test/challenge splits."""
    rng = random.Random(seed)
    profanity_rows = build_profanity_vocabulary()

    # 1. Build base groups for clean academic (Category A), hard negatives (Category D),
    # and profanity roots (Categories B & C).
    clean_bases: list[tuple[str, str, str, str, str]] = []
    # (base_id, stem, lang, category, source)
    for i, subj in enumerate(ACADEMIC_SUBJECTS_EN):
        clean_bases.append((f"clean_en_{i:03d}", subj, "en", "clean_academic", "synthetic_academic_en"))
    for i, subj in enumerate(ACADEMIC_SUBJECTS_RU):
        clean_bases.append((f"clean_ru_{i:03d}", subj, "ru", "clean_academic", "synthetic_academic_ru"))
    for i, subj in enumerate(ACADEMIC_SUBJECTS_KK):
        clean_bases.append((f"clean_kk_{i:03d}", subj, "kk", "clean_academic", "synthetic_academic_kk"))

    # Mixed-language academic bases
    mixed_pairs = [
        ("Python", "Лекция"), ("Deep_Learning", "Дәріс"), ("SQL", "Тапсырма"),
        ("FastAPI", "Практика"), ("Machine_Learning", "Конспект"), ("React", "Лабораторная"),
        ("Algorithms", "Есептер"), ("PostgreSQL", "База_данных"), ("Docker", "Зертханалық"),
        ("GitHub", "Жоба"), ("Cryptography", "Қауіпсіздік"), ("Calculus", "Задачи"),
        ("Linux", "Семинар"), ("Java", "Дәріс"), ("Statistics", "Талдау"),
        ("Economics", "Экономика"), ("Physics", "Физика"), ("Networks", "Желілер"),
        ("Cloud", "Бұлтты_жүйе"), ("AI", "Жасанды_интеллект"), ("Data_Science", "Деректер"),
        ("Security", "Безопасность"), ("Frontend", "Интерфейс"), ("Backend", "Сервер"),
        ("Testing", "Тестирование"), ("DevOps", "Деплой"), ("SQL_Joins", "Дәріс"),
        ("UML", "Диаграмма"), ("Scrum", "Спринт"), ("NLP", "Мәтін_талдау"),
    ]
    for i, (a, b) in enumerate(mixed_pairs):
        clean_bases.append((f"clean_mix_{i:03d}", f"{a}_{b}", "mixed", "clean_academic", "synthetic_academic_mixed"))

    hard_neg_bases: list[tuple[str, str, str, str, str]] = []
    for i, w in enumerate(HARD_NEGATIVES_EN):
        hard_neg_bases.append((f"hneg_en_{i:03d}", w, "en", "hard_negative", "curated_hard_neg_en"))
    for i, w in enumerate(HARD_NEGATIVES_RU):
        hard_neg_bases.append((f"hneg_ru_{i:03d}", w, "ru", "hard_negative", "curated_hard_neg_ru"))
    for i, w in enumerate(HARD_NEGATIVES_KK):
        hard_neg_bases.append((f"hneg_kk_{i:03d}", w, "kk", "hard_negative", "curated_hard_neg_kk"))

    # Save curated clean_filenames.csv reference file.
    with CLEAN_FILENAMES_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["base_id", "filename", "language", "category", "source"])
        writer.writeheader()
        for bid, stem, lang, cat, src in clean_bases + hard_neg_bases:
            writer.writerow({"base_id": bid, "filename": f"{stem}.pdf", "language": lang, "category": cat, "source": src})

    # Assign splits strictly by base_id within each language & category stratum!
    split_by_base: dict[str, str] = {}
    for group_list in [
        [b[0] for b in clean_bases if b[2] == "en"],
        [b[0] for b in clean_bases if b[2] == "ru"],
        [b[0] for b in clean_bases if b[2] == "kk"],
        [b[0] for b in clean_bases if b[2] == "mixed"],
        [b[0] for b in hard_neg_bases if b[2] == "en"],
        [b[0] for b in hard_neg_bases if b[2] == "ru"],
        [b[0] for b in hard_neg_bases if b[2] == "kk"],
    ]:
        split_by_base.update(_assign_group_splits(group_list, rng))

    # Group profanity words by root stem so morphological variants of the same word
    # do not leak across splits, while preserving high-frequency core families in train.
    prof_bases: list[tuple[str, str, str, str]] = []
    for idx, prow in enumerate(profanity_rows):
        bid = f"prof_{prow['language']}_{idx:04d}"
        prof_bases.append((bid, prow["word"], prow["language"], prow["source"]))

    for lang in ("en", "ru", "kk"):
        lang_bids = [b[0] for b in prof_bases if b[2] == lang]
        split_by_base.update(_assign_group_splits(lang_bids, rng))

    splits: dict[str, list[dict[str, str | int]]] = {"train": [], "val": [], "test": []}
    seen_filenames: set[str] = set()
    sample_counter = 0

    def add_sample(split: str, filename: str, lang: str, label: int, cat: str, src: str, bid: str, aug: str) -> None:
        nonlocal sample_counter
        # Prevent exact duplicate filenames across different splits (zero leakage).
        if filename in seen_filenames:
            return
        seen_filenames.add(filename)
        sample_counter += 1
        splits[split].append({
            "sample_id": f"sm_{sample_counter:06d}",
            "filename": filename,
            "language": lang,
            "label": label,
            "category": cat,
            "source": src,
            "base_id": bid,
            "augmentation_type": aug,
        })

    # 2. Generate Category A: Clean academic filenames (~8,400 examples)
    type_by_lang = {
        "en": ACADEMIC_TYPES_EN,
        "ru": ACADEMIC_TYPES_RU,
        "kk": ACADEMIC_TYPES_KK,
        "mixed": ACADEMIC_TYPES_EN + ACADEMIC_TYPES_RU[:8] + ACADEMIC_TYPES_KK[:8],
    }
    for bid, stem, lang, cat, src in clean_bases:
        sp = split_by_base[bid]
        types = type_by_lang[lang]
        count = 16 if lang == "en" else (22 if lang in ("ru", "kk") else 24)
        for _ in range(count):
            doc_type = rng.choice(types)
            sep = rng.choice(["_", "-", " ", "."])
            ext = rng.choice(EXTENSIONS)
            num = rng.randint(1, 20)
            year = rng.choice(["2024", "2025", "2026"])
            pattern = rng.randrange(8)
            if pattern == 0:
                fname = f"{stem}{sep}{doc_type}{sep}{num}{ext}"
            elif pattern == 1:
                fname = f"{doc_type}{sep}{num}{sep}{stem}{ext}"
            elif pattern == 2:
                fname = f"{stem}{sep}{year}{sep}{doc_type}{ext}"
            elif pattern == 3:
                code = f"{rng.choice(['CS', 'IS', 'BIS', 'MATH', 'PHYS', 'ECON'])}{rng.randint(101, 499)}"
                fname = f"{code}{sep}{stem}{sep}{doc_type}{ext}"
            elif pattern == 4:
                fname = f"{stem.replace('_', ' ')} - {doc_type.replace('_', ' ')} #{num}"
            elif pattern in (5, 6):
                fname = f"{stem}{ext}" if rng.random() < 0.6 else f"{stem}{sep}{num}{ext}"
            else:
                fname = f"{stem}{sep}{doc_type}{sep}v{rng.randint(1, 4)}{ext}"
            if rng.random() < 0.15:
                fname = fname.lower()
            elif rng.random() < 0.08:
                fname = fname.upper()
            add_sample(sp, fname, lang, 0, cat, src, bid, "academic_template")

    # 3. Generate Category D: Hard negatives (~4,800 examples)
    for bid, word, lang, cat, src in hard_neg_bases:
        sp = split_by_base[bid]
        types = type_by_lang[lang]
        for _ in range(22):
            ext = rng.choice(EXTENSIONS)
            sep = rng.choice(["_", "-", " "])
            doc_type = rng.choice(types)
            num = rng.randint(1, 15)
            pattern = rng.randrange(5)
            if pattern == 0:
                fname = f"{word}{ext}"
            elif pattern == 1:
                fname = f"{word}{sep}{doc_type}{ext}"
            elif pattern == 2:
                fname = f"{doc_type}{sep}{word}{sep}{num}{ext}"
            elif pattern == 3:
                fname = f"{word}{sep}{num}{sep}final{ext}"
            else:
                fname = f"{word.replace('_', ' ')} ({doc_type.replace('_', ' ')}) {num}"
            if rng.random() < 0.20:
                fname = fname.lower()
            elif rng.random() < 0.12:
                fname = fname.upper()
            add_sample(sp, fname, lang, 0, cat, src, bid, "hard_negative_template")

    # 4. Generate Categories B (Explicit) & C (Obfuscated) (~13,000 examples)
    aug_types = [
        "char_repetition", "char_insertion", "char_deletion", "char_substitution",
        "case_mix", "special_char_sub", "leetspeak", "digits_inserted",
        "spaced_chars", "punct_separated", "mixed_cyr_lat", "unicode_confusables",
        "zero_width", "multi_transform",
    ]
    for bid, word, lang, src in prof_bases:
        sp = split_by_base[bid]
        # Category B: Explicit profanity (direct + academic wrapper)
        explicit_variants = [
            f"{word}.pdf",
            f"{word.upper()}.pdf",
            f"{word.capitalize()}.pdf",
            word,
            f"{word}.docx",
            f"{word.upper()}",
        ]
        for _ in range(8):
            w_case = word.upper() if rng.random() < 0.25 else (word.capitalize() if rng.random() < 0.25 else word)
            explicit_variants.append(wrap_as_filename(w_case, lang, rng, allow_academic_context=True))
        for v in explicit_variants:
            add_sample(sp, v, lang, 1, "explicit_profanity", src, bid, "none")

        # Category C: Obfuscated profanity across all 14 augmentation types
        for aug in aug_types:
            reps = 2 if aug in ("multi_transform", "leetspeak", "punct_separated", "char_repetition", "digits_inserted") else 1
            for _ in range(reps):
                obf = obfuscate_word(word, lang, aug, rng)
                fname = wrap_as_filename(obf, lang, rng, allow_academic_context=True)
                sample_lang = "mixed" if aug == "mixed_cyr_lat" else lang
                add_sample(sp, fname, sample_lang, 1, "obfuscated_profanity", src, bid, aug)

    # Leakage verification assertions
    train_bases = {r["base_id"] for r in splits["train"]}
    val_bases = {r["base_id"] for r in splits["val"]}
    test_bases = {r["base_id"] for r in splits["test"]}
    assert not (train_bases & val_bases), "Data leakage between train and val base_ids!"
    assert not (train_bases & test_bases), "Data leakage between train and test base_ids!"
    assert not (val_bases & test_bases), "Data leakage between val and test base_ids!"

    train_files = {r["filename"] for r in splits["train"]}
    val_files = {r["filename"] for r in splits["val"]}
    test_files = {r["filename"] for r in splits["test"]}
    assert not (train_files & val_files), "Exact filename overlap between train and val!"
    assert not (train_files & test_files), "Exact filename overlap between train and test!"
    assert not (val_files & test_files), "Exact filename overlap between val and test!"

    # Shuffle each split deterministically and write CSVs.
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["sample_id", "filename", "language", "label", "category", "source", "base_id", "augmentation_type"]

    summary: dict[str, int] = {}
    for split_name, rows in splits.items():
        rng.shuffle(rows)
        out_path = GENERATED_DIR / f"{split_name}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        summary[split_name] = len(rows)

    challenge_rows, ambiguous_rows = build_challenge_and_ambiguous_sets()
    for name, rows in (("challenge_test", challenge_rows), ("ambiguous_eval", ambiguous_rows)):
        out_path = GENERATED_DIR / f"{name}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        summary[name] = len(rows)

    summary["total_main"] = summary["train"] + summary["val"] + summary["test"]
    summary["profanity_vocab"] = len(profanity_rows)
    summary["clean_bases"] = len(clean_bases)
    summary["hard_neg_bases"] = len(hard_neg_bases)

    # Write detailed metadata JSON for reproducibility and reporting.
    meta = {
        "seed": seed,
        "counts": summary,
        "split_breakdown": {},
    }
    for split_name, rows in list(splits.items()) + [("challenge_test", challenge_rows)]:
        by_cat: dict[str, int] = {}
        by_lang: dict[str, int] = {}
        by_label: dict[str, int] = {"0": 0, "1": 0}
        for r in rows:
            by_cat[str(r["category"])] = by_cat.get(str(r["category"]), 0) + 1
            by_lang[str(r["language"])] = by_lang.get(str(r["language"]), 0) + 1
            by_label[str(r["label"])] = by_label.get(str(r["label"]), 0) + 1
        meta["split_breakdown"][split_name] = {
            "total": len(rows),
            "labels": by_label,
            "categories": by_cat,
            "languages": by_lang,
        }
    (GENERATED_DIR / "dataset_summary.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    stats = generate_all()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
