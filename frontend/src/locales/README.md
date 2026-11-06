# Module responsibility

Alibek owns translations. messages.js holds every interface text in English and Russian under the same keys, and a test fails if a key is missing or a Russian value is left untranslated. App.jsx selects the language, saves the choice in the browser and passes t to pages.

Text from the server, such as titles, category names and validation messages, is shown as received. Kazakh remains future work. Personal owner review is pending.
