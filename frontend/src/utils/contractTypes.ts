export const CONTRACT_TYPE_OPTIONS = [
  { value: 'fixed_cost', label: 'Fixed Cost', shortLabel: 'Fixed' },
  { value: 'time_and_materials', label: 'Time and Materials', shortLabel: 'T&M' },
] as const;

export type ContractTypeValue = (typeof CONTRACT_TYPE_OPTIONS)[number]['value'];

export function getContractTypeShortLabel(contractType: ContractTypeValue): string {
  const contractTypeOption = CONTRACT_TYPE_OPTIONS.find((option) => option.value === contractType);
  return contractTypeOption?.shortLabel ?? contractType;
}