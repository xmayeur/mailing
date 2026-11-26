# Quickstart: Database Merge Fields (`011-database-merge-fields`)

## Automated checks

```bash
# from repo root
pytest tests/unit/test_sendmail_core.py -q               # format_message contract (C1, C4)
pytest tests/unit/test_sendmail_sending.py -q            # batch mode: 1 vs ≥2 addressees (C2)
pytest tests/unit/test_editor.py -q                      # editor picker + insert marker (C3)
pytest tests/integration/test_sendmail_integration.py -q # end-to-end batch semantics with donotsend
```

## Manual verification (5 minutes)

1. **Insert** — run the editor (`python3 src/editor.py`, or your usual launch command) with a profile whose subscriber database has headers such as `ID,FIRSTNAME,EMAIL`.
   - Click the "Insert field" control → pick `ID`.
   - Expected: the text `${ID}` appears at the cursor in the message editor; picker lists exactly the database headers.
2. **Persist** — save/switch profile and come back. Expected: `${ID}` still in the message; picker shows the new profile's fields.
3. **One-recipient send** — send (or dry-run) a mailing with one recipient whose `ID` is `42`.
   - Expected: outgoing body *and* subject contain `42` where the markers were.
4. **Multi-recipient message** — configure `max_addr_per_mail` ≥ 2 and send to a small list.
   - Expected: markers replaced by blank in the single message; no recipient's value appears.
5. **Robustness** — type `${TYPO}` (nonexistent field) and a lone `${` in the message.
   - Expected after send: `${TYPO}` → blank; the lone `${` → still literal `${`.
