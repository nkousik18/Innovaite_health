package ai.supplychain;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Minimal prototype for MODULE 2: Intelligent Supply Chain Management.
 * - Inventory tracking
 * - Simple demand forecasting (moving average / exponential smoothing stub)
 * - Greedy allocation optimizer with priority scoring
 * - Procurement trigger
 *
 * This is a simulation/prototype — replace forecasting / routing / procurement connectors with real implementations.
 */
public class SupplyChainAI {

    // --- domain enums & types ------------------------------------------------

    enum FacilityType { HOSPITAL, WAREHOUSE, SUPPLIER }

    enum Category {
        VENTILATOR,
        N95_MASK,
        SURGICAL_MASK,
        GOWN,
        SANITIZER,
        ANTIVIRAL,
        PCR_TEST
        // extend per your list
    }

    static class InventoryItem {
        final Category category;
        int quantity;
        double burnRatePerDay; // estimated consumption per day at the facility
        int reorderPoint;      // trigger to reorder
        int leadTimeDays;      // supplier lead time in days

        InventoryItem(Category category, int quantity, double burnRatePerDay, int reorderPoint, int leadTimeDays) {
            this.category = category;
            this.quantity = quantity;
            this.burnRatePerDay = burnRatePerDay;
            this.reorderPoint = reorderPoint;
            this.leadTimeDays = leadTimeDays;
        }

        double daysOfSupply() {
            if (burnRatePerDay <= 0) return Double.POSITIVE_INFINITY;
            return quantity / burnRatePerDay;
        }

        @Override public String toString() {
            return String.format("%s: qty=%d, burn/day=%.2f, days=%.1f, reorder=%d, lead=%d",
                    category, quantity, burnRatePerDay, daysOfSupply(), reorderPoint, leadTimeDays);
        }
    }

    static class Facility {
        final String id;
        final FacilityType type;
        final String region;
        final Map<Category, InventoryItem> inventory = new HashMap<>();
        // capacity metrics (e.g., ICU beds)
        int icuCapacity;
        int icuOccupied;

        Facility(String id, FacilityType type, String region) {
            this.id = id;
            this.type = type;
            this.region = region;
        }

        void addInventory(InventoryItem item) {
            inventory.put(item.category, item);
        }

        InventoryItem getItem(Category c) {
            return inventory.get(c);
        }

        double icuOccupancyPct() {
            if (icuCapacity == 0) return 0;
            return 100.0 * icuOccupied / icuCapacity;
        }

        @Override public String toString() {
            return String.format("%s (%s) region=%s ICU:%d/%d (%.0f%%)",
                    id, type, region, icuOccupied, icuCapacity, icuOccupancyPct());
        }
    }

    // --- inventory database (simple in-memory) -------------------------------

    static class InventoryDatabase {
        final Map<String, Facility> facilities = new HashMap<>();

        void addFacility(Facility f) { facilities.put(f.id, f); }
        Facility getFacility(String id) { return facilities.get(id); }
        List<Facility> listByType(FacilityType t) {
            return facilities.values().stream().filter(f -> f.type == t).collect(Collectors.toList());
        }
    }

    // --- Forecasting engine (stub / replaceable) -----------------------------
    static class Forecast {
        final Map<Category, Double> forecastedDailyConsumption; // per category

        Forecast(Map<Category, Double> map) { this.forecastedDailyConsumption = map; }
    }

    interface ForecastEngine {
        Forecast forecastDailyConsumption(Facility facility, int horizonDays, Map<String, Object> outbreakSignals);
    }

    static class SimpleHeuristicForecast implements ForecastEngine {
        @Override
        public Forecast forecastDailyConsumption(Facility facility, int horizonDays, Map<String, Object> outbreakSignals) {
            double outbreakFactor = 1.0;
            if (outbreakSignals != null && outbreakSignals.containsKey("growthRate")) {
                double growth = ((Number) outbreakSignals.get("growthRate")).doubleValue();
                outbreakFactor += Math.max(0, growth) * Math.min(1.0, horizonDays / 7.0);
            }

            Map<Category, Double> out = new HashMap<>();
            for (InventoryItem item : facility.inventory.values()) {
                double predicted = item.burnRatePerDay * outbreakFactor;
                out.put(item.category, predicted);
            }
            return new Forecast(out);
        }
    }

    // --- Allocation types ----------------------------------------------------

