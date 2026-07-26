import { QueryProvider } from "@/app/providers/query_provider";
import { AppRouter } from "@/app/router/index";

export default function App() {
  return (
    <QueryProvider>
      <AppRouter />
    </QueryProvider>
  );
}
