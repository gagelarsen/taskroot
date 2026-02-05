import { Box, TextField, MenuItem, IconButton, Paper } from '@mui/material';
import { ArrowUpward, ArrowDownward } from '@mui/icons-material';

interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  orderBy?: string;
  orderDir?: 'asc' | 'desc';
  onOrderByChange?: (value: string) => void;
  onOrderDirChange?: (value: 'asc' | 'desc') => void;
  orderByOptions?: { value: string; label: string }[];
  children?: React.ReactNode;
}

export function FilterBar({
  searchValue = '',
  onSearchChange,
  orderBy = '',
  orderDir = 'asc',
  onOrderByChange,
  onOrderDirChange,
  orderByOptions = [],
  children,
}: FilterBarProps) {
  const toggleOrderDir = () => {
    onOrderDirChange?.(orderDir === 'asc' ? 'desc' : 'asc');
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        {onSearchChange && (
          <TextField
            label="Search"
            variant="outlined"
            size="small"
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            sx={{ minWidth: 200, flexGrow: 1 }}
          />
        )}

        {children}

        {orderByOptions.length > 0 && onOrderByChange && (
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              select
              label="Order By"
              variant="outlined"
              size="small"
              value={orderBy}
              onChange={(e) => onOrderByChange(e.target.value)}
              sx={{ minWidth: 150 }}
            >
              {orderByOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <IconButton onClick={toggleOrderDir} size="small" color="primary">
              {orderDir === 'asc' ? <ArrowUpward /> : <ArrowDownward />}
            </IconButton>
          </Box>
        )}
      </Box>
    </Paper>
  );
}

