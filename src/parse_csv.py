import pandas as pd

from sources import DATE_COLUMNS, NUMBER_COLUMNS

DELIMITER = ";"


def _is_mask(line):
    # a segunda linha do CSV e so tracos: --------;--------
    compact = line.replace(DELIMITER, "").strip()
    return bool(compact) and set(compact) <= {"-"}


def parse_csv(raw):
    # a Bronze guarda o arquivo inteiro. aqui eu só separo o que dá para ler
    null_bytes = raw.count(b"\x00")
    text = raw.decode("latin-1").replace("\x00", "")
    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV vazio")

    header = lines[0].split(DELIMITER)
    expected = len(header)
    start = 2 if len(lines) > 1 and _is_mask(lines[1]) else 1

    rows = []
    rejected = []
    for index, line in enumerate(lines[start:], start=start + 1):
        if not line.strip():
            rejected.append({"line_number": index, "reason": "linha_vazia", "raw_line": line})
            continue
        # ponto e vírgula solto no texto quebra a contagem. não invento coluna
        if line.count(DELIMITER) != expected - 1:
            rejected.append(
                {"line_number": index, "reason": "contagem_de_campos", "raw_line": line[:500]}
            )
            continue
        rows.append(line.split(DELIMITER))

    frame = pd.DataFrame(rows, columns=header)
    quarantine = pd.DataFrame(rejected, columns=["line_number", "reason", "raw_line"])
    info = {"null_bytes_removed": null_bytes, "columns": expected, "mask_skipped": start == 2}
    return frame, quarantine, info


def blank_to_null(frame):
    # vazio vira nulo. nulo não vira zero
    cleaned = frame.copy()
    for column in cleaned.columns:
        text = cleaned[column].astype("string").str.strip()
        cleaned[column] = text.mask(text == "", pd.NA)
    return cleaned


def parse_number(series):
    # neste recorte o decimal e ponto, como em 2.03.
    # se aparecer virgula, trato como decimal e tiro o ponto de milhar
    text = series.astype("string").str.strip()
    text = text.mask(text == "", pd.NA)
    has_comma = text.str.contains(",", na=False)
    normalized = text.where(
        ~has_comma,
        text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    number = pd.to_numeric(normalized, errors="coerce")
    invalid = int((text.notna() & number.isna()).sum())
    return number, invalid


def apply_types(table, frame):
    typed = blank_to_null(frame)
    metrics = {"invalid_dates": {}, "invalid_numbers": {}}
    for column in DATE_COLUMNS.get(table, []):
        if column not in typed.columns:
            continue
        original = typed[column]
        parsed = pd.to_datetime(original, errors="coerce")
        metrics["invalid_dates"][column] = int((original.notna() & parsed.isna()).sum())
        typed[column] = parsed
    for column in NUMBER_COLUMNS.get(table, []):
        if column not in typed.columns:
            continue
        parsed, invalid = parse_number(typed[column])
        typed[column] = parsed
        metrics["invalid_numbers"][column] = invalid
    return typed, metrics


def deduplicate(frame, primary_key):
    # duplicata igual sai. mesma chave com conteudo diferente: fica a primeira e eu conto
    metrics = {"null_keys": 0, "exact_duplicates": 0, "divergent_duplicates": 0}
    if not primary_key or any(column not in frame.columns for column in primary_key):
        return frame, metrics

    null_key = frame[primary_key].isna().any(axis=1)
    metrics["null_keys"] = int(null_key.sum())
    keyed = frame.loc[~null_key].copy()

    exact = keyed.duplicated(keep="first")
    metrics["exact_duplicates"] = int(exact.sum())
    keyed = keyed.loc[~exact]

    key_dup = keyed.duplicated(subset=primary_key, keep=False)
    metrics["divergent_duplicates"] = int(keyed.loc[key_dup, primary_key].drop_duplicates().shape[0])
    keyed = keyed.drop_duplicates(subset=primary_key, keep="first")
    return keyed, metrics
