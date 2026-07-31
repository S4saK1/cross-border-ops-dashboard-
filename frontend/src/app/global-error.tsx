'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center max-w-md">
            <h1 className="text-2xl font-bold text-red-600 mb-4">系统错误</h1>
            <p className="text-gray-600 mb-6">{error.message || '发生未知系统错误'}</p>
            <button onClick={reset}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
              重试
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
