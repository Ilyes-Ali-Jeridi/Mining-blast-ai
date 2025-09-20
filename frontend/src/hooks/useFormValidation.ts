import { useState, useEffect, useCallback } from 'react';
import { FormValidationState, ValidationError } from '../types';
import { createValidator } from '../utils/validation';

export interface UseFormValidationOptions {
  validateOnChange?: boolean;
  debounceMs?: number;
}

export const useFormValidation = (
  validationFn: (validator: any, data: any) => boolean,
  data: any,
  options: UseFormValidationOptions = {}
) => {
  const { validateOnChange = true, debounceMs = 300 } = options;
  
  const [validationState, setValidationState] = useState<FormValidationState>({
    isValid: false,
    errors: [],
    warnings: []
  });
  
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [fieldWarnings, setFieldWarnings] = useState<Record<string, string>>({});

  const validate = useCallback(() => {
    const validator = createValidator();
    const isValid = validationFn(validator, data);
    const state = validator.getState();
    
    // Convert errors to field-keyed objects
    const errorMap: Record<string, string> = {};
    const warningMap: Record<string, string> = {};
    
    state.errors.forEach(error => {
      errorMap[error.field] = error.message;
    });
    
    state.warnings.forEach(warning => {
      warningMap[warning.field] = warning.message;
    });
    
    setValidationState(state);
    setFieldErrors(errorMap);
    setFieldWarnings(warningMap);
    
    return state;
  }, [validationFn, data]);

  // Debounced validation on data change
  useEffect(() => {
    if (!validateOnChange) return;
    
    const timeoutId = setTimeout(() => {
      validate();
    }, debounceMs);
    
    return () => clearTimeout(timeoutId);
  }, [data, validate, validateOnChange, debounceMs]);

  const getFieldError = useCallback((field: string): string | undefined => {
    return fieldErrors[field];
  }, [fieldErrors]);

  const getFieldWarning = useCallback((field: string): string | undefined => {
    return fieldWarnings[field];
  }, [fieldWarnings]);

  const hasFieldError = useCallback((field: string): boolean => {
    return !!fieldErrors[field];
  }, [fieldErrors]);

  const hasFieldWarning = useCallback((field: string): boolean => {
    return !!fieldWarnings[field];
  }, [fieldWarnings]);

  return {
    validationState,
    fieldErrors,
    fieldWarnings,
    validate,
    getFieldError,
    getFieldWarning,
    hasFieldError,
    hasFieldWarning,
    isValid: validationState.isValid,
    hasErrors: validationState.errors.length > 0,
    hasWarnings: validationState.warnings.length > 0
  };
};