import React, {} from "react";
import { Box } from "@mui/material";

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
    padding?: number;
    noPadding?: boolean;
}
  

export default function TabPanel(props: TabPanelProps) {
    const { children, value, index, padding, noPadding, ...other } = props;

    let _box_padding = padding ? padding : 3;
    if (noPadding) {
        _box_padding = 0
    }

    return (
        <Box
            role="tabpanel"
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            style={{flex: 1, flexDirection: 'column', justifyContent: 'flex-start' }}
            sx={{display: value !== index ? 'none': 'flex' }}
            {...other}
        >
        {value === index && (
            <Box sx={{ p: _box_padding, flexGrow: 1, display:'flex', flexDirection: 'column', minHeight: 0 }}>
                {children}
            </Box>
        )}
        </Box>
    );
}

export function a11yProps(index: number) {
    return {
      id: `simple-tab-${index}`,
      'aria-controls': `simple-tabpanel-${index}`,
    };
  }
  
  