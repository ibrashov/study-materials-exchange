"""Generate grouped synthetic examples, fit candidate models and export inference weights."""
import csv
import json
import random
import string

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.svm import LinearSVC

from ml_moderation.validator_v2 import ROOT, catalog, meaningful_features, relevance_features

COURSES = {
    "DB101": "Database Systems",
    "PROG101": "Introduction to Programming",
    "BIS101": "Basics of Information Systems",
}
LANGUAGES = ("en", "ru", "kk")
FORMATS = {
    "en": ("Worked examples: {}", "Practice with {}", "An introduction to {}",
           "How to use {}", "Exercises and solutions for {}", "Common errors in {}",
           "Design notes for {}", "A review of {}", "Study guide: {}", "Lab on {}"),
    "ru": ("Примеры: {}", "Практика: {}", "Введение: {}", "Как использовать {}",
           "Решения задач: {}", "Типичные ошибки: {}", "Проектирование: {}",
           "Обзор: {}", "Учебное пособие: {}", "Лабораторная работа: {}"),
    "kk": ("Мысалдар: {}", "Тәжірибе: {}", "Кіріспе: {}", "Қолдану жолдары: {}",
           "Есептердің шешімдері: {}", "Жиі кездесетін қателер: {}", "Жобалау: {}",
           "Шолу: {}", "Оқу құралы: {}", "Зертханалық жұмыс: {}"),
}
OTHER = (
    ("Hello", "Привет", "Сәлем"),
    ("Football highlights", "Обзор футбольного матча", "Футбол матчының шолуы"),
    ("Neural network architecture", "Архитектура нейросетей", "Нейрондық желі архитектурасы"),
    ("Organic chemistry", "Органическая химия", "Органикалық химия"),
    ("Weather forecast", "Прогноз погоды", "Ауа райы болжамы"),
    ("Music theory", "Теория музыки", "Музыка теориясы"),
    ("TCP/IP", "Компьютерные сети", "Компьютерлік желілер"),
    ("ReLU", "PyTorch", "x² + y²"),
    ("Cooking pasta recipe", "Рецепт пасты карбонара", "Тамақ дайындау рецепті"),
    ("Biology cell division", "Биология деление клетки", "Биология жасуша бөлінуі"),
    ("History of Rome", "История Древнего Рима", "Ежелгі Рим тарихы"),
    ("World literature essay", "Эссе по мировой литературе", "Әлем әдебиеті бойынша эссе"),
    ("Macroeconomics inflation report", "Макроэкономика и инфляция", "Макроэкономика және инфляция"),
    ("Linear algebra eigenvalues", "Линейная алгебра собственные значения", "Сызықтық алгебра матрицалар"),
    ("Quantum mechanics wave function", "Квантовая механика волновая функция", "Кванттық механика толқындық функция"),
    ("Travel guide to Paris", "Путеводитель по Парижу", "Парижге саяхат нұсқаулығы"),
    ("Movie review and cinema", "Рецензия на новый фильм", "Жаңа фильмге шолу"),
    ("Philosophy ethics seminar", "Философия и этика", "Философия және этика"),
    ("Art history renaissance", "История искусства эпохи Возрождения", "Өнер тарихы ренессанс"),
    ("Geography climate zones", "География климатические пояса", "География климаттық белдеулер"),
)


def generate():
    rng = random.Random(13)
    groups = [(code, i, aliases) for code, topics in catalog().items()
              for i, aliases in enumerate(topics)]
    academic = []
    for code in COURSES:
        domain = [group for group in groups if group[0] == code]
        rng.shuffle(domain)
        for i, group in enumerate(domain):
            academic.append((*group, ("test" if i == 0 else "validation" if i == 1 else "train")))
    meaning, relevance = [], []

    def add(title, lang, base, split, owners, meaningful, category):
        meaning.append(dict(sample_id=len(meaning), title=title, language=lang, base_id=base,
                            split=split, label=int(meaningful), category=category,
                            augmentation_type="template", source="synthetic"))
        for code, context in COURSES.items():
            relevance.append(dict(sample_id=len(relevance), title=title, language=lang,
                                  base_id=base, split=split, course_code=code, course_name=context,
                                  course_context=context, course_id="", label=int(code in owners),
                                  category=category, source="synthetic"))

    for code, index, aliases, split in academic:
        for lang in LANGUAGES:
            for alias in aliases:
                for template in FORMATS[lang]:
                    add(template.format(alias), lang, f"{code}-{index}", split, {code}, True, "academic")
        for alias in aliases:
            add(alias, "mixed", f"{code}-{index}", split, {code}, True, "short_term")
    for i, phrases in enumerate(OTHER):
        split = "test" if i in (0, 6) else "validation" if i == 1 else "train"
        for lang, phrase in zip(LANGUAGES, phrases):
            add(phrase, lang, f"other-{i}", split, set(), True, "off_topic")
            for template in FORMATS[lang]:
                add(template.format(phrase), lang, f"other-{i}", split, set(), True, "off_topic")
    seen_noise = set()
    alphabets = (string.ascii_lowercase, "фывапролджқңғүұө", string.digits, "!@#$%^&*",
                 "jklvbnфывақң0123")
    for i in range(900):
        alphabet = rng.choice(alphabets)
        title = "".join(rng.choices(alphabet, k=rng.randint(5, 24)))
        repeat = i % 5 == 0
        if repeat:
            title = title[0] * len(title)
        if title in seen_noise:
            continue
        seen_noise.add(title)
        add(title, "und", f"noise-{i}", rng.choices(("train", "validation", "test"), (70, 15, 15))[0],
            set(), False, "repeated" if repeat else "random")
    return meaning, relevance


