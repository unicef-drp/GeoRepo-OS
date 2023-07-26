import React, {useEffect, useState} from 'react';

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';

import { SummaryInterface } from '../../models/upload';

function FieldMapping(props: any) {
    return (
      <div>
        {
          props.fieldMapping.map((value: string, index: number) => (
            <div key={index}>{value}</div>
          ))
        }
      </div>
    )
}

interface FieldMappingSummaryInterface {
    summaries: SummaryInterface[]
}

export default function FieldMappingSummary(props: FieldMappingSummaryInterface) {
    const headerCells = [
        'Level',
        'File name',
        'Feature Count',
        'Field Mapping',
    ]

    return (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                {
                  headerCells.map((headerCell, index) => (
                    <TableCell key={index}>{headerCell}</TableCell>
                  ))
                }
              </TableRow>
            </TableHead>
            <TableBody>
              {props.summaries ? props.summaries.map((summary, index) => (
                <TableRow key={index}>
                  <TableCell>{summary.level}</TableCell>
                  <TableCell>{summary.file_name}</TableCell>
                  <TableCell>{summary.feature_count}</TableCell>
                  <TableCell>
                    <div>
                      <pre><FieldMapping fieldMapping={summary.field_mapping}/></pre>
                    </div>
                  </TableCell>
                </TableRow>
              )) : ''}
            </TableBody>
          </Table>
        </TableContainer>
    )
}

