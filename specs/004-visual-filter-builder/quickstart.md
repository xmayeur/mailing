# Quickstart: Visual Filter Builder

**Target Audience**: Newsletter managers and non-technical users  
**How to Use**: This explains how to build filters visually in the Send Mailing dialog

---

## What's New?

The **Send Mailing** dialog now has a visual **Filter** editor. Instead of writing YAML syntax, you can build filters by selecting fields and operators from dropdown menus.

Before this feature:
```yaml
email: is not empty
status: is active
region: contains USA
```

Now with visual editor:
1. Click **"Visual Editor"** tab
2. Click **"Add Row"** button
3. Select field: **email**
4. Select operator: **Is not empty**
5. Click **"Add Row"** again for next condition

The YAML is generated automatically.

---

## Opening the Send Mailing Dialog

1. In the newsletter editor, go to **File** → **Send Email** (or use toolbar button)
2. The **Send Mailing** dialog opens
3. Fill in required fields (Subject, Message, Database, etc.)
4. Scroll down to **Filter** section

---

## Using the Visual Filter Editor

### The Two Views

The **Filter** section has two tabs:

#### Visual Editor Tab (Default)

A table with columns:
- **Field** — Column name from your subscriber database
- **Operator** — Comparison type (equals, contains, greater than, etc.)
- **Value** — The value to compare against (optional for some operators)

Buttons:
- **Add Row** — Add a new filter condition
- **Delete** (on each row) — Remove that condition

#### YAML Tab

The raw YAML representation of your filter. Edit here directly if you prefer, or let the visual editor generate it for you.

Both tabs stay in sync automatically — edit one, the other updates.

---

## Step-by-Step Example

**Goal**: Send to active subscribers in the USA region with non-empty email addresses.

### Using Visual Editor

1. Click **Visual Editor** tab (if not already there)
2. Row 1: Add filter for active status
   - Click **Add Row**
   - **Field** dropdown: Select **status**
   - **Operator** dropdown: Select **Is equal to**
   - **Value** field: Type `active`
3. Row 2: Add filter for region
   - Click **Add Row**
   - **Field** dropdown: Select **region**
   - **Operator** dropdown: Select **Contains**
   - **Value** field: Type `USA`
4. Row 3: Add filter for non-empty email
   - Click **Add Row**
   - **Field** dropdown: Select **email**
   - **Operator** dropdown: Select **Is not empty**
   - Value field: Empty (not shown for this operator)

**Result**: Filter table shows 3 rows. YAML tab shows:
```yaml
status: is equal to active
region: contains USA
email: is not empty
```

### Preview

Below the filter section, you'll see **Matching Records: N**, showing how many subscribers match your filter. This updates automatically as you edit.

---

## Operators Explained

### Field Operators

#### Equality Operators
- **Is equal to** — Field value matches exactly (text or number)
- **Is not equal to** — Field value differs from specified value

#### Text Operators
- **Contains** — Field includes the text you enter
- **Does not contain** — Field does not include the text
- **Starts with** — Field begins with the text
- **Ends with** — Field ends with the text
- **Matches regex** — Field matches a regular expression pattern

#### Numeric Operators
- **Greater than** — Field value is larger than specified number
- **Less than** — Field value is smaller than specified number
- **Greater or equal** — Field value is ≥ specified number
- **Less or equal** — Field value is ≤ specified number

#### Empty Checks
- **Is empty** — Field has no value
- **Is not empty** — Field has a value

#### List Operators
- **In list** — Field value appears in comma-separated list (e.g., `active, pending, approved`)
- **Not in list** — Field value does not appear in list

---

## Available Fields

The **Field** dropdown shows all column names from your subscriber database. 

**How it works**:
1. You select a database file (CSV or Google Sheets) in the **Database** field
2. The visual editor reads column headers from that file
3. Those column names appear in the **Field** dropdown

If no database is selected, the **Field** dropdown is empty. Load a database first.

---

## Tips & Best Practices

### Multiple Conditions

Each row is a condition. All conditions must match for a subscriber to be included.

Example:
```
status: is equal to active
region: contains USA
```
This sends to subscribers who are **both** active **and** in USA regions. Subscribers who are active but in other regions are excluded.

### Editing Rows

To edit a row, click the field or operator dropdown and select a new value. Changes apply immediately.

To delete a row, click **Delete** on that row.

### YAML Mode

If you're familiar with YAML syntax, click the **YAML** tab to edit directly. Example:
```yaml
email: is not empty
status: is equal to active
region: contains USA
```

Changes in YAML mode sync back to visual mode automatically.

### Testing Filters

Use **Test** checkbox (in Flags section) to send test emails to admin addresses instead of actual subscribers. This lets you verify your filter works before sending to everyone.

---

## Common Issues & Troubleshooting

### "Matching Records: 0"

If no records match:
1. Check that database file is loaded (Database field should show file path)
2. Verify filter conditions are correct (compare to known data)
3. Try removing conditions one-by-one to see which is too restrictive
4. Check for typos in values (spaces, capitalization, etc.)

**Example Fix**: 
- If you filter for `status: is equal to Active` but your data has `active` (lowercase), nothing matches. Change operator to case-insensitive or fix the value.

### "Field not found" Error

If filter shows an error about missing fields:
1. Your filter references a field that doesn't exist in the database
2. This can happen if you:
   - Changed database files (new file has different columns)
   - Edited YAML directly with a typo
3. **Fix**: Delete that row from visual editor, or fix the field name in YAML

### Operator Doesn't Appear in Dropdown

Not all operators apply to all fields. For example, numeric operators (greater than) won't show for text fields.

If you need a specific operator:
1. Try switching to the **YAML** tab and typing it manually (advanced users)
2. Check that you've selected the correct field (wrong field type may hide the operator)

---

## Configuration & Persistence

Filters are saved with your **Profile** configuration in `config.yml`.

When you:
1. **Switch profiles** — Your filter for the previous profile is saved, new profile's filter is loaded
2. **Close and reopen** the Send Mailing dialog — Your last filter is restored

If you want to reuse a filter:
1. Build it once in the visual editor
2. Switch profiles and come back — your filter is remembered

---

## What Gets Sent?

When you click **Send**, the filter is applied. Only subscribers matching **all** filter conditions receive the email.

The newsletter editor shows:
- **Matching Records: N** — Number of subscribers who will receive the email
- **From index** / **To index** — If you want to send to a subset (e.g., records 100-200)

Example:
- Database has 1,000 subscribers
- Your filter matches 250
- **Matching Records** shows **250**
- If you set From index=0, To index=249, all 250 matching subscribers get the email

---

## Advanced: Regular Expressions

For power users, the **Matches regex** operator supports regular expressions.

Examples:
- `.*@example\.com` — Email addresses from example.com domain
- `^(active|pending)$` — Status field contains exactly "active" or "pending"
- `\d{5}` — 5-digit postal codes

Regex syntax: Standard Python/JavaScript regex patterns.

---

## Next Steps

1. **Try it out**: Build a simple filter with one condition, see **Matching Records** update
2. **Add more conditions**: Combine multiple fields
3. **Switch between tabs**: See visual editor and YAML stay in sync
4. **Send**: Once satisfied with the filter, click **Send** to email matching subscribers

Questions? Check the main sendMail documentation or contact support.
