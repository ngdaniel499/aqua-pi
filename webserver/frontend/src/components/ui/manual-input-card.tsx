'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface Measurement {
  Time: string;
  [key: string]: string | number;
}

interface ProcessedMeasurement extends Omit<Measurement, 'Time'> {
  Time: number;
}

interface DataStructure {
  [station: string]: ProcessedMeasurement[];
}

const ManualInputCard: React.FC = () => {
  const [, setData] = useState<DataStructure>({});
  const [stationList, setStationList] = useState<string[]>([]);
  const [customVariableList, setCustomVariableList] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [customStation, setCustomStation] = useState('');
  const [customTime, setCustomTime] = useState('');
  const [customParam, setCustomParam] = useState('');
  const [customValue, setCustomValue] = useState('');
  const [newCustomVar, setNewCustomVar] = useState('');
  const [user, setUser] = useState('');
  const [showUser, setShowUser] = useState(true); 
  const allowedUsers = ['whalexadmin', 'X!@SJKD)'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/data');
        const jsonText = await response.text();
        const jsonData = JSON.parse(jsonText.replace(/NaN/g, 'null'));

        const processedData = Object.fromEntries(
          Object.entries(jsonData).map(([station, measurements]) => [
            station,
            (measurements as Measurement[]).map(measurement => ({
              ...measurement,
              Time: new Date(measurement.Time).getTime()
            }))
          ])
        );

        setData(processedData as DataStructure);
        setStationList(Object.keys(processedData));

        const availableVariables = ['TempCal', 'TempRaw', 'CDOMRaw', 'Nitrate', 'ChlRaw', 'ChlCal', 'ChlVolts'];

        const customVars = [
          ...new Set(
            Object.values(processedData).flatMap(list =>
              list.flatMap(entry =>
                Object.keys(entry).filter(key => !['Time', ...availableVariables].includes(key))
              )
            )
          )
        ];

        setCustomVariableList(customVars.sort());
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAddCustomVariable = () => {
    if (newCustomVar && !customVariableList.includes(newCustomVar)) {
      setCustomVariableList(prev => [...prev, newCustomVar]);
      setCustomParam(newCustomVar);
      setNewCustomVar('');
    }
  };

const handleSubmit = async () => {
  if (!customStation || !customTime || !customParam || !customValue || customParam === '__new__' || !user) {
    alert('All fields are required.');
    return;
  }

  if (!allowedUsers.includes(user.trim().toLowerCase())) {
    alert('Unauthorized user.');
    return;
  }

  const response = await fetch('/api/add-measurement', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      station: customStation,
      timestamp: customTime,
      parameter: customParam,
      value: parseFloat(customValue),
    }),
  });

  const result = await response.json();
  if (response.ok) {
    alert('Manual data point added!');
  } else {
    alert(`Error: ${result.error}`);
  }
};


  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-lg">Loading data...</p>
      </div>
    );
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Add Manual Measurement</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <select value={customStation} onChange={e => setCustomStation(e.target.value)} className="border rounded px-2 py-1 w-full">
          <option value="">Select Station</option>
          {stationList.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <Input type="datetime-local" value={customTime} onChange={e => setCustomTime(e.target.value)} />

        <select value={customParam} onChange={e => setCustomParam(e.target.value)} className="border rounded px-2 py-1 w-full">
          <option value="">Select Parameter</option>
          {customVariableList.map(param => (
            <option key={param} value={param}>{param}</option>
          ))}
          <option value="__new__">Add new variable</option>
        </select>

        {customParam === '__new__' && (
          <div className="flex gap-2">
            <Input placeholder="New Parameter Name" value={newCustomVar} onChange={e => setNewCustomVar(e.target.value)} />
            <Button onClick={handleAddCustomVariable}>Add</Button>
          </div>
        )}

        <Input placeholder="Value" value={customValue} onChange={e => setCustomValue(e.target.value)} />
        <div className="flex items-center gap-2">
            <Input
                type={showUser ? 'text' : 'password'}
                placeholder="User"
                value={user}
                onChange={e => setUser(e.target.value)}
                className="flex-grow"
            />
            <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowUser(prev => !prev)}
                >
                {showUser ? 'Hide' : 'Show'}
            </Button>
        </div>


        <Button onClick={handleSubmit}>Submit</Button>
      </CardContent>
    </Card>
  );
};

export default ManualInputCard;
