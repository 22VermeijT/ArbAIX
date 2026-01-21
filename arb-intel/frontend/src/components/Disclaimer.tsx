// Advisory disclaimer banner component

interface DisclaimerProps {
  className?: string;
}

export function Disclaimer({ className = '' }: DisclaimerProps) {
  return (
    <div className={`bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="text-yellow-500 text-xl">!</span>
        <div className="text-sm text-yellow-200">
          <p className="font-semibold mb-1">ADVISORY ONLY - NOT FINANCIAL ADVICE</p>
          <p className="text-yellow-300/80">
            This system provides information only. No bets are placed automatically.
            All betting decisions and executions must be made by you. Odds can change
            rapidly. Always verify current odds before placing any bets. Gamble responsibly.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Disclaimer;