    static class AllocationRequest {
        final String facilityId;
        final Category category;
        final int requested;
        AllocationRequest(String facilityId, Category category, int requested) {
            this.facilityId = facilityId; this.category = category; this.requested = requested;
        }
    }

    static class AllocationResult {
        final String facilityId;
        final Category category;
        final int allocated;
        final String reason;
        AllocationResult(String facilityId, Category category, int allocated, String reason) {
            this.facilityId = facilityId; this.category = category; this.allocated = allocated; this.reason = reason;
        }
        public String toString() {
            return String.format("Facility=%s category=%s allocated=%d reason=%s", facilityId, category, allocated, reason);
        }
    }

    static class Allocator {
        final InventoryDatabase db;
        Allocator(InventoryDatabase db) { this.db = db; }

        double priorityScore(Facility f, Category c, int projectedNeedNext24h) {
            InventoryItem it = f.getItem(c);
            double occupancy = f.icuOccupancyPct() / 100.0;
            double daysSupply = (it == null) ? Double.POSITIVE_INFINITY : it.daysOfSupply();
            double shortage = (it == null) ? projectedNeedNext24h : Math.max(0, projectedNeedNext24h - it.quantity);
            double score = occupancy * 6.0 + (shortage > 0 ? 3.0 : 0.0) + (daysSupply < 3.0 ? 2.0 : 0.0);
            if (daysSupply <= 1.0) score += 1.5;
            return score;
        }

        List<AllocationResult> allocate(Category category, List<AllocationRequest> requests, String warehouseId) {
            Facility warehouse = db.getFacility(warehouseId);
            if (warehouse == null) throw new IllegalArgumentException("warehouse not found");
            InventoryItem whItem = warehouse.getItem(category);
            int totalAvailable = (whItem == null) ? 0 : whItem.quantity;

            List<Map.Entry<AllocationRequest, Double>> scored = new ArrayList<>();
            for (AllocationRequest req : requests) {
                Facility f = db.getFacility(req.facilityId);
                int projectedNeed24h = req.requested;
                double score = priorityScore(f, category, projectedNeed24h);
                scored.add(Map.entry(req, score));
            }
            scored.sort((a,b) -> Double.compare(b.getValue(), a.getValue()));

            List<AllocationResult> results = new ArrayList<>();
            for (var entry : scored) {
                AllocationRequest req = entry.getKey();
                Facility f = db.getFacility(req.facilityId);
                InventoryItem it = f.getItem(category);
                int needed = Math.max(0, req.requested);
                if (needed == 0) {
                    results.add(new AllocationResult(req.facilityId, category, 0, "No need requested"));
                    continue;
                }
                if (totalAvailable <= 0) {
                    results.add(new AllocationResult(req.facilityId, category, 0, "Warehouse out of stock"));
                    continue;
                }

                int allocate = Math.min(needed, totalAvailable);
                totalAvailable -= allocate;
                if (whItem != null) whItem.quantity -= allocate;
                if (it == null) {
                    f.addInventory(new InventoryItem(category, allocate, 0.0, 0, 0));
                } else {
                    it.quantity += allocate;
                }

                String reason = String.format("PriorityScore=%.2f (allocated to prevent ICU collapse / shortage)", entry.getValue());
                results.add(new AllocationResult(req.facilityId, category, allocate, reason));
            }
            return results;
        }
    }

    // --- Procurement manager -------------------------------------------------
    static class ProcurementManager {
        final InventoryDatabase db;
        ProcurementManager(InventoryDatabase db) { this.db = db; }

        List<String> scanAndTriggerOrders(int horizonDays, ForecastEngine forecastEngine) {
            List<String> orders = new ArrayList<>();
            for (Facility f : db.facilities.values()) {
                for (InventoryItem it : f.inventory.values()) {
                    boolean belowReorder = it.quantity <= it.reorderPoint;
                    Forecast fc = forecastEngine.forecastDailyConsumption(f, it.leadTimeDays, Map.of());
                    double projectedDaily = fc.forecastedDailyConsumption.getOrDefault(it.category, it.burnRatePerDay);
                    double projectedConsumption = projectedDaily * it.leadTimeDays;
                    boolean willRunOut = it.quantity - projectedConsumption <= 0;
                    if (belowReorder || willRunOut) {
                        String order = String.format("ORDER: facility=%s cat=%s qty=%d leadDays=%d reason=%s",
                                f.id, it.category, Math.max(it.reorderPoint*2, (int)Math.ceil(projectedConsumption - it.quantity + it.reorderPoint)),
                                it.leadTimeDays,
                                (belowReorder ? "below reorder" : "projected runout"));
                        orders.add(order);
                    }
                }
            }
            return orders;
        }
    }

