package ai.supplychain;

// A tiny manual test runner that performs the same checks as the JUnit test.
// Use this when Gradle/junit isn't cooperating.

import java.util.List;

public class ManualTestRunner {
    public static void main(String[] args) {
        try {
            // Setup DB, warehouse, hospital - mirror the JUnit test
            SupplyChainAI.InventoryDatabase db = new SupplyChainAI.InventoryDatabase();

            SupplyChainAI.Facility w = new SupplyChainAI.Facility("W", SupplyChainAI.FacilityType.WAREHOUSE, "R");
            w.addInventory(new SupplyChainAI.InventoryItem(SupplyChainAI.Category.VENTILATOR, 5, 0.0, 1, 1));
            db.addFacility(w);

            SupplyChainAI.Facility h = new SupplyChainAI.Facility("H", SupplyChainAI.FacilityType.HOSPITAL, "R");
            h.icuCapacity = 10; h.icuOccupied = 10;
            h.addInventory(new SupplyChainAI.InventoryItem(SupplyChainAI.Category.VENTILATOR, 0, 0.5, 1, 1));
            db.addFacility(h);

            SupplyChainAI.Allocator alloc = new SupplyChainAI.Allocator(db);
            List<SupplyChainAI.AllocationRequest> reqs = List.of(
                new SupplyChainAI.AllocationRequest("H", SupplyChainAI.Category.VENTILATOR, 3)
            );

            var results = alloc.allocate(SupplyChainAI.Category.VENTILATOR, reqs, "W");

            if (results.size() != 1) throw new AssertionError("Expected 1 result but got " + results.size());
            if (results.get(0).allocated != 3) throw new AssertionError("Expected 3 allocated but got " + results.get(0).allocated);
            if (!"H".equals(results.get(0).facilityId)) throw new AssertionError("Expected facilityId H but got " + results.get(0).facilityId);

            System.out.println("ManualTestRunner: ALL TESTS PASSED ✅");
        } catch (Throwable t) {
            System.err.println("ManualTestRunner: TESTS FAILED ❌");
            t.printStackTrace();
            System.exit(2);
        }
    }
}
