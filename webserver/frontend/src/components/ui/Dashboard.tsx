'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
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

// Types
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

interface CombinedDataPoint {
  Time: number;
  [key: string]: number | null;
}

// Constants
const AVAILABLE_VARIABLES = [
  { id: 'TempCal', label: 'Temperature (degC)' },
  { id: 'TempRaw', label: 'Temperature Raw' },
  { id: 'CDOMRaw', label: 'CDOM Raw' },
  { id: 'Nitrate', label: 'Nitrate(µg/L)' },
  { id: 'ChlRaw', label: 'Chlorophyll Raw' },
  { id: 'ChlCal', label: 'Chlorophyll Calibrated (µg/L)' },
  { id: 'ChlVolts', label: 'Chlorophyll Voltage (V)' }
] as const;

const CHART_COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#ff0000', 
  '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57'
];

const HOURS_24_IN_MS = 24 * 60 * 60 * 1000;
const LIVE_UPDATE_INTERVAL = 10000; // 10 seconds
const INTERVAL_15_MIN_MS = 15 * 60 * 1000; // 15 minutes in milliseconds

// Utility functions
const formatXAxisLabel = (tickItem: number): string => {
  if (!tickItem) return '';
  const date = new Date(tickItem);
  return `${date.toLocaleDateString()}\n${date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })}`;
};

/*const generateHourlyTicks = (data: CombinedDataPoint[]): number[] => {
  if (data.length === 0) return [];
  
  const minTime = Math.min(...data.map(d => d.Time));
  const maxTime = Math.max(...data.map(d => d.Time));
  
  const ticks: number[] = [];
  const startHour = new Date(minTime);
  startHour.setMinutes(0, 0, 0); // Round down to the hour
  
  let currentTime = startHour.getTime();
  while (currentTime <= maxTime) {
    ticks.push(currentTime);
    currentTime += 60 * 60 * 1000; // Add 1 hour
  }
  
  return ticks;
};*/

const roundToNearestInterval = (timestamp: number, intervalMs: number): number => {
  return Math.round(timestamp / intervalMs) * intervalMs;
};

const formatReadableDateTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
};

const processRawData = (rawData: number): DataStructure => {
  return Object.fromEntries(
    Object.entries(rawData).map(([station, measurements]) => [
      station,
      (measurements as Measurement[]).map(measurement => ({
        ...measurement,
        Time: new Date(measurement.Time).getTime()
      }))
    ])
  );
};

const snapToIntervals = (stationData: ProcessedMeasurement[]): ProcessedMeasurement[] => {
  // Simply snap each data point to its nearest 15-minute interval
  return stationData.map(measurement => ({
    ...measurement,
    Time: roundToNearestInterval(measurement.Time, INTERVAL_15_MIN_MS)
  })).sort((a, b) => a.Time - b.Time);
};

const getCustomVariables = (data: DataStructure): string[] => {
  const defaultVariableIds = AVAILABLE_VARIABLES.map(v => v.id);
  return [
    ...new Set(
      Object.values(data).flatMap(stationData =>
        stationData.flatMap(entry =>
          Object.keys(entry).filter(key =>
            !['Time', ...defaultVariableIds].includes(key)
          )
        )
      )
    )
  ];
};

const getStationsWithRecentData = (data: DataStructure): string[] => {
  const cutoff = Date.now() - HOURS_24_IN_MS;
  return Object.keys(data).filter(station =>
    data[station]?.some(point => point.Time >= cutoff)
  );
};

