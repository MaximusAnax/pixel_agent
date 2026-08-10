# `compare_table`

## Purpose
Compare LibreOffice Calc spreadsheet content against a gold sheet using rule-driven checks (cells, ranges, structure).

## Inputs
Predicted and gold spreadsheet paths (via getters); options/rules from evaluator.expected.

## Matching rules
Aggregates per-rule sheet comparisons; typically returns a float score in [0, 1].

## Common pitfalls
Dense rule sets; small formatting/value drift fails; prefer reading expected rules in the task JSON.

## Pilot usage
- Tasks (8): 12382c62-0cd1-4bf2-bdc8-1d20bf9b2371, 1273e544-688f-496b-8d89-3e0f40aa0606, 1954cced-e748-45c4-9c26-9855b97fbc5e, 357ef137-7eeb-4c80-a3bb-0951f26a8aff, 42e0a640-4f19-4b28-973d-729602b5a4a7, 51719eea-10bc-4246-a428-ac7c433dd4b3, 535364ea-05bd-46ea-9937-9f55c68507e8, f9584479-3d0d-4c79-affa-9ad7afdd8850
- Metrics module: `table.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def compare_table(result: str, expected: str = None, **options) -> float:
    #  function compare_table {{{ #
    """
    Args:
        result (str): path to result xlsx
        expected (str): path to golden xlsx
        rules (List[Dict[str, Any]]): list of dict like
          {
            "type": str,
            <str as parameters>: anything
          }
          as sequential rules

    Returns:
        float: the score
    """

    if result is None:
        logger.error("Result file path is None")
        return 0.0

    # Check if result file exists
    if not os.path.exists(result):
        logger.error(f"Result file not found: {result}")
        return 0.0

    try:
        logger.info(f"Loading result file: {result}")
        xlworkbookr: Workbook = openpyxl.load_workbook(filename=result)
        pdworkbookr = pd.ExcelFile(result)
        logger.info(
            f"Successfully loaded result file with sheets: {pdworkbookr.sheet_names}"
        )
    except Exception as e:
        logger.error(f"Failed to load result file {result}: {e}")
        return 0.0
    worksheetr_names: List[str] = pdworkbookr.sheet_names

    if expected is not None:
        xlworkbooke: Workbook = openpyxl.load_workbook(filename=expected)
        pdworkbooke = pd.ExcelFile(expected)
        worksheete_names: List[str] = pdworkbooke.sheet_names
    else:
        xlworkbooke: Workbook = None
        pdworkbooke = None
        worksheete_names: List[str] = None

    parse_idx: Callable[[Union[str, int], BOOK, BOOK], Tuple[BOOK, str]] = (
        functools.partial(
            _parse_sheet_idx,
            result_sheet_names=worksheetr_names,
            expected_sheet_names=worksheete_names,
        )
    )

    passes = True
    for r in options["rules"]:
        if r["type"] == "sheet_name":
            #  Compare Sheet Names {{{ #
            metric: bool = worksheetr_names == worksheete_names
            logger.debug(
                "Assertion: %s.sheet_names == %s.sheet_names - %s",
                result,
                expected,
                metric,
            )
            #  }}} Compare Sheet Names #

        elif r["type"] == "sheet_data":
            #  Compare Sheet Data by Internal Value {{{ #
            # sheet_idx0: 0 == "RI0" == "RNSheet1" | "EI0" == "ENSheet1"
            # sheet_idx1: as sheet_idx0
            # precision: int as number of decimal digits, default to 4

            error_limit: int = r.get("precision", 4)
            sheet1: pd.DataFrame = _load_sheet(
                *parse_idx(r["sheet_idx0"], pdworkbookr, pdworkbooke)
            )
            if sheet1 is None:
                return 0.0
# ... truncated ...

```
