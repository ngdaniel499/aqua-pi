import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  ResponsiveContainer,
  Brush 
} from 'recharts';

// Define types for the measurement data
interface Measurement {
  Time: string;
  Probe_TempCal: number;
  Condraw: number;
  CondCal: number;
  SpCond: number;
  Salinity: number;
  TurbRaw: number;
  TurbCal: number;
  ChlRaw: number;
  ChlCal: number;
  ChlAdj: number;
  ChlVolts: number;
  [key: string]: string | number;
}

interface ProcessedMeasurement extends Omit<Measurement, 'Time'> {
  Time: number;
}

interface DataStructure {
  [station: string]: ProcessedMeasurement[];
}

interface CombinedDataPoint {
  Time: number;
  [key: string]: number | null;
}

const availableVariables = [
  //{ id: 'Probe_TempCal', label: 'Temperature (Calibrated)' },
  //{ id: 'Condraw', label: 'Conductivity (Raw)' },
  //{ id: 'CondCal', label: 'Conductivity (Calibrated)' },
  //{ id: 'SpCond', label: 'Specific Conductivity' },
  //{ id: 'Salinity', label: 'Salinity' },
  //{ id: 'TurbRaw', label: 'Turbidity Raw' },
 // { id: 'TurbCal', label: 'Turbidity (Calibrated)' },
  { id: 'ChlRaw', label: 'Chlorophyll Raw' },
  { id: 'ChlCal', label: 'Chlorophyll Calibrated (µg/L)' },
  //{ id: 'ChlAdj', label: 'Chlorophyll Adjusted (µg/L)' },
  { id: 'ChlVolts', label: 'Chlorophyll Voltage (V)' }
] as const;

const colors = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#ff0000',
  '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57'
];

const formatXAxis = (tickItem: number): string => {
  if (!tickItem) return '';
  const date = new Date(tickItem);
  return date.toLocaleDateString() + '\n' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DataStructure>({});
  const [selectedStations, setSelectedStations] = useState<string[]>([]);
  const [selectedVariables, setSelectedVariables] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/data');
        const jsonData: { [key: string]: Measurement[] } = await response.json();
        
        const processedData = Object.fromEntries(
          Object.entries(jsonData).map(([station, measurements]) => [
            station,
            measurements.map(measurement => ({
              ...measurement,
              Time: new Date(measurement.Time).getTime()
            }))
          ])
        );
        
        setData(processedData as DataStructure);
        setIsLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Create separate combined datasets for each variable
  const getCombinedDataForVariable = (variable: string) => {
    if (!selectedStations.length) return [];

    const allTimestamps = new Set<number>();
    selectedStations.forEach(station => {
      if (data[station]) {
        data[station].forEach(point => {
          allTimestamps.add(point.Time);
        });
      }
    });

    return Array.from(allTimestamps)
      .sort((a, b) => a - b)
      .map(timestamp => {
        const point: CombinedDataPoint = { Time: timestamp };
        selectedStations.forEach(station => {
          const stationData = data[station]?.find(d => d.Time === timestamp);
          if (stationData) {
            point[`${station}`] = stationData[variable] as number;
          } else {
            point[`${station}`] = null;
          }
        });
        return point;
      });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-lg">Loading data...</p>
      </div>
    );
  }

  const renderCharts = () => {
    return selectedVariables.map(variable => (
      <Card key={variable} className="w-full h-[500px] mb-6">
        <CardHeader>
          <CardTitle>
            {availableVariables.find(v => v.id === variable)?.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={450}>
            <LineChart data={getCombinedDataForVariable(variable)} margin={{ top: 5, right: 30, left: 20, bottom: 70 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="Time"
                type="number"
                domain={['dataMin', 'dataMax']}
                scale="time"
                tickFormatter={formatXAxis}
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={100}
                interval="preserveStartEnd"
                
              />
              <Brush dataKey="Time" height={15} tickFormatter={() => ''} stroke="#8884d8" />
              <YAxis />
              <Tooltip 
                labelFormatter={formatXAxis}
              />
              <Legend />
              {selectedStations.map((station, index) => (
                <Line
                  key={station}
                  type="monotone"
                  dataKey={station}
                  name={station}
                  stroke={colors[index % colors.length]}
                  dot={{ r: 1, fill: colors[index % colors.length], strokeWidth: 1 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    ));
  };

  return (
    <div className="p-4 max-w-[1400px] mx-auto">
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>AquaPi Dashboard</CardTitle>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Select Stations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              {Object.keys(data).map(station => (
                <div key={station} className="flex items-center space-x-2">
                  <Checkbox
                    id={`station-${station}`}
                    checked={selectedStations.includes(station)}
                    onCheckedChange={(checked) => {
                      setSelectedStations(prev => 
                        checked 
                          ? [...prev, station]
                          : prev.filter(s => s !== station)
                      );
                    }}
                  />
                  <label htmlFor={`station-${station}`} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    {station}
                  </label>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Select Variables</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              {availableVariables.map(variable => (
                <div key={variable.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`var-${variable.id}`}
                    checked={selectedVariables.includes(variable.id)}
                    onCheckedChange={(checked) => {
                      setSelectedVariables(prev => 
                        checked 
                          ? [...prev, variable.id]
                          : prev.filter(v => v !== variable.id)
                      );
                    }}
                  />
                  <label htmlFor={`var-${variable.id}`} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                    {variable.label}
                  </label>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {renderCharts()}
    </div>
  );
};

export default Dashboard;