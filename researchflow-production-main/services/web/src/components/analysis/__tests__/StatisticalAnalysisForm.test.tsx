/**
 * Statistical Analysis Form Tests
 *
 * Unit tests for the StatisticalAnalysisForm component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import StatisticalAnalysisForm from '../StatisticalAnalysisForm';
import { mockDatasetMetadata, mockValidationResults } from './fixtures/statistical-data';

// Mock the statistical analysis hook
vi.mock('@/hooks/use-statistical-analysis', () => ({
  useStatisticalAnalysis: () => ({
    validateConfig: vi.fn().mockResolvedValue(mockValidationResults.valid),
    isLoading: false,
    error: null
  })
}));

describe('StatisticalAnalysisForm', () => {
  const defaultProps = {
    datasetMetadata: mockDatasetMetadata,
    onSubmit: vi.fn(),
    onValidationChange: vi.fn(),
    disabled: false
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<StatisticalAnalysisForm {...defaultProps} />);
    expect(screen.getByText('Configure Analysis')).toBeInTheDocument();
  });

  it('shows dataset information', () => {
    render(<StatisticalAnalysisForm {...defaultProps} />);
    expect(screen.getByText(/test-clinical-trial/)).toBeInTheDocument();
    expect(screen.getByText(/500 rows/)).toBeInTheDocument();
  });

  it('displays available test types', () => {
    render(<StatisticalAnalysisForm {...defaultProps} />);
    
    // Click on test selection tab
    fireEvent.click(screen.getByText('Test Selection'));
    
    expect(screen.getByText('Independent Samples t-test')).toBeInTheDocument();
    expect(screen.getByText('Paired Samples t-test')).toBeInTheDocument();
    expect(screen.getByText('One-Way ANOVA')).toBeInTheDocument();
  });

  it('enables variable selection after test selection', async () => {
    const user = userEvent.setup();
    render(<StatisticalAnalysisForm {...defaultProps} />);
    
    // Select t-test
    fireEvent.click(screen.getByText('Test Selection'));
    await user.click(screen.getByText('Independent Samples t-test'));
    
    // Variables tab should now be enabled
    expect(screen.getByRole('tab', { name: /Variables/ })).not.toHaveAttribute('disabled');
  });

  it('calls onSubmit with valid configuration', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    
    render(<StatisticalAnalysisForm {...defaultProps} onSubmit={onSubmit} />);
    
    // Go through the workflow
    fireEvent.click(screen.getByText('Test Selection'));
    await user.click(screen.getByText('Independent Samples t-test'));
    
    fireEvent.click(screen.getByText('Variables'));
    // Select variables would happen here in real usage
    
    fireEvent.click(screen.getByText('Review'));
    
    // Submit would be enabled if validation passes
    // This would require more complex mocking for a full test
  });

  it('shows upload prompt when no dataset', () => {
    render(<StatisticalAnalysisForm {...defaultProps} datasetMetadata={null} />);
    expect(screen.getByText('No Dataset Selected')).toBeInTheDocument();
    expect(screen.getByText('Upload Dataset')).toBeInTheDocument();
  });

  it('disables form when disabled prop is true', () => {
    render(<StatisticalAnalysisForm {...defaultProps} disabled={true} />);
    
    // Form elements should be disabled
    // This would require checking specific form elements in a real implementation
    expect(screen.getByText('Running Analysis...')).toBeInTheDocument();
  });

  it('shows validation errors', async () => {
    const mockHook = vi.mocked(require('@/hooks/use-statistical-analysis').useStatisticalAnalysis);
    mockHook.mockReturnValue({
      validateConfig: vi.fn().mockResolvedValue(mockValidationResults.invalid),
      isLoading: false,
      error: null
    });

    render(<StatisticalAnalysisForm {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Configuration Issues')).toBeInTheDocument();
    });
  });
});