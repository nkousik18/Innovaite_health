package ai.supplychain;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.List;

public class AllocatorTest {

    @Test
    public void simpleAllocationTest() {
        // Note: InventoryDatabase, Allocator, AllocationRequest are nested inside SupplyChainAI
        SupplyChainAI.InventoryDatabase db = new SupplyChainAI.InventoryDatabase();

        // Create a warehouse with 5 ventilators
        SupplyChainAI.Facility w = new SupplyChainAI.Facility("W", SupplyChainAI.FacilityType.WAREHOUSE, "R");
        w.addInventory(new SupplyChainAI.InventoryItem(SupplyChainAI.Category.VENTILATOR, 5, 0.0, 1, 1));
        db.addFacility(w);

        // Create a hospital needing ventilators
        SupplyChainAI.Facility h = new SupplyChainAI.Facility("H", SupplyChainAI.FacilityType.HOSPITAL, "R");
        h.icuCapacity = 10; h.icuOccupied = 10;
        h.addInventory(new SupplyChainAI.InventoryItem(SupplyChainAI.Category.VENTILATOR, 0, 0.5, 1, 1));
        db.addFacility(h);

        SupplyChainAI.Allocator alloc = new SupplyChainAI.Allocator(db);

        List<SupplyChainAI.AllocationRequest> reqs = List.of(
            new SupplyChainAI.AllocationRequest("H", SupplyChainAI.Category.VENTILATOR, 3)
        );

        var results = alloc.allocate(SupplyChainAI.Category.VENTILATOR, reqs, "W");

        assertEquals(1, results.size(), "Should return exactly one allocation result");
        assertEquals(3, results.get(0).allocated, "Should allocate 3 ventilators to hospital H");
        assertEquals("H", results.get(0).facilityId);
    }
}
