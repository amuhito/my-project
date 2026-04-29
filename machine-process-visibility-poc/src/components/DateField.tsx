import { isDatePickerValue, normalizeDateInput } from "../utils/date";

export function DateField({
  value,
  onChange,
  label,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  disabled?: boolean;
}) {
  const control = (
    <div className="dateField">
      <input
        type="text"
        inputMode="numeric"
        placeholder="例: 0425 / 4/25"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onBlur={(event) => onChange(normalizeDateInput(event.target.value))}
      />
      <input
        className="datePicker"
        type="date"
        value={isDatePickerValue(value)}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-label={`${label ?? "日付"}をカレンダーから選択`}
      />
    </div>
  );
  return label ? <label>{label}{control}</label> : control;
}
