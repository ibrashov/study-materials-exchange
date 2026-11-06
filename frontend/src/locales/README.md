# Module responsibility

Alibek owns translations and language switching.

`en.js` and `ru.js` hold every interface text under the same keys, and a test fails if a key is missing from either file. Components read text with `const { t } = useLanguage()`. Add new text to both dictionaries; do not write interface text directly in components.

The switcher is in the page header. The choice is saved in the browser only. Text sent by the server, such as material titles, category names and validation messages, is shown as received.