def metrics(labels, predictions):
    p, r, f, _ = precision_recall_fscore_support(labels, predictions, average="binary", zero_division=0)
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    return dict(accuracy=accuracy_score(labels, predictions), precision=p, recall=r, f1=f,
                confusion_matrix=matrix.tolist(), false_positive_rate=float(fp / max(fp + tn, 1)),
                false_rejection_rate=float(fn / max(fn + tp, 1)))


def best_threshold(labels, scores):
    return max(np.linspace(.05, .95, 37),
               key=lambda t: (metrics(labels, scores >= t)["f1"], -abs(t - .5)))


def run(rows, features, name):
    y = np.array([r["label"] for r in rows])
    train, val, test = (np.array([r["split"] == s for r in rows])
                        for s in ("train", "validation", "test"))
    report = {"counts": dict(zip(("train", "validation", "test"), map(lambda a: int(a.sum()), (train, val, test))))}
    candidates = {"hybrid_logistic": LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced")}
    if name == "meaning":
        candidates["linear_svm"] = LinearSVC(class_weight="balanced")
    for label, classifier in candidates.items():
        classifier.fit(features[train], y[train])
        if hasattr(classifier, "predict_proba"):
            probs = classifier.predict_proba(features)[:, 1]
            threshold = best_threshold(y[val], probs[val])
            predictions = probs >= threshold
            weights = dict(coef=classifier.coef_[0], bias=classifier.intercept_[0], threshold=threshold)
        else:
            predictions = classifier.predict(features)
        report[label] = metrics(y[test], predictions[test])
        if label == "hybrid_logistic":
            report["languages"] = {}
            for lang in sorted({row["language"] for row in rows}):
                subset = test & np.array([row["language"] == lang for row in rows])
                if subset.any():
                    report["languages"][lang] = {"n": int(subset.sum()), **metrics(y[subset], predictions[subset])}
    if name == "relevance":
        for label, scores in (("keyword", features[:, 0]), ("concept_cosine", features[:, 2])):
            threshold = best_threshold(y[val], scores[val])
            report[label] = metrics(y[test], scores[test] >= threshold)
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        vectorizer.fit([row["title"] for row, use in zip(rows, train) if use] + list(COURSES.values()))
        titles = vectorizer.transform([row["title"] for row in rows])
        contexts = vectorizer.transform([row["course_context"] for row in rows])
        cosine = np.asarray(titles.multiply(contexts).sum(axis=1)).ravel()
        report["tfidf_cosine"] = metrics(y[test], cosine[test] >= best_threshold(y[val], cosine[val]))
        ablation = LogisticRegression(max_iter=1000, C=10, class_weight="balanced")
        lexical = features[:, [0, 1, 6]]
        ablation.fit(lexical[train], y[train])
        probs = ablation.predict_proba(lexical)[:, 1]
        report["lexical_ablation"] = metrics(y[test], probs[test] >= best_threshold(y[val], probs[val]))
    return report, {f"{name}_{key}": value for key, value in weights.items()}


def main():
    report_dir = ROOT / "reports/week13"
    report_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = ROOT / "datasets/generated/week13"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    meaning, relevance = generate()
    results, artifact = {}, {}
    for name, filename, rows, extractor in (
        ("meaning", "meaningfulness_dataset.csv", meaning, lambda r: meaningful_features(r["title"])),
        ("relevance", "course_title_relevance.csv", relevance,
         lambda r: relevance_features(r["title"], r["course_code"], r["course_context"])),
    ):
        with (dataset_dir / filename).open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        results[name], weights = run(rows, np.stack([extractor(row) for row in rows]), name)
        artifact.update(weights)
    path = ROOT / "models/title_validator_v2.npz"
    np.savez_compressed(path, **artifact)
    results["artifact_bytes"] = path.stat().st_size
    (report_dir / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
