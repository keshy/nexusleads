# CLAUDE.md — Project Conventions for AI Assistants

## Dropdown / Select Theming

**NEVER use native HTML `<select>` elements.** They do not respect the dark theme and show white browser-default dropdowns.

Always use the `StyledSelect` component from `frontend/src/components/StyledSelect.tsx` instead.

```tsx
import StyledSelect from '../components/StyledSelect'

<StyledSelect
  value={value}
  onChange={(v) => setValue(v)}
  options={[{ value: 'a', label: 'Option A' }, { value: 'b', label: 'Option B' }]}
  placeholder="Select..."
  className="w-full py-2"   // optional: use for full-width form fields
/>
```

- For filter bars: omit `className` (uses default `min-w-[160px]`)
- For form fields in drawers/modals: pass `className="w-full py-2"`
- The component handles dark mode, outside-click-to-close, checkmark on selected item, and chevron animation automatically.

## Chat Sidecar

- Chat message bubbles must have `overflow-hidden` on the bubble container.
- The `.chat-markdown` CSS class must include `overflow-wrap: break-word` and `word-break: break-word` to prevent long strings from spilling out.

## General UI

- All UI must work in both light and dark mode. Always include `dark:` variants for backgrounds, borders, and text colors.
- Use the project's design system: `rounded-lg`, `border-gray-200 dark:border-gray-700`, `bg-white dark:bg-gray-800`, `shadow-xl` for floating menus.
- Custom dropdowns should open with `absolute z-30` positioning and include outside-click handlers via `useRef` + `useEffect`.