    // --- Route optimizer stub ------------------------------------------------
    static class RouteOptimizer {
        double estimateHours(String fromRegion, String toRegion, boolean useAir) {
            if (fromRegion.equals(toRegion)) return 1.0;
            if (useAir) return 6.0;
            return 24.0;
        }
    }

    // --- Example runner ------------------------------------------------------
    public void setupExampleAndRun() {
        InventoryDatabase db = new InventoryDatabase();

        Facility hospitalA = new Facility("HospitalA", FacilityType.HOSPITAL, "Region1");
        hospitalA.icuCapacity = 20; hospitalA.icuOccupied = 19;
        hospitalA.addInventory(new InventoryItem(Category.VENTILATOR, 15, 1.0, 3, 5));
        db.addFacility(hospitalA);

        Facility hospitalB = new Facility("HospitalB", FacilityType.HOSPITAL, "Region1");
        hospitalB.icuCapacity = 20; hospitalB.icuOccupied = 12;
        hospitalB.addInventory(new InventoryItem(Category.VENTILATOR, 18, 0.2, 3, 5));
        db.addFacility(hospitalB);

        Facility hospitalC = new Facility("HospitalC", FacilityType.HOSPITAL, "Region2");
        hospitalC.icuCapacity = 40; hospitalC.icuOccupied = 34;
        hospitalC.addInventory(new InventoryItem(Category.VENTILATOR, 30, 1.8, 5, 3));
        db.addFacility(hospitalC);

        Facility warehouse = new Facility("RegionalWarehouse", FacilityType.WAREHOUSE, "Region1");
        warehouse.addInventory(new InventoryItem(Category.VENTILATOR, 15, 0.0, 5, 7));
        db.addFacility(warehouse);

        System.out.println("INITIAL STATE:");
        db.facilities.values().forEach(f -> {
            System.out.println(f);
            f.inventory.values().forEach(it -> System.out.println("  " + it));
        });
        System.out.println();

        List<AllocationRequest> requests = List.of(
                new AllocationRequest("HospitalA", Category.VENTILATOR, 8),
                new AllocationRequest("HospitalB", Category.VENTILATOR, 2),
                new AllocationRequest("HospitalC", Category.VENTILATOR, 12)
        );

        Allocator allocator = new Allocator(db);
        System.out.println("ALLOCATING available ventilators from RegionalWarehouse...");
        List<AllocationResult> results = allocator.allocate(Category.VENTILATOR, requests, "RegionalWarehouse");
        results.forEach(r -> System.out.println("  " + r));
        System.out.println();

        System.out.println("POST-ALLOCATION STATE:");
        db.facilities.values().forEach(f -> {
            System.out.println(f);
            f.inventory.values().forEach(it -> System.out.println("  " + it));
        });
        System.out.println();

        ProcurementManager pm = new ProcurementManager(db);
        ForecastEngine fe = new SimpleHeuristicForecast();
        List<String> orders = pm.scanAndTriggerOrders(7, fe);
        System.out.println("PROCUREMENT ORDERS TRIGGERED:");
        orders.forEach(o -> System.out.println("  " + o));

        RouteOptimizer routeOpt = new RouteOptimizer();
        double etaHours = routeOpt.estimateHours(warehouse.region, hospitalC.region, false);
        System.out.println("\nEstimated transport time (warehouse -> HospitalC) hours: " + etaHours);

        Map<String, Object> outbreakSignals = Map.of("growthRate", 0.5);
        Forecast fA = fe.forecastDailyConsumption(hospitalA, 7, outbreakSignals);
        System.out.println("\nForecasted daily consumption at HospitalA (7-day horizon, outbreak factor):");
        fA.forecastedDailyConsumption.forEach((cat,val) -> System.out.println("  "+cat+" -> "+String.format("%.2f/day", val)));
    }

    // convenience main if you want to run this class directly
    public static void main(String[] args) {
        SupplyChainAI ai = new SupplyChainAI();
        ai.setupExampleAndRun();
    }
}
