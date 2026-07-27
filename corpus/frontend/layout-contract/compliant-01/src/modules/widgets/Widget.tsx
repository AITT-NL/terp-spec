import { HubCard, HubPage } from "@terpjs/react-core";
export function Widget() {
  return (
    <HubPage title="Notes">
      <HubCard title="All notes" to="/notes" />
    </HubPage>
  );
}