// Main Component
const Dashboard: React.FC = () => {
  // State
  const [data, setData] = useState<DataStructure>({});
  const [selectedStations, setSelectedStations] = useState<string[]>([]);
  const [selectedVariables, setSelectedVariables] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'live' | 'detailed'>('detailed');

  // Computed values
  const customVariables = getCustomVariables(data);
  const availableStations = viewMode === 'live' 
    ? getStationsWithRecentData(data)
    : Object.keys(data);

  // Data fetching
  const fetchData = async () => {
    try {
      const response = await fetch('/api/data');
      const jsonText = await response.text();
      const jsonData = JSON.parse(jsonText.replace(/NaN/g, 'null'));
      const processedData = processRawData(jsonData);
      
      setData(processedData);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setIsLoading(false);
    }
  };

  // Effects
  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (viewMode === 'live') {
      interval = setInterval(fetchData, LIVE_UPDATE_INTERVAL);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [viewMode]);

  useEffect(() => {
    if (viewMode === 'live' && Object.keys(data).length > 0) {
      const recentStations = getStationsWithRecentData(data);
      setSelectedStations(prev =>
        prev.filter(station => recentStations.includes(station))
      );
    }
  }, [viewMode, data]);

  // Chart data processing with 15-minute interval snapping
  const getCombinedDataForVariable = (variable: string): CombinedDataPoint[] => {
    if (!selectedStations.length) return [];

    const timeFilter = viewMode === 'live' 
      ? (time: number) => time >= Date.now() - HOURS_24_IN_MS
      : () => true;

    // Snap each station's data points to 15-minute intervals
    const snappedStationData: { [station: string]: ProcessedMeasurement[] } = {};
    selectedStations.forEach(station => {
      if (data[station]) {
        const filteredData = data[station].filter(point => timeFilter(point.Time));
        snappedStationData[station] = snapToIntervals(filteredData);
      }
    });

    // Get all unique interval timestamps
    const allTimestamps = new Set<number>();
    Object.values(snappedStationData).forEach(stationData => {
      stationData.forEach(point => allTimestamps.add(point.Time));
    });

    return Array.from(allTimestamps)
      .sort((a, b) => a - b)
      .map(timestamp => {
        const point: CombinedDataPoint = { Time: timestamp };
        selectedStations.forEach(station => {
          // Get all data points for this station at this timestamp
          const stationPoints = snappedStationData[station]?.filter(d => d.Time === timestamp) || [];
          if (stationPoints.length > 0) {
            // If multiple points exist at same interval, use the first one (could also average)
            point[station] = stationPoints[0][variable] as number ?? null;
          } else {
            point[station] = null;
          }
        });
        return point;
      });
  };

  // Export functionality with original timestamps and interval snapping
  const exportSelectedData = () => {
    if (!selectedStations.length || !selectedVariables.length) {
      alert("Please select at least one station and one variable.");
      return;
    }

    // Headers for original data plus interval timestamp
    const headers = [
      'Original_DateTime',
      'Interval_Timestamp',
      ...selectedStations.flatMap(station =>
        selectedVariables.map(variable => `${station}.${variable}`)
      )
    ];

    // Collect all original data points
    const allDataPoints: Array<{
      originalTime: number;
      intervalTime: number;
      stationData: { [station: string]: ProcessedMeasurement | undefined };
    }> = [];
    
    selectedStations.forEach(station => {
      data[station]?.forEach(point => {
        const intervalTime = roundToNearestInterval(point.Time, INTERVAL_15_MIN_MS);
        allDataPoints.push({
          originalTime: point.Time,
          intervalTime: intervalTime,
          stationData: { [station]: point }
        });
      });
    });

    // Group by original timestamp to combine station data
    const groupedData = new Map<number, {
      originalTime: number;
      intervalTime: number;
      stationData: { [station: string]: ProcessedMeasurement | undefined };
    }>();

    allDataPoints.forEach(point => {
      const existing = groupedData.get(point.originalTime);
      if (existing) {
        Object.assign(existing.stationData, point.stationData);
      } else {
        groupedData.set(point.originalTime, point);
      }
    });

    const rows = [
      headers.join(','),
      ...Array.from(groupedData.values())
        .sort((a, b) => a.originalTime - b.originalTime)
        .map(dataPoint => {
          const row = [
            `"${formatReadableDateTime(dataPoint.originalTime)}"`, // Original readable datetime (quoted)
            `"${formatReadableDateTime(dataPoint.intervalTime)}"`, // Interval readable datetime (quoted)
          ];
          
          selectedStations.forEach(station => {
            selectedVariables.forEach(variable => {
              const stationPoint = dataPoint.stationData[station];
              const value = stationPoint?.[variable];
              // Handle numbers properly to avoid scientific notation
              if (typeof value === 'number') {
                row.push(value.toString());
              } else {
                row.push(value?.toString() ?? '');
              }
            });
          });
          
          return row.join(',');
        })
    ];

    const csvContent = rows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'export_15min_intervals.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Event handlers
  const handleStationToggle = (station: string, checked: boolean) => {
    setSelectedStations(prev =>
      checked ? [...prev, station] : prev.filter(s => s !== station)
    );
  };

  const handleVariableToggle = (variable: string, checked: boolean) => {
    setSelectedVariables(prev =>
      checked ? [...prev, variable] : prev.filter(v => v !== variable)
    );
  };

  const handleViewModeChange = (mode: 'live' | 'detailed') => {
    setViewMode(mode);
  };

  // Render helpers
  const renderStationCheckbox = (station: string) => (
    <div key={station} className="flex items-center space-x-2">
      <Checkbox
        id={`station-${station}`}
        checked={selectedStations.includes(station)}
        onCheckedChange={(checked) => handleStationToggle(station, !!checked)}
      />
      <label 
        htmlFor={`station-${station}`} 
        className="text-sm font-medium leading-none cursor-pointer"
      >
        {station}
      </label>
    </div>
  );

  const renderVariableCheckbox = (variable: { id: string; label: string }) => (
    <div key={variable.id} className="flex items-center space-x-2">
      <Checkbox
        id={`var-${variable.id}`}
        checked={selectedVariables.includes(variable.id)}
        onCheckedChange={(checked) => handleVariableToggle(variable.id, !!checked)}
      />
      <label 
        htmlFor={`var-${variable.id}`} 
        className="text-sm font-medium cursor-pointer"
      >
        {variable.label}
      </label>
    </div>
  );

  const renderCustomVariableCheckbox = (customVar: string) => (
    <div key={customVar} className="flex items-center space-x-2">
      <Checkbox
        id={`var-${customVar}`}
        checked={selectedVariables.includes(customVar)}
        onCheckedChange={(checked) => handleVariableToggle(customVar, !!checked)}
      />
      <label 
        htmlFor={`var-${customVar}`} 
        className="text-sm font-mono text-gray-700 cursor-pointer"
      >
        {customVar}
      </label>
    </div>
  );

  const renderChart = (variable: string) => {
    const chartData = getCombinedDataForVariable(variable);
    const variableLabel = AVAILABLE_VARIABLES.find(v => v.id === variable)?.label || variable;

    return (
      <Card key={variable} className="w-full h-[500px] mb-6">
        <CardHeader>
          <CardTitle>
            {variableLabel}
            <span className="ml-2 text-sm text-gray-500">
              — {viewMode === 'live' ? 'Past 24 Hours' : 'All Data'} (snapped to 15-min intervals)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="flex items-center justify-center h-[450px] text-sm text-gray-500">
              No data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={450}>
              <LineChart 
                data={chartData} 
                margin={{ top: 5, right: 30, left: 20, bottom: 70 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="Time"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  scale="time"
                  tickFormatter={formatXAxisLabel}
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval="preserveStartEnd"
                />
                {viewMode === 'detailed' && (
                  <Brush 
                    dataKey="Time" 
                    height={15} 
                    tickFormatter={() => ''} 
                    stroke="#8884d8" 
                  />
                )}
                <YAxis />
                <Tooltip labelFormatter={formatXAxisLabel} />
                <Legend />
                {selectedStations.map((station, index) => (
                  <Line
                    key={station}
                    type="monotone"
                    dataKey={station}
                    name={station}
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    dot={{ 
                      r: 2, 
                      fill: CHART_COLORS[index % CHART_COLORS.length], 
                      strokeWidth: 1 
                    }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-lg">Loading data...</p>
      </div>
    );
  }

  // Main render
  return (
    <div className="p-4 max-w-[1400px] mx-auto">
      {/* Header */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>AquaPi Dashboard</CardTitle>
          <p className="text-sm text-gray-600 mt-2">
            Data points are snapped to 15-minute intervals for cleaner visualization. Multiple data points within the same interval will both be plotted.
          </p>
          <div className="flex gap-2 mt-4">
            <Button
              variant={viewMode === 'live' ? 'default' : 'outline'}
              onClick={() => handleViewModeChange('live')}
            >
              Live View (Past 24h)
            </Button>
            <Button
              variant={viewMode === 'detailed' ? 'default' : 'outline'}
              onClick={() => handleViewModeChange('detailed')}
            >
              Detailed View (all data)
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Station Selection */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Select Stations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              {availableStations.map(renderStationCheckbox)}
            </div>
          </CardContent>
        </Card>

        {/* Default Variables */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Default Variables</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4">
              {AVAILABLE_VARIABLES.map(renderVariableCheckbox)}
            </div>
          </CardContent>
        </Card>

        {/* Custom Variables */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Custom Variables</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-2">
              {selectedStations.length > 0 && customVariables.length > 0 ? (
                customVariables
                  .filter(customVar => 
                    selectedStations.some(station =>
                      data[station]?.some(entry => 
                        Object.keys(entry).includes(customVar)
                      )
                    )
                  )
                  .sort()
                  .map(renderCustomVariableCheckbox)
              ) : (
                <p className="text-sm text-gray-500">
                  Select stations to see custom variables
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Export Button */}
      <Button 
        variant="outline" 
        onClick={exportSelectedData} 
        className="mb-4"
        disabled={!selectedStations.length || !selectedVariables.length}
      >
        Export CSV (15-min intervals)
      </Button>

      {/* Charts */}
      {selectedVariables.length > 0 ? (
        selectedVariables.map(renderChart)
      ) : (
        <Card className="w-full h-[200px]">
          <CardContent className="flex items-center justify-center h-full">
            <p className="text-gray-500">
              Select stations and variables to display charts
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;