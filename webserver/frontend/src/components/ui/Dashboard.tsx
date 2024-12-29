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
  ResponsiveContainer 
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
  [key: string]: string | number; // Allow for dynamic keys
}

// Define type for processed measurement with timestamp
interface ProcessedMeasurement extends Omit<Measurement, 'Time'> {
  Time: number;
}

// Define type for the data structure
interface DataStructure {
  [station: string]: ProcessedMeasurement[];
}

// Define type for combined data point
interface CombinedDataPoint {
  Time: number;
  [key: string]: number | null;
}

const availableVariables = [
  { id: 'Probe_TempCal', label: 'Temperature (Calibrated)' },
  { id: 'Condraw', label: 'Conductivity (Raw)' },
  { id: 'CondCal', label: 'Conductivity (Calibrated)' },
  { id: 'SpCond', label: 'Specific Conductivity' },
  { id: 'Salinity', label: 'Salinity' },
  { id: 'TurbRaw', label: 'Turbidity (Raw)' },
  { id: 'TurbCal', label: 'Turbidity (Calibrated)' },
  { id: 'ChlRaw', label: 'Chlorophyll (Raw)' },
  { id: 'ChlCal', label: 'Chlorophyll (Calibrated)' },
  { id: 'ChlAdj', label: 'Chlorophyll (Adjusted)' }
] as const;

const colors = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#ff0000',
  '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57'
];

const formatXAxis = (tickItem: number): string => {
  if (!tickItem) return '';
  const date = new Date(tickItem);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
        
        // Convert all Time strings to Date objects
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

  // Create a time-aligned dataset with all stations' data
  const combinedData = React.useMemo(() => {
    if (!selectedVariables.length || !selectedStations.length) return [];

    // Get all unique timestamps
    const allTimestamps = new Set<number>();
    selectedStations.forEach(station => {
      if (data[station]) {
        data[station].forEach(point => {
          allTimestamps.add(point.Time);
        });
      }
    });

    // Create aligned data points
    return Array.from(allTimestamps)
      .sort((a, b) => a - b)
      .map(timestamp => {
        const point: CombinedDataPoint = { Time: timestamp };
        selectedStations.forEach(station => {
          const stationData = data[station]?.find(d => d.Time === timestamp);
          if (stationData) {
            selectedVariables.forEach(variable => {
              point[`${station}`] = stationData[variable] as number;
            });
          }
        });
        return point;
      });
  }, [data, selectedStations, selectedVariables]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-lg">Loading data...</p>
      </div>
    );
  }

  const renderCharts = () => {
    return selectedVariables.map(variable => (
      <Card key={variable} className="w-full h-[400px] mb-6">
        <CardHeader>
          <CardTitle>
            {availableVariables.find(v => v.id === variable)?.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={combinedData}>
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
              />
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
                  dot={false}
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
          <CardTitle>AquaPi Water Quality Dashboard</CardTitle>
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