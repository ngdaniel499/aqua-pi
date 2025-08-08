'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
//import { Input } from '@/components/ui/input';

interface Measurement {
  Time: number;
  [key: string]: string | number | null;
}

interface DataStructure {
  [station: string]: Measurement[];
}

const LiveGraphCard: React.FC = () => {
  const [data, setData] = useState<DataStructure>({});
  const [selectedStation, setSelectedStation] = useState('');
  const [selectedVariable, setSelectedVariable] = useState('');
  const [availableVariables, setAvailableVariables] = useState<string[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      const res = await fetch('/api/data');
      const text = await res.text();
      const json = JSON.parse(text.replace(/NaN/g, 'null'));

      const processed = Object.fromEntries(
        Object.entries(json).map(([station, list]) => [
          station,
          (list as Measurement[]).map(m => ({
            ...m,
            Time: new Date(m.Time).getTime(),
          }))
        ])
      );

      setData(processed as DataStructure);
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedStation && data[selectedStation]) {
      const allVars = new Set<string>();
      data[selectedStation].forEach(entry => {
        Object.keys(entry).forEach(k => {
          if (k !== 'Time') allVars.add(k);
        });
      });
      setAvailableVariables(Array.from(allVars).sort());
    }
  }, [selectedStation, data]);

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const todayStart = startOfToday.getTime();

  const graphData = selectedStation && selectedVariable
    ? data[selectedStation]?.filter(entry =>
        entry.Time >= todayStart && typeof entry[selectedVariable] === 'number'
      ).map(entry => ({
        Time: entry.Time,
        value: entry[selectedVariable],
      })) ?? []
    : [];

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Live View</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-4">
          <select
            value={selectedStation}
            onChange={e => {
              setSelectedStation(e.target.value);
              setSelectedVariable('');
            }}
            className="border px-2 py-1 rounded w-1/2"
          >
            <option value="">Select Station</option>
            {Object.keys(data).sort().map(st => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>

          <select
            value={selectedVariable}
            onChange={e => setSelectedVariable(e.target.value)}
            className="border px-2 py-1 rounded w-1/2"
            disabled={!selectedStation}
          >
            <option value="">Select Variable</option>
            {availableVariables.map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        {selectedStation && selectedVariable && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={graphData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="Time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={time => new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              />
              <YAxis />
              <Tooltip labelFormatter={time => new Date(time).toLocaleTimeString()} />
              <Line type="monotone" dataKey="value" stroke="#8884d8" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
};

export default LiveGraphCard;
