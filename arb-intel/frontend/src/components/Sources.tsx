// Data sources status component

interface Source {
  name: string;
  id: string;
  type: string;
  description: string;
  markets: number;
  status: string;
  url: string;
}

interface SourcesProps {
  sources: Source[];
}

export function Sources({ sources }: SourcesProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'api_key_exhausted':
        return 'bg-yellow-500';
      case 'inactive':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Active';
      case 'api_key_exhausted':
        return 'API Key Exhausted';
      case 'inactive':
        return 'Inactive';
      default:
        return status;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Data Sources</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {sources.map((source) => (
          <a
            key={source.id}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-700 rounded-lg p-3 hover:bg-gray-600 transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-white text-sm">{source.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${getStatusColor(source.status)}`}
                title={getStatusText(source.status)}
              />
            </div>
            <div className="text-xs text-gray-400 mb-1">{source.type}</div>
            <div className="text-lg font-bold text-white">{source.markets}</div>
            <div className="text-xs text-gray-500">markets</div>
            {source.status !== 'active' && (
              <div className="text-xs text-yellow-400 mt-1">
                {getStatusText(source.status)}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
