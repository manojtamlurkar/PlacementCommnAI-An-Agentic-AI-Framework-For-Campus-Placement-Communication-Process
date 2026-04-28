import { useEffect, useState } from "react";
import { Button } from "../../../shared/components/Button";

export interface CompanyFormValues {
  company_name: string;
  email: string;
  priority: string;
  poc_name: string;
  poc_phone: string;
  poc_email: string;
  location: string;
  address: string;
}

const emptyValues: CompanyFormValues = {
  company_name: "",
  email: "",
  priority: "",
  poc_name: "",
  poc_phone: "",
  poc_email: "",
  location: "",
  address: "",
};

interface CompanyFormProps {
  initialValues?: CompanyFormValues;
  submitLabel: string;
  onSubmit: (values: CompanyFormValues) => Promise<void>;
  onCancel?: () => void;
}

export function CompanyForm({
  initialValues,
  submitLabel,
  onSubmit,
  onCancel,
}: CompanyFormProps) {
  const [values, setValues] = useState<CompanyFormValues>(initialValues ?? emptyValues);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setValues(initialValues ?? emptyValues);
  }, [initialValues]);

  const update = (key: keyof CompanyFormValues, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  return (
    <form
      className="stack"
      onSubmit={async (event) => {
        event.preventDefault();
        setSubmitting(true);
        try {
          await onSubmit(values);
          if (!initialValues) {
            setValues(emptyValues);
          }
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <div className="field-grid">
        <div className="field">
          <label htmlFor="company_name">Company name</label>
          <input
            id="company_name"
            value={values.company_name}
            onChange={(event) => update("company_name", event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="company_email">Primary HR email</label>
          <input
            id="company_email"
            type="email"
            value={values.email}
            onChange={(event) => update("email", event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="company_priority">Priority</label>
          <input
            id="company_priority"
            value={values.priority}
            onChange={(event) => update("priority", event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="company_location">Location</label>
          <input
            id="company_location"
            value={values.location}
            onChange={(event) => update("location", event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="poc_name">POC name</label>
          <input
            id="poc_name"
            value={values.poc_name}
            onChange={(event) => update("poc_name", event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="poc_email">POC email</label>
          <input
            id="poc_email"
            type="email"
            value={values.poc_email}
            onChange={(event) => update("poc_email", event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="poc_phone">POC phone</label>
          <input
            id="poc_phone"
            value={values.poc_phone}
            onChange={(event) => update("poc_phone", event.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="company_address">Address</label>
        <textarea
          id="company_address"
          value={values.address}
          onChange={(event) => update("address", event.target.value)}
        />
      </div>
      <div className="panel__actions">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}
